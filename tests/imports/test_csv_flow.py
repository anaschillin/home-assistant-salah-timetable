"""Exercise CSV approval through HA options flows and authenticated uploads."""

from datetime import date
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from aiohttp import FormData
from homeassistant.components.file_upload import DOMAIN as UPLOAD_DATA
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er

from custom_components.salah_timetable.const import DOMAIN
from custom_components.salah_timetable.parsers.import_model import MAX_SOURCE_BYTES

CSV = b"Date,Fajr Start,Fajr Jamaat\n2026-10-21,05:45,06:15\n2026-10-22,05:47,06:15\n"
REPLACEMENT_CSV = b"Date,Fajr Start,Fajr Jamaat\n2026-10-21,05:55,06:25\n"


@pytest.fixture(autouse=True)
def import_clock(freezer):
    """Freeze before HA creates bearer tokens so their issue time stays valid."""
    freezer.move_to("2026-10-21 10:00:00+00:00")


@pytest.fixture
async def upload_client(authenticated_upload_client):
    return authenticated_upload_client


async def upload(hass, client, content=CSV):
    body = FormData()
    body.add_field("file", content, filename="timetable.csv", content_type="text/csv")
    response = await client.post("/api/file_upload", data=body)
    assert response.status == 200
    file_id = (await response.json())["file_id"]
    path = hass.data[UPLOAD_DATA].file_path(file_id)
    assert await hass.async_add_executor_job(path.is_file)
    return file_id, path


async def begin_import(hass, entry):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert "import_csv" in result["menu_options"]
    return await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "import_csv"}
    )


async def stage_upload(hass, entry, client, content=CSV, *, kind="annual", year=2026):
    result = await begin_import(hass, entry)
    assert result["step_id"] == "import_csv"
    file_id, path = await upload(hass, client, content)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"file": file_id, "kind": kind, "year": year}
    )
    assert result["step_id"] == "map_columns"
    assert not await hass.async_add_executor_job(path.exists)
    assert file_id not in hass.data[UPLOAD_DATA].files
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "date_column": "Date",
            "time_format": "24h",
            "fajr_begin": "Fajr Start",
            "fajr_jamaat": "Fajr Jamaat",
        },
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "review"
    assert "summary" in result["description_placeholders"]
    return result


async def test_upload_preview_approve_and_reload(hass, entry, freezer, upload_client):
    freezer.move_to("2026-10-21 10:00:00+00:00")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, "example_fajr_begin"
    )
    assert hass.states.get(entity_id).state == "unavailable"
    result = await stage_upload(hass, entry, upload_client)
    storage = entry.runtime_data.storage
    assert storage.staged is not None
    assert storage.for_date(date(2026, 10, 21)) is None
    assert hass.states.get(entity_id).state == "unavailable"
    assert "missing" in result["description_placeholders"]["summary"].lower()
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": "approve"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "2026-10-21T04:45:00+00:00"
    assert entry.runtime_data.storage.staged is None
    assert (
        entry.runtime_data.storage.approved_sources["annual-2026"].source_text
        == CSV.decode()
    )
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "2026-10-21T04:45:00+00:00"
    assert entry.options == {}


async def test_approved_manual_mapping_is_suggested_after_reload(
    hass, entry, upload_client
):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await begin_import(hass, entry)
    file_id, _ = await upload(
        hass, upload_client, b"Published,Dawn clock,Note\n2026-10-21,05:45,old\n"
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"file": file_id, "kind": "annual", "year": 2026}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"date_column": "Published", "time_format": "24h", "fajr_begin": "Dawn clock"},
    )
    await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": "approve"}
    )
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    result = await begin_import(hass, entry)
    file_id, _ = await upload(
        hass, upload_client, b"Note,Dawn clock,Published\nnew,05:50,2027-10-21\n"
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"file": file_id, "kind": "annual", "year": 2027}
    )
    schema = result["data_schema"].schema

    def default(name):
        return next(key.default() for key in schema if key.schema == name)

    assert default("date_column") == "Published"
    assert default("fajr_begin") == "Dawn clock"
    assert default("isha_begin") == "__ignore__"
    assert "previously approved" in result["description_placeholders"]["detail"]
    assert entry.runtime_data.storage.staged is None


