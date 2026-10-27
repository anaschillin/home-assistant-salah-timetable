"""Bounded remote checks stage validated changes and never activate them."""

import asyncio
import logging
from collections.abc import Awaitable
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util import dt as dt_util

from . import download
from .csv_parser import CsvParser
from .import_model import ImportValidationError
from .storage import PendingImportError, TimetableStorage

CHECK_INTERVAL = timedelta(days=1)
_LOGGER = logging.getLogger(__name__)


class SourceUpdateManager:
    """Serialize manual/scheduled checks without risking active timetables."""

    def __init__(
        self, hass: HomeAssistant, entry, storage: TimetableStorage, coordinator
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.storage = storage
        self.coordinator = coordinator
        self._lock = asyncio.Lock()
        self._tasks: set[asyncio.Task] = set()
        self._unsubscribe = None
        self._unsubscribe_coordinator = None
        self._started = False
        self._scheduled_for: datetime | None = None
        self._attempted_at: dict[str, tuple[Any, datetime]] = {}
        self._stopped = False
        self._runtime_error: str | None = None

    @property
    def status(self) -> dict[str, Any]:
        """Aggregate public state without URLs, source data or exception text."""
        checks = list(self.storage.remote_checks.values())
        error_count = sum(check.get("status") == "error" for check in checks)
        if self._runtime_error:
            error_count += 1
        pending = self.storage.staged is not None
        if not self.storage.remote_sources:
            state = "not_configured"
        elif pending:
            state = "pending_review"
        elif error_count:
            state = "error"
        else:
            # A successful HTTP check does not mean its published bytes are
            # approved. Compare the latest validated digest with the exact
            # approved profile; never expose either digest in sensor attributes.
            states = []
            for source_id, source in self.storage.remote_sources.items():
                check = self.storage.remote_checks.get(source_id, {})
                seen = check.get("last_seen_sha256")
                approved = self.storage.approved_sources.get(source_id)
                if not seen or not check.get("last_success"):
                    states.append("configured")
                elif check.get("rejected_sha256") == seen or (
                    check.get("status") == "rejected"
                    and not check.get("rejected_sha256")
                ):
                    # Legacy rejected checks have no separate digest until the
                    # next unchanged download migrates their metadata.
                    states.append("rejected_version")
                elif (
                    approved is not None
                    and approved.sha256 == seen
                    and approved.source_url == source.url
                ):
                    states.append("up_to_date")
                else:
                    states.append("differs_from_approved")
            state = next(
                (
                    candidate
                    for candidate in (
                        "rejected_version",
                        "differs_from_approved",
                        "configured",
                    )
                    if candidate in states
                ),
                "up_to_date",
            )
        return {
            "status": state,
            "configured_sources": len(self.storage.remote_sources),
            "pending_review": pending,
            "error_count": error_count,
            "last_checked": max(
                (
                    check["last_checked"]
                    for check in checks
                    if check.get("last_checked")
                ),
                default=None,
            ),
            "last_success": max(
                (
                    check["last_success"]
                    for check in checks
                    if check.get("last_success")
                ),
                default=None,
            ),
        }

    def _notify(self) -> None:
        if not self._stopped:
            self._schedule_next()
            self.coordinator.async_update_listeners()

    def _due_at(self, source, now: datetime) -> datetime:
        """Use persisted UTC time, so repeated restarts cannot postpone a check."""
        saved = self.storage.remote_checks.get(source.source_id, {}).get("last_checked")
        anchors = []
        if saved is not None and (parsed := dt_util.parse_datetime(saved)) is not None:
            saved_time = dt_util.as_utc(parsed)
            if saved_time <= now:
                anchors.append(saved_time)
        attempt = self._attempted_at.get(source.source_id)
        if attempt is not None and attempt[0] == source and attempt[1] <= now:
            anchors.append(attempt[1])
        if not anchors:
            return now
        # Future timestamps after a clock correction are ignored. A fresh attempt
        # then rebases scheduling even if its persistence fails.
        return max(anchors) + CHECK_INTERVAL

    def _schedule_next(self) -> None:
        """Schedule the earliest due source; called after checks and UI changes."""
        if not self._started or self._stopped:
            return
        now = dt_util.utcnow()
        when = min(
            (
                self._due_at(source, now)
                for source in self.storage.remote_sources.values()
            ),
            default=None,
        )
        if when is not None:
            when = max(now, when)
        if when == self._scheduled_for and self._unsubscribe is not None:
            return
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        self._scheduled_for = when
        if when is not None:
            self._unsubscribe = async_track_point_in_utc_time(
                self.hass, self._async_scheduled_check, when
            )

    async def async_start(self) -> None:
        """Resume persisted due times, including background startup catch-up."""
        if self._started:
            return
        self._stopped = False
        self._started = True
        self._unsubscribe_coordinator = self.coordinator.async_add_listener(
            self._schedule_next
        )
        self._schedule_next()

    async def _async_scheduled_check(self, _now) -> None:
        self._unsubscribe = None
        self._scheduled_for = None
        await self._run(None, due_only=True)

    async def async_stop(self) -> None:
        """Stop new work, cancel downloads, and join any already-started writes."""
        self._stopped = True
        self._started = False
        self._scheduled_for = None
        if self._unsubscribe_coordinator is not None:
            self._unsubscribe_coordinator()
            self._unsubscribe_coordinator = None
        if self._unsubscribe is not None:
            self._unsubscribe()
            self._unsubscribe = None
        tasks = tuple(
            task for task in self._tasks if task is not asyncio.current_task()
        )
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _run(self, source_id: str | None, *, due_only: bool = False) -> None:
        if self._stopped:
            return
        task = asyncio.create_task(
            self._async_run_checks(source_id, due_only=due_only),
            name="salah_timetable_source_check",
        )
        self._tasks.add(task)
        try:
            await task
        finally:
            self._tasks.discard(task)

    def source_profiles_changed(self) -> None:
        """Recalculate the next due check after a source profile changes."""
        self._notify()

    async def async_check_all(self) -> None:
        """Attempt every configured source once; no active data is changed."""
        await self._run(None)

    async def async_check(self, source_id: str) -> None:
        """Check one configured source, using the same lock as the daily timer."""
        await self._run(source_id)

    async def _async_run_checks(
        self, source_id: str | None, *, due_only: bool = False
    ) -> None:
        async with self._lock:
            if self._stopped:
                return
            try:
                await self.storage.async_load()
            except (
                ValueError,
                KeyError,
                TypeError,
                OSError,
                HomeAssistantError,
            ):
                self._runtime_error = "storage_failed"
                now = dt_util.utcnow()
                for source in self.storage.remote_sources.values():
                    self._attempted_at[source.source_id] = (source, now)
                self._notify()
                return
            ids = (
                [source_id]
                if source_id is not None
                else list(self.storage.remote_sources)
            )
            for current_id in ids:
                if self._stopped:
                    return
                source = self.storage.remote_sources.get(current_id)
                if source is not None and (
                    not due_only
                    or self._due_at(source, dt_util.utcnow()) <= dt_util.utcnow()
                ):
                    await self._async_check_source(source)
            self._notify()

    async def _async_write(self, operation: Awaitable) -> Any:
        """Cancellation must join a file transaction rather than orphaning it."""
        task = asyncio.create_task(operation)
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            await task
            raise

    async def _record(self, source, patch: dict[str, Any]) -> bool:
        if self._stopped:
            return False
        try:
            await self._async_write(
                self.storage.async_record_check(
                    source.source_id, patch, expected_source=source
                )
            )
        except (
            ValueError,
            KeyError,
        ):
            # A setting changed or the profile was removed while downloading.
            return False
        except (
            OSError,
            HomeAssistantError,
        ):
            self._runtime_error = "storage_failed"
            return False
        self._runtime_error = None
        return True

    @staticmethod
    def _unchanged_check_patch(previous: dict, baseline: str | None, result, now: str):
        """Keep validators and legacy rejection when HTTP bytes are unchanged."""
        return {
            "status": "unchanged",
            "last_checked": now,
            "last_success": now,
            "error_code": None,
            "rejected_sha256": previous.get("rejected_sha256")
            or (baseline if previous.get("status") == "rejected" else None),
            "etag": result.etag or previous.get("etag"),
            "last_modified": result.last_modified or previous.get("last_modified"),
        }

    async def _async_stage_downloaded_source(self, source, result, now: str) -> None:
        """Stage validated remote bytes, never approve them automatically."""
        try:
            candidate = await self.hass.async_add_executor_job(
                self._parse, source, result.content
            )
            candidate = await self.hass.async_add_executor_job(
                lambda: replace(
                    candidate,
                    source_url=source.url,
                    etag=result.etag,
                    last_modified=result.last_modified,
                )
            )
            if self._stopped:
                return
            await self._async_write(
                self.storage.async_stage(candidate, expected_source=source)
            )
        except PendingImportError:
            await self._record(
                source, {"status": "pending", "last_checked": now, "error_code": None}
            )
            return
        except ImportValidationError, ValueError:
            _LOGGER.warning(
                "Downloaded timetable failed validation; approved data retained"
            )
            await self._record(
                source,
                {
                    "status": "error",
                    "last_checked": now,
                    "error_code": "invalid_timetable",
                },
            )
            return
        except OSError, HomeAssistantError:
            self._runtime_error = "storage_failed"
            return
        await self._record(
            source,
            {
                "status": "pending",
                "last_checked": now,
                "last_success": now,
                "last_seen_sha256": result.sha256,
                "rejected_sha256": None,
                "etag": result.etag,
                "last_modified": result.last_modified,
                "error_code": None,
            },
        )

    async def _async_check_source(self, source) -> None:
        checked_at = dt_util.utcnow()
        now = checked_at.isoformat()
        self._attempted_at[source.source_id] = (source, checked_at)
        if self.storage.staged is not None:
            await self._record(
                source, {"status": "pending", "last_checked": now, "error_code": None}
            )
            return
        previous = dict(self.storage.remote_checks.get(source.source_id, {}))
        baseline = previous.get("last_seen_sha256")
        try:
            result = await download.async_download(
                source.url,
                media_type=source.media_type,
                etag=previous.get("etag") if baseline else None,
                last_modified=previous.get("last_modified") if baseline else None,
            )
        except download.DownloadError as err:
            _LOGGER.warning(
                "Timetable source check failed (%s); approved data retained", err.code
            )
            await self._record(
                source, {"status": "error", "last_checked": now, "error_code": err.code}
            )
            return
        except (
            TimeoutError,
            OSError,
        ):
            await self._record(
                source,
                {
                    "status": "error",
                    "last_checked": now,
                    "error_code": "download_failed",
                },
            )
            return
        if self._stopped:
            return
        # A separately opened options flow may have changed this profile while
        # awaiting the response. Refresh before both parsing and storage CAS.
        try:
            await self.storage.async_load()
        except (
            ValueError,
            KeyError,
            TypeError,
            OSError,
            HomeAssistantError,
        ):
            self._runtime_error = "storage_failed"
            return
        if self.storage.remote_sources.get(source.source_id) != source:
            return
        if result.not_modified or (baseline is not None and result.sha256 == baseline):
            await self._record(
                source, self._unchanged_check_patch(previous, baseline, result, now)
            )
            return
        if self.storage.staged is not None:
            await self._record(
                source, {"status": "pending", "last_checked": now, "error_code": None}
            )
            return
        await self._async_stage_downloaded_source(source, result, now)

    @staticmethod
    def _parse(source, content: bytes):
        if source.media_type == "pdf":
            from .pdf_parser import PdfParser

            parser = PdfParser(layout_id=source.parser_id)
        else:
            parser = CsvParser()
        return parser.parse(
            content,
            timetable_id=source.source_id,
            kind=source.kind,
            year=source.year,
            date_column=source.date_column,
            columns=dict(source.columns),
            time_format=source.time_format,
        )
