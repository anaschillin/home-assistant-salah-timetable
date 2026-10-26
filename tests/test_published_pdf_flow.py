"""Fictional publication fixtures remain staged until approval and confirmed-date activation."""

import base64
from datetime import date, time
from hashlib import sha256
from pathlib import Path

import pytest
from aiohttp import FormData
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component

from custom_components.salah_timetable.frontend import async_setup_frontend
from custom_components.salah_timetable.import_model import ImportCandidate
from custom_components.salah_timetable.model import PrayerField
from custom_components.salah_timetable.pdf_parser import PdfParser
from custom_components.salah_timetable.ramadan import RamadanSettings, resolve_day
from custom_components.salah_timetable.source_model import RemoteSource

FIXTURES = Path(__file__).parent / "fixtures/pdf"


@pytest.fixture(autouse=True)
def published_clock(freezer):
    freezer.move_to("2026-02-18T12:00:00+00:00")


@pytest.mark.parametrize(
    "filename,layout,year,count,start,end",
    [
        (
            "mosque_a_monthly_2022.pdf",
            "mosque_a_monthly_v1",
            2022,
            61,
            "2022-05-01",
            "2022-06-30",
        ),
        (
            "mosque_b_2026.pdf",
            "mosque_b_ramadan_v1",
            2026,
            31,
            "2026-02-18",
            "2026-03-20",
        ),
    ],
)
async def test_synthetic_pdf_upload_staging_approval_and_persistence(
    hass, entry, hass_client, filename, layout, year, count, start, end
):
    # Install the bundled assets before the test HTTP client freezes routes.
    assert await async_setup_component(hass, "file_upload", {})
    await async_setup_frontend(hass)
    client = await hass_client()
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "import_pdf"}
    )
    content = (FIXTURES / filename).read_bytes()
    body = FormData()
    body.add_field("file", content, filename=filename, content_type="application/pdf")
    response = await client.post("/api/file_upload", data=body)
    assert response.status == 200
    file_id = (await response.json())["file_id"]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"file": file_id, "kind": "ramadan", "year": year},
    )
    assert result["step_id"] == "map_columns"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], result["data_schema"]({})
    )
    assert result["step_id"] == "review"
    summary = result["description_placeholders"]["summary"]
    assert start in summary and end in summary
    assert "no confirmed dates" in summary
    storage = entry.runtime_data.storage
    assert storage.timetables == ()
    candidate = storage.staged.candidate
    assert candidate.coverage.row_count == count
    assert candidate.parser_id == layout
    assert candidate.sha256 == sha256(content).hexdigest()
    assert base64.b64decode(candidate.source_base64) == content
    assert ImportCandidate.from_dict(candidate.as_dict()) == candidate
    profile = RemoteSource(
        f"ramadan-{year}",
        "https://mosque.example.org/calendar.pdf",
        "pdf",
        "ramadan",
        year,
        "Date",
        candidate.columns,
        parser_id=layout,
    )
    assert RemoteSource.from_dict(profile.as_dict()) == profile
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": "approve"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert not entry.runtime_data.data.effective.ramadan_active
    assert entry.runtime_data.data.effective.row is None
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.storage.approved_sources[f"ramadan-{year}"] == candidate
    assert entry.runtime_data.storage.staged is None
    if layout != "mosque_b_ramadan_v1":
        return
    # A printed Hijri/Eid row does not confirm an extra day of Ramadan.
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "ramadan"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "ramadan_mode": "auto",
            "ramadan_start": "2026-02-18",
            "ramadan_end": "2026-03-19",
            "ramadan_adjustment": 0,
            "ramadan_source_id": "__auto__",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    effective = entry.runtime_data.data.effective
    assert effective.ramadan_active
    assert effective.row.times[PrayerField.IFTAR] == (time(18, 17),)
    assert effective.taraweeh_text == "After Isha Jamaat"
    assert PrayerField.MAGHRIB_JAMAAT not in effective.row.times
    assert PrayerField.TARAWEEH not in effective.row.times
    tables = entry.runtime_data.storage.timetables
    settings = RamadanSettings.from_options(entry.options)
    assert resolve_day(date(2026, 3, 19), tables, settings).ramadan_active
    eid = resolve_day(date(2026, 3, 20), tables, settings)
    assert not eid.ramadan_active
    assert eid.row is None
    assert PrayerField.IFTAR not in candidate.timetable.days[0].times


@pytest.mark.parametrize(
    "layout,filename,overrides",
    [
        ("mosque_a_monthly_v1", "mosque_a_monthly_2022.pdf", {"year": 2026}),
        (
            "mosque_a_monthly_v1",
            "mosque_a_monthly_2022.pdf",
            {"columns": {"Fajr Begin": "isha_begin"}},
        ),
        ("mosque_b_ramadan_v1", "mosque_b_2026.pdf", {"kind": "annual"}),
        (
            "mosque_b_ramadan_v1",
            "mosque_b_2026.pdf",
            {"columns": {"Dhuhr Jamaat": "jumuah"}},
        ),
    ],
)
def test_synthetic_layout_semantics_cannot_be_reassigned(layout, filename, overrides):
    arguments = {
        "timetable_id": "ramadan-2026",
        "kind": "ramadan",
        "year": 2022 if layout == "mosque_a_monthly_v1" else 2026,
        "date_column": "Date",
        "columns": {"Fajr Begin": "fajr_begin"},
    }
    arguments.update(overrides)
    with pytest.raises(ValueError):
        PdfParser(layout).parse((FIXTURES / filename).read_bytes(), **arguments)
