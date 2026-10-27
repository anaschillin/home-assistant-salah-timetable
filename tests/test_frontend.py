"""Use HA's real resource collection and authenticated static HTTP endpoint."""

from asyncio import gather
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from homeassistant.components import frontend as ha_frontend
from homeassistant.components.lovelace.resources import (
    ResourceStorageCollection,
    ResourceYAMLCollection,
)
from homeassistant.const import EVENT_COMPONENT_LOADED, EVENT_HOMEASSISTANT_STOP
from homeassistant.exceptions import HomeAssistantError
from homeassistant.setup import async_setup_component

from custom_components.salah_timetable.frontend import (
    CARD_PATH,
    CARD_URL,
    async_setup_frontend,
)


async def make_resources(hass):
    collection = ResourceStorageCollection(
        hass, SimpleNamespace(async_load=AsyncMock(return_value={}))
    )
    hass.data["lovelace"] = SimpleNamespace(
        resource_mode="storage", resources=collection
    )
    return collection


async def test_bundled_modules_are_served_and_paths_registered_once(hass, hass_client):
    assert await async_setup_component(hass, "http", {})
    with patch.object(
        hass.http,
        "async_register_static_paths",
        wraps=hass.http.async_register_static_paths,
    ) as register:
        await gather(async_setup_frontend(hass), async_setup_frontend(hass))
        assert register.call_count == 1
    client = await hass_client()
    response = await client.get(CARD_URL)
    assert response.status == 200
    assert "SalahTimetableCard" in await response.text()
    utility = await client.get("/salah_timetable/card-utils.js")
    assert utility.status == 200
    assert "export" in await utility.text()
    translations = await client.get("/salah_timetable/card-i18n.js")
    assert translations.status == 200
    source = await translations.text()
    assert "CATALOGS" in source
    assert "الفجر" in source


async def test_resource_created_once_across_entries_and_reload(hass):
    assert await async_setup_component(hass, "http", {})
    resources = await make_resources(hass)
    await gather(async_setup_frontend(hass), async_setup_frontend(hass))
    await async_setup_frontend(hass)
    assert resources.async_items() == [
        {"id": resources.async_items()[0]["id"], "url": CARD_URL, "type": "module"}
    ]


async def test_upgrade_reuses_id_removes_only_own_duplicates(hass):
    assert await async_setup_component(hass, "http", {})
    resources = await make_resources(hass)
    original = await resources.async_create_item(
        {"url": CARD_PATH + "?v=0.4.0", "res_type": "js"}
    )
    await resources.async_create_item({"url": CARD_PATH, "res_type": "module"})
    unrelated = await resources.async_create_item(
        {"url": "/local/other-card.js", "res_type": "module"}
    )
    external = await resources.async_create_item(
        {"url": "https://example.org" + CARD_PATH, "res_type": "module"}
    )
    malformed = await resources.async_create_item(
        {"url": "http://[", "res_type": "module"}
    )
    await async_setup_frontend(hass)
    assert len(resources.async_items()) == 4
    assert {
        "id": original["id"],
        "url": CARD_URL,
        "type": "module",
    } in resources.async_items()
    assert unrelated in resources.async_items()
    assert external in resources.async_items()
    assert malformed in resources.async_items()


async def test_dashboards_loaded_later_register_module(hass):
    assert await async_setup_component(hass, "http", {})
    await async_setup_frontend(hass)
    resources = await make_resources(hass)
    hass.bus.async_fire(EVENT_COMPONENT_LOADED, {"component": "sensor"})
    await hass.async_block_till_done()
    assert resources.async_items() == []
    hass.bus.async_fire(EVENT_COMPONENT_LOADED, {"component": "lovelace"})
    await hass.async_block_till_done()
    assert len(resources.async_items()) == 1
    assert resources.async_items()[0]["url"] == CARD_URL


async def test_yaml_resources_untouched_with_extra_module_fallback(hass):
    assert await async_setup_component(hass, "http", {})
    original = [{"url": "/local/user.js", "type": "module"}]
    resources = ResourceYAMLCollection(original)
    hass.data["lovelace"] = SimpleNamespace(resource_mode="yaml", resources=resources)
    changes = Mock()
    manager = ha_frontend.UrlManager(changes, [])
    hass.data[ha_frontend.DATA_EXTRA_MODULE_URL] = manager
    with patch.object(
        ha_frontend, "add_extra_js_url", wraps=ha_frontend.add_extra_js_url
    ) as add:
        await async_setup_frontend(hass)
        await async_setup_frontend(hass)
    add.assert_called_once_with(hass, CARD_URL)
    assert manager.urls == {CARD_URL}
    assert resources.async_items() == original
    changes.assert_called_once_with("added", CARD_URL)


async def test_yaml_fallback_waits_for_frontend_then_updates_only_own_urls(hass):
    assert await async_setup_component(hass, "http", {})
    resources = ResourceYAMLCollection([])
    hass.data["lovelace"] = SimpleNamespace(resource_mode="yaml", resources=resources)
    await async_setup_frontend(hass)
    old = CARD_PATH + "?v=0.4.0"
    unrelated = "/local/user-module.js"
    external = "https://example.org" + CARD_PATH
    manager = ha_frontend.UrlManager(Mock(), [old, unrelated, external])
    hass.data[ha_frontend.DATA_EXTRA_MODULE_URL] = manager
    with patch.object(
        ha_frontend, "remove_extra_js_url", wraps=ha_frontend.remove_extra_js_url
    ) as remove:
        hass.bus.async_fire(EVENT_COMPONENT_LOADED, {"component": "frontend"})
        await hass.async_block_till_done()
    remove.assert_called_once_with(hass, old)
    assert manager.urls == {CARD_URL, unrelated, external}
    assert resources.async_items() == []


async def test_storage_resource_registration_removes_prior_extra_fallback(hass):
    assert await async_setup_component(hass, "http", {})
    resources = await make_resources(hass)
    unrelated = "/local/user-module.js"
    manager = ha_frontend.UrlManager(Mock(), [CARD_URL, unrelated])
    hass.data[ha_frontend.DATA_EXTRA_MODULE_URL] = manager
    await async_setup_frontend(hass)
    assert resources.async_items()[0]["url"] == CARD_URL
    assert manager.urls == {unrelated}


@pytest.mark.parametrize(
    "error",
    [OSError("disk error"), HomeAssistantError("private resource URL must not leak")],
)
async def test_resource_storage_failure_keeps_assets_available(
    hass, hass_client, caplog, error
):
    assert await async_setup_component(hass, "http", {})
    resources = await make_resources(hass)
    with patch.object(resources, "async_get_info", AsyncMock(side_effect=error)):
        await async_setup_frontend(hass)
    assert "private resource URL must not leak" not in caplog.text
    assert "Could not register" in caplog.text
    client = await hass_client()
    assert (await client.get(CARD_URL)).status == 200
    await async_setup_frontend(hass)
    assert len(resources.async_items()) == 1


async def test_frontend_component_listener_removed_on_homeassistant_stop(hass):
    assert await async_setup_component(hass, "http", {})
    await async_setup_frontend(hass)
    state = hass.data["salah_timetable_frontend"]
    assert state.listening
    assert state.unsubscribe_loaded is not None
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    await hass.async_block_till_done()
    assert not state.listening
    assert state.unsubscribe_loaded is None
