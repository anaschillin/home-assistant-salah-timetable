"""Approval, staged-source lifecycle and remote-source metadata management.

Uses the owner's lock, refresh and validated persistence methods.
"""

from dataclasses import replace
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import uuid4

from ..domain.ramadan import RamadanSettings
from ..domain.ramadan_validation import validate_ramadan_selection
from ..parsers.import_model import ImportCandidate
from ..sources.source_model import RemoteSource, validate_check
from .storage_records import (
    ImportReviewBaseline,
    PendingImportError,
    RamadanApprovalError,
    ReviewChangedError,
    StagedImport,
)


class StorageReviewMixin:
    """Stage, approve and reject imports with atomic persistence."""

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
