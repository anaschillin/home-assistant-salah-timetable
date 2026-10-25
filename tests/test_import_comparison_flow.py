"""HA review pagination and compare-and-swap approval against real disk stores."""

from datetime import date, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.storage import Store
from homeassistant.util.json import load_json

from custom_components.salah_timetable.config_flow import SalahOptionsFlow
from custom_components.salah_timetable.const import DOMAIN, STORAGE_VERSION
from custom_components.salah_timetable.csv_parser import CsvParser
from custom_components.salah_timetable.model import Timetable
from custom_components.salah_timetable.publication_profiles import publication_profile
from custom_components.salah_timetable.source_flow import ProfiledPdfParser
from custom_components.salah_timetable.storage import (
    ImportReviewBaseline,
    ReviewChangedError,
    TimetableStorage,
)


@pytest.fixture(autouse=True)
def import_clock(freezer):
    freezer.move_to("2026-10-21T03:00:00Z")


def candidate(value="05:45", *, count=1, year=2026, notes="printed", bom=False):
    first = date(year, 10, 21)
    text = "Date,Fajr Begin,Notes\n" + "".join(
        f"{first + timedelta(days=offset)},{value},{notes}\n" for offset in range(count)
    )
    return CsvParser().parse(
        (("\ufeff" if bom else "") + text).encode(),
        timetable_id=f"annual-{year}",
        kind="annual",
        year=year,
        date_column="Date",
        columns={"Fajr Begin": "fajr_begin"},
    )


async def loaded(hass, entry, previous=None):
    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    if previous is not None:
        await storage.async_approve(await storage.async_stage(previous))
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry.runtime_data.storage


async def open_review(hass, entry):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert "review" in result["menu_options"]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "review"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "review"
    return result


async def choose(hass, result, decision):
    return await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": decision}
    )


async def compare(hass, result):
    result = await choose(hass, result, "compare")
    assert result["step_id"] == "compare"
    return result


async def act(hass, result, action):
    return await hass.config_entries.options.async_configure(
        result["flow_id"], {"action": action}
    )


def summary(result):
    placeholders = result["description_placeholders"]
    return placeholders.get("summary", placeholders.get("detail"))


def choices(result):
    decision_selector = next(iter(result["data_schema"].schema.values()))
    return decision_selector.config["options"]


async def test_first_import_shows_additions_and_keeps_approval_explicit(hass, entry):
    storage = await loaded(hass, entry)
    proposal = candidate()
    stage_id = await storage.async_stage(proposal)
    result = await open_review(hass, entry)
    assert "Import comparison — page" not in summary(result)
    assert "First import for this source ID" in summary(result)
    assert "Dates added: **1**" in summary(result)
    assert "Field entries added: **1**" in summary(result)
    assert "Additional original-cell changes: **2**" in summary(result)
    assert choices(result) == ["compare", "approve", "reject"]
    result = await compare(hass, result)
    assert "Import comparison — page 1 of 1" in summary(result)
    assert "2026-10-21 — fajr begin" in summary(result)
    assert choices(result) == ["review"]
    assert storage.staged.stage_id == stage_id
    assert storage.timetables == ()
    result = await act(hass, result, "review")
    result = await choose(hass, result, "approve")
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert storage.staged is None
    assert storage.timetables == (proposal.timetable,)


async def test_every_change_is_reachable_and_paging_never_makes_a_decision(hass, entry):
    previous = candidate(count=21)
    storage = await loaded(hass, entry, previous)
    proposal = candidate("05:55", count=21)
    stage_id = await storage.async_stage(proposal)
    result = await open_review(hass, entry)
    assert "Field entries changed: **21**" in summary(result)
    result = await compare(hass, result)
    assert "Import comparison — page 1 of 3" in summary(result)
    assert "previous" not in choices(result)
    for page in (2, 3):
        result = await act(hass, result, "next")
        assert f"Import comparison — page {page} of 3" in summary(result)
        assert storage.staged.stage_id == stage_id
        assert storage.timetables == (previous.timetable,)
        assert "previous" in choices(result)
        assert "approve" not in choices(result)
        assert "reject" not in choices(result)
    assert "next" not in choices(result)
    assert "2026-11-10 — fajr begin: **05:45 → 05:55**" in summary(result)
    result = await act(hass, result, "previous")
    assert "Import comparison — page 2 of 3" in summary(result)
    result = await act(hass, result, "review")
    result = await choose(hass, result, "approve")
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert storage.staged is None
    assert storage.approved_sources["annual-2026"] == proposal


