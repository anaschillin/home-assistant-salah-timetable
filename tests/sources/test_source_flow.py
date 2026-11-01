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

from custom_components.salah_timetable.const import DOMAIN
from custom_components.salah_timetable.parsers.import_model import MAX_PDF_BYTES
from custom_components.salah_timetable.sources.download import (
    DownloadError,
    DownloadResult,
)

PDF_FIXTURE = Path(__file__).parents[1] / "fixtures/pdf/sample_table.pdf"
CSV = b"Date,Fajr Start,Fajr Jamaat\n2026-01-01,05:45,06:15\n2026-01-02,05:47,06:15\n"
PUBLIC_URL = "https://mosque.example.org/timetable.pdf"


@pytest.fixture(autouse=True)
def source_clock(freezer):
    """Freeze before bearer token creation so authenticated uploads remain valid."""
    freezer.move_to("2026-01-01 10:00:00+00:00")


@pytest.fixture
async def source_upload_client(authenticated_upload_client):
    return authenticated_upload_client


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
        "custom_components.salah_timetable.sources.source_flow.async_download",
        AsyncMock(return_value=downloaded(content, media_type)),
    ) as fetch:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "url": PUBLIC_URL,
                "media_type": media_type,
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


@pytest.mark.parametrize("step", ["import_pdf", "import_url"])
async def test_ordinary_import_offers_timetable_type_without_layout_choice(
    hass, entry, step
):
    await setup_mosque(hass, entry)
    result = await open_step(hass, entry, step)
    fields = {key.schema: value for key, value in result["data_schema"].schema.items()}
    assert "pdf_layout" not in fields
    assert fields["kind"].config["options"] == ["annual", "monthly", "ramadan"]


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
        "custom_components.salah_timetable.sources.source_flow.async_download",
        AsyncMock(side_effect=DownloadError("network_error", secret_url)),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "url": secret_url,
                "media_type": "pdf",
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
        "custom_components.salah_timetable.sources.source_flow.async_download",
        AsyncMock(),
    ) as fetch:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "url": url,
                "media_type": "pdf",
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
        "custom_components.salah_timetable.sources.source_flow.async_download",
        AsyncMock(),
    ) as fetch:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "url": PUBLIC_URL,
                "media_type": "pdf",
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
        {"file": file_id, "kind": "annual", "year": 2026},
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


async def test_invalid_pdf_upload_is_cleaned_up(hass, entry, source_upload_client):
    """Reject each bad PDF and allow another upload on the same options flow.

    Reusing one HA/client lifecycle avoids repeated mocked-server teardown
    between parametrizations on the minimum supported HA version.
    """
    await setup_mosque(hass, entry)
    result = await open_step(hass, entry, "import_pdf")

    invalid_uploads = (
        ("non_pdf", b"not a pdf"),
        ("malformed_pdf", b"%PDF-invalid"),
        ("oversized_pdf", b"%PDF-" + b"x" * MAX_PDF_BYTES),
    )
    for case, content in invalid_uploads:
        file_id, path = await upload_pdf(hass, source_upload_client, content)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"file": file_id, "kind": "annual", "year": 2026},
        )
        assert result["step_id"] == "import_pdf", case
        assert result["errors"] == {"base": "invalid_pdf"}, case
        assert not await hass.async_add_executor_job(path.exists), case
        assert file_id not in hass.data[UPLOAD_DATA].files, case
        assert entry.runtime_data.storage.staged is None, case


