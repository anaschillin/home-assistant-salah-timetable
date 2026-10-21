"""Atomic per-mosque persistence for approved and staged timetable sources."""

from asyncio import Lock
from dataclasses import dataclass
from datetime import date
from types import MappingProxyType
from typing import Mapping
from uuid import uuid4
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util.json import load_json

from .const import DOMAIN, STORAGE_VERSION
from .import_model import ImportCandidate
from .model import DailyPrayers, PrayerField, Timetable


class PendingImportError(ValueError):
    """A proposal must be reviewed before another can be staged."""


@dataclass(frozen=True)
class StagedImport:
    """A durable proposal; its identity prevents stale previews being approved."""

    stage_id: str
    candidate: ImportCandidate

    def as_dict(self) -> dict:
        return {"stage_id": self.stage_id, "candidate": self.candidate.as_dict()}

    @classmethod
    def from_dict(cls, data: dict) -> "StagedImport":
        stage_id = data["stage_id"]
        if (
            not isinstance(stage_id, str)
            or len(stage_id) != 32
            or any(char not in "0123456789abcdef" for char in stage_id)
        ):
            raise ValueError("Invalid staged import identity")
        return cls(stage_id, ImportCandidate.from_dict(data["candidate"]))


@dataclass(frozen=True)
class _Snapshot:
    timetables: tuple[Timetable, ...]
    approved_sources: Mapping[str, ImportCandidate]
    staged: StagedImport | None

    def as_dict(self) -> dict:
        return {
            "timetables": [table.as_dict() for table in self.timetables],
            "approved_sources": {
                key: candidate.as_dict()
                for key, candidate in self.approved_sources.items()
            },
            "staged": self.staged.as_dict() if self.staged else None,
        }


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
        if old_major_version != 1:
            raise ValueError("Unsupported timetable storage version")
        payload = {
            "timetables": old_data["timetables"],
            "approved_sources": {},
            "staged": None,
        }
        await self.hass.async_add_executor_job(self._owner._decode, payload)
        return payload


class TimetableStorage:
    """Promote changes only after validating and confirming their disk write."""

    def __init__(self, hass: HomeAssistant, entry_id: str, zone: ZoneInfo) -> None:
        self._hass = hass
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

    @property
    def staged(self) -> StagedImport | None:
        return self._snapshot.staged

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
        snapshot = _Snapshot(tables, MappingProxyType(approved), staged)
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
                _Snapshot(tables, MappingProxyType(approved), self.staged)
            )

    async def async_stage(self, candidate: ImportCandidate) -> str:
        """Save a proposal without changing any active timetable values."""
        async with self._lock:
            await self._async_refresh_snapshot()
            if self.staged is not None:
                raise PendingImportError(
                    "Review the pending import before uploading another"
                )
            stage_id = uuid4().hex
            await self._async_persist(
                _Snapshot(
                    self.timetables,
                    self.approved_sources,
                    StagedImport(stage_id, candidate),
                )
            )
            return stage_id

    def _require_stage(self, stage_id: str) -> StagedImport:
        if self.staged is None or self.staged.stage_id != stage_id:
            raise ValueError("This staged import is no longer current")
        return self.staged

    async def async_approve(self, stage_id: str) -> None:
        """Atomically activate the exact proposal that the user reviewed."""
        async with self._lock:
            await self._async_refresh_snapshot()
            staged = self._require_stage(stage_id)
            candidate = staged.candidate
            approved = dict(self.approved_sources)
            approved[candidate.timetable.timetable_id] = candidate
            await self._async_persist(
                _Snapshot(
                    self._replacement_tables(self.timetables, candidate),
                    MappingProxyType(approved),
                    None,
                )
            )

    async def async_reject(self, stage_id: str) -> None:
        """Discard the exact proposal, preserving the last approved source."""
        async with self._lock:
            await self._async_refresh_snapshot()
            self._require_stage(stage_id)
            await self._async_persist(
                _Snapshot(self.timetables, self.approved_sources, None)
            )

    def for_date(self, day: date) -> DailyPrayers | None:
        """Use exact annual dates only; Ramadan activation is not implemented."""
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
