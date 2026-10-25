"""Remote checks exercise real persistence while mocking only outbound transport."""

import asyncio
from dataclasses import replace
from datetime import date
from hashlib import sha256
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.salah_timetable.download import DownloadError, DownloadResult
from custom_components.salah_timetable.source_model import RemoteSource
from custom_components.salah_timetable.source_updates import (
    SourceUpdateManager,
)
from custom_components.salah_timetable.storage import TimetableStorage

CSV = b"Date,Fajr Begin\n2026-10-21,05:45\n"
UPDATED = b"Date,Fajr Begin\n2026-10-21,05:55\n"


def response(content=CSV, etag='"v1"'):
    return DownloadResult(content, "csv", etag, None, sha256(content).hexdigest())


def source(**changes):
    initial = RemoteSource(
        "annual-2026",
        "https://example.com/timetable.csv",
        "csv",
        "annual",
        2026,
        "Date",
        {"Fajr Begin": "fajr_begin"},
        parser_id="csv_v1",
    )
    return replace(initial, **changes)


@pytest.fixture
async def manager(hass, entry):
    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    await storage.async_load()
    await storage.async_set_remote_source(source())
    return SourceUpdateManager(hass, entry, storage, MagicMock())


async def test_changed_download_stages_without_activation(manager):
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(return_value=response()),
    ) as fetch:
        await manager.async_check_all()
    fetch.assert_awaited_once_with(
        source().url, media_type="csv", etag=None, last_modified=None
    )
    assert manager.storage.for_date(date(2026, 10, 21)) is None
    candidate = manager.storage.staged.candidate
    assert candidate.sha256 == sha256(CSV).hexdigest()
    assert candidate.source_url == source().url
    assert candidate.etag == '"v1"'
    assert manager.status["status"] == "pending_review"
    assert (
        manager.storage.remote_checks[source().source_id]["last_seen_sha256"]
        == candidate.sha256
    )
    manager.coordinator.async_update_listeners.assert_called()


async def test_changed_update_keeps_last_approved(manager):
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(return_value=response()),
    ):
        await manager.async_check_all()
    await manager.storage.async_approve(manager.storage.staged.stage_id)
    previous = manager.storage.timetables
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(return_value=response(UPDATED, '"v2"')),
    ):
        await manager.async_check_all()
    assert manager.storage.timetables == previous
    assert manager.storage.staged.candidate.sha256 == sha256(UPDATED).hexdigest()
    assert (
        manager.storage.approved_sources[source().source_id].sha256
        == sha256(CSV).hexdigest()
    )


async def test_rejected_unchanged_content_is_not_restaged(manager):
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(return_value=response()),
    ):
        await manager.async_check_all()
        await manager.storage.async_reject(manager.storage.staged.stage_id)
        await manager.async_check_all()
    assert manager.storage.staged is None
    assert manager.storage.timetables == ()
    assert manager.status["status"] == "rejected_version"
    check = manager.storage.remote_checks[source().source_id]
    assert check["status"] == "unchanged"
    assert check["rejected_sha256"] == sha256(CSV).hexdigest()


async def test_approved_source_is_up_to_date_only_for_matching_publication(manager):
    assert manager.status["status"] == "configured"
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(return_value=response()),
    ):
        await manager.async_check_all()
    assert manager.status["status"] == "pending_review"
    await manager.storage.async_approve(manager.storage.staged.stage_id)
    assert manager.status["status"] == "up_to_date"
    assert manager.storage.remote_checks[source().source_id]["rejected_sha256"] is None
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(return_value=DownloadResult(None, "csv", '"v1"', None, None, True)),
    ):
        await manager.async_check_all()
    assert manager.status["status"] == "up_to_date"


async def test_unapproved_successful_check_never_claims_up_to_date(manager):
    await manager.storage.async_record_check(
        source().source_id,
        {
            "status": "unchanged",
            "last_seen_sha256": sha256(CSV).hexdigest(),
            "last_success": "2026-10-21T12:00:00+00:00",
        },
    )
    assert manager.status["status"] == "differs_from_approved"
    assert set(manager.status) == {
        "status",
        "configured_sources",
        "pending_review",
        "error_count",
        "last_checked",
        "last_success",
    }
    assert "example.com" not in repr(manager.status)
    assert sha256(CSV).hexdigest() not in repr(manager.status)


