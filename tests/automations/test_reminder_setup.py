"""Admin reminder previews and saving ordinary Home Assistant automations."""

from copy import deepcopy
from datetime import date, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from homeassistant.components.config import automation as automation_api
from homeassistant.config_entries import ConfigEntryDisabler
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    async_mock_service,
)

from custom_components.salah_timetable.const import DOMAIN
from custom_components.salah_timetable.data_api import register_websocket_commands
from custom_components.salah_timetable.domain.model import (
    DailyPrayers,
    PrayerField,
    Timetable,
)
from custom_components.salah_timetable.persistence.storage import TimetableStorage
from custom_components.salah_timetable.reminders import _DELIVERY, reminder_automation


@pytest.fixture
async def destinations(hass):
    calls = {
        name: async_mock_service(hass, domain, service)
        for name, domain, service in (
            ("phone", "notify", "mobile_app_phone"),
            ("notify_entity", "notify", "send_message"),
            ("play", "media_player", "play_media"),
            ("volume", "media_player", "volume_set"),
        )
    }
    async_mock_service(hass, "automation", "reload")
    hass.states.async_set("notify.phone", "unknown", {"friendly_name": "Phone"})
    hass.states.async_set("media_player.hall", "idle")
    return calls


@pytest.fixture
async def reminder_client(hass, hass_ws_client):
    assert await async_setup_component(hass, "websocket_api", {})
    register_websocket_commands(hass)
    return await hass_ws_client(hass)


def request(entry, **updates):
    result = {
        "type": "salah_timetable/reminder_preview",
        "name": "Prayer reminders",
        "mosques": [
            {
                "id": entry.entry_id,
                "fields": ["fajr_begin", "dhuhr_begin", "fajr_jamaat"],
                "begin_minutes": 10,
                "jamaat_minutes": 20,
            }
        ],
        "delivery": {"notification_actions": ["notify.mobile_app_phone"]},
    }
    result.update(updates)
    return result


async def send(client, message):
    await client.send_json_auto_id(message)
    return await client.receive_json()


async def test_discovery_lists_masjids_and_notification_destinations(
    hass, entry, destinations, reminder_client
):
    disabled = MockConfigEntry(
        domain=DOMAIN,
        title="Disabled masjid",
        unique_id="disabled",
        disabled_by=ConfigEntryDisabler.USER,
    )
    disabled.add_to_hass(hass)
    result = await send(reminder_client, {"type": "salah_timetable/reminder_options"})
    assert result["success"], result
    options = result["result"]
    assert [item["id"] for item in options["mosques"]] == [entry.entry_id]
    mosque = options["mosques"][0]
    assert mosque["name"] == "Example Mosque"
    assert mosque["time_zone"] == "Europe/London"
    assert mosque["ready"] is False
    fields = {item["value"] for item in mosque["fields"]}
    assert len(fields) == 11
    assert {"fajr_begin", "isha_jamaat", "jumuah"} <= fields
    assert "sunrise" not in fields
    assert options["notification_actions"] == [
        {"value": "notify.mobile_app_phone", "label": "mobile app phone"}
    ]
    assert options["notification_entities"] == [
        {"value": "notify.phone", "label": "Phone"}
    ]
    assert not any(destinations.values())


