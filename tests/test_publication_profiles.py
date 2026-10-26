"""Edition defaults retain exact source values and the normal approval boundary."""

import base64
from dataclasses import replace
from datetime import date, timedelta
from hashlib import sha256
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import voluptuous as vol
from aiohttp import FormData
from homeassistant.components.file_upload import DOMAIN as UPLOAD_DATA
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component

from custom_components.salah_timetable.csv_parser import CsvParser
from custom_components.salah_timetable.import_model import (
    ImportCandidate,
    ImportValidationError,
)
from custom_components.salah_timetable.pdf_parser import PdfParser, extract_pdf_pages
from custom_components.salah_timetable.publication_profiles import (
    PROFILES,
    publication_profile,
)
from custom_components.salah_timetable.source_flow import ProfiledPdfParser

FIXTURES = Path(__file__).parent / "fixtures/pdf"
EDITIONS = [
    ("nms_annual_2026_v1", "nms_synthetic_2026.pdf"),
    ("nms_monthly_may_june_2022_v1", "nms ramadhan.pdf"),
    ("zak_annual_2026_v1", "zak.pdf"),
    ("zak_ramadan_2026_v1", "zak.pdf"),
]


def parse(profile, content, *, profiled=True, **changes):
    arguments = {
        "timetable_id": f"{profile.kind}-{profile.year}",
        "kind": profile.kind,
        "year": profile.year,
        "date_column": profile.date_column,
        "columns": dict(profile.columns),
        "time_format": profile.time_format,
        **changes,
    }
    parser = (
        ProfiledPdfParser(profile)
        if profiled
        else PdfParser(layout_id=profile.layout_id)
    )
    return parser.parse(content, **arguments)


@pytest.mark.parametrize(("profile_id", "filename"), EDITIONS)
def test_exact_editions_preserve_values_binary_and_coverage(profile_id, filename):
    profile = publication_profile(profile_id)
    content = (FIXTURES / filename).read_bytes()
    ordinary = parse(profile, content, profiled=False)
    candidate = parse(profile, content)
    assert candidate == replace(ordinary, publication_profile_id=profile_id)
    assert candidate.publication_profile_id == profile_id
    assert candidate.source_text == ordinary.source_text
    assert candidate.timetable == ordinary.timetable
    assert candidate.warnings == ordinary.warnings
    assert candidate.coverage == ordinary.coverage
    assert candidate.timetable.days[0].day == profile.start_date
    assert candidate.timetable.days[-1].day == profile.end_date
    assert base64.b64decode(candidate.source_base64) == content
    assert candidate.sha256 == sha256(content).hexdigest()
    assert candidate.source_url is None
    assert ImportCandidate.from_dict(candidate.as_dict()) == candidate
    assert "publication_profile_id" not in ordinary.as_dict()
    assert ImportCandidate.from_dict(ordinary.as_dict()) == ordinary


def test_catalog_and_nested_defaults_are_immutable():
    profile = publication_profile("nms_annual_2026_v1")
    with pytest.raises(TypeError):
        PROFILES["arbitrary"] = profile
    with pytest.raises(TypeError):
        profile.columns["Unpublished"] = "fajr_begin"
    assert profile.time_zone == "Europe/London"
    assert "no public HTTPS source has been verified" in profile.summary


@pytest.mark.parametrize("profile_id", [None, [], 42, "", "nms_annual_2027_v1"])
def test_unknown_editions_cannot_silently_reuse_a_layout(profile_id):
    with pytest.raises(ImportValidationError, match="inspected publication"):
        publication_profile(profile_id)


def test_profile_rejects_csv_and_another_known_pdf_edition():
    candidate = CsvParser().parse(
        b"Date,Fajr\n2026-01-01,05:30\n",
        timetable_id="annual-2026",
        kind="annual",
        year=2026,
        date_column="Date",
        columns={"Fajr": "fajr_begin"},
    )
    with pytest.raises(ImportValidationError, match="publication profile"):
        replace(candidate, publication_profile_id="nms_annual_2026_v1")
    profile = publication_profile("nms_monthly_may_june_2022_v1")
    candidate = parse(profile, (FIXTURES / "nms ramadhan.pdf").read_bytes())
    with pytest.raises(ImportValidationError, match="publication profile"):
        replace(candidate, source_url="https://mosque.example.org/calendar.pdf")
    with pytest.raises(ImportValidationError, match="publication profile"):
        replace(candidate, publication_profile_id="nms_annual_2026_v1")
    stored = candidate.as_dict()
    stored["publication_profile_id"] = "nms_monthly_may_june_2022_v999"
    with pytest.raises(ImportValidationError, match="Stored import data"):
        ImportCandidate.from_dict(stored)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "reverse", "next_year"])
