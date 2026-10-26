"""The published Zakariyya annual calendar survives native HA import and use."""

import base64
from datetime import date, time
from hashlib import sha256
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import FormData
from homeassistant.components.file_upload import DOMAIN as UPLOAD_DATA
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

from custom_components.salah_timetable.const import DOMAIN
from custom_components.salah_timetable.frontend import async_setup_frontend
from custom_components.salah_timetable.download import DownloadResult
from custom_components.salah_timetable.import_flow import IGNORE_COLUMN
from custom_components.salah_timetable.model import PrayerField
from custom_components.salah_timetable.source_model import RemoteSource

FIXTURE = Path(__file__).parent / "fixtures/pdf/zak.pdf"
SOURCE_URL = "https://mosque.example.org/zakariyya-2026.pdf"


@pytest.fixture(autouse=True)
def annual_clock(freezer):
    """Freeze before HA issues credentials for the real authenticated upload."""
    freezer.move_to("2026-01-02T10:00:00+00:00")


@pytest.fixture
async def annual_upload_client(hass, hass_client):
    # Register bundled static assets before the mocked HTTP router freezes.
    assert await async_setup_component(hass, "file_upload", {})
    await async_setup_frontend(hass)
    return await hass_client()


async def open_step(hass, entry, step):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert step in result["menu_options"]
    return await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": step}
    )


async def upload(hass, entry, client, *, kind="annual"):
    result = await open_step(hass, entry, "import_pdf")
    body = FormData()
    body.add_field(
        "file", FIXTURE.read_bytes(), filename="zak.pdf", content_type="application/pdf"
    )
    response = await client.post("/api/file_upload", data=body)
    assert response.status == 200
    file_id = (await response.json())["file_id"]
    path = hass.data[UPLOAD_DATA].file_path(file_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"file": file_id, "kind": kind, "year": 2026},
    )
    assert result["step_id"] == "map_columns"
    assert not await hass.async_add_executor_job(path.exists)
    assert file_id not in hass.data[UPLOAD_DATA].files
    return result


async def map_columns(hass, result):
    values = result["data_schema"]({})
    assert values["date_column"] == "Date"
    assert values["time_format"] == "24h"
    assert values["dhuhr_jamaat"] == "Dhuhr Jamaat"
    assert values["jumuah"] == IGNORE_COLUMN
    assert values["maghrib_jamaat"] == IGNORE_COLUMN
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], values
    )
    assert result["step_id"] == "review"
    assert not result["errors"]
    return result


async def approve(hass, result):
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": "approve"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()


def entity_state(hass, key):
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"example_{key}"
    )
    assert entity_id is not None
    state = hass.states.get(entity_id)
    assert state is not None
    return state.state


async def test_annual_upload_review_approval_reload_and_dst_events(
    hass, entry, annual_upload_client, freezer
):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entity_state(hass, "fajr_begin") == "unavailable"
    result = await map_columns(hass, await upload(hass, entry, annual_upload_client))
    summary = result["description_placeholders"]["summary"]
    assert "May" in summary and "2026-05-01" in summary
    storage = entry.runtime_data.storage
    assert storage.timetables == ()
    assert entity_state(hass, "fajr_begin") == "unavailable"
    candidate = storage.staged.candidate
    assert candidate.parser_id == "zak_annual_v1"
    assert candidate.coverage.row_count == 365
    assert candidate.coverage.missing_dates == ()
    assert sum(len(row.times) for row in candidate.timetable.days) == 3770
    content = FIXTURE.read_bytes()
    assert candidate.sha256 == sha256(content).hexdigest()
    assert base64.b64decode(candidate.source_base64) == content
    may = next(row for row in candidate.timetable.days if row.day == date(2026, 5, 1))
    assert may.original["Published Date"] == "May …"
    assert may.original["Published Date Interpretation"]
    await approve(hass, result)
    assert entity_state(hass, "fajr_begin") == "2026-01-02T06:46:00+00:00"
    assert entity_state(hass, "dhuhr_jamaat") == "2026-01-02T12:40:00+00:00"
    assert entity_state(hass, "jumuah") == "unavailable"
    assert entity_state(hass, "maghrib_jamaat") == "unavailable"
    assert entity_state(hass, "sehri_ends") == "unavailable"
    assert entity_state(hass, "iftar") == "unavailable"
    assert not entry.runtime_data.data.effective.ramadan_active
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.storage.approved_sources["annual-2026"] == candidate
    for instant, expected in (
        ("2026-03-29T12:00:00+00:00", "2026-03-29T04:14:00+00:00"),
        ("2026-10-25T12:00:00+00:00", "2026-10-25T05:18:00+00:00"),
    ):
        freezer.move_to(instant)
        await entry.runtime_data.async_refresh()
        assert entity_state(hass, "fajr_begin") == expected
    # Tomorrow's printed Fajr changes by three minutes across the clock change.
    freezer.move_to("2026-03-28T23:00:00+00:00")
    await entry.runtime_data.async_refresh()
    assert entity_state(hass, "fajr_begin") == "2026-03-28T04:17:00+00:00"
    assert entity_state(hass, "next_salah") == "2026-03-29T04:14:00+00:00"