async def test_all_original_only_changes_are_paged_without_claiming_prayer_changes(
    hass, entry
):
    previous = candidate(count=21, notes="old note")
    storage = await loaded(hass, entry, previous)
    proposal = candidate(count=21, notes="new note")
    await storage.async_stage(proposal)
    result = await open_review(hass, entry)
    assert "Canonical prayer values and dates are unchanged." in summary(result)
    assert "Additional original-cell changes: **21**" in summary(result)
    assert "Field entries changed: **0**" in summary(result)
    result = await compare(hass, result)
    result = await act(hass, result, "next")
    result = await act(hass, result, "next")
    assert "2026-11-10 — original cell Notes: “old note” → “new note”" in summary(
        result
    )
    result = await act(hass, result, "review")
    result = await choose(hass, result, "reject")
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert storage.staged is None
    assert storage.approved_sources["annual-2026"] == previous


async def test_cancel_and_reload_preserve_proposal_and_restart_comparison_at_page_one(
    hass, entry
):
    previous = candidate(count=21)
    storage = await loaded(hass, entry, previous)
    stage_id = await storage.async_stage(candidate("05:55", count=21))
    result = await open_review(hass, entry)
    result = await compare(hass, result)
    result = await act(hass, result, "next")
    hass.config_entries.options.async_abort(result["flow_id"])
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    result = await open_review(hass, entry)
    result = await compare(hass, result)
    assert "Import comparison — page 1 of 3" in summary(result)
    assert entry.runtime_data.storage.staged.stage_id == stage_id
    assert entry.runtime_data.storage.approved_sources["annual-2026"] == previous


async def test_byte_only_update_is_distinguished_from_dated_value_changes(hass, entry):
    previous = candidate()
    storage = await loaded(hass, entry, previous)
    proposal = candidate(bom=True)
    assert proposal.timetable == previous.timetable
    assert proposal.sha256 != previous.sha256
    await storage.async_stage(proposal)
    result = await open_review(hass, entry)
    assert "Canonical prayer values and dates are unchanged." in summary(result)
    assert "Source bytes or provenance metadata changed." in summary(result)
    assert choices(result) == ["compare", "approve", "reject"]
    result = await compare(hass, result)
    assert "No dated value or original-cell changes to display." in summary(result)
    assert choices(result) == ["review"]


@pytest.mark.parametrize("existing", [False, True])
async def test_changed_approved_baseline_requires_fresh_review_and_another_approve(
    hass, entry, existing
):
    previous = candidate(count=21) if existing else None
    storage = await loaded(hass, entry, previous)
    proposal = candidate("05:55", count=21)
    stage_id = await storage.async_stage(proposal)
    result = await open_review(hass, entry)
    result = await compare(hass, result)
    result = await act(hass, result, "next")
    result = await act(hass, result, "review")
    # Another runtime writes the target source while keeping the same proposal.
    external = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    changed = candidate("06:00", count=21)
    await external.async_replace((changed.timetable,))
    assert external.staged.stage_id == stage_id
    result = await choose(hass, result, "approve")
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "review_changed"}
    # async_replace has no approved import provenance. The old mapping is
    # therefore unknown, so all 21 changed raw Fajr cells remain inspectable
    # beside the 21 canonical changes: 42 entries, five pages.
    assert "Field entries changed: **21**" in summary(result)
    assert "Additional original-cell changes: **21**" in summary(result)
    assert "Previous source provenance is unavailable" in summary(result)
    result = await compare(hass, result)
    assert "Import comparison — page 1 of 5" in summary(result)
    assert "2026-10-21 — original cell Fajr Begin: “06:00” → “05:55”" in summary(result)
    assert "**06:00 → 05:55**" in summary(result)
    assert storage.staged.stage_id == stage_id
    assert storage.timetables == (changed.timetable,)
    result = await act(hass, result, "review")
    result = await choose(hass, result, "approve")
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert storage.staged is None
    assert storage.timetables == (proposal.timetable,)


