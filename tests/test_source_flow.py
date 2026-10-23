"""Exercise URL and PDF imports through real Home Assistant options flows."""

from datetime import date
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
from custom_components.salah_timetable.download import DownloadError, DownloadResult

PDF_FIXTURE = Path(__file__).parent / "fixtures/pdf/sample_table.pdf"
CSV = b"Date,Fajr Start,Fajr Jamaat\n2026-01-01,05:45,06:15\n2026-01-02,05:47,06:15\n"
PUBLIC_URL = "https://mosque.example.org/timetable.pdf"


@pytest.fixture(autouse=True)
def source_clock(freezer):
    """Freeze before bearer token creation so authenticated uploads remain valid."""
    freezer.move_to("2026-01-01 10:00:00+00:00")


@pytest.fixture
async def source_upload_client(hass, hass_client):
    assert await async_setup_component(hass, "file_upload", {})
    return await hass_client()


def downloaded(content=CSV, media_type="csv"):
    return DownloadResult(
        content,
        media_type,
        '"version-1"',
        "Thu, 01 Jan 2026 00:00:00 GMT",
        sha256(content).hexdigest(),
    )


async def setup_mosque(hass, entry):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def status_entity_id(hass, entry):
    return er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{entry.unique_id}_source_status"
    )


def assert_source_status(hass, entry, expected, *, pending=False):
    state = hass.states.get(status_entity_id(hass, entry))
    assert state is not None
    assert state.state == expected
    assert state.attributes["pending_review"] is pending


async def open_step(hass, entry, step):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert step in result["menu_options"]
    return await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": step}
    )


async def stage_url(hass, entry, *, content=CSV, media_type="csv"):
    result = await open_step(hass, entry, "import_url")
    assert result["step_id"] == "import_url"
    with patch(
        "custom_components.salah_timetable.source_flow.async_download",
        AsyncMock(return_value=downloaded(content, media_type)),
    ) as fetch:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "url": PUBLIC_URL,
                "media_type": media_type,
                "pdf_layout": "pdf_table_v1",
                "kind": "annual",
                "year": 2026,
            },
        )
    fetch.assert_awaited_once_with(PUBLIC_URL, media_type=media_type)
    assert result["step_id"] == "map_columns"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "date_column": "Date",
            "time_format": "24h",
            "fajr_begin": "Fajr Begin" if media_type == "pdf" else "Fajr Start",
        },
    )
    assert result["step_id"] == "review"
    return result


async def approve(hass, result):
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": "approve"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()


@pytest.mark.parametrize("media_type", ["csv", "pdf"])
async def test_url_import_stages_then_approves_and_survives_reload(
    hass, entry, media_type
):
    await setup_mosque(hass, entry)
    assert_source_status(hass, entry, "not_configured")
    content = PDF_FIXTURE.read_bytes() if media_type == "pdf" else CSV
    result = await stage_url(hass, entry, content=content, media_type=media_type)
    await hass.async_block_till_done()
    assert_source_status(hass, entry, "pending_review", pending=True)
    storage = entry.runtime_data.storage
    assert storage.timetables == ()
    assert storage.staged.candidate.source_url == PUBLIC_URL
    assert storage.staged.candidate.sha256 == sha256(content).hexdigest()
    source = storage.remote_sources["annual-2026"]
    assert source.url == PUBLIC_URL
    assert source.media_type == media_type
    assert source.parser_id == ("pdf_table_v1" if media_type == "pdf" else "csv_v1")
    assert storage.remote_checks["annual-2026"]["status"] == "pending"
    assert (
        storage.remote_checks["annual-2026"]["last_seen_sha256"]
        == sha256(content).hexdigest()
    )
    await approve(hass, result)
    assert_source_status(hass, entry, "up_to_date")
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, "example_fajr_begin"
    )
    expected = (
        "2026-01-01T06:15:00+00:00"
        if media_type == "pdf"
        else "2026-01-01T05:45:00+00:00"
    )
    assert hass.states.get(entity_id).state == expected
    assert storage.staged is None
    assert storage.remote_checks["annual-2026"]["status"] == "approved"
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.storage.remote_sources["annual-2026"] == source
    assert (
        entry.runtime_data.storage.remote_checks["annual-2026"]["etag"] == '"version-1"'
    )
    assert (
        entry.runtime_data.storage.approved_sources["annual-2026"].sha256
        == sha256(content).hexdigest()
    )
    assert hass.states.get(entity_id).state == expected
    assert_source_status(hass, entry, "up_to_date")
    assert entry.options == {}