async def test_multi_masjid_preview_groups_offsets_without_running_delivery(
    hass, entry, destinations, reminder_client
):
    other = MockConfigEntry(domain=DOMAIN, title="Other masjid", unique_id="other")
    other.add_to_hass(hass)
    payload = request(entry)
    payload["mosques"].append(
        {
            "id": other.entry_id,
            "fields": ["isha_begin", "jumuah"],
            "begin_minutes": 5,
            "jamaat_minutes": 30,
        }
    )
    payload["delivery"] = {
        "notification_actions": ["notify.mobile_app_phone", "notify.mobile_app_phone"],
        "notification_entities": ["notify.phone", "notify.phone"],
        "media_players": ["media_player.hall", "media_player.hall"],
        "media_content_id": "media-source://media_source/local/reminder.mp3",
        "media_content_type": "audio/mpeg",
        "volume": 0.4,
    }
    result = await send(reminder_client, payload)
    assert result["success"], result
    config = result["result"]["config"]
    assert [item["options"] for item in config["triggers"]] == [
        {
            "mosque_id": entry.entry_id,
            "fields": ["dhuhr_begin", "fajr_begin"],
            "minutes_before": 10,
        },
        {"mosque_id": entry.entry_id, "fields": ["fajr_jamaat"], "minutes_before": 20},
        {"mosque_id": other.entry_id, "fields": ["isha_begin"], "minutes_before": 5},
        {"mosque_id": other.entry_id, "fields": ["jumuah"], "minutes_before": 30},
    ]
    assert all(
        item["trigger"] == "salah_timetable.prayer_time" for item in config["triggers"]
    )
    actions = config["actions"]
    assert [item["action"] for item in actions] == [
        "notify.mobile_app_phone",
        "notify.send_message",
        "media_player.volume_set",
        "media_player.play_media",
    ]
    assert actions[1]["target"]["entity_id"] == "notify.phone"
    assert actions[2]["data"] == {"volume_level": 0.4}
    assert actions[3]["target"]["entity_id"] == "media_player.hall"
    assert actions[3]["data"]["media_content_id"].endswith("reminder.mp3")
    assert all(item["continue_on_error"] for item in actions)
    assert config["mode"] == "parallel"
    assert not any(destinations.values())
    assert not hass.states.async_all("automation")
    assert not Path(hass.config.path("automations.yaml")).exists()


@pytest.mark.parametrize("command", ["reminder_options", "reminder_preview"])
async def test_reminder_endpoints_require_admin(
    entry, destinations, reminder_client, hass_admin_user, command
):
    hass_admin_user.groups.clear()
    hass_admin_user.invalidate_cache()
    message = (
        request(entry)
        if command == "reminder_preview"
        else {"type": "salah_timetable/reminder_options"}
    )
    result = await send(reminder_client, message)
    assert not result["success"]
    assert result["error"]["code"] == "unauthorized"
    assert not any(destinations.values())


@pytest.mark.parametrize(
    "case",
    [
        "duplicate_mosque",
        "missing_mosque",
        "wrong_domain_mosque",
        "empty_name",
        "no_delivery",
        "unknown_action",
        "unknown_entity",
        "wrong_entity_domain",
        "missing_media",
        "no_play_service",
        "no_notify_entity_service",
        "no_volume_service",
        "no_automation_service",
    ],
)
async def test_invalid_preview_has_no_side_effects(
    hass, entry, destinations, reminder_client, case
):
    payload = request(entry)
    if case == "duplicate_mosque":
        payload["mosques"].append(deepcopy(payload["mosques"][0]))
    elif case == "missing_mosque":
        payload["mosques"][0]["id"] = "missing"
    elif case == "wrong_domain_mosque":
        other = MockConfigEntry(domain="other", title="Other")
        other.add_to_hass(hass)
        payload["mosques"][0]["id"] = other.entry_id
    elif case == "empty_name":
        payload["name"] = " "
    elif case == "no_delivery":
        payload["delivery"] = {}
    elif case == "unknown_action":
        payload["delivery"] = {"notification_actions": ["notify.removed"]}
    elif case in {"unknown_entity", "wrong_entity_domain"}:
        payload["delivery"] = {
            "notification_entities": [
                "notify.removed" if case == "unknown_entity" else "media_player.hall"
            ]
        }
    elif case == "no_notify_entity_service":
        payload["delivery"] = {"notification_entities": ["notify.phone"]}
        hass.services.async_remove("notify", "send_message")
    elif case == "no_automation_service":
        hass.services.async_remove("automation", "reload")
    else:
        payload["delivery"] = {
            "media_players": ["media_player.hall"],
            "media_content_id": "reminder.mp3",
        }
        if case == "missing_media":
            payload["delivery"]["media_content_id"] = " "
        elif case == "no_play_service":
            hass.services.async_remove("media_player", "play_media")
        elif case == "no_volume_service":
            payload["delivery"]["volume"] = 0.5
            hass.services.async_remove("media_player", "volume_set")
    result = await send(reminder_client, payload)
    assert not result["success"], result
    assert result["error"]["code"] == "invalid_reminder"
    assert not any(destinations.values())