async def test_monthly_upload_detects_pdf_and_stores_partial_annual_kind(
    hass, entry, source_upload_client
):
    await setup_mosque(hass, entry)
    result = await open_step(hass, entry, "import_pdf")
    file_id, _ = await upload_pdf(hass, source_upload_client, PDF_FIXTURE.read_bytes())
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"file": file_id, "kind": "monthly", "year": 2026},
    )
    assert result["step_id"] == "map_columns"
    assert "Recognized PDF" in result["description_placeholders"]["detail"]
    assert result["data_schema"].schema
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "date_column": "Date",
            "time_format": "24h",
            "fajr_begin": "Fajr Begin",
        },
    )
    assert result["step_id"] == "review"
    assert "Recognized PDF" in result["description_placeholders"]["summary"]
    assert entry.runtime_data.storage.staged.candidate.parser_id == "pdf_table_v1"
    assert entry.runtime_data.storage.staged.candidate.timetable.kind == "annual"
    await approve(hass, result)
    assert (
        "annual-2026-monthly-0101-0103" in entry.runtime_data.storage.approved_sources
    )


async def test_monthly_imports_preserve_other_published_months(
    hass, entry, source_upload_client
):
    import runpy

    await setup_mosque(hass, entry)

    async def import_month(content):
        result = await open_step(hass, entry, "import_pdf")
        file_id, _ = await upload_pdf(hass, source_upload_client, content)
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"file": file_id, "kind": "monthly", "year": 2026},
        )
        assert result["step_id"] == "map_columns"
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {"date_column": "Date", "time_format": "24h", "fajr_begin": "Fajr Begin"},
        )
        assert result["step_id"] == "review"
        await approve(hass, result)

    await import_month(PDF_FIXTURE.read_bytes())
    assert entry.runtime_data.storage.for_date(date(2026, 1, 1)) is not None

    make_pdf = runpy.run_path(
        str(Path(__file__).parents[1] / "fixtures/pdf/generate.py")
    )["make_pdf"]
    february = make_pdf(
        [
            [
                "Salah Timetable",
                "Year 2026",
                "Date | Fajr Begin | Sunrise",
                "2026-02-01 | 05:40 | 07:30",
                "2026-02-02 | 05:42 | 07:28",
            ]
        ]
    )
    await import_month(february)
    storage = entry.runtime_data.storage
    assert storage.for_date(date(2026, 1, 1)) is not None
    assert storage.for_date(date(2026, 2, 1)) is not None
    assert set(storage.approved_sources) == {
        "annual-2026-monthly-0101-0103",
        "annual-2026-monthly-0201-0202",
    }


async def test_url_auto_detection_persists_concrete_parser_for_future_checks(
    hass, entry
):
    await setup_mosque(hass, entry)
    result = await open_step(hass, entry, "import_url")
    with patch(
        "custom_components.salah_timetable.sources.source_flow.async_download",
        AsyncMock(return_value=downloaded(PDF_FIXTURE.read_bytes(), "pdf")),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "url": PUBLIC_URL,
                "media_type": "pdf",
                "kind": "monthly",
                "year": 2026,
            },
        )
    assert result["step_id"] == "map_columns"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "date_column": "Date",
            "time_format": "24h",
            "fajr_begin": "Fajr Begin",
        },
    )
    assert result["step_id"] == "review"
    assert (
        entry.runtime_data.storage.remote_sources[
            "annual-2026-monthly-0101-0103"
        ].parser_id
        == "pdf_table_v1"
    )
    await approve(hass, result)
    source = entry.runtime_data.storage.remote_sources["annual-2026-monthly-0101-0103"]
    assert source.kind == "annual"
    assert source.parser_id == "pdf_table_v1"


async def test_monthly_csv_url_uses_distinct_published_date_span(hass, entry):
    await setup_mosque(hass, entry)
    result = await open_step(hass, entry, "import_url")
    with patch(
        "custom_components.salah_timetable.sources.source_flow.async_download",
        AsyncMock(return_value=downloaded(CSV)),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            {
                "url": PUBLIC_URL,
                "media_type": "csv",
                "kind": "monthly",
                "year": 2026,
            },
        )
    assert result["step_id"] == "map_columns"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {"date_column": "Date", "time_format": "24h", "fajr_begin": "Fajr Start"},
    )
    assert result["step_id"] == "review"
    await approve(hass, result)
    source_id = "annual-2026-monthly-0101-0102"
    storage = entry.runtime_data.storage
    assert storage.remote_sources[source_id].media_type == "csv"
    assert storage.approved_sources[source_id].parser_id == "csv_v1"
    assert storage.for_date(date(2026, 1, 1)) is not None


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
    assert_source_status(hass, entry, "rejected_version")