async def test_annual_url_profile_and_separate_ramadan_confirmation(
    hass, entry, annual_upload_client, freezer
):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await open_step(hass, entry, "import_url")
    content = FIXTURE.read_bytes()
    downloaded = DownloadResult(
        content, "pdf", '"zak-2026"', None, sha256(content).hexdigest()
    )
    with patch(
        "custom_components.salah_timetable.source_flow.async_download",
        AsyncMock(return_value=downloaded),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "url": SOURCE_URL,
                "media_type": "pdf",
                "kind": "annual",
                "year": 2026,
            },
        )
    result = await map_columns(hass, result)
    await approve(hass, result)
    annual = entry.runtime_data.storage.approved_sources["annual-2026"]
    profile = entry.runtime_data.storage.remote_sources["annual-2026"]
    assert profile.parser_id == "zak_annual_v1"
    assert profile.url == SOURCE_URL
    assert RemoteSource.from_dict(profile.as_dict()) == profile
    result = await map_columns(
        hass,
        await upload(hass, entry, annual_upload_client, kind="ramadan"),
    )
    await approve(hass, result)
    ramadan = entry.runtime_data.storage.approved_sources["ramadan-2026"]
    result = await open_step(hass, entry, "ramadan")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "ramadan_mode": "auto",
            "ramadan_start": "2026-02-18",
            "ramadan_end": "2026-03-19",
            "ramadan_adjustment": 0,
            "ramadan_source_id": "ramadan-2026",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    freezer.move_to("2026-02-18T12:00:00+00:00")
    await entry.runtime_data.async_refresh()
    effective = entry.runtime_data.data.effective
    assert effective.ramadan_active
    assert effective.row.times[PrayerField.IFTAR] == (time(17, 31),)
    assert effective.taraweeh_text == "After Isha Jamaat"
    assert PrayerField.MAGHRIB_JAMAAT not in effective.row.times
    assert PrayerField.JUMUAH not in effective.row.times
    assert entry.runtime_data.storage.approved_sources["annual-2026"] == annual
    assert entry.runtime_data.storage.approved_sources["ramadan-2026"] == ramadan
    assert entry.runtime_data.storage.remote_sources["annual-2026"] == profile
    assert all(PrayerField.IFTAR not in row.times for row in annual.timetable.days)
    assert all(PrayerField.IFTAR not in row.times for row in ramadan.timetable.days)
    freezer.move_to("2026-03-20T12:00:00+00:00")
    await entry.runtime_data.async_refresh()
    assert not entry.runtime_data.data.effective.ramadan_active
    assert entry.runtime_data.data.effective.annual_row is not None
    assert entity_state(hass, "iftar") == "unavailable"


async def test_reassigning_annual_columns_is_rejected_without_staging(
    hass, entry, annual_upload_client
):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await upload(hass, entry, annual_upload_client)
    defaults = result["data_schema"]({})
    for original, reassigned, header in (
        ("dhuhr_jamaat", "jumuah", "Dhuhr Jamaat"),
        ("maghrib_begin", "maghrib_jamaat", "Maghrib Begin"),
    ):
        values = {**defaults, original: IGNORE_COLUMN, reassigned: header}
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], values
        )
        assert result["step_id"] == "map_columns"
        assert result["errors"] == {"base": "invalid_csv"}
        assert "labelled prayer columns" in result["description_placeholders"]["detail"]
        assert entry.runtime_data.storage.staged is None
        assert entry.runtime_data.storage.timetables == ()
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], defaults
    )
    assert result["step_id"] == "review"
    await approve(hass, result)
    assert len(entry.runtime_data.storage.timetables) == 1