@pytest.mark.parametrize(
    "field,value",
    [
        ("begin_minutes", -1),
        ("begin_minutes", 181),
        ("begin_minutes", 1.5),
        ("begin_minutes", True),
        ("fields", []),
        ("fields", ["sunrise"]),
    ],
)
async def test_invalid_prayer_inputs_are_rejected_by_schema(
    entry, destinations, reminder_client, field, value
):
    payload = request(entry)
    payload["mosques"][0][field] = value
    result = await send(reminder_client, payload)
    assert not result["success"]
    assert result["error"]["code"] == "invalid_format"
    assert not any(destinations.values())


@pytest.mark.parametrize("volume", [-0.1, 1.1, True, "loud"])
async def test_invalid_volume_is_rejected(entry, destinations, reminder_client, volume):
    payload = request(entry)
    payload["delivery"]["volume"] = volume
    result = await send(reminder_client, payload)
    assert not result["success"]
    assert result["error"]["code"] == "invalid_format"


async def test_preview_saves_native_editable_automation_through_admin_api(
    hass, entry, destinations, hass_ws_client, hass_client
):
    assert await async_setup_component(hass, "automation", {"automation": []})
    assert await async_setup_component(hass, "http", {})
    assert automation_api.async_setup(hass)
    register_websocket_commands(hass)
    ws = await hass_ws_client(hass)
    payload = request(entry)
    payload["mosques"][0].update(fields=["fajr_begin"], begin_minutes=0)
    result = await send(ws, payload)
    assert result["success"], result
    config = result["result"]["config"]
    assert len(config["triggers"]) == 1
    assert config["triggers"][0]["options"]["minutes_before"] == 0
    Path(hass.config.path("configuration.yaml")).write_text(
        "automation: !include automations.yaml\n", encoding="utf-8"
    )
    client = await hass_client()
    response = await client.post(
        "/api/config/automation/config/reminder-test", json=config
    )
    assert response.status == 200, await response.text()
    await hass.async_block_till_done()
    stored = await client.get("/api/config/automation/config/reminder-test")
    assert stored.status == 200
    assert (await stored.json())["alias"] == "Prayer reminders"
    assert Path(hass.config.path("automations.yaml")).exists()
    automations = hass.states.async_all("automation")
    assert len(automations) == 1
    assert automations[0].state == "on"
    assert automations[0].attributes["id"] == "reminder-test"
    assert not any(destinations.values())


async def test_generated_automation_renders_actual_reminder_notification(
    hass, entry, destinations, freezer
):
    """Generated templates consume the integration trigger's real payload."""
    freezer.move_to("2026-11-02T04:00:00Z")
    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    table = Timetable(
        "annual-2026",
        "annual",
        (DailyPrayers(date(2026, 11, 2), {PrayerField.FAJR_BEGIN: (time(5),)}, {}),),
    )
    await storage.async_replace((table,))
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    config = reminder_automation(
        hass,
        "Prayer reminders",
        [
            {
                "id": entry.entry_id,
                "fields": ["fajr_begin"],
                "begin_minutes": 10,
                "jamaat_minutes": 10,
            }
        ],
        _DELIVERY({"notification_actions": ["notify.mobile_app_phone"]}),
    )
    assert await async_setup_component(hass, "automation", {"automation": [config]})
    await hass.async_start()
    await hass.async_block_till_done()
    assert not destinations["phone"]
    instant = "2026-11-02T04:50:00Z"
    freezer.move_to(instant)
    async_fire_time_changed(hass, dt_util.parse_datetime(instant))
    await hass.async_block_till_done()
    assert len(destinations["phone"]) == 1
    message = destinations["phone"][0].data["message"]
    assert "Example Mosque" in message
    assert "Fajr" in message
    assert "05:00" in message
    assert "10 minutes remaining" in message
    assert "{{" not in message