async def test_reject_changed_source_preserves_live_sensor_after_reload(hass, entry):
    """Rejecting changed prayer times must retain the approved sensor value."""
    await setup_mosque(hass, entry)

    result = await stage_url(hass, entry)
    await approve(hass, result)

    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id("sensor", DOMAIN, "example_fajr_begin")
    assert entity_id is not None

    original_state = hass.states.get(entity_id).state
    original_timetables = entry.runtime_data.storage.timetables

    changed_csv = (
        b"Date,Fajr Start,Fajr Jamaat\n2026-01-01,06:00,06:15\n2026-01-02,06:02,06:15\n"
    )

    result = await stage_url(hass, entry, content=changed_csv)
    await hass.async_block_till_done()

    assert_source_status(hass, entry, "pending_review", pending=True)
    assert hass.states.get(entity_id).state == original_state

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"decision": "reject"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    assert entry.runtime_data.storage.staged is None
    assert entry.runtime_data.storage.timetables == original_timetables
    assert hass.states.get(entity_id).state == original_state
    assert_source_status(hass, entry, "rejected_version")

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.runtime_data.storage.staged is None
    assert entry.runtime_data.storage.timetables == original_timetables
    assert hass.states.get(entity_id).state == original_state
    assert_source_status(hass, entry, "rejected_version")


@pytest.mark.parametrize("year", [True, "2026", float("nan"), 2026.5, 1899, 2200])
def test_source_year_requires_a_bounded_integer(year):
    from custom_components.salah_timetable.parsers.import_model import (
        ImportValidationError,
    )
    from custom_components.salah_timetable.sources.source_flow import _year

    with pytest.raises(ImportValidationError, match="whole number"):
        _year(year)


def test_source_year_and_kind_preserve_declared_values():
    from custom_components.salah_timetable.parsers.import_model import (
        ImportValidationError,
    )
    from custom_components.salah_timetable.sources.source_flow import (
        _year,
        canonical_kind,
    )

    assert _year(2026.0) == 2026
    assert canonical_kind("annual") == "annual"
    assert canonical_kind("monthly") == "annual"
    assert canonical_kind("ramadan") == "ramadan"
    with pytest.raises(ImportValidationError, match="Annual, Monthly or Ramadan"):
        canonical_kind("unknown")


async def test_empty_download_does_not_stage_any_source(hass, entry):
    await setup_mosque(hass, entry)
    form = await open_step(hass, entry, "import_url")
    with patch(
        "custom_components.salah_timetable.sources.source_flow.async_download",
        AsyncMock(return_value=DownloadResult(None, "csv", None, None, None)),
    ):
        result = await hass.config_entries.options.async_configure(
            form["flow_id"],
            {
                "url": PUBLIC_URL,
                "media_type": "csv",
                "kind": "annual",
                "year": 2026,
            },
        )
    assert result["step_id"] == "import_url"
    assert result["errors"] == {"base": "source_failed"}
    assert entry.runtime_data.storage.staged is None
    assert entry.runtime_data.storage.remote_sources == {}


async def test_unexpected_download_validation_error_is_generic_and_safe(hass, entry):
    await setup_mosque(hass, entry)
    form = await open_step(hass, entry, "import_url")
    with patch(
        "custom_components.salah_timetable.sources.source_flow.async_download",
        AsyncMock(side_effect=OSError("upstream path /private/config")),
    ):
        result = await hass.config_entries.options.async_configure(
            form["flow_id"],
            {
                "url": PUBLIC_URL,
                "media_type": "csv",
                "kind": "annual",
                "year": 2026,
            },
        )
    assert result["errors"] == {"base": "source_failed"}
    assert "/private/config" not in str(result["description_placeholders"])
    assert entry.runtime_data.storage.remote_sources == {}


