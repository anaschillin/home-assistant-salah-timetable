"""Serve the bundled card and load it in storage- or YAML-resource dashboards."""

import logging
from asyncio import Lock
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfoNotFoundError

from homeassistant.components import frontend as ha_frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import MODE_STORAGE
from homeassistant.const import EVENT_COMPONENT_LOADED, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant, HomeAssistantError

from .const import DOMAIN

CARD_VERSION = "0.9.16"
STATIC_PATH = "/salah_timetable"
CARD_PATH = f"{STATIC_PATH}/salah-timetable-card.js"
CARD_URL = f"{CARD_PATH}?v={CARD_VERSION}"
_FRONTEND_DIR = str(Path(__file__).with_name("frontend"))
_DATA_KEY = f"{DOMAIN}_frontend"
_LOGGER = logging.getLogger(__name__)


@dataclass
class _FrontendState:
    lock: Lock = field(default_factory=Lock)
    static_registered: bool = False
    listening: bool = False
    unsubscribe_loaded: object | None = None
    unsubscribe_stop: object | None = None


def _is_card_resource(url: str) -> bool:
    """Only claim this integration's relative asset, never a remote resource."""
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    return not parsed.scheme and not parsed.netloc and parsed.path == CARD_PATH


def _remove_extra_versions(hass: HomeAssistant, *, keep_current: bool) -> None:
    """Use only the official frontend helpers to alter our extra module URLs."""
    manager = hass.data.get(ha_frontend.DATA_EXTRA_MODULE_URL)
    if manager is None:
        return
    for url in manager.urls:
        if _is_card_resource(url) and (not keep_current or url != CARD_URL):
            ha_frontend.remove_extra_js_url(hass, url)


async def _async_register_resource(hass: HomeAssistant) -> None:
    data = hass.data.get("lovelace")
    if data is None:
        return
    if data.resource_mode != MODE_STORAGE:
        # YAML collections are user-owned and must not be edited. HA's supported
        # extra-module helper loads the bundled card without requiring YAML edits.
        manager = hass.data.get(ha_frontend.DATA_EXTRA_MODULE_URL)
        if manager is None:
            return  # The frontend-loaded event will retry once its manager exists.
        _remove_extra_versions(hass, keep_current=True)
        if CARD_URL not in manager.urls:
            ha_frontend.add_extra_js_url(hass, CARD_URL)
        return
    resources = data.resources
    await resources.async_get_info()  # Public API loads the collection if necessary.
    existing = [
        item
        for item in resources.async_items()
        if isinstance(item.get("url"), str) and _is_card_resource(item["url"])
    ]
    if not existing:
        await resources.async_create_item({"url": CARD_URL, "res_type": "module"})
        _remove_extra_versions(hass, keep_current=False)
        return
    primary, *duplicates = existing
    if primary["url"] != CARD_URL or primary.get("type") != "module":
        await resources.async_update_item(
            primary["id"], {"url": CARD_URL, "res_type": "module"}
        )
    for duplicate in duplicates:
        await resources.async_delete_item(duplicate["id"])
    _remove_extra_versions(hass, keep_current=False)


async def async_setup_frontend(hass: HomeAssistant) -> None:
    """Register once per HA instance; handle dashboards loaded after the mosque."""
    state = hass.data.setdefault(_DATA_KEY, _FrontendState())
    async with state.lock:
        if not state.static_registered:
            await hass.http.async_register_static_paths(
                [StaticPathConfig(STATIC_PATH, _FRONTEND_DIR, cache_headers=True)]
            )
            state.static_registered = True
        if not state.listening:

            async def component_loaded(event: Event) -> None:
                if event.data.get("component") in {"lovelace", "frontend"}:
                    await async_setup_frontend(hass)

            def homeassistant_stopping(_event: Event) -> None:
                if state.unsubscribe_loaded is not None:
                    state.unsubscribe_loaded()
                    state.unsubscribe_loaded = None
                state.listening = False

            state.unsubscribe_loaded = hass.bus.async_listen(
                EVENT_COMPONENT_LOADED, component_loaded
            )
            state.unsubscribe_stop = hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STOP, homeassistant_stopping
            )
            state.listening = True
        try:
            await _async_register_resource(hass)
        except (
            HomeAssistantError,
            ZoneInfoNotFoundError,
            ValueError,
            TypeError,
            OSError,
        ):
            # A dashboard-storage error must not make valid prayer data unavailable.
            # Do not emit collection contents, which may include private URLs.
            _LOGGER.warning(
                "Could not register the bundled Salah Timetable card resource; "
                "retry setup or add %s as a module resource",
                CARD_URL,
            )