async def test_cross_year_upload_approves_both_dates_together(
    hass, entry, upload_client
):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await stage_upload(
        hass,
        entry,
        upload_client,
        b"Date,Fajr Start,Fajr Jamaat\n2026-12-31,06:00,06:30\n2027-01-01,06:01,06:31\n",
        kind="cross_year",
    )
    storage = entry.runtime_data.storage
    assert storage.for_date(date(2026, 12, 31)) is None
    assert storage.for_date(date(2027, 1, 1)) is None
    assert "2026-12-31 to 2027-01-01" in result["description_placeholders"]["summary"]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": "approve"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert storage.for_date(date(2026, 12, 31)) is not None
    assert storage.for_date(date(2027, 1, 1)) is not None
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.storage.for_date(date(2027, 1, 1)) is not None


async def test_pending_survives_cancel_reload_and_new_flow(hass, entry, upload_client):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await stage_upload(hass, entry, upload_client)
    stage_id = entry.runtime_data.storage.staged.stage_id
    hass.config_entries.options.async_abort(result["flow_id"])
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.storage.staged.stage_id == stage_id
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert "review" in result["menu_options"]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "review"}
    )
    assert result["step_id"] == "review"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": "approve"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.runtime_data.storage.for_date(date(2026, 10, 21)) is not None


async def test_rejection_preserves_active_data(hass, populated, freezer, upload_client):
    freezer.move_to("2026-10-21 10:00:00+00:00")
    assert await hass.config_entries.async_setup(populated.entry_id)
    await hass.async_block_till_done()
    previous = populated.runtime_data.storage.timetables
    result = await stage_upload(hass, populated, upload_client, REPLACEMENT_CSV)
    assert populated.runtime_data.storage.timetables == previous
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": "reject"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert populated.runtime_data.storage.timetables == previous
    assert populated.runtime_data.storage.staged is None
    assert await hass.config_entries.async_reload(populated.entry_id)
    await hass.async_block_till_done()
    assert populated.runtime_data.storage.timetables == previous


@pytest.mark.parametrize(
    "content",
    [
        b"\xff\xfeinvalid",
        b"Date,Fajr\n2026-10-21,05:45,extra\n",
        b"x" * (MAX_SOURCE_BYTES + 1),
    ],
    ids=["invalid-encoding", "extra-columns", "oversized-source"],
)
async def test_invalid_upload_is_removed(hass, entry, upload_client, content):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await begin_import(hass, entry)
    file_id, path = await upload(hass, upload_client, content)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"file": file_id, "kind": "annual", "year": 2026}
    )
    assert result["step_id"] == "import_csv"
    assert result["errors"] == {"base": "invalid_csv"}
    assert not await hass.async_add_executor_job(path.exists)
    assert file_id not in hass.data[UPLOAD_DATA].files
    assert entry.runtime_data.storage.staged is None


async def test_unknown_csv_kind_is_rejected_after_upload(hass, entry, upload_client):
    """A direct flow call cannot stage a kind outside the offered choices."""
    from custom_components.salah_timetable.imports.import_flow import (
        CsvImportOptionsFlow,
    )

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    file_id, path = await upload(hass, upload_client)
    flow = CsvImportOptionsFlow()
    flow.hass = hass
    flow._coordinator = lambda: entry.runtime_data
    result = await flow.async_step_import_csv(
        {"file": file_id, "kind": "unknown", "year": 2026}
    )
    assert result["step_id"] == "import_csv"
    assert result["errors"] == {"base": "invalid_csv"}
    assert "valid timetable type" in result["description_placeholders"]["detail"]
    assert not await hass.async_add_executor_job(path.exists)
    assert entry.runtime_data.storage.staged is None


