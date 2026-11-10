"""Use HA's real resource collection and authenticated static HTTP endpoint."""

import re
from asyncio import gather
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from urllib.parse import urljoin

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
    BUNDLE_PATH,
    CARD_PATH,
    CARD_URL,
    CARD_VERSION,
    _bundle_fingerprint,
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
    styles = await client.get("/salah_timetable/card-styles.js")
    assert styles.status == 200
    assert "CARD_CSS" in await styles.text()
    backgrounds = await client.get("/salah_timetable/mosque-backgrounds.js")
    assert backgrounds.status == 200
    assert "MOSQUE_BACKGROUNDS" in await backgrounds.text()
    image = await client.get("/salah_timetable/backgrounds/masjid-al-haram.webp")
    assert image.status == 200
    assert image.headers["Content-Type"].startswith("image/webp")
    assert (await image.read()).startswith(b"RIFF")
    translations = await client.get("/salah_timetable/card-i18n.js")
    assert translations.status == 200
    source = await translations.text()
    assert "CATALOGS" in source
    assert "الفجر" in source
    wizard = await client.get("/salah_timetable/reminder-wizard.js")
    assert wizard.status == 200
    assert "openReminderWizard" in await wizard.text()


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


def test_frontend_namespace_changes_when_only_an_imported_helper_changes(tmp_path):
    entry = tmp_path / "salah-timetable-card.js"
    entry.write_text('import "./card-i18n.js?v=1.0.0";')
    helper = tmp_path / "card-i18n.js"
    helper.write_text('export const label = "old";')
    first = _bundle_fingerprint(tmp_path)
    assert first == _bundle_fingerprint(tmp_path)
    helper.write_text('export const label = "Prayer reminders";')
    assert _bundle_fingerprint(tmp_path) != first
    assert entry.read_text() == 'import "./card-i18n.js?v=1.0.0";'


async def test_same_version_deployment_replaces_resource_and_versions_all_imports(
    hass, hass_client
):
    assert await async_setup_component(hass, "http", {})
    resources = await make_resources(hass)
    old = await resources.async_create_item(
        {"url": f"{CARD_PATH}?v={CARD_VERSION}", "res_type": "module"}
    )
    await async_setup_frontend(hass)
    assert resources.async_items() == [
        {"id": old["id"], "url": CARD_URL, "type": "module"}
    ]
    assert f"?v={CARD_VERSION}" in CARD_URL
    assert CARD_URL != old["url"]
    client = await hass_client()
    response = await client.get(CARD_URL)
    assert response.status == 200
    source = await response.text()
    assert "card-editor.js" in source
    assert "card-rendering.js" in source
    assert "card-monthly.js" in source
    assert "card-view-helpers.js" in source

    def imports(module):
        return re.findall(
            r"""(?:from\s*|import\s*)["'](\./[^"'\n]+\.js[^"'\n]*)["']""",
            module,
        )

    pending = [(CARD_URL, imported) for imported in imports(source)]
    assert pending
    visited = {CARD_URL}
    while pending:
        parent, imported = pending.pop()
        resolved = urljoin(parent, imported)
        if resolved in visited:
            continue
        visited.add(resolved)
        assert resolved.startswith(BUNDLE_PATH + "/")
        assert f"?v={CARD_VERSION}" in resolved
        helper = await client.get(resolved)
        assert helper.status == 200, resolved
        content = await helper.text()
        pending.extend((resolved, child) for child in imports(content))
        if "card-i18n.js" in resolved:
            assert "Prayer reminders" in content
        if "reminder-wizard.js" in resolved:
            assert "openReminderWizard" in content
        if "card-editor.js" in resolved:
            assert "_reminderButton" in content
    # Verify that every new rendering module is served under the same bundle namespace.
    for module in ("card-rendering.js", "card-monthly.js", "card-view-helpers.js"):
        assert any(module in url for url in visited), module
    # Preserve old manual URLs while managed resources move to the new namespace.
    assert (await client.get(CARD_PATH)).status == 200


async def test_old_fingerprinted_resources_are_migrated_without_touching_other_urls(
    hass,
):
    assert await async_setup_component(hass, "http", {})
    resources = await make_resources(hass)
    old_url = "/salah_timetable/0123456789abcdef/salah-timetable-card.js?v=1.0.0"
    old = await resources.async_create_item({"url": old_url, "res_type": "module"})
    remote = await resources.async_create_item(
        {"url": "https://example.com" + old_url, "res_type": "module"}
    )
    other = await resources.async_create_item(
        {
            "url": "/salah_timetable/user-custom/salah-timetable-card.js",
            "res_type": "module",
        }
    )
    await async_setup_frontend(hass)
    assert {
        "id": old["id"],
        "url": CARD_URL,
        "type": "module",
    } in resources.async_items()
    assert remote in resources.async_items()
    assert other in resources.async_items()
