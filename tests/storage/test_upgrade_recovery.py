"""Historical files and complete backup recovery through HA lifecycle boundaries."""

import json
from datetime import date, time
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import UnsupportedStorageVersionError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.util.file import WriteError

from custom_components.salah_timetable.const import DOMAIN, STORAGE_VERSION
from custom_components.salah_timetable.parsers.csv_parser import CsvParser
from custom_components.salah_timetable.domain.model import PrayerField
from custom_components.salah_timetable.persistence.storage import TimetableStorage

FIXTURES = Path(__file__).parents[1] / "fixtures" / "storage"


def historical_payload(version):
    name = "v1_multi_year.json" if version == 1 else "v2_approved_pending.json"
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


async def write_store(hass, entry, payload, *, version=STORAGE_VERSION, minor=1):
    path = Path(hass.config.path(".storage", f"{DOMAIN}.{entry.entry_id}"))
    content = json.dumps(
        {
            "version": version,
            "minor_version": minor,
            "key": f"{DOMAIN}.{entry.entry_id}",
            "data": payload,
        },
        ensure_ascii=False,
        indent=2,
    ).encode()

    def write():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    await hass.async_add_executor_job(write)
    return path, content


async def read_bytes(hass, path):
    return await hass.async_add_executor_job(path.read_bytes)


def entity_id(hass, key):
    result = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"example_{key}")
    assert result is not None
    return result


def state(hass, key):
    result = hass.states.get(entity_id(hass, key))
    assert result is not None
    return result


async def test_v1_upgrade_uses_literal_multi_year_data_without_new_provenance(
    hass, entry, freezer
):
    freezer.move_to("2026-10-21T10:00:00+00:00")
    payload = historical_payload(1)
    path, _ = await write_store(hass, entry, payload, version=1)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    ids = set(er.async_get(hass).entities)
    assert (
        len([entity_id for entity_id in ids if entity_id.startswith("sensor.")]) == 26
    )
    assert (
        len([entity_id for entity_id in ids if entity_id.startswith("calendar.")]) == 1
    )
    assert state(hass, "fajr_begin").state == "2026-10-21T04:45:00+00:00"
    storage = entry.runtime_data.storage
    assert storage.timetables[0].timetable_id == "legacy-annual"
    assert storage.timetables[0].as_dict() == payload["timetables"][0]
    assert storage.approved_sources == {}
    assert storage.staged is None
    migrated = json.loads(await read_bytes(hass, path))
    assert migrated["version"] == STORAGE_VERSION
    assert migrated["data"]["remote_sources"] == {}
    assert migrated["data"]["remote_checks"] == {}
    assert migrated["data"]["approved_sources"] == {}

    # A legacy source may span years. Its exact next-year row survives migration;
    # the event engine must not reuse the October wall time at the year boundary.
    freezer.move_to("2026-12-31T21:00:00+00:00")
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert state(hass, "fajr_begin").state == "unavailable"
    assert state(hass, "next_salah").state == "2027-01-01T06:10:00+00:00"
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert set(er.async_get(hass).entities) == ids
    assert state(hass, "next_salah").state == "2027-01-01T06:10:00+00:00"


async def test_v2_upgrade_keeps_literal_raw_values_and_pending_review_until_approval(
    hass, entry, freezer
):
    freezer.move_to("2026-10-21T10:00:00+00:00")
    payload = historical_payload(2)
    await write_store(hass, entry, payload, version=2)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    ids = set(er.async_get(hass).entities)
    storage = entry.runtime_data.storage
    approved = storage.approved_sources["annual-2026"]
    proposal = storage.staged.candidate
    assert (
        approved.source_text
        == payload["approved_sources"]["annual-2026"]["source_text"]
    )
    assert approved.source_text.startswith("\ufeff")
    assert approved.timetable.days[1].original["Fajr Jamaat"] == '"'
    assert approved.timetable.days[1].times[PrayerField.FAJR_JAMAAT] == (time(6, 15),)
    assert storage.staged.stage_id == payload["staged"]["stage_id"]
    assert proposal.source_text == payload["staged"]["candidate"]["source_text"]
    assert state(hass, "fajr_begin").state == "2026-10-21T04:45:00+00:00"

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "review"}
    )
    assert result["step_id"] == "review"
    assert proposal.sha256 in result["description_placeholders"]["summary"]
    assert state(hass, "fajr_begin").state == "2026-10-21T04:45:00+00:00"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": "approve"}
    )
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert state(hass, "fajr_begin").state == "2026-10-21T05:00:00+00:00"
    assert entry.runtime_data.storage.staged is None
    assert entry.runtime_data.storage.approved_sources["annual-2026"] == proposal
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert set(er.async_get(hass).entities) == ids
    assert state(hass, "fajr_begin").state == "2026-10-21T05:00:00+00:00"


@pytest.mark.parametrize("version", [1, 2])
async def test_failed_migration_preserves_literal_file_and_retries_on_same_runtime(
    hass, entry, version
):
    payload = historical_payload(version)
    path, before = await write_store(hass, entry, payload, version=version)
    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    with (
        patch.object(
            storage._store, "_write_prepared_data", side_effect=WriteError("disk full")
        ),
        pytest.raises(OSError, match="persistence"),
    ):
        await storage.async_load()
    assert await read_bytes(hass, path) == before
    assert storage.timetables == ()
    assert storage.approved_sources == {}
    assert storage.staged is None
    await storage.async_load()
    assert [table.as_dict() for table in storage.timetables] == payload["timetables"]
    if version == 2:
        assert storage.staged.stage_id == payload["staged"]["stage_id"]
        assert (
            storage.approved_sources["annual-2026"].sha256
            == payload["approved_sources"]["annual-2026"]["sha256"]
        )
    assert json.loads(await read_bytes(hass, path))["version"] == STORAGE_VERSION