async def test_missing_upload_is_reported(hass, entry):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await begin_import(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"file": uuid4().hex, "kind": "annual", "year": 2026}
    )
    assert result["step_id"] == "import_csv"
    assert result["errors"] == {"base": "invalid_csv"}
    assert entry.runtime_data.storage.staged is None


async def test_duplicate_mapping_is_rejected(hass, entry, upload_client):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await begin_import(hass, entry)
    file_id, _ = await upload(hass, upload_client)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"file": file_id, "kind": "annual", "year": 2026}
    )
    assert result["step_id"] == "map_columns"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "date_column": "Date",
            "time_format": "24h",
            "fajr_begin": "Fajr Start",
            "fajr_jamaat": "Fajr Start",
        },
    )
    assert result["step_id"] == "map_columns"
    assert result["errors"] == {"base": "invalid_mapping"}
    assert entry.runtime_data.storage.staged is None


async def test_unloaded_entry_cannot_start_import(hass, entry):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "import_csv"}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "integration_not_loaded"


async def test_stage_save_failure_can_be_retried(hass, entry, upload_client):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await begin_import(hass, entry)
    file_id, _ = await upload(hass, upload_client)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"file": file_id, "kind": "annual", "year": 2026}
    )
    mapping = {"date_column": "Date", "time_format": "24h", "fajr_begin": "Fajr Start"}
    with patch.object(
        entry.runtime_data.storage,
        "async_stage",
        AsyncMock(side_effect=OSError("disk full")),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], mapping
        )
    assert result["step_id"] == "map_columns"
    assert result["errors"] == {"base": "save_failed"}
    assert entry.runtime_data.storage.staged is None
    assert entry.runtime_data.storage.timetables == ()
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], mapping
    )
    assert result["step_id"] == "review"
    assert entry.runtime_data.storage.staged is not None
    assert entry.runtime_data.storage.timetables == ()


async def test_approval_save_failure_keeps_pending_and_active(
    hass, populated, upload_client
):
    assert await hass.config_entries.async_setup(populated.entry_id)
    await hass.async_block_till_done()
    previous = populated.runtime_data.storage.timetables
    result = await stage_upload(hass, populated, upload_client, REPLACEMENT_CSV)
    staged = populated.runtime_data.storage.staged
    with patch.object(
        populated.runtime_data.storage,
        "async_approve",
        AsyncMock(side_effect=OSError("disk full")),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"decision": "approve"}
        )
    assert result["step_id"] == "review"
    assert result["errors"] == {"base": "save_failed"}
    assert populated.runtime_data.storage.timetables == previous
    assert populated.runtime_data.storage.staged == staged
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": "approve"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert populated.runtime_data.storage.staged is None
    assert populated.runtime_data.storage.timetables != previous


async def test_stale_preview_cannot_approve_new_stage(hass, entry, upload_client):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await stage_upload(hass, entry, upload_client)
    old = entry.runtime_data.storage.staged
    await entry.runtime_data.storage.async_reject(old.stage_id)
    current_id = await entry.runtime_data.storage.async_stage(old.candidate)
    assert current_id != old.stage_id
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": "approve"}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "stale_import"
    assert entry.runtime_data.storage.staged.stage_id == current_id
    assert entry.runtime_data.storage.timetables == ()


