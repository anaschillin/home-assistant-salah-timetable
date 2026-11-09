"""Atomic per-mosque persistence for approved and staged timetable sources."""

from asyncio import Lock
from dataclasses import replace
from datetime import date, tzinfo
from types import MappingProxyType
from typing import Any, Mapping

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util.json import load_json

from ..const import DOMAIN, STORAGE_VERSION
from ..domain.model import DailyPrayers, PrayerField, Timetable
from ..parsers.import_model import ImportCandidate
from ..sources.source_model import RemoteSource, validate_check
from .storage_records import (
    ImportReviewBaseline,
    PendingImportError as PendingImportError,
    RamadanApprovalError as RamadanApprovalError,
    ReviewChangedError as ReviewChangedError,
    StagedImport,
    _Snapshot,
)
from .storage_review import StorageReviewMixin


class _TimetableStore(Store[dict]):
    """Validate the old schema before HA writes a migration over its source."""

    def __init__(self, owner: "TimetableStorage", entry_id: str) -> None:
        self._owner = owner
        super().__init__(
            owner._hass,
            STORAGE_VERSION,
            f"{DOMAIN}.{entry_id}",
            private=True,
            atomic_writes=True,
            serialize_in_event_loop=False,
        )

    async def _async_migrate_func(
        self, old_major_version: int, old_minor_version: int, old_data: dict
    ) -> dict:
        if old_major_version not in {1, 2}:
            raise ValueError("Unsupported timetable storage version")
        payload = {
            "timetables": old_data["timetables"],
            "approved_sources": old_data["approved_sources"]
            if old_major_version == 2
            else {},
            "staged": old_data["staged"] if old_major_version == 2 else None,
            "remote_sources": {},
            "remote_checks": {},
        }

        def migrate():
            return self._owner._decode(payload).as_dict()

        return await self.hass.async_add_executor_job(migrate)