def test_profile_requires_the_complete_ordered_inspected_date_span(mutation):
    profile = publication_profile("nms_monthly_may_june_2022_v1")
    dates = [profile.start_date + timedelta(days=offset) for offset in range(61)]
    if mutation == "missing":
        del dates[20]
    elif mutation == "duplicate":
        dates[20] = dates[19]
    elif mutation == "reverse":
        dates.reverse()
    else:
        dates = [value.replace(year=2023) for value in dates]
    with pytest.raises(ImportValidationError, match="inspected publication edition"):
        profile.validate_dates(dates)


@pytest.mark.parametrize("content", ["Fajr\n05:30\n", "Date\nnot-a-date\n", "Date\n"])
def test_invalid_dated_extraction_is_rejected(content):
    with pytest.raises(ImportValidationError):
        publication_profile("nms_annual_2026_v1").validate_csv(content)


def test_profile_inspection_rejects_a_valid_but_partial_publication():
    content = (FIXTURES / "nms ramadhan.pdf").read_bytes()
    may, _june = extract_pdf_pages(content)
    parser = ProfiledPdfParser(publication_profile("nms_monthly_may_june_2022_v1"))
    with (
        patch(
            "custom_components.salah_timetable.pdf_parser.extract_pdf_pages",
            return_value=(may,),
        ),
        pytest.raises(ImportValidationError, match="inspected publication edition"),
    ):
        parser.inspect(content)


def test_mapping_may_omit_fields_without_fabricating_values():
    profile = publication_profile("nms_monthly_may_june_2022_v1")
    column = next(
        name for name, field in profile.columns.items() if field == "fajr_begin"
    )
    candidate = parse(
        profile,
        (FIXTURES / "nms ramadhan.pdf").read_bytes(),
        columns={column: "fajr_begin"},
    )
    assert candidate.publication_profile_id == profile.profile_id
    assert all(set(row.times) == {"fajr_begin"} for row in candidate.timetable.days)
    assert all("Published Hijri" in row.original for row in candidate.timetable.days)


@pytest.fixture
def profile_clock(freezer):
    freezer.move_to("2026-01-01 10:00:00+00:00")


async def open_profiles(hass, entry):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert "publication_profile" in result["menu_options"]
    return await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "publication_profile"}
    )


@pytest.mark.usefixtures("profile_clock")
async def test_picker_requires_printed_year_and_blocks_timezone_changes(hass, entry):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await open_profiles(hass, entry)
    year_key = next(key for key in result["data_schema"].schema if key.schema == "year")
    assert year_key.default is vol.UNDEFINED
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"profile_id": "nms_annual_2026_v1", "year": 2027}
    )
    assert result["errors"] == {"base": "invalid_publication_profile"}
    assert "2026" in result["description_placeholders"]["detail"]
    assert entry.runtime_data.storage.staged is None
    assert entry.options == {}
    hass.config_entries.async_update_entry(entry, options={"time_zone": "Asia/Riyadh"})
    await hass.async_block_till_done()
    result = await open_profiles(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"profile_id": "nms_annual_2026_v1", "year": 2026}
    )
    assert result["errors"] == {"base": "invalid_publication_profile"}
    assert "Europe/London" in result["description_placeholders"]["detail"]
    assert "Asia/Riyadh" in result["description_placeholders"]["detail"]
    assert entry.options == {"time_zone": "Asia/Riyadh"}
    assert entry.runtime_data.storage.staged is None