async def test_next_year_approval_preserves_current_year(
    hass, populated, upload_client
):
    assert await hass.config_entries.async_setup(populated.entry_id)
    await hass.async_block_till_done()
    previous = populated.runtime_data.storage.for_date(date(2026, 10, 21))
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, "example_fajr_begin"
    )
    state = hass.states.get(entity_id).state
    result = await stage_upload(
        hass, populated, upload_client, CSV.replace(b"2026-", b"2027-"), year=2027
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": "approve"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert populated.runtime_data.storage.for_date(date(2026, 10, 21)) == previous
    assert populated.runtime_data.storage.for_date(date(2027, 10, 21)) is not None
    assert hass.states.get(entity_id).state == state
    assert {
        table.timetable_id for table in populated.runtime_data.storage.timetables
    } == {"annual-2026", "annual-2027"}


async def test_unconfirmed_ramadan_approval_does_not_apply_overrides(
    hass, populated, upload_client
):
    assert await hass.config_entries.async_setup(populated.entry_id)
    await hass.async_block_till_done()
    previous = populated.runtime_data.storage.for_date(date(2026, 10, 21))
    result = await stage_upload(
        hass, populated, upload_client, REPLACEMENT_CSV, kind="ramadan"
    )
    assert "only on confirmed dates" in result["description_placeholders"]["summary"]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": "approve"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert "ramadan-2026" in populated.runtime_data.storage.approved_sources
    assert populated.runtime_data.storage.for_date(date(2026, 10, 21)) == previous
    assert populated.runtime_data.data.effective.row == previous
    assert populated.runtime_data.data.effective.ramadan_active is False


async def test_conflicting_ramadan_approval_stays_reviewable_and_can_be_rejected(
    hass, entry, upload_client
):
    from zoneinfo import ZoneInfo

    from custom_components.salah_timetable.parsers.csv_parser import CsvParser
    from custom_components.salah_timetable.persistence.storage import TimetableStorage

    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    original = CsvParser().parse(
        CSV,
        timetable_id="legacy-ramadan",
        kind="ramadan",
        year=2026,
        date_column="Date",
        columns={"Fajr Start": "fajr_begin", "Fajr Jamaat": "fajr_jamaat"},
    )
    await storage.async_approve(await storage.async_stage(original))
    hass.config_entries.async_update_entry(entry, options={"ramadan_mode": "on"})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await stage_upload(
        hass, entry, upload_client, REPLACEMENT_CSV, kind="ramadan"
    )
    staged = entry.runtime_data.storage.staged
    assert "Unresolved dates" in result["description_placeholders"]["summary"]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": "approve"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "ramadan_conflict"}
    assert entry.runtime_data.storage.timetables == (original.timetable,)
    assert entry.runtime_data.storage.staged == staged
    assert entry.runtime_data.last_update_success
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": "reject"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.runtime_data.storage.timetables == (original.timetable,)
    assert entry.runtime_data.storage.staged is None


async def test_fractional_year_does_not_consume_upload(hass, entry, upload_client):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await begin_import(hass, entry)
    file_id, path = await upload(hass, upload_client)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"file": file_id, "kind": "annual", "year": 2026.5}
    )
    assert result["step_id"] == "import_csv"
    assert result["errors"] == {"base": "invalid_csv"}
    assert "whole number" in result["description_placeholders"]["detail"]
    assert await hass.async_add_executor_job(path.exists)
    assert file_id in hass.data[UPLOAD_DATA].files
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"file": file_id, "kind": "annual", "year": 2026}
    )
    assert result["step_id"] == "map_columns"
    assert not await hass.async_add_executor_job(path.exists)
    assert file_id not in hass.data[UPLOAD_DATA].files


async def test_two_mapping_flows_cannot_overwrite_pending_import(
    hass, entry, upload_client
):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    flows = []
    for content in (CSV, REPLACEMENT_CSV):
        result = await begin_import(hass, entry)
        file_id, _ = await upload(hass, upload_client, content)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"file": file_id, "kind": "annual", "year": 2026}
        )
        assert result["step_id"] == "map_columns"
        flows.append(result["flow_id"])
    mapping = {"date_column": "Date", "time_format": "24h", "fajr_begin": "Fajr Start"}
    first = await hass.config_entries.options.async_configure(flows[0], mapping)
    assert first["step_id"] == "review"
    staged = entry.runtime_data.storage.staged
    second = await hass.config_entries.options.async_configure(flows[1], mapping)
    assert second["type"] == FlowResultType.ABORT
    assert second["reason"] == "pending_import_exists"
    assert entry.runtime_data.storage.staged == staged
    assert entry.runtime_data.storage.staged.candidate.source_text == CSV.decode()
    assert entry.runtime_data.storage.timetables == ()


