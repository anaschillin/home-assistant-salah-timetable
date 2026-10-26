from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.salah_timetable.const import DOMAIN
from custom_components.salah_timetable.model import PrayerField


async def test_empty_setup_and_unload(hass, entry):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.LOADED
    assert len(er.async_get(hass).entities) == len(PrayerField) + 11
    assert (
        hass.states.get("sensor.example_mosque_fajr_beginning").state == "unavailable"
    )
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, "example"), entry.entry_id
    )
    assert device.name == "Example Mosque"
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state == ConfigEntryState.NOT_LOADED


async def test_timestamps_reload_rollover_and_stable_ids(hass, populated, freezer):
    freezer.move_to("2026-10-21 10:00:00+00:00")
    assert await hass.config_entries.async_setup(populated.entry_id)
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, "example_fajr_begin"
    )
    assert hass.states.get(entity_id).state == "2026-10-21T04:45:00+00:00"
    jumuah = hass.states.get(
        er.async_get(hass).async_get_entity_id("sensor", DOMAIN, "example_jumuah")
    )
    assert len(jumuah.attributes["scheduled_times"]) == 2
    ids = set(er.async_get(hass).entities)
    assert await hass.config_entries.async_reload(populated.entry_id)
    await hass.async_block_till_done()
    assert set(er.async_get(hass).entities) == ids
    freezer.move_to("2026-10-22 00:01:00+01:00")
    async_fire_time_changed(hass, datetime(2026, 10, 21, 23, 1, tzinfo=timezone.utc))
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "2026-10-22T04:47:00+00:00"
    freezer.move_to("2026-10-23 12:00:00+00:00")
    await populated.runtime_data.async_refresh()
    assert hass.states.get(entity_id).state == "unavailable"


async def test_invalid_store_setup_error(hass, entry):
    with patch(
        "custom_components.salah_timetable.storage._TimetableStore.async_load",
        AsyncMock(return_value={"timetables": [{}]}),
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state == ConfigEntryState.SETUP_ERROR


async def test_options_reload(hass, populated, freezer):
    freezer.move_to("2026-10-21 10:00:00+00:00")
    assert await hass.config_entries.async_setup(populated.entry_id)
    await hass.async_block_till_done()
    hass.config_entries.async_update_entry(
        populated, options={"time_zone": "Asia/Riyadh"}
    )
    await hass.async_block_till_done()
    assert str(populated.runtime_data.zone) == "Asia/Riyadh"
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, "example_fajr_begin"
    )
    assert hass.states.get(entity_id).state == "2026-10-21T02:45:00+00:00"


async def test_remove_entry_cleans_storage(hass, populated):
    key = f"{DOMAIN}.{populated.entry_id}"
    assert await hass.config_entries.async_remove(populated.entry_id)
    from homeassistant.helpers.storage import Store

    assert await Store(hass, 1, key).async_load() is None


async def test_two_mosques_are_isolated(hass, populated, freezer):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    freezer.move_to("2026-10-21 10:00:00+00:00")
    other = MockConfigEntry(
        domain=DOMAIN,
        title="Other Mosque",
        unique_id="other",
        data={"name": "Other Mosque", "mosque_id": "other", "time_zone": "UTC"},
    )
    assert await hass.config_entries.async_setup(populated.entry_id)
    await hass.async_block_till_done()
    other.add_to_hass(hass)
    assert await hass.config_entries.async_setup(other.entry_id)
    await hass.async_block_till_done()
    devices = dr.async_get(hass)
    first = devices.async_get_device_by_identifier(
        (DOMAIN, "example"), populated.entry_id
    )
    second = devices.async_get_device_by_identifier((DOMAIN, "other"), other.entry_id)
    assert first.id != second.id
    registry = er.async_get(hass)
    first_id = registry.async_get_entity_id("sensor", DOMAIN, "example_fajr_begin")
    second_id = registry.async_get_entity_id("sensor", DOMAIN, "other_fajr_begin")
    assert hass.states.get(first_id).state != "unavailable"
    assert hass.states.get(second_id).state == "unavailable"
    # Each mosque has its own dashboard entity, even before its first import.
    first_dashboard = registry.async_get_entity_id(
        "sensor", DOMAIN, "example_dashboard"
    )
    second_dashboard = registry.async_get_entity_id("sensor", DOMAIN, "other_dashboard")
    assert first_dashboard != second_dashboard
    assert (
        hass.states.get(first_dashboard).attributes["mosque_name"] == "Example Mosque"
    )
    assert hass.states.get(second_dashboard).attributes["mosque_name"] == "Other Mosque"
    assert len(registry.entities) == 2 * (len(PrayerField) + 11)


async def test_unchanged_data_does_not_write_states(hass, populated, freezer):
    freezer.move_to("2026-10-21 10:00:00+00:00")
    assert await hass.config_entries.async_setup(populated.entry_id)
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, "example_fajr_begin"
    )
    previous = hass.states.get(entity_id)
    freezer.tick(60)
    await populated.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(entity_id) is previous