@pytest.mark.usefixtures("profile_clock")
async def test_timezone_changed_after_upload_cannot_stage_profiled_rows(hass, entry):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    profile = publication_profile("nms_annual_2026_v1")
    result = await open_profiles(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"profile_id": profile.profile_id, "year": profile.year}
    )
    with (
        patch(
            "custom_components.salah_timetable.source_flow.read_uploaded_pdf",
            return_value=b"%PDF-test",
        ),
        patch.object(
            ProfiledPdfParser, "inspect", return_value=("Date", *profile.columns)
        ),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"file": "00000000-0000-0000-0000-000000000001"}
        )
    assert result["step_id"] == "map_columns"
    hass.config_entries.async_update_entry(entry, options={"time_zone": "Asia/Riyadh"})
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"date_column": "Date", "time_format": "24h", "fajr_begin": "Fajr Begin"},
    )
    assert result["step_id"] == "publication_profile"
    assert result["errors"] == {"base": "invalid_publication_profile"}
    assert entry.runtime_data.storage.staged is None
    assert entry.runtime_data.storage.timetables == ()


@pytest.mark.usefixtures("profile_clock")
@pytest.mark.parametrize("decision", ["approve", "reject"])
async def test_manual_profile_upload_requires_review_and_persists_on_approval(
    hass, entry, hass_client, decision
):
    # The mock HTTP router is frozen once the test client starts; initialize
    # the integration's bundled frontend path before constructing that client.
    assert await async_setup_component(hass, "file_upload", {})
    assert await hass.config_entries.async_setup(entry.entry_id)
    client = await hass_client()
    await hass.async_block_till_done()
    profile = publication_profile("nms_monthly_may_june_2022_v1")
    content = (FIXTURES / "nms ramadhan.pdf").read_bytes()
    result = await open_profiles(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"profile_id": profile.profile_id, "year": profile.year}
    )
    assert result["step_id"] == "profile_pdf"
    form = FormData()
    form.add_field(
        "file", content, filename="edition.pdf", content_type="application/pdf"
    )
    response = await client.post("/api/file_upload", data=form)
    assert response.status == 200
    file_id = (await response.json())["file_id"]
    path = hass.data[UPLOAD_DATA].file_path(file_id)
    with patch(
        "custom_components.salah_timetable.source_flow.async_download", AsyncMock()
    ) as download:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"file": file_id}
        )
    download.assert_not_awaited()
    assert result["step_id"] == "map_columns"
    assert not await hass.async_add_executor_job(path.exists)
    assert file_id not in hass.data[UPLOAD_DATA].files
    defaults = {
        key.schema: key.default()
        for key in result["data_schema"].schema
        if callable(key.default)
    }
    assert defaults["fajr_begin"] == "Fajr Begin"
    assert defaults["time_format"] == "24h"
    assert defaults["date_column"] == "Date"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], defaults
    )
    assert result["step_id"] == "review"
    storage = entry.runtime_data.storage
    assert storage.timetables == ()
    assert storage.staged.candidate.publication_profile_id == profile.profile_id
    assert profile.profile_id in result["description_placeholders"]["summary"]
    assert not storage.remote_sources
    # Pending provenance survives reload and appears when review is reopened.
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "review"}
    )
    assert profile.profile_id in result["description_placeholders"]["summary"]
    if decision == "approve":
        # A second options flow may change the mosque timezone while review is open.
        hass.config_entries.async_update_entry(
            entry, options={"time_zone": "Asia/Riyadh"}
        )
        await hass.async_block_till_done()
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "review"}
        )
        assert result["errors"] == {"base": "invalid_publication_profile"}
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"decision": "approve"}
        )
        assert result["errors"] == {"base": "invalid_publication_profile"}
        assert entry.runtime_data.storage.timetables == ()
        assert entry.runtime_data.storage.staged is not None
        hass.config_entries.async_update_entry(entry, options={})
        await hass.async_block_till_done()
        result = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"next_step_id": "review"}
        )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": decision}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    storage = entry.runtime_data.storage
    assert storage.staged is None
    if decision == "approve":
        candidate = storage.approved_sources["annual-2022"]
        assert candidate.publication_profile_id == profile.profile_id
        assert candidate.sha256 == sha256(content).hexdigest()
        assert candidate.source_url is None
        assert candidate.timetable.days[0].day == date(2022, 5, 1)
    else:
        assert storage.timetables == ()
        assert not storage.approved_sources
    assert entry.options == {}