async def test_rejected_http_304_survives_restart_without_reprompt(manager):
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(return_value=response()),
    ):
        await manager.async_check_all()
    await manager.storage.async_reject(manager.storage.staged.stage_id)

    restored = TimetableStorage(
        manager.hass, manager.entry.entry_id, ZoneInfo("Europe/London")
    )
    await restored.async_load()
    restarted = SourceUpdateManager(manager.hass, manager.entry, restored, MagicMock())
    assert restarted.status["status"] == "rejected_version"
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(return_value=DownloadResult(None, "csv", '"v1"', None, None, True)),
    ) as fetch:
        await restarted.async_check_all()
    fetch.assert_awaited_once_with(
        source().url, media_type="csv", etag='"v1"', last_modified=None
    )
    assert restarted.storage.staged is None
    assert restarted.status["status"] == "rejected_version"
    assert (
        restarted.storage.remote_checks[source().source_id]["rejected_sha256"]
        == sha256(CSV).hexdigest()
    )


async def test_legacy_rejected_check_is_upgraded_on_unchanged_check(manager):
    digest = sha256(CSV).hexdigest()
    await manager.storage.async_record_check(
        source().source_id,
        {
            "status": "rejected",
            "last_seen_sha256": digest,
            "last_success": "2026-10-21T12:00:00+00:00",
            "etag": '"v1"',
        },
    )
    assert manager.status["status"] == "rejected_version"
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(return_value=DownloadResult(None, "csv", '"v1"', None, None, True)),
    ):
        await manager.async_check_all()
    check = manager.storage.remote_checks[source().source_id]
    assert check["status"] == "unchanged"
    assert check["rejected_sha256"] == digest
    assert manager.status["status"] == "rejected_version"


async def test_rejected_change_retains_approval_and_stages_only_new_digest(manager):
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(return_value=response()),
    ):
        await manager.async_check_all()
    await manager.storage.async_approve(manager.storage.staged.stage_id)
    previous = manager.storage.timetables

    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(return_value=response(UPDATED, '"v2"')),
    ):
        await manager.async_check_all()
    assert manager.status["status"] == "pending_review"
    await manager.storage.async_reject(manager.storage.staged.stage_id)
    assert manager.status["status"] == "rejected_version"
    assert manager.storage.timetables == previous

    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(return_value=response(UPDATED, '"v2"')),
    ):
        await manager.async_check_all()
    assert manager.storage.staged is None
    assert manager.status["status"] == "rejected_version"

    changed = b"Date,Fajr Begin\n2026-10-21,06:05\n"
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(return_value=response(changed, '"v3"')),
    ):
        await manager.async_check_all()
    assert manager.status["status"] == "pending_review"
    assert manager.storage.remote_checks[source().source_id]["rejected_sha256"] is None
    assert manager.storage.timetables == previous
    await manager.storage.async_approve(manager.storage.staged.stage_id)
    assert manager.status["status"] == "up_to_date"
    assert manager.storage.remote_checks[source().source_id]["rejected_sha256"] is None


async def test_source_error_has_precedence_over_last_rejection(manager):
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(return_value=response()),
    ):
        await manager.async_check_all()
    await manager.storage.async_reject(manager.storage.staged.stage_id)
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(side_effect=DownloadError("request_failed", "safe")),
    ):
        await manager.async_check_all()
    assert manager.status["status"] == "error"
    assert manager.storage.remote_checks[source().source_id]["rejected_sha256"]
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(return_value=response()),
    ):
        await manager.async_check_all()
    assert manager.status["status"] == "rejected_version"


async def test_not_modified_uses_only_saved_validators(manager):
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(return_value=response()),
    ):
        await manager.async_check_all()
    await manager.storage.async_approve(manager.storage.staged.stage_id)
    result = DownloadResult(None, "csv", '"v1"', None, None, True)
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(return_value=result),
    ) as fetch:
        await manager.async_check_all()
    fetch.assert_awaited_once_with(
        source().url, media_type="csv", etag='"v1"', last_modified=None
    )
    assert manager.storage.staged is None
    assert (
        manager.storage.remote_checks[source().source_id]["last_seen_sha256"]
        == sha256(CSV).hexdigest()
    )