@pytest.mark.parametrize("section", ["approved_sources", "staged"])
async def test_invalid_legacy_provenance_never_replaces_original_file(
    hass, entry, section
):
    payload = historical_payload(2)
    candidate = (
        payload[section]["annual-2026"]
        if section == "approved_sources"
        else payload[section]["candidate"]
    )
    candidate["sha256"] = "0" * 64
    path, invalid = await write_store(hass, entry, payload, version=2)
    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    with pytest.raises(ValueError, match="Stored import data is invalid"):
        await storage.async_load()
    assert await read_bytes(hass, path) == invalid
    assert storage.timetables == ()
    assert storage.staged is None
    await write_store(hass, entry, historical_payload(2), version=2)
    await storage.async_load()
    assert storage.staged.stage_id == "a" * 32
    assert storage.for_date(date(2026, 10, 21)).times[PrayerField.FAJR_BEGIN] == (
        time(5, 45),
    )


@pytest.mark.parametrize(
    ("version", "minor", "error"),
    [
        (STORAGE_VERSION + 1, 1, UnsupportedStorageVersionError),
        (STORAGE_VERSION, 2, ValueError),
    ],
)
async def test_future_storage_versions_preserve_working_memory_and_disk(
    hass, entry, version, minor, error
):
    await write_store(hass, entry, historical_payload(2), version=2)
    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    await storage.async_load()
    original_tables, original_stage = storage.timetables, storage.staged
    path = Path(hass.config.path(".storage", f"{DOMAIN}.{entry.entry_id}"))
    backup = await read_bytes(hass, path)
    payload = json.loads(backup)["data"]
    _, future = await write_store(hass, entry, payload, version=version, minor=minor)
    with pytest.raises(error):
        await storage.async_load()
    assert await read_bytes(hass, path) == future
    assert storage.timetables == original_tables
    assert storage.staged == original_stage
    await hass.async_add_executor_job(path.write_bytes, backup)
    await storage.async_load()
    assert storage.timetables == original_tables
    assert storage.staged == original_stage


async def test_complete_backup_restore_clears_repair_and_preserves_ids_and_proposal(
    hass, entry, freezer
):
    freezer.move_to("2026-10-21T10:00:00+00:00")
    await write_store(hass, entry, historical_payload(2), version=2)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    storage = entry.runtime_data.storage
    ramadan = CsvParser().parse(
        b"Date,Fajr Begin,Maghrib Begin\n2026-10-21,05:30,17:30\n",
        timetable_id="ramadan-2026",
        kind="ramadan",
        year=2026,
        date_column="Date",
        columns={"Fajr Begin": "fajr_begin", "Maghrib Begin": "maghrib_begin"},
    )
    # Approve the Ramadan source and then re-stage the same annual replacement,
    # retaining real provenance for both approved sources in the backup.
    proposal = storage.staged.candidate
    await storage.async_reject(storage.staged.stage_id)
    await storage.async_approve(await storage.async_stage(ramadan))
    await storage.async_stage(proposal)
    hass.config_entries.async_update_entry(
        entry,
        options={
            "ramadan_mode": "auto",
            "ramadan_start": "2026-10-21",
            "ramadan_end": "2026-10-21",
        },
    )
    await hass.async_block_till_done()
    storage = entry.runtime_data.storage
    ids = set(er.async_get(hass).entities)
    before_tables = storage.timetables
    before_stage = storage.staged
    before_approved = dict(storage.approved_sources)
    assert state(hass, "fajr_begin").state == "2026-10-21T04:30:00+00:00"
    assert state(hass, "iftar").state == "2026-10-21T16:30:00+00:00"
    path = Path(hass.config.path(".storage", f"{DOMAIN}.{entry.entry_id}"))
    backup = await read_bytes(hass, path)
    assert await hass.config_entries.async_unload(entry.entry_id)
    damaged = json.loads(backup)
    damaged["data"]["approved_sources"]["annual-2026"]["sha256"] = "0" * 64
    corrupt = json.dumps(damaged, indent=2).encode()
    await hass.async_add_executor_job(path.write_bytes, corrupt)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state == ConfigEntryState.SETUP_ERROR
    issue_id = f"invalid_storage_{entry.entry_id}"
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None
    assert await read_bytes(hass, path) == corrupt

    # Restore the complete backup rather than constructing a new empty file.
    await hass.async_add_executor_job(path.write_bytes, backup)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.LOADED
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
    assert set(er.async_get(hass).entities) == ids
    restored = entry.runtime_data.storage
    assert restored.timetables == before_tables
    assert restored.approved_sources == before_approved
    assert restored.staged == before_stage
    assert state(hass, "fajr_begin").state == "2026-10-21T04:30:00+00:00"
    assert state(hass, "iftar").state == "2026-10-21T16:30:00+00:00"
    assert restored.for_date(date(2026, 10, 21)).times[PrayerField.FAJR_BEGIN] == (
        time(5, 45),
    )
