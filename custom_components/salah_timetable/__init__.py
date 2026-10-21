"""Salah Timetable integration."""

from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers import device_registry as dr

from .const import CONF_TIME_ZONE, DOMAIN
from .coordinator import SalahCoordinator
from .storage import TimetableStorage

type SalahConfigEntry = ConfigEntry[SalahCoordinator]
PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: SalahConfigEntry) -> bool:
    zone = ZoneInfo(entry.options.get(CONF_TIME_ZONE, entry.data[CONF_TIME_ZONE]))
    storage = TimetableStorage(hass, entry.entry_id, zone)
    try:
        await storage.async_load()
    except (ValueError, TypeError, KeyError) as err:
        raise ConfigEntryError(
            "Stored timetable is invalid; original storage retained"
        ) from err
    coordinator = SalahCoordinator(hass, entry, storage, zone)
    entry.runtime_data = coordinator
    await coordinator.async_config_entry_first_refresh()
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.unique_id)},
        name=entry.title,
        manufacturer="Salah Timetable",
        model="Mosque timetable",
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    return True


async def async_update_options(hass: HomeAssistant, entry: SalahConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: SalahConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: SalahConfigEntry) -> None:
    await TimetableStorage(hass, entry.entry_id, ZoneInfo("UTC")).async_remove()