async def test_url_failure_preserves_active_and_redacts_details(hass, populated):
    await setup_mosque(hass, populated)
    previous = populated.runtime_data.storage.timetables
    result = await open_step(hass, populated, "import_url")
    secret_url = "https://mosque.example.org/timetable.pdf?token=private"
    with patch(
        "custom_components.salah_timetable.source_flow.async_download",
        AsyncMock(side_effect=DownloadError("network_error", secret_url)),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "url": secret_url,
                "media_type": "pdf",
                "pdf_layout": "pdf_table_v1",
                "kind": "annual",
                "year": 2026,
            },
        )
    assert result["step_id"] == "import_url"
    assert result["errors"] == {"base": "source_failed"}
    assert "private" not in str(result["description_placeholders"])
    assert "mosque.example.org" not in str(result["description_placeholders"])
    assert populated.runtime_data.storage.timetables == previous
    assert populated.runtime_data.storage.staged is None
    assert populated.runtime_data.storage.remote_sources == {}


@pytest.mark.parametrize(
    "url",
    [
        "http://mosque.example.org/timetable.pdf",
        "https://127.0.0.1/timetable.pdf",
        "https://user:password@mosque.example.org/timetable.pdf",
    ],
)
async def test_unsafe_url_rejected_before_network(hass, entry, url):
    await setup_mosque(hass, entry)
    result = await open_step(hass, entry, "import_url")
    with patch(
        "custom_components.salah_timetable.source_flow.async_download", AsyncMock()
    ) as fetch:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "url": url,
                "media_type": "pdf",
                "pdf_layout": "pdf_table_v1",
                "kind": "annual",
                "year": 2026,
            },
        )
    fetch.assert_not_awaited()
    assert result["errors"] == {"base": "source_failed"}
    assert entry.runtime_data.storage.staged is None


async def test_fractional_url_year_rejected_before_network(hass, entry):
    await setup_mosque(hass, entry)
    result = await open_step(hass, entry, "import_url")
    with patch(
        "custom_components.salah_timetable.source_flow.async_download", AsyncMock()
    ) as fetch:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "url": PUBLIC_URL,
                "media_type": "pdf",
                "pdf_layout": "pdf_table_v1",
                "kind": "annual",
                "year": 2026.5,
            },
        )
    fetch.assert_not_awaited()
    assert result["errors"] == {"base": "source_failed"}
    assert entry.runtime_data.storage.staged is None


async def upload_pdf(hass, client, content):
    form = FormData()
    form.add_field(
        "file", content, filename="timetable.pdf", content_type="application/pdf"
    )
    response = await client.post("/api/file_upload", data=form)
    assert response.status == 200
    file_id = (await response.json())["file_id"]
    path = hass.data[UPLOAD_DATA].file_path(file_id)
    assert await hass.async_add_executor_job(path.exists)
    return file_id, path


async def test_manual_pdf_upload_approval_uses_same_persistence(
    hass, entry, source_upload_client
):
    await setup_mosque(hass, entry)
    result = await open_step(hass, entry, "import_pdf")
    content = PDF_FIXTURE.read_bytes()
    file_id, path = await upload_pdf(hass, source_upload_client, content)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"file": file_id, "pdf_layout": "pdf_table_v1", "kind": "annual", "year": 2026},
    )
    assert result["step_id"] == "map_columns"
    assert not await hass.async_add_executor_job(path.exists)
    assert file_id not in hass.data[UPLOAD_DATA].files
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "date_column": "Date",
            "time_format": "24h",
            "fajr_begin": "Fajr Begin",
            "fajr_jamaat": "Fajr Jamaat",
        },
    )
    assert result["step_id"] == "review"
    assert entry.runtime_data.storage.timetables == ()
    await approve(hass, result)
    source = entry.runtime_data.storage.approved_sources["annual-2026"]
    assert source.source_format == "pdf"
    assert source.source_base64 is not None
    assert source.sha256 == sha256(content).hexdigest()
    assert source.source_url is None
    assert entry.runtime_data.storage.remote_sources == {}
    assert entry.runtime_data.storage.for_date(date(2026, 1, 2)).times


