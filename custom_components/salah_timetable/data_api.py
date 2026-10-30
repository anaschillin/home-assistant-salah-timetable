"""Authenticated, bounded approved timetable reads for the card and export."""

from typing import Any

import voluptuous as vol
from homeassistant.auth.permissions.const import POLICY_READ
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .domain.month_data import (
    approved_month,
    approved_source_details,
    approved_year_csv,
)
from .domain.ramadan import RamadanSettings


def _entry_for_dashboard(hass: HomeAssistant, connection, entity_id: str):
    """Resolve a real installed mosque dashboard entity and enforce read permission."""
    entity = er.async_get(hass).async_get(entity_id)
    if (
        entity is None
        or entity.platform != DOMAIN
        or not entity.unique_id.endswith("_dashboard")
    ):
        return None
    user = connection.user
    if user is None or (
        not user.is_admin and not user.permissions.check_entity(entity_id, POLICY_READ)
    ):
        raise Unauthorized(entity_id=entity_id, permission=POLICY_READ)
    entry = hass.config_entries.async_get_entry(entity.config_entry_id)
    if entry is None or entry.domain != DOMAIN or entry.runtime_data is None:
        return None
    return entry


@websocket_api.websocket_command(
    {
        vol.Required("type"): "salah_timetable/month",
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("year"): vol.All(vol.Coerce(int), vol.Range(min=1, max=9999)),
        vol.Required("month"): vol.All(vol.Coerce(int), vol.Range(min=1, max=12)),
    }
)
@websocket_api.async_response
async def ws_month(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    """Read a Gregorian month; never return staged records."""
    entry = _entry_for_dashboard(hass, connection, msg["entity_id"])
    if entry is None:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "Mosque unavailable")
        return
    runtime = entry.runtime_data
    settings = RamadanSettings.from_options(entry.options)
    try:
        rows = await hass.async_add_executor_job(
            approved_month, runtime.storage.timetables, settings, msg["year"], msg["month"]
        )
    except ValueError:
        connection.send_error(msg["id"], "unresolved_timetable", "Review conflicting approved source dates")
        return
    connection.send_result(msg["id"], {"year": msg["year"], "month": msg["month"], "rows": rows})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "salah_timetable/year_csv",
        vol.Required("entity_id"): cv.entity_id,
        vol.Required("year"): vol.All(vol.Coerce(int), vol.Range(min=1, max=9999)),
    }
)
@websocket_api.async_response
async def ws_year_csv(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    """Return a downloadable CSV of approved effective fields."""
    entry = _entry_for_dashboard(hass, connection, msg["entity_id"])
    if entry is None:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "Mosque unavailable")
        return
    runtime = entry.runtime_data
    settings = RamadanSettings.from_options(entry.options)
    try:
        data = await hass.async_add_executor_job(
            approved_year_csv,
            runtime.storage.timetables,
            settings,
            msg["year"],
            runtime.zone.key,
        )
    except ValueError:
        connection.send_error(msg["id"], "unresolved_timetable", "Review conflicting approved source dates")
        return
    connection.send_result(msg["id"], {"year": msg["year"], "csv": data})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "salah_timetable/sources",
        vol.Required("entity_id"): cv.entity_id,
    }
)
@websocket_api.async_response
async def ws_sources(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    """Return metadata without publishing URLs, original source text or pending imports."""
    entry = _entry_for_dashboard(hass, connection, msg["entity_id"])
    if entry is None:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "Mosque unavailable")
        return
    connection.send_result(msg["id"], {"sources": approved_source_details(entry.runtime_data.storage)})


def register_websocket_commands(hass: HomeAssistant) -> None:
    """Register each command once, across any number of mosque instances."""
    key = f"{DOMAIN}_data_api_registered"
    if hass.data.get(key):
        return
    for handler in (ws_month, ws_year_csv, ws_sources):
        websocket_api.async_register_command(hass, handler)
    hass.data[key] = True
