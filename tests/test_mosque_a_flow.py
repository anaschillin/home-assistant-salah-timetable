"""MOSQUE_A annual PDF support uses the same HA upload, review and update workflow."""

import base64
from datetime import date, timezone
from hashlib import sha256
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import FormData
from homeassistant.components.file_upload import DOMAIN as UPLOAD_DATA
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er

from custom_components.salah_timetable.const import DOMAIN
from custom_components.salah_timetable.download import DownloadResult
from custom_components.salah_timetable.model import PrayerField

FIXTURE = Path(__file__).parent / "fixtures/pdf/mosque_a_synthetic_2026.pdf"
SOURCE_URL = "https://mosque-a.example.org/timetables/time-table.pdf"


@pytest.fixture(autouse=True)
def mosque_a_clock(freezer):
    """Friday before HA creates credentials for its real upload endpoint."""
    freezer.move_to("2026-01-02 10:00:00+00:00")



async def setup(hass, entry):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def menu_step(hass, entry, step):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert step in result["menu_options"]
    return await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": step}
    )


async def upload_pdf(hass, client, content):
    form = FormData()
    form.add_field(
        "file", content, filename="mosque_a_annual.pdf", content_type="application/pdf"
    )
    response = await client.post("/api/file_upload", data=form)
    assert response.status == 200
    file_id = (await response.json())["file_id"]
    return file_id, hass.data[UPLOAD_DATA].file_path(file_id)


async def submit_mapping(hass, result):
    assert result["step_id"] == "map_columns"
    defaults = result["data_schema"]({})
    assert defaults["date_column"] == "Date"
    assert defaults["time_format"] == "24h"
    assert defaults["jumuah"] == "Jumuah"
    assert defaults["maghrib_begin"] == "Maghrib Begin"
    assert defaults["maghrib_jamaat"] == "Maghrib Jamaat"
    assert defaults["iftar"] == "Iftar"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], defaults
    )
    assert result["step_id"] == "review"
    assert result["errors"] == {}
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


def as_state(row, field, zone):
    return row.timestamps(field, zone)[0].astimezone(timezone.utc).isoformat()


async def test_mosque_a_upload_default_mapping_approval_and_weekday_sensors(
    hass, entry, authenticated_upload_client, freezer
):
    await setup(hass, entry)
    result = await menu_step(hass, entry, "import_pdf")
    content = FIXTURE.read_bytes()
    file_id, path = await upload_pdf(hass, authenticated_upload_client, content)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "file": file_id,
            "kind": "annual",
            "year": 2026,
        },
    )
    assert not await hass.async_add_executor_job(path.exists)
    assert file_id not in hass.data[UPLOAD_DATA].files
    result = await submit_mapping(hass, result)
    storage = entry.runtime_data.storage
    assert storage.timetables == ()
    candidate = storage.staged.candidate
    assert candidate.parser_id == "mosque_a_annual_v1"
    assert candidate.source_format == "pdf"
    assert candidate.sha256 == sha256(content).hexdigest()
    assert base64.b64decode(candidate.source_base64) == content
    assert candidate.coverage.row_count == 365
    assert candidate.coverage.missing_dates == ()
    assert any(
        value in {'"', '""', "“", "”", "″"}
        for row in candidate.timetable.days
        for key, value in row.original.items()
        if key.startswith("Published ")
    )
    await approve(hass, result)
    friday = storage.for_date(date(2026, 1, 2))
    thursday = storage.for_date(date(2026, 1, 1))
    saturday = storage.for_date(date(2026, 1, 3))
    assert PrayerField.JUMUAH in friday.times
    assert PrayerField.DHUHR_JAMAAT not in friday.times
    assert PrayerField.JUMUAH not in thursday.times
    assert PrayerField.DHUHR_JAMAAT in thursday.times
    assert PrayerField.JUMUAH not in saturday.times
    assert friday.times[PrayerField.IFTAR] == friday.times[PrayerField.MAGHRIB_JAMAAT]
    assert friday.times[PrayerField.IFTAR] != friday.times[PrayerField.MAGHRIB_BEGIN]
    assert entity_state(hass, "jumuah") == as_state(
        friday, PrayerField.JUMUAH, entry.runtime_data.zone
    )
    assert entity_state(hass, "dhuhr_jamaat") == "unavailable"
    assert entity_state(hass, "iftar") == as_state(
        friday, PrayerField.IFTAR, entry.runtime_data.zone
    )
    assert entity_state(hass, "maghrib_begin") != entity_state(hass, "iftar")

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.storage.approved_sources["annual-2026"] == candidate
    assert entity_state(hass, "jumuah") == as_state(
        friday, PrayerField.JUMUAH, entry.runtime_data.zone
    )
    freezer.move_to("2026-01-01 10:00:00+00:00")
    await entry.runtime_data.async_refresh()
    assert entity_state(hass, "jumuah") == "unavailable"
    assert entity_state(hass, "dhuhr_jamaat") == as_state(
        thursday, PrayerField.DHUHR_JAMAAT, entry.runtime_data.zone
    )
    freezer.move_to("2026-01-03 10:00:00+00:00")
    await entry.runtime_data.async_refresh()
    assert entity_state(hass, "jumuah") == "unavailable"
    assert entity_state(hass, "dhuhr_jamaat") == as_state(
        saturday, PrayerField.DHUHR_JAMAAT, entry.runtime_data.zone
    )