async def test_changed_baseline_on_page_turn_resets_to_fresh_first_page(hass, entry):
    storage = await loaded(hass, entry, candidate(count=21))
    await storage.async_stage(candidate("05:55", count=21))
    result = await open_review(hass, entry)
    result = await compare(hass, result)
    external = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    await external.async_replace((candidate("06:00", count=21).timetable,))
    result = await act(hass, result, "next")
    assert result["errors"] == {"base": "review_changed"}
    assert "Import comparison — page 1 of 5" in summary(result)
    assert "Field entries changed: **21**" in summary(result)
    assert "Additional original-cell changes: **21**" in summary(result)
    assert "previous" not in choices(result)
    assert storage.staged is not None


async def test_unrelated_source_and_mosque_updates_do_not_invalidate_review(
    hass, entry
):
    original = candidate()
    storage = await loaded(hass, entry, original)
    proposal = candidate("05:55")
    await storage.async_stage(proposal)
    result = await open_review(hass, entry)
    external = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    next_year = candidate(year=2027)
    await external.async_replace((original.timetable, next_year.timetable))
    other = TimetableStorage(hass, "other-mosque-entry", ZoneInfo("Europe/London"))
    other_source = candidate("06:30")
    await other.async_approve(await other.async_stage(other_source))
    result = await choose(hass, result, "approve")
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert set(table.timetable_id for table in storage.timetables) == {
        "annual-2026",
        "annual-2027",
    }
    assert storage.approved_sources["annual-2026"] == proposal
    await other.async_load()
    assert other.timetables == (other_source.timetable,)


async def test_legacy_same_id_multiyear_rows_are_included_in_replacement_review(
    hass, entry
):
    storage = await loaded(hass, entry)
    old = Timetable(
        "annual-2026",
        "annual",
        (*candidate(year=2025).timetable.days, *candidate().timetable.days),
    )
    await storage.async_replace((old,))
    await storage.async_stage(candidate("05:55"))
    result = await open_review(hass, entry)
    assert "Annual 2025–2026" in summary(result)
    assert "Dates removed: **1**" in summary(result)
    assert "Previous source provenance is unavailable" in summary(result)
    result = await compare(hass, result)
    assert "2025-10-21 — date removed" in summary(result)


async def test_unrecognized_direct_review_action_never_rejects_pending_data(
    hass, entry
):
    storage = await loaded(hass, entry)
    stage_id = await storage.async_stage(candidate())
    flow = SalahOptionsFlow()
    flow.hass = hass
    flow.handler = entry.entry_id
    await flow.async_step_review()
    result = await flow.async_step_review({"decision": "unexpected"})
    assert result["errors"] == {"base": "invalid_import_decision"}
    result = await flow.async_step_review({"decision": "compare"})
    assert result["step_id"] == "compare"
    result = await flow.async_step_compare({"action": "approve"})
    assert result["errors"] == {"base": "invalid_import_decision"}
    assert storage.staged.stage_id == stage_id
    assert storage.timetables == ()