@pytest.mark.parametrize(
    "content", [b"not a pdf", b"%PDF-invalid", b"x" * (2 * 1024 * 1024 + 1)]
)
async def test_invalid_pdf_upload_is_cleaned_up(
    hass, entry, source_upload_client, content
):
    await setup_mosque(hass, entry)
    result = await open_step(hass, entry, "import_pdf")
    file_id, path = await upload_pdf(hass, source_upload_client, content)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"file": file_id, "pdf_layout": "pdf_table_v1", "kind": "annual", "year": 2026},
    )
    assert result["step_id"] == "import_pdf"
    assert result["errors"] == {"base": "invalid_pdf"}
    assert not await hass.async_add_executor_job(path.exists)
    assert file_id not in hass.data[UPLOAD_DATA].files
    assert entry.runtime_data.storage.staged is None


async def test_remove_remote_source_retains_approved_timetable(hass, entry):
    await setup_mosque(hass, entry)
    result = await stage_url(hass, entry)
    await approve(hass, result)
    assert_source_status(hass, entry, "up_to_date")
    previous = entry.runtime_data.storage.timetables
    result = await open_step(hass, entry, "manage_sources")
    assert result["step_id"] == "manage_sources"
    assert PUBLIC_URL not in result["description_placeholders"]["summary"]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"source_id": "annual-2026", "action": "remove"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.runtime_data.storage.remote_sources == {}
    assert entry.runtime_data.storage.timetables == previous
    assert_source_status(hass, entry, "not_configured")
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.storage.timetables == previous
    assert entry.runtime_data.storage.remote_sources == {}
    assert_source_status(hass, entry, "not_configured")


async def test_manual_update_buttons_dispatch_checks(hass, entry):
    await setup_mosque(hass, entry)
    result = await stage_url(hass, entry)
    await approve(hass, result)
    result = await open_step(hass, entry, "check_updates")
    assert result["step_id"] == "check_updates"
    with patch.object(
        entry.runtime_data.source_updates, "async_check_all", AsyncMock()
    ) as check_all:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {}
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "checks_complete"
    check_all.assert_awaited_once()
    result = await open_step(hass, entry, "manage_sources")
    with patch.object(
        entry.runtime_data.source_updates, "async_check", AsyncMock()
    ) as check_one:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], {"source_id": "annual-2026", "action": "check"}
        )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    check_one.assert_awaited_once_with("annual-2026")


async def test_unloaded_entry_cannot_start_url_or_pdf_import(hass, entry):
    for step in ("import_url", "import_pdf"):
        result = await open_step(hass, entry, step)
        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "integration_not_loaded"


async def test_source_status_changes_when_daily_timetable_stays_equal(hass, entry):
    """Approving/rejecting an equal source must notify the diagnostic sensor."""
    await setup_mosque(hass, entry)
    result = await stage_url(hass, entry)
    await approve(hass, result)
    assert_source_status(hass, entry, "up_to_date")
    unchanged = entry.runtime_data.data

    result = await stage_url(hass, entry)
    await hass.async_block_till_done()
    assert entry.runtime_data.data == unchanged
    assert_source_status(hass, entry, "pending_review", pending=True)
    await approve(hass, result)
    assert entry.runtime_data.data == unchanged
    assert_source_status(hass, entry, "up_to_date")

    result = await stage_url(hass, entry)
    await hass.async_block_till_done()
    assert_source_status(hass, entry, "pending_review", pending=True)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": "reject"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.runtime_data.data == unchanged
    assert entry.runtime_data.storage.staged is None
    assert (
        entry.runtime_data.storage.remote_checks["annual-2026"]["status"] == "rejected"
    )
    assert_source_status(hass, entry, "up_to_date")
