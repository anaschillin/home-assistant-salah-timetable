"""Staging, approval and migration exercise the actual atomic HA Store files."""

from asyncio import gather
from datetime import date, time
from pathlib import Path
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.helpers.storage import Store
from homeassistant.util.file import WriteError
from homeassistant.util.json import load_json

from custom_components.salah_timetable.const import DOMAIN, STORAGE_VERSION
from custom_components.salah_timetable.csv_parser import CsvParser
from custom_components.salah_timetable.model import DailyPrayers, PrayerField, Timetable
from custom_components.salah_timetable.storage import (
    PendingImportError,
    TimetableStorage,
)


def candidate(value="05:45", year=2026, kind="annual", table_id=None):
    return CsvParser().parse(
        f"Date,Fajr Begin\n{year}-10-21,{value}\n".encode(),
        timetable_id=table_id or f"{kind}-{year}",
        kind=kind,
        year=year,
        date_column="Date",
        columns={"Fajr Begin": "fajr_begin"},
    )


async def reload_storage(hass, entry):
    result = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    await result.async_load()
    return result


async def test_staging_survives_restart_without_activation(hass, entry):
    proposal = candidate()
    storage = await reload_storage(hass, entry)
    stage_id = await storage.async_stage(proposal)
    assert storage.timetables == ()
    assert storage.approved_sources == {}
    assert storage.for_date(date(2026, 10, 21)) is None
    reloaded = await reload_storage(hass, entry)
    assert reloaded.staged.stage_id == stage_id
    assert reloaded.staged.candidate == proposal
    assert reloaded.timetables == ()
    await reloaded.async_approve(stage_id)
    approved = await reload_storage(hass, entry)
    assert approved.staged is None
    assert approved.timetables == (proposal.timetable,)
    assert approved.approved_sources == {"annual-2026": proposal}
    assert approved.approved_sources["annual-2026"].source_text == proposal.source_text
    assert approved.for_date(date(2026, 10, 21)).times[PrayerField.FAJR_BEGIN] == (
        time(5, 45),
    )


async def test_reject_keeps_approved_source_after_restart(hass, entry):
    original = candidate()
    storage = await reload_storage(hass, entry)
    stage_id = await storage.async_stage(original)
    await storage.async_approve(stage_id)
    stage_id = await storage.async_stage(candidate("06:00"))
    assert storage.timetables == (original.timetable,)
    await storage.async_reject(stage_id)
    reloaded = await reload_storage(hass, entry)
    assert reloaded.staged is None
    assert reloaded.approved_sources == {"annual-2026": original}
    assert reloaded.timetables == (original.timetable,)


async def test_exact_stage_id_prevents_stale_approval_or_rejection(hass, entry):
    storage = await reload_storage(hass, entry)
    first = await storage.async_stage(candidate())
    await storage.async_reject(first)
    second = await storage.async_stage(candidate("06:00"))
    assert first != second
    for action in (storage.async_approve, storage.async_reject):
        with pytest.raises(ValueError, match="no longer current"):
            await action(first)
    assert storage.staged.stage_id == second
    assert storage.timetables == ()
    await storage.async_approve(second)
    with pytest.raises(ValueError, match="no longer current"):
        await storage.async_approve(second)


async def test_approve_replaces_same_source_id_and_keeps_other_year(hass, entry):
    storage = await reload_storage(hass, entry)
    current, next_year, replacement = (
        candidate(),
        candidate(year=2027),
        candidate("06:00"),
    )
    for proposal in (current, next_year):
        await storage.async_approve(await storage.async_stage(proposal))
    await storage.async_approve(await storage.async_stage(replacement))
    assert len(storage.timetables) == 2
    assert storage.approved_sources == {
        "annual-2026": replacement,
        "annual-2027": next_year,
    }
    assert storage.for_date(date(2026, 10, 21)).times[PrayerField.FAJR_BEGIN] == (
        time(6),
    )
    assert storage.for_date(date(2027, 10, 21)).times[PrayerField.FAJR_BEGIN] == (
        time(5, 45),
    )


