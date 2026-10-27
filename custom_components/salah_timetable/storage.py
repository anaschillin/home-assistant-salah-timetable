"""Atomic per-mosque persistence for approved and staged timetable sources."""

from asyncio import Lock
from dataclasses import dataclass, replace
from dataclasses import field as dataclass_field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util.json import load_json

from .const import DOMAIN, STORAGE_VERSION
from .import_model import ImportCandidate
from .model import PrayerField, Timetable
from .ramadan import RamadanSettings
from .ramadan_validation import validate_ramadan_selection
from .source_model import RemoteSource, validate_check


class PendingImportError(ValueError):
    """A proposal must be reviewed before another can be staged."""


class RamadanApprovalError(ValueError):
    """A proposal cannot safely resolve under the current Ramadan settings."""


class ReviewChangedError(ValueError):
    """The approved source changed after the replacement comparison was shown."""


@dataclass(frozen=True)
class ImportReviewBaseline:
    """Exact approved records and provenance used by a replacement review."""

    timetable: Timetable | None
    source: ImportCandidate | None


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
    remote_sources: Mapping[str, RemoteSource] = dataclass_field(
        default_factory=lambda: MappingProxyType({})
    )
    remote_checks: Mapping[str, Mapping[str, Any]] = dataclass_field(
        default_factory=lambda: MappingProxyType({})
    )

    def as_dict(self) -> dict:
        return {
            "timetables": [table.as_dict() for table in self.timetables],
            "approved_sources": {
                key: candidate.as_dict()
                for key, candidate in self.approved_sources.items()
            },
            "staged": self.staged.as_dict() if self.staged else None,
            "remote_sources": {
                key: source.as_dict() for key, source in self.remote_sources.items()
            },
            "remote_checks": {
                key: dict(check) for key, check in self.remote_checks.items()
            },
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


class TimetableStorage:
    """Promote changes only after validating and confirming their disk write."""

    def __init__(self, hass: HomeAssistant, entry_id: str, zone: ZoneInfo) -> None:
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

    def _require_source(
        self, source_id: str, expected_source: RemoteSource | None = None
    ) -> RemoteSource:
        source = self.remote_sources.get(source_id)
        if source is None or (
            expected_source is not None and source != expected_source
        ):
            raise ValueError("The configured remote source has changed")
        return source

    @staticmethod
    def _candidate_matches_source(
        candidate: ImportCandidate, source: RemoteSource
    ) -> bool:
        return (
            candidate.timetable.timetable_id == source.source_id
            and candidate.timetable.kind == source.kind
            and candidate.year == source.year
            and candidate.source_url == source.url
            and candidate.source_format == source.media_type
            and candidate.date_column == source.date_column
            and candidate.columns == source.columns
            and candidate.time_format == source.time_format
            and candidate.parser_id == source.parser_id
        )

    async def async_stage(
        self,
        candidate: ImportCandidate,
        *,
        remote_source: RemoteSource | None = None,
        expected_source: RemoteSource | None = None,
    ) -> str:
        """Save a proposal and optional URL profile without changing active values."""
        async with self._lock:
            await self._async_refresh_snapshot()
            if self.staged is not None:
                raise PendingImportError(
                    "Review the pending import before uploading another"
                )
            if expected_source is not None:
                self._require_source(expected_source.source_id, expected_source)
            profile = remote_source or expected_source
            sources = dict(self.remote_sources)
            checks = dict(self.remote_checks)
            if profile is not None:
                if not self._candidate_matches_source(candidate, profile):
                    raise ValueError(
                        "Imported data does not match its remote source profile"
                    )
                sources[profile.source_id] = profile
                now = datetime.now(timezone.utc).isoformat()
                checks[profile.source_id] = validate_check(
                    {
                        "status": "pending",
                        "last_checked": now,
                        "last_success": now,
                        "last_seen_sha256": candidate.sha256,
                        "rejected_sha256": None,
                        "etag": candidate.etag,
                        "last_modified": candidate.last_modified,
                        "error_code": None,
                    }
                )
            stage_id = uuid4().hex
            await self._async_persist(
                replace(
                    self._snapshot,
                    staged=StagedImport(stage_id, candidate),
                    remote_sources=MappingProxyType(sources),
                    remote_checks=MappingProxyType(checks),
                )
            )
            return stage_id

    async def async_set_remote_source(
        self, source: RemoteSource, *, expected_source: RemoteSource | None = None
    ) -> None:
        """Save an explicit profile; changed profiles start with no old validators."""
        async with self._lock:
            await self._async_refresh_snapshot()
            if expected_source is not None:
                self._require_source(source.source_id, expected_source)
            previous = self.remote_sources.get(source.source_id)
            if (
                previous != source
                and self.staged is not None
                and self.staged.candidate.timetable.timetable_id == source.source_id
            ):
                raise PendingImportError(
                    "Review the pending import before changing its source"
                )
            sources = dict(self.remote_sources)
            sources[source.source_id] = source
            checks = dict(self.remote_checks)
            if previous != source:
                checks[source.source_id] = validate_check({"status": "configured"})
            await self._async_persist(
                replace(
                    self._snapshot,
                    remote_sources=MappingProxyType(sources),
                    remote_checks=MappingProxyType(checks),
                )
            )

    async def async_record_check(
        self,
        source_id: str,
        check: Mapping[str, Any],
        *,
        expected_source: RemoteSource | None = None,
    ) -> None:
        """Merge only redacted metadata, conditional on an unchanged URL profile."""
        async with self._lock:
            await self._async_refresh_snapshot()
            self._require_source(source_id, expected_source)
            checks = dict(self.remote_checks)
            checks[source_id] = validate_check(
                {**checks.get(source_id, {}), **validate_check(check)}
            )
            await self._async_persist(
                replace(self._snapshot, remote_checks=MappingProxyType(checks))
            )

    async def async_remove_remote_source(
        self, source_id: str, *, expected_source: RemoteSource | None = None
    ) -> None:
        """Stop checking a URL without removing any approved or staged timetable."""
        async with self._lock:
            await self._async_refresh_snapshot()
            self._require_source(source_id, expected_source)
            sources = dict(self.remote_sources)
            sources.pop(source_id)
            checks = dict(self.remote_checks)
            checks.pop(source_id, None)
            await self._async_persist(
                replace(
                    self._snapshot,
                    remote_sources=MappingProxyType(sources),
                    remote_checks=MappingProxyType(checks),
                )
            )

    def _decision_checks(
        self, candidate: ImportCandidate, status: str
    ) -> Mapping[str, Mapping[str, Any]]:
        checks = dict(self.remote_checks)
        source_id = candidate.timetable.timetable_id
        source = self.remote_sources.get(source_id)
        if source is not None and candidate.source_url == source.url:
            checks[source_id] = validate_check(
                {
                    **checks.get(source_id, {}),
                    "status": status,
                    "rejected_sha256": candidate.sha256
                    if status == "rejected"
                    else None,
                }
            )
        return MappingProxyType(checks)

    def _require_stage(self, stage_id: str) -> StagedImport:
        if self.staged is None or self.staged.stage_id != stage_id:
            raise ValueError("This staged import is no longer current")
        return self.staged

    async def async_approve(
        self,
        stage_id: str,
        *,
        expected_baseline: ImportReviewBaseline | None = None,
    ) -> None:
        """Atomically activate the exact proposal that the user reviewed."""
        async with self._lock:
            await self._async_refresh_snapshot()
            staged = self._require_stage(stage_id)
            candidate = staged.candidate
            if (
                expected_baseline is not None
                and expected_baseline
                != self.review_baseline(candidate.timetable.timetable_id)
            ):
                raise ReviewChangedError(
                    "The approved source changed; review the updated comparison before approving"
                )
            tables = self._replacement_tables(self.timetables, candidate)
            entry = self._hass.config_entries.async_get_entry(self._entry_id)
            try:
                validate_ramadan_selection(
                    tables,
                    RamadanSettings.from_options(entry.options if entry else {}),
                )
            except ValueError as err:
                raise RamadanApprovalError(str(err)) from err
            approved = dict(self.approved_sources)
            approved[candidate.timetable.timetable_id] = candidate
            await self._async_persist(
                replace(
                    self._snapshot,
                    timetables=tables,
                    approved_sources=MappingProxyType(approved),
                    staged=None,
                    remote_checks=self._decision_checks(candidate, "approved"),
                )
            )

    async def async_reject(self, stage_id: str) -> None:
        """Discard the exact proposal, preserving the last approved source."""
        async with self._lock:
            await self._async_refresh_snapshot()
            staged = self._require_stage(stage_id)
            await self._async_persist(
                replace(
                    self._snapshot,
                    staged=None,
                    remote_checks=self._decision_checks(staged.candidate, "rejected"),
                )
            )

    async def async_remove(self) -> None:
        async with self._lock:
            await self._store.async_remove()
            self._snapshot = _Snapshot((), MappingProxyType({}), None)