async def test_remote_source_removal_failure_preserves_stored_profile(hass, entry):
    await setup_mosque(hass, entry)
    staged = await stage_url(hass, entry)
    await approve(hass, staged)
    existing = dict(entry.runtime_data.storage.remote_sources)
    form = await open_step(hass, entry, "manage_sources")
    with patch.object(
        entry.runtime_data.storage,
        "async_remove_remote_source",
        AsyncMock(side_effect=OSError("disk full")),
    ):
        result = await hass.config_entries.options.async_configure(
            form["flow_id"], {"source_id": "annual-2026", "action": "remove"}
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "source_save_failed"
    assert entry.runtime_data.storage.remote_sources == existing


async def test_unloaded_entry_hides_source_check_action(hass, entry):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert "check_updates" not in result["menu_options"]
    assert "manage_sources" not in result["menu_options"]


@pytest.mark.parametrize("step", ["import_url", "import_pdf", "import_csv"])
async def test_pending_approval_blocks_another_import_form(hass, entry, step):
    await setup_mosque(hass, entry)
    existing_form = await open_step(hass, entry, step)
    staged = await stage_url(hass, entry)
    assert staged["step_id"] == "review"
    pending = entry.runtime_data.storage.staged
    data = {"kind": "annual", "year": 2026}
    if step == "import_url":
        data.update(url=PUBLIC_URL, media_type="csv")
    else:
        # The pending guard must run before any uploaded file is read.
        data["file"] = "00000000-0000-0000-0000-000000000000"
    result = await hass.config_entries.options.async_configure(
        existing_form["flow_id"], data
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "pending_import_exists"
    assert entry.runtime_data.storage.staged == pending
    assert entry.runtime_data.storage.timetables == ()


async def test_remove_source_during_manage_dialog_aborts_without_recreating(
    hass, entry
):
    await setup_mosque(hass, entry)
    result = await stage_url(hass, entry)
    await approve(hass, result)
    form = await open_step(hass, entry, "manage_sources")
    assert form["step_id"] == "manage_sources"
    await entry.runtime_data.storage.async_remove_remote_source("annual-2026")
    result = await hass.config_entries.options.async_configure(
        form["flow_id"], {"source_id": "annual-2026", "action": "remove"}
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_remote_sources"
    assert entry.runtime_data.storage.remote_sources == {}


@pytest.mark.parametrize("step", ["check_updates", "manage_sources"])
async def test_unloaded_entry_cannot_run_previously_opened_source_action(
    hass, entry, step
):
    await setup_mosque(hass, entry)
    staged = await stage_url(hass, entry)
    await approve(hass, staged)
    form = await open_step(hass, entry, step)
    assert form["step_id"] == step
    assert await hass.config_entries.async_unload(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        form["flow_id"],
        {}
        if step == "check_updates"
        else {"source_id": "annual-2026", "action": "check"},
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "integration_not_loaded"


async def test_reload_during_url_download_requires_reopening_import(hass, entry):
    """A completed download must not attach its profile to a retired runtime."""
    await setup_mosque(hass, entry)
    original = entry.runtime_data
    form = await open_step(hass, entry, "import_url")

    async def reload_during_download(*args, **kwargs):
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        return downloaded()

    with patch(
        "custom_components.salah_timetable.sources.source_flow.async_download",
        side_effect=reload_during_download,
    ):
        result = await hass.config_entries.options.async_configure(
            form["flow_id"],
            {"url": PUBLIC_URL, "media_type": "csv", "kind": "annual", "year": 2026},
        )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "integration_reloaded"
    assert entry.runtime_data is not original
    assert original.source_updates._stopped
    assert entry.runtime_data.storage.staged is None
    assert entry.runtime_data.storage.remote_sources == {}
    # Reopening after the reload can still reach review without approving data.
    reopened = await stage_url(hass, entry)
    assert reopened["step_id"] == "review"
    assert entry.runtime_data.storage.timetables == ()


def annual_csv(year):
    return (
        "Date,Fajr Start,Fajr Jamaat\n"
        + "".join(
            f"{date(year, 1, 1).fromordinal(date(year, 1, 1).toordinal() + day).isoformat()},05:45,06:15\n"
            for day in range(365)
        )
    ).encode()


async def test_annual_rollover_uses_explicit_new_url_and_requires_approval(hass, entry):
    await setup_mosque(hass, entry)
    first = await stage_url(hass, entry, content=annual_csv(2026))
    await approve(hass, first)
    assert (
        "annual_rollover"
        in (await hass.config_entries.options.async_init(entry.entry_id))[
            "menu_options"
        ]
    )

    flow = await open_step(hass, entry, "annual_rollover")
    assert flow["step_id"] == "annual_rollover"
    new_url = "https://mosque.example.org/2027.pdf"
    fresh = b"Date,Fajr Start,Fajr Jamaat\n2027-01-01,05:46,06:15\n"
    with patch(
        "custom_components.salah_timetable.sources.source_flow.async_download",
        AsyncMock(return_value=downloaded(fresh)),
    ) as fetch:
        form = await hass.config_entries.options.async_configure(
            flow["flow_id"], {"source_id": "annual-2026", "url": new_url}
        )
    fetch.assert_awaited_once_with(new_url, media_type="csv")
    assert form["step_id"] == "map_columns"
    staged = await hass.config_entries.options.async_configure(
        form["flow_id"],
        {
            "date_column": "Date",
            "time_format": "24h",
            "fajr_begin": "Fajr Start",
        },
    )
    assert staged["step_id"] == "review"
    assert entry.runtime_data.storage.staged.candidate.year == 2027
    assert set(entry.runtime_data.storage.approved_sources) == {"annual-2026"}
    assert set(entry.runtime_data.storage.remote_sources) == {
        "annual-2026",
        "annual-2027",
    }
    await approve(hass, staged)
    assert set(entry.runtime_data.storage.approved_sources) == {
        "annual-2026",
        "annual-2027",
    }


async def test_annual_rollover_not_offered_without_approved_full_year(hass, entry):
    await setup_mosque(hass, entry)
    assert (
        "annual_rollover"
        not in (await hass.config_entries.options.async_init(entry.entry_id))[
            "menu_options"
        ]
    )
    staged = await stage_url(hass, entry, content=CSV)
    await approve(hass, staged)
    assert (
        "annual_rollover"
        not in (await hass.config_entries.options.async_init(entry.entry_id))[
            "menu_options"
        ]
    )


def rollover_scenario(
    *,
    source_year=2026,
    source_kind="annual",
    source_id=None,
    approved=True,
    row_count=365,
):
    """Minimal approved-source snapshot to exercise rollover guard decisions."""
    from types import SimpleNamespace

    key = source_id or f"annual-{source_year}"
    publication = SimpleNamespace(kind=source_kind, year=source_year, media_type="csv")
    row = SimpleNamespace(day=date(source_year, 1, 1))
    table = SimpleNamespace(timetable_id=key, kind="annual", days=(row,) * row_count)
    storage = SimpleNamespace(
        staged=None,
        remote_sources={key: publication},
        approved_sources={key: object()} if approved else {},
        timetables=(table,),
    )
    return storage


@pytest.mark.parametrize(
    ("variant", "kwargs"),
    [
        ("non_annual", {"source_kind": "ramadan"}),
        ("last_supported_year", {"source_year": 2199}),
        ("noncanonical_id", {"source_id": "annual-2026-monthly-0101-1231"}),
        ("not_approved", {"approved": False}),
        ("insufficient_coverage", {"row_count": 299}),
    ],
)
def test_rollover_candidates_reject_ineligible_source_profiles(variant, kwargs):
    from types import SimpleNamespace

    from custom_components.salah_timetable.sources.source_flow import SourceOptionsFlow

    storage = rollover_scenario(**kwargs)
    assert SourceOptionsFlow._rollover_sources(SimpleNamespace(storage=storage)) == {}


async def test_rollover_step_rejects_unavailable_and_pending_sources():
    from types import SimpleNamespace

    from custom_components.salah_timetable.sources.source_flow import SourceOptionsFlow

    flow = SourceOptionsFlow()
    flow._coordinator = lambda: None
    assert (await flow.async_step_annual_rollover())[
        "reason"
    ] == "integration_not_loaded"
    storage = rollover_scenario()
    coordinator = SimpleNamespace(storage=storage)
    flow._coordinator = lambda: coordinator
    storage.staged = object()
    assert (await flow.async_step_annual_rollover())[
        "reason"
    ] == "pending_import_exists"
    storage.staged = None
    storage.approved_sources.clear()
    assert (await flow.async_step_annual_rollover())["reason"] == "no_rollover_sources"


async def test_rollover_step_handles_changed_selection_and_existing_years():
    from types import SimpleNamespace

    from custom_components.salah_timetable.sources.source_flow import SourceOptionsFlow

    flow = SourceOptionsFlow()
    flow.hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_known_entry=lambda _: SimpleNamespace(options={})
        )
    )
    flow.handler = "entry"
    storage = rollover_scenario()
    coordinator = SimpleNamespace(storage=storage)
    flow._coordinator = lambda: coordinator
    assert (await flow.async_step_annual_rollover())["step_id"] == "annual_rollover"

    invalid = await flow.async_step_annual_rollover(
        {"source_id": "annual-2025", "url": "https://mosque.example.org/2027.csv"}
    )
    assert invalid["errors"] == {"base": "invalid_rollover"}

    next_year = SimpleNamespace(
        timetable_id="annual-2027",
        kind="annual",
        days=(SimpleNamespace(day=date(2027, 1, 1)),),
    )
    storage.timetables += (next_year,)
    already = await flow.async_step_annual_rollover(
        {"source_id": "annual-2026", "url": "https://mosque.example.org/2027.csv"}
    )
    assert already["errors"] == {"base": "rollover_already_approved"}

    storage.timetables = storage.timetables[:1]
    storage.remote_sources["annual-2027"] = SimpleNamespace(
        kind="annual", year=2027, media_type="csv"
    )
    configured = await flow.async_step_annual_rollover(
        {"source_id": "annual-2026", "url": "https://mosque.example.org/2027.csv"}
    )
    assert configured["errors"] == {"base": "rollover_already_configured"}


async def test_rollover_step_delegates_valid_new_year_to_existing_import():
    from types import SimpleNamespace

    from custom_components.salah_timetable.sources.source_flow import SourceOptionsFlow

    flow = SourceOptionsFlow()
    flow.hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_known_entry=lambda _: SimpleNamespace(options={})
        )
    )
    flow.handler = "entry"
    flow._coordinator = lambda: SimpleNamespace(storage=rollover_scenario())
    result = {"type": FlowResultType.FORM, "step_id": "map_columns"}
    with patch.object(
        flow, "async_step_import_url", AsyncMock(return_value=result)
    ) as handler:
        response = await flow.async_step_annual_rollover(
            {"source_id": "annual-2026", "url": "https://mosque.example.org/2027.csv"}
        )
    assert response is result
    handler.assert_awaited_once_with(
        {
            "year": 2027,
            "kind": "annual",
            "media_type": "csv",
            "url": "https://mosque.example.org/2027.csv",
        }
    )