async def test_invalid_change_does_not_replace_digest_or_active(manager):
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(return_value=response()),
    ):
        await manager.async_check_all()
    await manager.storage.async_approve(manager.storage.staged.stage_id)
    previous = manager.storage.timetables
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(
            return_value=response(b"Date,Fajr Begin\n2026-10-21,unknown\n", '"invalid"')
        ),
    ):
        await manager.async_check_all()
    assert manager.storage.timetables == previous
    assert manager.storage.staged is None
    check = manager.storage.remote_checks[source().source_id]
    assert check["status"] == "error"
    assert check["error_code"] == "invalid_timetable"
    assert check["last_seen_sha256"] == sha256(CSV).hexdigest()
    assert check["etag"] == '"v1"'
    assert manager.status["status"] == "error"


async def test_pending_review_defers_all_new_downloads(manager):
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(return_value=response()),
    ):
        await manager.async_check_all()
    before = manager.storage.staged
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(),
    ) as fetch:
        await manager.async_check_all()
    fetch.assert_not_awaited()
    assert manager.storage.staged == before
    assert manager.storage.timetables == ()
    # A restart must not allow downloads to bypass pending review.
    restored = TimetableStorage(
        manager.hass,
        manager.entry.entry_id,
        ZoneInfo("Europe/London"),
    )
    await restored.async_load()

    restarted = SourceUpdateManager(
        manager.hass,
        manager.entry,
        restored,
        MagicMock(),
    )

    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(),
    ) as fetch:
        await restarted.async_check_all()

    fetch.assert_not_awaited()
    assert restarted.storage.staged == before
    assert restarted.storage.timetables == ()
    assert restarted.status["status"] == "pending_review"


@pytest.mark.parametrize(
    "error",
    [
        DownloadError("unsafe_destination", "safe message"),
        TimeoutError(),
        OSError("https://secret.invalid/private"),
    ],
)
async def test_network_failure_redacts_errors_and_preserves_data(manager, error):
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(side_effect=error),
    ):
        await manager.async_check_all()
    check = manager.storage.remote_checks[source().source_id]
    assert check["status"] == "error"
    assert check["error_code"] in {"unsafe_destination", "download_failed"}
    assert "secret" not in repr(check)
    assert manager.storage.staged is None
    assert manager.storage.timetables == ()


@pytest.mark.parametrize("remove", [False, True])
async def test_profile_change_while_downloading_cannot_stage_stale_data(
    manager, remove
):
    started, resume = asyncio.Event(), asyncio.Event()

    async def fetch(*args, **kwargs):
        started.set()
        await resume.wait()
        return response()

    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        fetch,
    ):
        task = asyncio.create_task(manager.async_check_all())
        await started.wait()
        if remove:
            await manager.storage.async_remove_remote_source(source().source_id)
        else:
            await manager.storage.async_set_remote_source(
                source(url="https://example.org/new.csv")
            )
        resume.set()
        await task
    assert manager.storage.staged is None
    assert manager.storage.timetables == ()
    if not remove:
        assert (
            manager.storage.remote_checks[source().source_id].get("last_seen_sha256")
            is None
        )


async def test_stop_cancels_owned_download_and_prevents_future_work(manager):
    started = asyncio.Event()

    async def fetch(*args, **kwargs):
        started.set()
        await asyncio.Event().wait()

    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        fetch,
    ):
        task = asyncio.create_task(manager.async_check_all())
        await started.wait()
        await manager.async_stop()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert not manager._tasks
    assert manager.storage.staged is None
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(),
    ) as fetch:
        await manager.async_check_all()
    fetch.assert_not_awaited()


async def test_manual_and_scheduled_checks_share_lock(manager):
    started, resume = asyncio.Event(), asyncio.Event()

    async def fetch(*args, **kwargs):
        started.set()
        await resume.wait()
        return response()

    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(side_effect=fetch),
    ) as mocked:
        first = asyncio.create_task(manager.async_check(source().source_id))
        await started.wait()
        second = asyncio.create_task(manager.async_check_all())
        resume.set()
        await asyncio.gather(first, second)
    assert mocked.await_count == 1
    assert manager.storage.staged is not None


