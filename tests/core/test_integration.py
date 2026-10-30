from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.salah_timetable.const import DOMAIN
from custom_components.salah_timetable.domain.model import PrayerField


async def test_empty_setup_and_unload(hass, entry):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.LOADED
    assert len(er.async_get(hass).entities) == len(PrayerField) + 12
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
        "custom_components.salah_timetable.persistence.storage._TimetableStore.async_load",
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


async def test_removing_one_mosque_cleans_its_device_and_entities_only(
    hass, populated, freezer
):
    """One fixed mosque device belongs to one entry; removal is isolated."""
    from homeassistant.helpers.storage import Store
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
    # Adding an entry while HA is running can initiate its setup automatically.
    await hass.async_block_till_done()
    if other.state == ConfigEntryState.NOT_LOADED:
        assert await hass.config_entries.async_setup(other.entry_id)
        await hass.async_block_till_done()
    assert other.state == ConfigEntryState.LOADED

    devices = dr.async_get(hass)
    entities = er.async_get(hass)
    first = devices.async_get_device_by_identifier(
        (DOMAIN, "example"), populated.entry_id
    )
    second = devices.async_get_device_by_identifier((DOMAIN, "other"), other.entry_id)
    assert first is not None and second is not None
    first_sensor = entities.async_get_entity_id("sensor", DOMAIN, "example_fajr_begin")
    first_calendar = entities.async_get_entity_id(
        "calendar", DOMAIN, "example_prayer_calendar"
    )
    second_sensor = entities.async_get_entity_id("sensor", DOMAIN, "other_fajr_begin")
    second_calendar = entities.async_get_entity_id(
        "calendar", DOMAIN, "other_prayer_calendar"
    )
    assert all((first_sensor, first_calendar, second_sensor, second_calendar))

    assert await hass.config_entries.async_remove(populated.entry_id)
    await hass.async_block_till_done()
    assert (
        devices.async_get_device_by_identifier((DOMAIN, "example"), populated.entry_id)
        is None
    )
    assert (
        devices.async_get_device_by_identifier((DOMAIN, "other"), other.entry_id)
        is not None
    )
    assert entities.async_get_entity_id("sensor", DOMAIN, "example_fajr_begin") is None
    assert (
        entities.async_get_entity_id("calendar", DOMAIN, "example_prayer_calendar")
        is None
    )
    assert hass.states.get(first_sensor) is None
    assert hass.states.get(first_calendar) is None
    assert hass.states.get(second_sensor) is not None
    assert hass.states.get(second_calendar) is not None
    assert await Store(hass, 1, f"{DOMAIN}.{populated.entry_id}").async_load() is None
    assert other.runtime_data.storage.timetables == ()


async def test_new_entity_defaults_preserve_dashboard_and_automation_interfaces(
    hass, populated, freezer
):
    freezer.move_to("2026-10-21T10:00:00+00:00")
    assert await hass.config_entries.async_setup(populated.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    entries = er.async_entries_for_config_entry(registry, populated.entry_id)
    disabled = [item for item in entries if item.disabled_by is not None]
    assert len(disabled) == 1
    previous = disabled[0]
    assert previous.unique_id == "example_previous_jamaat"
    assert previous.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get(previous.entity_id) is None

    for item in entries:
        assert item.has_entity_name
        assert item.translation_key
        assert item.original_name
        assert item.device_id == previous.device_id
        if item is not previous:
            assert hass.states.get(item.entity_id) is not None

    # Diagnostic information is available to the supplied health blueprint.
    for key in ("source_status", "coverage_status"):
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"example_{key}")
        item = registry.async_get(entity_id)
        assert item.entity_category is EntityCategory.DIAGNOSTIC
        assert item.original_device_class == "enum"

    for key in (
        *(field.value for field in PrayerField),
        "next_salah",
        "next_jamaat",
        "previous_jamaat",
        "next_sehri",
        "next_iftar",
    ):
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"example_{key}")
        assert registry.async_get(entity_id).original_device_class == "timestamp"

    dashboard = registry.async_get_entity_id("sensor", DOMAIN, "example_dashboard")
    assert hass.states.get(dashboard).attributes["previous_jamaat"] is not None
    calendar = registry.async_get_entity_id(
        "calendar", DOMAIN, "example_prayer_calendar"
    )
    assert registry.async_get(calendar).supported_features == 0


async def test_user_enabled_previous_jamaat_survives_reload(hass, populated, freezer):
    freezer.move_to("2026-10-21T10:00:00+00:00")
    assert await hass.config_entries.async_setup(populated.entry_id)
    await hass.async_block_till_done()
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "sensor", DOMAIN, "example_previous_jamaat"
    )
    registry.async_update_entity(entity_id, disabled_by=None)
    assert await hass.config_entries.async_reload(populated.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get(entity_id).disabled_by is None
    assert hass.states.get(entity_id).state == "2026-10-21T05:15:00+00:00"
    assert await hass.config_entries.async_reload(populated.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get(entity_id).disabled_by is None
    assert hass.states.get(entity_id).state == "2026-10-21T05:15:00+00:00"


async def test_existing_previous_jamaat_registry_choice_is_retained(
    hass, populated, freezer
):
    """An upgrade must keep both enabled and explicitly user-disabled choices."""
    freezer.move_to("2026-10-21T10:00:00+00:00")
    registry = er.async_get(hass)
    previous = registry.async_get_or_create(
        "sensor", DOMAIN, "example_previous_jamaat", config_entry=populated
    )
    assert await hass.config_entries.async_setup(populated.entry_id)
    await hass.async_block_till_done()
    assert registry.async_get(previous.entity_id).disabled_by is None
    assert hass.states.get(previous.entity_id) is not None
    registry.async_update_entity(
        previous.entity_id, disabled_by=er.RegistryEntryDisabler.USER
    )
    assert await hass.config_entries.async_reload(populated.entry_id)
    await hass.async_block_till_done()
    assert (
        registry.async_get(previous.entity_id).disabled_by
        is er.RegistryEntryDisabler.USER
    )
    assert hass.states.get(previous.entity_id) is None