async def test_overlapping_source_rejected_before_staging(hass, entry):
    storage = await reload_storage(hass, entry)
    original = candidate()
    await storage.async_approve(await storage.async_stage(original))
    with pytest.raises(ValueError, match="Overlapping"):
        await storage.async_stage(candidate("06:00", table_id="different"))
    assert storage.staged is None
    assert storage.timetables == (original.timetable,)


async def test_approval_failure_retains_last_good_and_staged_proposal(hass, entry):
    storage = await reload_storage(hass, entry)
    original, replacement = candidate(), candidate("06:00")
    await storage.async_approve(await storage.async_stage(original))
    stage_id = await storage.async_stage(replacement)
    with (
        patch.object(
            storage._store, "_write_prepared_data", side_effect=WriteError("disk full")
        ),
        pytest.raises(OSError, match="persistence"),
    ):
        await storage.async_approve(stage_id)
    assert storage.timetables == (original.timetable,)
    assert storage.staged.stage_id == stage_id
    reloaded = await reload_storage(hass, entry)
    assert reloaded.timetables == (original.timetable,)
    assert reloaded.staged.candidate == replacement
    await reloaded.async_approve(stage_id)
    assert reloaded.timetables == (replacement.timetable,)


async def test_staging_failure_preserves_approved_source(hass, entry):
    storage = await reload_storage(hass, entry)
    original = candidate()
    await storage.async_approve(await storage.async_stage(original))
    with (
        patch.object(
            storage._store, "async_save", AsyncMock(side_effect=OSError("disk full"))
        ),
        pytest.raises(OSError),
    ):
        await storage.async_stage(candidate("06:00"))
    assert storage.staged is None
    assert storage.timetables == (original.timetable,)
    reloaded = await reload_storage(hass, entry)
    assert reloaded.staged is None
    assert reloaded.timetables == (original.timetable,)


async def test_rejection_failure_keeps_proposal(hass, entry):
    storage = await reload_storage(hass, entry)
    stage_id = await storage.async_stage(candidate())
    with (
        patch.object(
            storage._store, "async_save", AsyncMock(side_effect=OSError("disk full"))
        ),
        pytest.raises(OSError),
    ):
        await storage.async_reject(stage_id)
    assert storage.staged.stage_id == stage_id


async def test_v1_migration_retains_data_without_inventing_provenance(
    hass, entry, timetable
):
    legacy = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}", atomic_writes=True)
    await legacy.async_save({"timetables": [timetable.as_dict()]})
    storage = await reload_storage(hass, entry)
    assert storage.timetables == (timetable,)
    assert storage.approved_sources == {}
    assert storage.staged is None
    saved = await hass.async_add_executor_job(load_json, legacy.path)
    assert saved["version"] == STORAGE_VERSION == 3
    assert saved["data"]["timetables"] == [timetable.as_dict()]
    assert saved["data"]["approved_sources"] == {}
    assert (await reload_storage(hass, entry)).timetables == (timetable,)


async def test_invalid_v1_does_not_overwrite_source(hass, entry):
    legacy = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}", atomic_writes=True)
    await legacy.async_save({"timetables": [{"id": "broken"}]})
    before = await hass.async_add_executor_job(Path(legacy.path).read_bytes)
    with pytest.raises(KeyError):
        await reload_storage(hass, entry)
    after = await hass.async_add_executor_job(Path(legacy.path).read_bytes)
    assert before == after


async def test_failed_migration_does_not_claim_persisted_upgrade(
    hass, entry, timetable
):
    legacy = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}", atomic_writes=True)
    await legacy.async_save({"timetables": [timetable.as_dict()]})
    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    with (
        patch.object(
            storage._store, "_write_prepared_data", side_effect=WriteError("disk full")
        ),
        pytest.raises(OSError, match="persistence"),
    ):
        await storage.async_load()
    assert storage.timetables == ()
    saved = await hass.async_add_executor_job(load_json, legacy.path)
    assert saved["version"] == 1
    assert (await reload_storage(hass, entry)).timetables == (timetable,)