async def test_mosque_a_url_profile_and_changed_pdf_require_new_approval(
    hass, entry, freezer
):
    await setup(hass, entry)
    content = FIXTURE.read_bytes()
    result = await menu_step(hass, entry, "import_url")
    first = DownloadResult(
        content, "pdf", '"mosque_a-v1"', None, sha256(content).hexdigest()
    )
    with patch(
        "custom_components.salah_timetable.source_flow.async_download",
        AsyncMock(return_value=first),
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
    result = await submit_mapping(hass, result)
    await approve(hass, result)
    storage = entry.runtime_data.storage
    previous = storage.timetables
    profile = storage.remote_sources["annual-2026"]
    assert profile.parser_id == "mosque_a_annual_v1"
    assert profile.media_type == "pdf"
    assert profile.url == SOURCE_URL
    assert profile.time_format == "24h"
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    freezer.move_to("2026-01-01T10:00:00+00:00")
    await entry.runtime_data.async_refresh()
    previous_fajr_state = entity_state(hass, "fajr_begin")
    storage = entry.runtime_data.storage
    assert storage.remote_sources["annual-2026"] == profile
    assert storage.approved_sources["annual-2026"].sha256 == sha256(content).hexdigest()

    # The synthetic fixture uses uncompressed, fixed-width PDF text streams.
    # Changing Jan 1 Dawn preserves PDF offsets and creates a real changed event.
    changed = content.replace(b"5:07", b"5:08", 1)
    assert changed != content
    second = DownloadResult(
        changed, "pdf", '"mosque_a-v2"', None, sha256(changed).hexdigest()
    )
    with patch(
        "custom_components.salah_timetable.source_updates.download.async_download",
        AsyncMock(return_value=second),
    ) as fetch:
        await entry.runtime_data.source_updates.async_check_all()
    fetch.assert_awaited_once_with(
        SOURCE_URL, media_type="pdf", etag='"mosque_a-v1"', last_modified=None
    )
    assert storage.timetables == previous
    assert storage.approved_sources["annual-2026"].sha256 == sha256(content).hexdigest()
    assert storage.staged.candidate.sha256 == sha256(changed).hexdigest()
    assert storage.staged.candidate.parser_id == "mosque_a_annual_v1"
    assert (
        storage.staged.candidate.timetable.days[0]
        .times[PrayerField.FAJR_BEGIN][0]
        .strftime("%H:%M")
        == "05:08"
    )
    assert (
        storage.for_date(date(2026, 1, 1))
        .times[PrayerField.FAJR_BEGIN][0]
        .strftime("%H:%M")
        == "05:07"
    )
    assert entity_state(hass, "source_status") == "pending_review"
    assert entity_state(hass, "fajr_begin") == previous_fajr_state

    # A pending update must survive reload without changing the active timetable.
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.runtime_data.storage.timetables == previous
    assert (
        entry.runtime_data.storage.staged.candidate.sha256
        == sha256(changed).hexdigest()
    )
    assert entity_state(hass, "fajr_begin") == previous_fajr_state

    # Explicit approval activates the updated timetable.
    result = await menu_step(hass, entry, "review")
    assert result["step_id"] == "review"
    await approve(hass, result)

    updated = entry.runtime_data.storage.for_date(date(2026, 1, 1))
    assert updated.times[PrayerField.FAJR_BEGIN][0].strftime("%H:%M") == "05:08"

    # The live sensor must now reflect the approved change.
    assert entity_state(hass, "fajr_begin") == as_state(
        updated,
        PrayerField.FAJR_BEGIN,
        entry.runtime_data.zone,
    )
    assert entity_state(hass, "fajr_begin") != previous_fajr_state
    assert entry.runtime_data.storage.staged is None
    assert entity_state(hass, "source_status") == "up_to_date"

    # The approved update must survive another Home Assistant reload.
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.runtime_data.storage.staged is None
    assert (
        entry.runtime_data.storage.approved_sources["annual-2026"].sha256
        == sha256(changed).hexdigest()
    )
    assert entity_state(hass, "fajr_begin") == as_state(
        updated,
        PrayerField.FAJR_BEGIN,
        entry.runtime_data.zone,
    )


async def test_mosque_a_monthly_pdf_ramadan_upload_approval_and_activation(
    hass, entry, authenticated_upload_client, freezer
):
    """MOSQUE_A monthly PDF can be approved and activated as a Ramadan source."""
    from datetime import time

    monthly_fixture = Path(__file__).parent / "fixtures/pdf/mosque_a_monthly_2022.pdf"

    await setup(hass, entry)

    # Upload the fictional Mosque A monthly PDF as a Ramadan source.
    result = await menu_step(hass, entry, "import_pdf")
    content = monthly_fixture.read_bytes()
    file_id, path = await upload_pdf(hass, authenticated_upload_client, content)

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "file": file_id,
            "kind": "ramadan",
            "year": 2022,
        },
    )

    assert not await hass.async_add_executor_job(path.exists)

    result = await submit_mapping(hass, result)

    storage = entry.runtime_data.storage
    candidate = storage.staged.candidate

    assert candidate.parser_id == "mosque_a_monthly_v1"
    assert candidate.coverage.row_count == 61
    assert candidate.coverage.missing_dates == ()

    await approve(hass, result)

    ramadan = storage.approved_sources["ramadan-2022"]

    # Importing a Ramadan source does not automatically activate it.
    freezer.move_to("2022-05-01T12:00:00+00:00")
    await entry.runtime_data.async_refresh()
    assert not entry.runtime_data.data.effective.ramadan_active

    # Confirm a deliberately selected test window.
    result = await menu_step(hass, entry, "ramadan")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "ramadan_mode": "auto",
            "ramadan_start": "2022-05-01",
            "ramadan_end": "2022-05-02",
            "ramadan_adjustment": 0,
            "ramadan_source_id": "ramadan-2022",
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    # Confirm settings and approved source survive a reload.
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.runtime_data.storage.approved_sources["ramadan-2022"] == ramadan

    freezer.move_to("2022-05-01T12:00:00+00:00")
    await entry.runtime_data.async_refresh()

    effective = entry.runtime_data.data.effective

    assert effective.ramadan_active
    assert effective.row is not None
    assert effective.row.times[PrayerField.IFTAR] == (time(18, 22),)
    assert effective.row.times[PrayerField.MAGHRIB_BEGIN] == (time(18, 17),)
    assert PrayerField.TARAWEEH not in effective.row.times

    # Outside the confirmed window, Ramadan is inactive.
    freezer.move_to("2022-05-03T12:00:00+00:00")
    await entry.runtime_data.async_refresh()

    assert not entry.runtime_data.data.effective.ramadan_active