async def test_failed_review_refresh_retains_cached_data_and_blocks_approval(
    hass, entry
):
    previous = candidate()
    storage = await loaded(hass, entry, previous)
    proposal = candidate("05:55")
    stage_id = await storage.async_stage(proposal)
    result = await open_review(hass, entry)
    with patch.object(
        storage, "async_load", AsyncMock(side_effect=OSError("read failed"))
    ):
        result = await choose(hass, result, "approve")
    assert result["errors"] == {"base": "save_failed"}
    assert "Field entries changed: **1**" in summary(result)
    result = await compare(hass, result)
    assert "**05:45 → 05:55**" in summary(result)
    with patch.object(
        storage, "async_load", AsyncMock(side_effect=OSError("read failed"))
    ):
        result = await act(hass, result, "review")
    assert result["step_id"] == "compare"
    assert result["errors"] == {"base": "save_failed"}
    assert "**05:45 → 05:55**" in summary(result)
    assert storage.timetables == (previous.timetable,)
    assert storage.staged.stage_id == stage_id
    result = await act(hass, result, "review")
    result = await choose(hass, result, "approve")
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert storage.staged is None


async def test_storage_compares_approved_provenance_even_when_the_table_is_equal(
    hass, entry
):
    original = candidate()
    storage = await loaded(hass, entry, original)
    stage_id = await storage.async_stage(candidate("05:55"))
    baseline = storage.review_baseline("annual-2026")
    rewritten = candidate(bom=True)
    assert rewritten.timetable == original.timetable
    # Simulate another valid writer updating only approved source provenance.
    store = Store(
        hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}", atomic_writes=True
    )
    payload = (await hass.async_add_executor_job(load_json, store.path))["data"]
    payload["approved_sources"]["annual-2026"] = rewritten.as_dict()
    await store.async_save(payload)
    with pytest.raises(ReviewChangedError):
        await storage.async_approve(stage_id, expected_baseline=baseline)
    assert storage.staged.stage_id == stage_id
    assert storage.approved_sources["annual-2026"] == rewritten
    await storage.async_approve(
        stage_id, expected_baseline=storage.review_baseline("annual-2026")
    )
    assert storage.staged is None


async def test_storage_guard_is_checked_after_loading_current_disk_snapshot(
    hass, entry
):
    storage = await loaded(hass, entry)
    stage_id = await storage.async_stage(candidate("05:55"))
    baseline = ImportReviewBaseline(None, None)
    external = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    changed = candidate("06:00")
    await external.async_replace((changed.timetable,))
    with pytest.raises(ReviewChangedError):
        await storage.async_approve(stage_id, expected_baseline=baseline)
    assert storage.timetables == (changed.timetable,)
    assert storage.staged.stage_id == stage_id


async def test_profile_guard_and_metadata_use_newly_loaded_pending_candidate(
    hass, entry
):
    hass.config_entries.async_update_entry(entry, options={"time_zone": "UTC"})
    storage = await loaded(hass, entry)
    old_stage = await storage.async_stage(candidate(year=2027))
    menu = await hass.config_entries.options.async_init(entry.entry_id)
    # The menu's runtime cache still has a CSV; another runtime replaces only
    # the pending proposal with a valid London publication before review opens.
    external = TimetableStorage(hass, entry.entry_id, ZoneInfo("UTC"))
    await external.async_reject(old_stage)
    profile = publication_profile("nms_annual_2026_v1")
    content = (
        Path(__file__).parent / "fixtures/pdf/nms_synthetic_2026.pdf"
    ).read_bytes()
    proposal = await hass.async_add_executor_job(
        lambda: ProfiledPdfParser(profile).parse(
            content,
            timetable_id="annual-2026",
            kind=profile.kind,
            year=profile.year,
            date_column=profile.date_column,
            columns=dict(profile.columns),
            time_format=profile.time_format,
        )
    )
    stage_id = await external.async_stage(proposal)
    result = await hass.config_entries.options.async_configure(
        menu["flow_id"], {"next_step_id": "review"}
    )
    assert result["errors"] == {"base": "invalid_publication_profile"}
    assert profile.profile_id in summary(result)
    result = await compare(hass, result)
    assert result["errors"] == {"base": "invalid_publication_profile"}
    assert profile.profile_id in summary(result)
    result = await act(hass, result, "review")
    result = await choose(hass, result, "approve")
    assert result["errors"] == {"base": "invalid_publication_profile"}
    assert storage.staged.stage_id == stage_id
    assert storage.timetables == ()