async def test_recent_profile_waits_only_remaining_day_after_restart(manager, freezer):
    from homeassistant.util import dt as dt_util

    freezer.move_to("2026-10-21 12:00:00+00:00")
    last_checked = "2026-10-21T04:00:00+00:00"
    await manager.storage.async_record_check(
        source().source_id, {"last_checked": last_checked}
    )
    unsubscribe = MagicMock()
    with (
        patch(
            "custom_components.salah_timetable.source_updates.async_track_point_in_utc_time",
            return_value=unsubscribe,
        ) as track,
        patch(
            "custom_components.salah_timetable.source_updates.download.async_download",
            AsyncMock(),
        ) as fetch,
    ):
        await manager.async_start()
        await manager.async_start()
        track.assert_called_once_with(
            manager.hass,
            manager._async_scheduled_check,
            dt_util.parse_datetime("2026-10-22T04:00:00+00:00"),
        )
        fetch.assert_not_awaited()
        await manager.async_stop()
    unsubscribe.assert_called_once()
    manager.coordinator.async_add_listener.return_value.assert_called_once()


async def test_storage_failure_is_visible_without_replacing_active(manager):
    with (
        patch.object(
            manager.storage,
            "async_record_check",
            AsyncMock(side_effect=OSError("disk full")),
        ),
        patch(
            "custom_components.salah_timetable.source_updates.download.async_download",
            AsyncMock(side_effect=DownloadError("timeout", "safe")),
        ),
    ):
        await manager.async_check_all()
    assert manager.status["status"] == "error"
    assert manager.status["error_count"] == 1
    assert manager.storage.timetables == ()


async def test_no_profiles_no_download(hass, entry):
    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("UTC"))
    manager = SourceUpdateManager(hass, entry, storage, MagicMock())
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(),
    ) as fetch:
        await manager.async_check_all()
        await manager.async_check("missing")
    fetch.assert_not_awaited()
    assert manager.status["status"] == "not_configured"


async def test_pdf_check_uses_isolated_parser_and_retains_binary_provenance(manager):
    from pathlib import Path

    pdf = Path("tests/fixtures/pdf/sample_table.pdf").read_bytes()
    profile = source(
        url="https://example.com/timetable.pdf",
        media_type="pdf",
        columns={"Fajr Begin": "fajr_begin", "Fajr Jamaat": "fajr_jamaat"},
        parser_id="pdf_table_v1",
    )
    await manager.storage.async_set_remote_source(profile)
    result = DownloadResult(pdf, "pdf", '"pdf-v1"', None, sha256(pdf).hexdigest())
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(return_value=result),
    ):
        await manager.async_check_all()
    assert manager.storage.staged.candidate.source_format == "pdf"
    assert manager.storage.staged.candidate.source_base64
    assert manager.storage.staged.candidate.sha256 == sha256(pdf).hexdigest()
    assert manager.storage.timetables == ()


async def test_failed_snapshot_refresh_does_not_fetch_or_clear_active(manager):
    with (
        patch.object(
            manager.storage, "async_load", AsyncMock(side_effect=OSError("disk failed"))
        ),
        patch(
            "custom_components.salah_timetable.source_updates.download.async_download",
            AsyncMock(),
        ) as fetch,
    ):
        await manager.async_check_all()
    fetch.assert_not_awaited()
    assert manager.status["status"] == "error"
    assert manager.storage.timetables == ()


async def test_pending_created_during_download_is_not_overwritten(manager):
    started, resume = asyncio.Event(), asyncio.Event()
    from custom_components.salah_timetable.csv_parser import CsvParser

    async def fetch(*args, **kwargs):
        started.set()
        await resume.wait()
        return response(UPDATED)

    candidate = CsvParser().parse(
        CSV,
        timetable_id="manual",
        kind="annual",
        year=2026,
        date_column="Date",
        columns={"Fajr Begin": "fajr_begin"},
    )
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        fetch,
    ):
        task = asyncio.create_task(manager.async_check_all())
        await started.wait()
        pending_id = await manager.storage.async_stage(candidate)
        resume.set()
        await task
    assert manager.storage.staged.stage_id == pending_id
    assert (
        manager.storage.remote_checks[source().source_id].get("last_seen_sha256")
        is None
    )