@pytest.mark.parametrize(
    "template",
    [
        "https://example.org/timetable.pdf",
        "https://example.org/{year}/{year}.pdf",
        "https://example.org/{year}/{month}.pdf",
        "http://example.org/{year}.pdf",
        "https://127.0.0.1/{year}.pdf",
        "https://user:secret@example.org/{year}.pdf",
        "https://example.org/{year}.pdf}",
    ],
)
def test_publisher_templates_reject_invalid_or_unsafe_addresses(template):
    from custom_components.salah_timetable.sources.source_flow import (
        render_publisher_url,
    )

    with pytest.raises(ValueError):
        render_publisher_url(template, 2027)


def test_publisher_template_renders_the_next_year():
    from custom_components.salah_timetable.sources.source_flow import (
        render_publisher_url,
    )

    assert render_publisher_url("https://example.org/{year}.pdf", 2028) == (
        "https://example.org/2028.pdf"
    )


async def test_publisher_template_preview_requires_confirmation():
    from types import SimpleNamespace

    from custom_components.salah_timetable.sources.source_flow import SourceOptionsFlow

    flow = SourceOptionsFlow()
    flow.hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_known_entry=lambda _: SimpleNamespace(
                options={"publisher_url_template": "https://example.org/{year}.csv"}
            )
        )
    )
    flow.handler = "entry"
    storage = rollover_scenario()
    flow._coordinator = lambda: SimpleNamespace(storage=storage)
    with patch.object(flow, "async_step_import_url", AsyncMock()) as handler:
        preview = await flow.async_step_annual_rollover(
            {"source_id": "annual-2026", "use_template": True}
        )
        assert preview["step_id"] == "annual_rollover_preview"
        handler.assert_not_awaited()
        await flow.async_step_annual_rollover_preview(
            {"url": "https://example.org/2027.csv"}
        )
        handler.assert_awaited_once_with(
            {
                "year": 2027,
                "kind": "annual",
                "media_type": "csv",
                "url": "https://example.org/2027.csv",
            }
        )