async def test_reloaded_preview_requires_reopening_review(hass, entry, upload_client):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await stage_upload(hass, entry, upload_client)
    stage_id = entry.runtime_data.storage.staged.stage_id
    hass.config_entries.async_update_entry(entry, options={"time_zone": "Asia/Riyadh"})
    await hass.async_block_till_done()
    assert entry.runtime_data.zone.key == "Asia/Riyadh"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": "approve"}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "integration_reloaded"
    assert entry.runtime_data.storage.staged.stage_id == stage_id
    assert entry.runtime_data.storage.timetables == ()
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "review"}
    )
    assert result["step_id"] == "review"
    assert "Asia/Riyadh" in result["description_placeholders"]["summary"]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": "approve"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.runtime_data.storage.staged is None
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, "example_fajr_begin"
    )
    assert hass.states.get(entity_id).state == "2026-10-21T02:45:00+00:00"


async def test_comparison_review_is_read_only_and_returns_to_reject(
    hass, populated, upload_client
):
    assert await hass.config_entries.async_setup(populated.entry_id)
    await hass.async_block_till_done()
    result = await stage_upload(hass, populated, upload_client, REPLACEMENT_CSV)
    store = populated.runtime_data.storage
    approved = store.timetables
    staged_id = store.staged.stage_id
    assert "Compare changes" in result["description_placeholders"]["summary"]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": "compare"}
    )
    assert result["step_id"] == "compare"
    details = result["description_placeholders"]["detail"]
    assert "2026-10-22 — date removed" in details
    assert "fajr begin: **05:45 → 05:55**" in details
    assert "Original mapped cells:" in details
    assert store.timetables == approved
    assert store.staged.stage_id == staged_id

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"action": "review"}
    )
    assert result["step_id"] == "review"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": "reject"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert store.timetables == approved
    assert store.staged is None


async def test_large_comparison_paginates_without_approving(hass, entry, upload_client):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    content = (
        "Date,Fajr Start,Fajr Jamaat\n"
        + "".join(f"2026-10-{day:02d},05:45,06:15\n" for day in range(1, 32))
    ).encode()
    result = await stage_upload(hass, entry, upload_client, content)
    store = entry.runtime_data.storage
    assert not store.timetables
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": "compare"}
    )
    assert result["step_id"] == "compare"
    first = result["description_placeholders"]["detail"]
    # Each new date has a date entry, two canonical fields (with their mapped
    # source tokens), and the original Date cell: 124 entries over 13 pages.
    assert "page 1 of 13" in first
    assert "Comparison entries 1–10 of 124" in first
    assert "- 2026-10-01 — date added" in first
    assert "- 2026-10-04 — date added" not in first
    pages = [first]
    for page in range(2, 14):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"action": "next"}
        )
        detail = result["description_placeholders"]["detail"]
        assert f"page {page} of 13" in detail
        pages.append(detail)
        assert not store.timetables
        assert store.staged is not None
    all_changes = "\n".join(pages)
    for day in range(1, 32):
        assert f"- 2026-10-{day:02d} — date added" in all_changes
        assert f"- 2026-10-{day:02d} — fajr begin: **absent → 05:45**" in all_changes
        assert f"- 2026-10-{day:02d} — fajr jamaat: **absent → 06:15**" in all_changes
        assert f"- 2026-10-{day:02d} — original cell Date:" in all_changes
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"action": "previous"}
    )
    assert "page 12 of 13" in result["description_placeholders"]["detail"]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"action": "review"}
    )
    assert result["step_id"] == "review"
    assert not store.timetables
    assert store.staged is not None
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": "approve"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert store.staged is None
    assert len(store.timetables[0].days) == 31