async def test_stop_joins_in_progress_storage_transaction(manager):
    started, resume = asyncio.Event(), asyncio.Event()
    original_stage = manager.storage.async_stage

    async def delayed_stage(*args, **kwargs):
        started.set()
        await resume.wait()
        return await original_stage(*args, **kwargs)

    with (
        patch(
            "custom_components.salah_timetable.source_updates.download.async_download",
            AsyncMock(return_value=response()),
        ),
        patch.object(manager.storage, "async_stage", delayed_stage),
    ):
        running = asyncio.create_task(manager.async_check_all())
        await started.wait()
        stopping = asyncio.create_task(manager.async_stop())
        await asyncio.sleep(0)
        assert not stopping.done()
        resume.set()
        await stopping
        with pytest.raises(asyncio.CancelledError):
            await running
    # The already-started transaction completed before stop returned; it only
    # stages data and can never activate a timetable during shutdown.
    assert manager.storage.staged is not None
    assert manager.storage.timetables == ()


async def test_overdue_profile_is_checked_once_after_restart(manager, freezer):
    freezer.move_to("2026-10-21 12:00:00+00:00")
    await manager.storage.async_record_check(
        source().source_id, {"last_checked": "2026-10-19T12:00:00+00:00"}
    )
    restored = TimetableStorage(
        manager.hass, manager.entry.entry_id, ZoneInfo("Europe/London")
    )
    await restored.async_load()
    restarted = SourceUpdateManager(manager.hass, manager.entry, restored, MagicMock())
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(return_value=response()),
    ) as fetch:
        await restarted.async_start()
        async_fire_time_changed(manager.hass)
        await manager.hass.async_block_till_done()
        assert fetch.await_count == 1
        assert restarted.storage.staged is not None
        assert restarted._scheduled_for.isoformat() == "2026-10-22T12:00:00+00:00"
        await restarted.async_stop()


async def test_scheduler_only_checks_due_sources(manager, freezer):
    freezer.move_to("2026-10-21 12:00:00+00:00")
    next_year = source(
        source_id="annual-2027", year=2027, url="https://example.com/2027.csv"
    )
    await manager.storage.async_set_remote_source(next_year)
    recent = "2026-10-21T04:00:00+00:00"
    await manager.storage.async_record_check(
        next_year.source_id, {"last_checked": recent}
    )
    await manager.storage.async_record_check(
        source().source_id, {"last_checked": "2026-10-19T12:00:00+00:00"}
    )
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(return_value=response()),
    ) as fetch:
        await manager.async_start()
        async_fire_time_changed(manager.hass)
        await manager.hass.async_block_till_done()
        fetch.assert_awaited_once_with(
            source().url, media_type="csv", etag=None, last_modified=None
        )
        assert (
            manager.storage.remote_checks[next_year.source_id]["last_checked"] == recent
        )
        assert manager._scheduled_for.isoformat() == "2026-10-22T04:00:00+00:00"
        await manager.async_stop()


async def test_no_profiles_start_has_no_timer_or_network(hass, entry):
    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("UTC"))
    empty = SourceUpdateManager(hass, entry, storage, MagicMock())
    with (
        patch(
            "custom_components.salah_timetable.source_updates.async_track_point_in_utc_time"
        ) as track,
        patch(
            "custom_components.salah_timetable.source_updates.download.async_download",
            AsyncMock(),
        ) as fetch,
    ):
        await empty.async_start()
        await hass.async_block_till_done()
        track.assert_not_called()
        fetch.assert_not_awaited()
        await empty.async_stop()


async def test_clock_correction_rebases_future_check_time(manager, freezer):
    from homeassistant.util import dt as dt_util

    freezer.move_to("2026-10-21 12:00:00+00:00")
    await manager.storage.async_record_check(
        source().source_id, {"last_checked": "2026-11-21T12:00:00+00:00"}
    )
    with patch(
        "custom_components.salah_timetable.source_updates.async_track_point_in_utc_time",
        return_value=MagicMock(),
    ) as track:
        await manager.async_start()
        assert track.call_args.args[2] == dt_util.utcnow()
        await manager.async_stop()