async def test_publisher_template_is_validated_saved_and_removed(hass, entry):
    await setup_mosque(hass, entry)
    staged = await stage_url(hass, entry)
    await approve(hass, staged)
    original = dict(entry.options)

    form = await open_step(hass, entry, "publisher_template")
    assert form["description_placeholders"]["year_placeholder"] == "{year}"
    invalid = await hass.config_entries.options.async_configure(
        form["flow_id"], {"template": "http://example.org/{year}.csv"}
    )
    assert invalid["errors"] == {"base": "invalid_publisher_template"}
    assert dict(entry.options) == original

    template = "https://example.org/timetable-{year}.csv"
    result = await hass.config_entries.options.async_configure(
        form["flow_id"], {"template": template}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options["publisher_url_template"] == template
    assert all(entry.options[key] == value for key, value in original.items())

    form = await open_step(hass, entry, "publisher_template")
    result = await hass.config_entries.options.async_configure(
        form["flow_id"], {"template": ""}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert "publisher_url_template" not in entry.options
    assert dict(entry.options) == original


async def test_rollover_rejects_missing_url_and_invalid_saved_template():
    from types import SimpleNamespace

    from custom_components.salah_timetable.sources.source_flow import SourceOptionsFlow

    options = {"publisher_url_template": "http://example.org/{year}.csv"}
    flow = SourceOptionsFlow()
    flow.hass = SimpleNamespace(
        config_entries=SimpleNamespace(
            async_get_known_entry=lambda _: SimpleNamespace(options=options)
        )
    )
    flow.handler = "entry"
    flow._coordinator = lambda: SimpleNamespace(storage=rollover_scenario())
    with patch.object(flow, "async_step_import_url", AsyncMock()) as download:
        missing = await flow.async_step_annual_rollover({"source_id": "annual-2026"})
        assert missing["errors"] == {"base": "rollover_url_required"}
        invalid = await flow.async_step_annual_rollover(
            {"source_id": "annual-2026", "use_template": True}
        )
        assert invalid["errors"] == {"base": "invalid_publisher_template"}
        download.assert_not_awaited()
