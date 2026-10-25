"""Salah Timetable integration."""

from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir

from .const import CONF_TIME_ZONE, DOMAIN
from .coordinator import SalahCoordinator
from .frontend import async_setup_frontend
from .source_updates import SourceUpdateManager
from .storage import TimetableStorage

type SalahConfigEntry = ConfigEntry[SalahCoordinator]
PLATFORMS = [Platform.SENSOR, Platform.CALENDAR]


async def async_setup_entry(hass: HomeAssistant, entry: SalahConfigEntry) -> bool:
    await async_setup_frontend(hass)
    zone = ZoneInfo(entry.options.get(CONF_TIME_ZONE, entry.data[CONF_TIME_ZONE]))
    storage = TimetableStorage(hass, entry.entry_id, zone)
    try:
        await storage.async_load()
    except (ValueError, TypeError, KeyError) as err:
        ir.async_create_issue(
            hass,
            DOMAIN,
            f"invalid_storage_{entry.entry_id}",
            is_fixable=False,
            is_persistent=True,
            severity=ir.IssueSeverity.ERROR,
            translation_key="invalid_storage",
            translation_placeholders={"mosque": entry.title},
        )
        raise ConfigEntryError(
            "Stored timetable is invalid; original storage retained"
        ) from err
    ir.async_delete_issue(hass, DOMAIN, f"invalid_storage_{entry.entry_id}")
    coordinator = SalahCoordinator(hass, entry, storage, zone)
    coordinator.source_updates = SourceUpdateManager(hass, entry, storage, coordinator)
    entry.runtime_data = coordinator
    try:
        await coordinator.async_config_entry_first_refresh()
        dr.async_get(hass).async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.title,
            manufacturer="Salah Timetable",
            model="Mosque timetable",
        )
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        await coordinator.source_updates.async_start()
        entry.async_on_unload(entry.add_update_listener(async_update_options))
    except BaseException:
        # First refresh may already have installed an independent boundary timer.
        # Also clean up if platform setup or startup is interrupted.
        await coordinator.source_updates.async_stop()
        await coordinator.async_shutdown()
        raise
    return True


async def async_update_options(hass: HomeAssistant, entry: SalahConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: SalahConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.source_updates.async_stop()
        await entry.runtime_data.async_shutdown()
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: SalahConfigEntry) -> None:
    await TimetableStorage(hass, entry.entry_id, ZoneInfo("UTC")).async_remove()
    ir.async_delete_issue(hass, DOMAIN, f"invalid_storage_{entry.entry_id}")