async def _open_mapped_csv_form(hass, entry, client):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    form = await begin_import(hass, entry)
    file_id, _ = await upload(hass, client)
    form = await hass.config_entries.options.async_configure(
        form["flow_id"], {"file": file_id, "kind": "annual", "year": 2026}
    )
    assert form["step_id"] == "map_columns"
    return form


async def test_mapping_does_not_accept_changes_after_entry_unloaded(
    hass, entry, upload_client
):
    form = await _open_mapped_csv_form(hass, entry, upload_client)
    assert await hass.config_entries.async_unload(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        form["flow_id"],
        {"date_column": "Date", "time_format": "24h", "fajr_begin": "Fajr Start"},
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "integration_not_loaded"


async def test_mapping_does_not_stage_when_runtime_changes_during_parse(
    hass, entry, upload_client
):
    from custom_components.salah_timetable.imports.import_flow import (
        CsvImportOptionsFlow,
    )

    form = await _open_mapped_csv_form(hass, entry, upload_client)
    # Simulate the runtime changing immediately after the executor parses
    # a candidate. The old options flow must not stage against a retired entry.
    old_runtime = entry.runtime_data
    with patch.object(
        CsvImportOptionsFlow, "_coordinator", side_effect=[old_runtime, None]
    ) as current:
        result = await hass.config_entries.options.async_configure(
            form["flow_id"],
            {"date_column": "Date", "time_format": "24h", "fajr_begin": "Fajr Start"},
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "integration_reloaded"
    assert current.call_count == 2
    assert entry.runtime_data.storage.staged is None


async def test_uninitialised_mapping_step_fails_without_upload():
    from custom_components.salah_timetable.config_flow import SalahOptionsFlow

    flow = SalahOptionsFlow()
    result = await flow.async_step_map_columns()
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "upload_expired"


@pytest.mark.parametrize(
    ("monthly", "remote", "reload_after"),
    [(True, False, 2), (False, True, 2), (True, True, 3)],
    ids=["monthly-identity", "remote-provenance", "monthly-remote-provenance"],
)
async def test_reload_during_candidate_preparation_does_not_persist_proposal(
    hass, entry, monthly, remote, reload_after
):
    """A retired runtime must not stage a proposal after executor preparation."""
    from types import SimpleNamespace

    from custom_components.salah_timetable.imports.import_flow import (
        CsvImportOptionsFlow,
    )

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    original = entry.runtime_data
    flow = CsvImportOptionsFlow()
    flow.hass = hass
    flow._content = CSV
    flow._year = 2026
    flow._monthly = monthly
    flow._coordinator = lambda: entry.runtime_data
    if remote:
        flow._remote_url = "https://mosque.example.org/timetable.csv"
        flow._download_result = SimpleNamespace(etag=None, last_modified=None)

    executor = hass.async_add_executor_job
    completed = 0
    reloaded = False

    async def reload_after_preparation(target, *args):
        nonlocal completed, reloaded
        result = await executor(target, *args)
        completed += 1
        if not reloaded and completed == reload_after:
            reloaded = True
            assert await hass.config_entries.async_reload(entry.entry_id)
            await hass.async_block_till_done()
        return result

    with patch.object(
        hass, "async_add_executor_job", side_effect=reload_after_preparation
    ):
        staged = await flow._stage_mapped_candidate(
            {"date_column": "Date", "time_format": "24h"},
            {"Fajr Start": "fajr_begin"},
            original,
        )

    assert reloaded
    assert entry.runtime_data is not original
    assert not staged
    assert original.storage.staged is None
    await entry.runtime_data.storage.async_load()
    assert entry.runtime_data.storage.staged is None
    assert entry.runtime_data.storage.remote_sources == {}
    assert entry.runtime_data.storage.timetables == ()
