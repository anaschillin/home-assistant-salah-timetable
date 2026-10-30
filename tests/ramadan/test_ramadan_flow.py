"""Graphical Ramadan confirmation preserves options and validates ambiguity."""

from datetime import date, time
from zoneinfo import ZoneInfo

import pytest
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er

from custom_components.salah_timetable.const import DOMAIN
from custom_components.salah_timetable.domain.model import (
    DailyPrayers,
    PrayerField,
    Timetable,
)
from custom_components.salah_timetable.persistence.storage import TimetableStorage


async def ramadan_flow(hass, entry):
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.MENU
    assert "ramadan" in result["menu_options"]
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "ramadan"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "ramadan"
    return result


def data(**changes):
    result = {
        "ramadan_mode": "auto",
        "ramadan_start": "2026-03-10",
        "ramadan_end": "2026-03-11",
        "ramadan_adjustment": 0,
        "ramadan_source_id": "__auto__",
    }
    result.update(changes)
    return result


async def test_confirm_and_clear_dates_preserving_other_options(hass, entry):
    hass.config_entries.async_update_entry(
        entry, options={"time_zone": "Europe/London", "custom_marker": "keep me"}
    )
    result = await ramadan_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], data()
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options["time_zone"] == "Europe/London"
    assert entry.options["custom_marker"] == "keep me"
    assert entry.options["ramadan_start"] == "2026-03-10"
    assert entry.options["ramadan_end"] == "2026-03-11"
    assert entry.options["ramadan_source_id"] is None
    result = await ramadan_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "ramadan_mode": "auto",
            "ramadan_adjustment": 0,
            "ramadan_source_id": "__auto__",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options["ramadan_start"] is None
    assert entry.options["ramadan_end"] is None
    assert entry.options["custom_marker"] == "keep me"


async def test_timezone_edit_retains_ramadan_confirmation(hass, entry):
    hass.config_entries.async_update_entry(
        entry,
        options={
            "ramadan_mode": "auto",
            "ramadan_start": "2026-03-10",
            "ramadan_end": "2026-03-11",
            "ramadan_adjustment": 1,
            "custom_marker": "keep me",
        },
    )
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"next_step_id": "settings"}
    )
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"time_zone": "Asia/Riyadh"}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options["time_zone"] == "Asia/Riyadh"
    assert entry.options["ramadan_start"] == "2026-03-10"
    assert entry.options["ramadan_adjustment"] == 1
    assert entry.options["custom_marker"] == "keep me"


@pytest.mark.parametrize(
    "changes",
    [
        {"ramadan_end": "2026-03-09"},
        {"ramadan_end": "2026-05-10"},
        {"ramadan_adjustment": 1.5},
        {"ramadan_end": None},
    ],
)
async def test_invalid_confirmation_is_not_saved(hass, entry, changes):
    result = await ramadan_flow(hass, entry)
    values = data(**changes)
    if values.get("ramadan_end") is None:
        values.pop("ramadan_end", None)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], values
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_ramadan"}
    assert not entry.options
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], data()
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options["ramadan_start"] == "2026-03-10"
    assert entry.options["ramadan_end"] == "2026-03-11"


async def test_invalid_stored_ramadan_settings_can_be_replaced(hass, entry):
    """A legacy invalid option must not stop the user opening its repair form."""
    hass.config_entries.async_update_entry(
        entry, options={"ramadan_mode": "unsupported", "custom_marker": "keep me"}
    )
    result = await ramadan_flow(hass, entry)
    fields = {key.schema: key for key in result["data_schema"].schema}
    assert fields["ramadan_mode"].default() == "auto"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], data()
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options["ramadan_mode"] == "auto"
    assert entry.options["custom_marker"] == "keep me"


async def test_removed_ramadan_source_can_be_reselected_on_same_flow(hass, entry):
    """A source removed after opening the form cannot become a saved selection."""
    table = Timetable(
        "ramadan-2026",
        "ramadan",
        (DailyPrayers(date(2026, 3, 10), {PrayerField.FAJR_BEGIN: (time(5),)}, {}),),
    )
    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    await storage.async_replace((table,))
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await ramadan_flow(hass, entry)
    await entry.runtime_data.storage.async_replace(())
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], data(ramadan_source_id="ramadan-2026")
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_ramadan"}
    assert not entry.options
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], data()
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.options["ramadan_source_id"] is None
    await hass.async_block_till_done()


async def test_overlapping_ramadan_requires_explicit_source(hass, entry, freezer):
    freezer.move_to("2026-03-10T10:00:00+00:00")
    annual = Timetable(
        "annual-2026",
        "annual",
        (DailyPrayers(date(2026, 3, 10), {PrayerField.FAJR_BEGIN: (time(6),)}, {}),),
    )
    first = Timetable(
        "ramadan-a",
        "ramadan",
        (DailyPrayers(date(2026, 3, 10), {PrayerField.FAJR_BEGIN: (time(5),)}, {}),),
    )
    second = Timetable(
        "ramadan-b",
        "ramadan",
        (
            DailyPrayers(
                date(2026, 3, 10), {PrayerField.FAJR_BEGIN: (time(5, 15),)}, {}
            ),
        ),
    )
    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    await storage.async_replace((annual, first, second))
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await ramadan_flow(hass, entry)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], data()
    )
    assert result["errors"] == {"base": "invalid_ramadan"}
    assert not entry.options
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], data(ramadan_source_id="ramadan-b")
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options["ramadan_source_id"] == "ramadan-b"
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, "example_fajr_begin"
    )
    assert hass.states.get(entity_id).state == "2026-03-10T05:15:00+00:00"