async def test_legacy_replace_discards_only_obsolete_provenance(hass, entry):
    storage = await reload_storage(hass, entry)
    original = candidate()
    await storage.async_approve(await storage.async_stage(original))
    await storage.async_replace((original.timetable,))
    assert storage.approved_sources == {"annual-2026": original}
    modified = Timetable(
        "annual-2026",
        "annual",
        (DailyPrayers(date(2026, 10, 21), {PrayerField.FAJR_BEGIN: (time(7),)}, {}),),
    )
    await storage.async_replace((modified,))
    assert storage.approved_sources == {}
    assert storage.timetables == (modified,)


async def test_ramadan_source_is_approved_but_not_implicitly_applied(hass, entry):
    storage = await reload_storage(hass, entry)
    await storage.async_approve(await storage.async_stage(candidate(kind="ramadan")))
    assert "ramadan-2026" in storage.approved_sources
    assert storage.for_date(date(2026, 10, 21)) is None


async def test_entry_storage_isolation(hass, entry):
    first = await reload_storage(hass, entry)
    second = TimetableStorage(hass, "another-entry", ZoneInfo("Europe/London"))
    await second.async_load()
    stage_id = await first.async_stage(candidate())
    assert second.staged is None
    with pytest.raises(ValueError, match="no longer current"):
        await second.async_approve(stage_id)
    await first.async_approve(stage_id)
    await second.async_load()
    assert second.timetables == ()
    assert second.approved_sources == {}


async def test_concurrent_staging_preserves_first_proposal(hass, entry):
    storage = await reload_storage(hass, entry)
    first, second = candidate(), candidate("06:00")
    results = await gather(
        storage.async_stage(first), storage.async_stage(second), return_exceptions=True
    )
    assert isinstance(results[0], str)
    assert isinstance(results[1], PendingImportError)
    assert storage.staged.stage_id == results[0]
    assert storage.staged.candidate == first
    assert storage.timetables == ()
    reloaded = await reload_storage(hass, entry)
    assert reloaded.staged == storage.staged


@pytest.mark.parametrize(
    "data",
    [
        [],
        {"timetables": {}},
        {
            "timetables": [
                {
                    "id": "test",
                    "kind": "annual",
                    "days": [{"date": "2026-01-01", "times": [], "original": {}}],
                }
            ]
        },
        {"timetables": [], "approved_sources": [], "staged": None},
    ],
)
async def test_malformed_storage_structure_is_a_validation_error(hass, entry, data):
    storage = await reload_storage(hass, entry)
    with (
        patch.object(storage._store, "async_load", AsyncMock(return_value=data)),
        pytest.raises(ValueError),
    ):
        await storage.async_load()
    assert storage.timetables == ()
    assert storage.staged is None


async def test_two_instances_serialize_staging_for_same_entry(hass, entry):
    first = await reload_storage(hass, entry)
    second = await reload_storage(hass, entry)
    assert first._lock is second._lock
    first_candidate, second_candidate = candidate(), candidate("06:00")
    results = await gather(
        first.async_stage(first_candidate),
        second.async_stage(second_candidate),
        return_exceptions=True,
    )
    assert isinstance(results[0], str)
    assert isinstance(results[1], PendingImportError)
    assert second.staged == first.staged
    assert (await reload_storage(hass, entry)).staged.candidate == first_candidate


async def test_stale_instances_refresh_before_all_import_transactions(hass, entry):
    first = await reload_storage(hass, entry)
    second = await reload_storage(hass, entry)
    current_year, next_year = candidate(), candidate(year=2027)
    await first.async_approve(await first.async_stage(current_year))
    assert second.timetables == ()
    next_stage = await second.async_stage(next_year)
    assert second.timetables == (current_year.timetable,)
    # The old first instance has never observed next_stage. Rejecting it reads
    # the exact latest proposal rather than using its stale in-memory snapshot.
    await first.async_reject(next_stage)
    assert first.staged is None
    with pytest.raises(ValueError, match="no longer current"):
        await second.async_approve(next_stage)
    next_stage = await first.async_stage(next_year)
    await second.async_approve(next_stage)
    assert len(second.timetables) == 2
    replacement = candidate("06:00")
    replacement_stage = await first.async_stage(replacement)
    await second.async_approve(replacement_stage)
    reloaded = await reload_storage(hass, entry)
    assert reloaded.approved_sources == {
        "annual-2026": replacement,
        "annual-2027": next_year,
    }
    assert len(reloaded.timetables) == 2