class TimetableStorage(StorageReviewMixin):
    """Promote changes only after validating and confirming their disk write."""

    def __init__(self, hass: HomeAssistant, entry_id: str, zone: tzinfo) -> None:
        self._hass = hass
        self._entry_id = entry_id
        # Config-entry reloads can leave an older options flow awaiting parsing
        # while a new runtime opens this entry's store. Serialize both instances.
        locks = hass.data.setdefault(f"{DOMAIN}_storage_locks", {})
        self._lock = locks.setdefault(entry_id, Lock())
        self._zone = zone
        self._store = _TimetableStore(self, entry_id)
        self._snapshot = _Snapshot((), MappingProxyType({}), None)

    @property
    def timetables(self) -> tuple[Timetable, ...]:
        return self._snapshot.timetables

    @property
    def approved_sources(self) -> Mapping[str, ImportCandidate]:
        return self._snapshot.approved_sources

    def review_baseline(self, timetable_id: str) -> ImportReviewBaseline:
        """Capture one source from the current immutable snapshot, without I/O."""
        return ImportReviewBaseline(
            next(
                (
                    table
                    for table in self.timetables
                    if table.timetable_id == timetable_id
                ),
                None,
            ),
            self.approved_sources.get(timetable_id),
        )

    @property
    def staged(self) -> StagedImport | None:
        return self._snapshot.staged

    @property
    def remote_sources(self) -> Mapping[str, RemoteSource]:
        return self._snapshot.remote_sources

    @property
    def remote_checks(self) -> Mapping[str, Mapping[str, Any]]:
        return self._snapshot.remote_checks

    def _validate(self, tables: tuple[Timetable, ...]) -> None:
        if len({table.timetable_id for table in tables}) != len(tables):
            raise ValueError("Duplicate timetable ID")
        annual_dates: set[date] = set()
        for table in tables:
            for row in table.days:
                for field in PrayerField:
                    row.timestamps(field, self._zone)
                if table.kind == "annual":
                    if row.day in annual_dates:
                        raise ValueError("Overlapping annual timetables")
                    annual_dates.add(row.day)

    @staticmethod
    def _replacement_tables(
        tables: tuple[Timetable, ...], candidate: ImportCandidate
    ) -> tuple[Timetable, ...]:
        timetable = candidate.timetable
        existing = next(
            (table for table in tables if table.timetable_id == timetable.timetable_id),
            None,
        )
        if existing and existing.kind != timetable.kind:
            raise ValueError("An import cannot change an existing timetable's kind")
        return tuple(
            table for table in tables if table.timetable_id != timetable.timetable_id
        ) + (timetable,)

    def _validate_snapshot(self, snapshot: _Snapshot) -> None:
        self._validate(snapshot.timetables)
        approved_tables = {table.timetable_id: table for table in snapshot.timetables}
        for key, candidate in snapshot.approved_sources.items():
            if (
                key != candidate.timetable.timetable_id
                or approved_tables.get(key) != candidate.timetable
            ):
                raise ValueError("Approved provenance does not match active timetable")
        if set(snapshot.remote_checks) - set(snapshot.remote_sources):
            raise ValueError("Source checks require a configured remote source")
        for key, source in snapshot.remote_sources.items():
            if key != source.source_id:
                raise ValueError("Remote source identity does not match its key")
        for check in snapshot.remote_checks.values():
            validate_check(check)
        if snapshot.staged:
            self._validate(
                self._replacement_tables(snapshot.timetables, snapshot.staged.candidate)
            )

    def _decode(self, data: dict) -> _Snapshot:
        if not isinstance(data, dict):
            raise ValueError("Invalid timetable storage structure")
        table_data = data["timetables"]
        if not isinstance(table_data, list):
            raise ValueError("Stored timetables must be a list")
        try:
            tables = tuple(Timetable.from_dict(item) for item in table_data)
        except AttributeError as err:
            raise ValueError("Invalid stored timetable structure") from err
        # Decode tables first so malformed legacy data is diagnosed without ever
        # being migrated or replaced by an empty snapshot.
        self._validate(tables)
        sources = data["approved_sources"]
        staged_data = data["staged"]
        if not isinstance(sources, dict) or (
            staged_data is not None and not isinstance(staged_data, dict)
        ):
            raise ValueError("Invalid import storage structure")
        approved = {
            key: ImportCandidate.from_dict(value) for key, value in sources.items()
        }
        staged = (
            StagedImport.from_dict(staged_data) if staged_data is not None else None
        )
        raw_sources = data["remote_sources"]
        raw_checks = data["remote_checks"]
        if not isinstance(raw_sources, dict) or not isinstance(raw_checks, dict):
            raise ValueError("Invalid remote source storage structure")
        remote_sources = {
            key: RemoteSource.from_dict(value) for key, value in raw_sources.items()
        }
        remote_checks = {
            key: validate_check(value) for key, value in raw_checks.items()
        }
        snapshot = _Snapshot(
            tables,
            MappingProxyType(approved),
            staged,
            MappingProxyType(remote_sources),
            MappingProxyType(remote_checks),
        )
        self._validate_snapshot(snapshot)
        return snapshot

    async def _async_refresh_snapshot(self) -> None:
        """Read current disk state while the shared entry lock is held."""
        data = await self._store.async_load()
        if data is None:
            self._snapshot = _Snapshot((), MappingProxyType({}), None)
            return
        snapshot = await self._hass.async_add_executor_job(self._decode, data)
        # HA logs a failed migration write rather than raising. Confirm both
        # the schema version and payload before treating migration as done.
        await self._async_verify_written(data)
        self._snapshot = snapshot

    async def async_load(self) -> None:
        async with self._lock:
            await self._async_refresh_snapshot()

    async def _async_verify_written(self, payload: dict) -> None:
        written = await self._hass.async_add_executor_job(load_json, self._store.path)
        if (
            not isinstance(written, dict)
            or written.get("version") != STORAGE_VERSION
            or written.get("data") != payload
        ):
            raise OSError("Timetable persistence could not be confirmed")

    async def _async_persist(self, snapshot: _Snapshot) -> None:
        """Must be called with the lock held; state changes only at the end."""
        await self._hass.async_add_executor_job(self._validate_snapshot, snapshot)
        payload = await self._hass.async_add_executor_job(snapshot.as_dict)
        await self._store.async_save(payload)
        await self._async_verify_written(payload)
        self._snapshot = snapshot

    async def async_replace(self, tables: tuple[Timetable, ...]) -> None:
        """Internal replacement API retained for legacy callers and tests."""
        async with self._lock:
            await self._async_refresh_snapshot()
            tables = tuple(tables)
            by_id = {table.timetable_id: table for table in tables}
            approved = {
                key: candidate
                for key, candidate in self.approved_sources.items()
                if by_id.get(key) == candidate.timetable
            }
            await self._async_persist(
                replace(
                    self._snapshot,
                    timetables=tables,
                    approved_sources=MappingProxyType(approved),
                )
            )

    def for_date(self, day: date) -> DailyPrayers | None:
        """Legacy annual-only lookup; effective Ramadan dates use resolve_day."""
        return next(
            (
                row
                for table in self.timetables
                if table.kind == "annual"
                for row in table.days
                if row.day == day
            ),
            None,
        )

    async def async_remove(self) -> None:
        async with self._lock:
            await self._store.async_remove()
            self._snapshot = _Snapshot((), MappingProxyType({}), None)
