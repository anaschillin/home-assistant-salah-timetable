"""Admin reminder previews and saving ordinary Home Assistant automations."""

from copy import deepcopy
from datetime import date, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from homeassistant.components.config import automation as automation_api
from homeassistant.config_entries import ConfigEntryDisabler
from homeassistant.core import Context
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.script import Script
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
from custom_components.salah_timetable.reminders import (
    _DELIVERIES,
    _DELIVERY,
    reminder_automation,
)


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


@pytest.mark.parametrize(
    "variables", [{}, {"trigger": None}, {"trigger": {"platform": None}}]
)
async def test_individual_actions_without_prayer_trigger_send_test_notification(
    hass, entry, destinations, variables
):
    """The action editor test has no automation variables or real trigger payload."""
    config = reminder_automation(
        hass,
        "Manual reminder test",
        [
            {
                "id": entry.entry_id,
                "fields": ["fajr_begin"],
                "begin_minutes": 10,
                "jamaat_minutes": 10,
            }
        ],
        _DELIVERY(
            {
                "notification_actions": ["notify.mobile_app_phone"],
                "notification_entities": ["notify.phone"],
                "media_players": ["media_player.hall"],
                "media_content_id": "library://track/123",
                "media_content_type": "music",
            }
        ),
    )
    for action in config["actions"]:
        action["continue_on_error"] = False
    await Script(
        hass, cv.SCRIPT_SCHEMA(config["actions"]), "Manual reminder actions", DOMAIN
    ).async_run(variables, context=Context())
    for destination in ("phone", "notify_entity"):
        assert len(destinations[destination]) == 1
        message = destinations[destination][0].data["message"]
        assert (
            message
            == "Test notification from Salah Timetable. No prayer event triggered this test."
        )
        assert "Fajr" not in message
    assert len(destinations["play"]) == 1
    assert destinations["play"][0].data["media_content_id"] == "library://track/123"


async def test_manual_automation_run_without_prayer_trigger_sends_test_notification(
    hass, entry, destinations
):
    config = reminder_automation(
        hass,
        "Manual reminder test",
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
    config["actions"][0]["continue_on_error"] = False
    assert await async_setup_component(hass, "automation", {"automation": [config]})
    await hass.async_start()
    await hass.async_block_till_done()
    automation = hass.states.async_all("automation")[0]
    await hass.services.async_call(
        "automation", "trigger", {"entity_id": automation.entity_id}, blocking=True
    )
    await hass.async_block_till_done()
    assert len(destinations["phone"]) == 1
    assert (
        destinations["phone"][0]
        .data["message"]
        .startswith("Test notification from Salah Timetable.")
    )


async def test_separate_delivery_preview_routes_each_category_without_sending(
    hass, entry, destinations, reminder_client
):
    payload = request(entry)
    payload["delivery"] = {
        "beginning": {"notification_actions": ["notify.mobile_app_phone"]},
        "jamaat": {
            "notification_entities": ["notify.phone"],
            "media_players": ["media_player.hall"],
            "media_content_id": "library://track/jamaat",
            "media_content_type": "music",
            "volume": 0.6,
        },
    }
    result = await send(reminder_client, payload)
    assert result["success"], result
    config = result["result"]["config"]
    assert [trigger["id"] for trigger in config["triggers"]] == ["beginning", "jamaat"]
    assert [trigger["options"]["minutes_before"] for trigger in config["triggers"]] == [
        10,
        20,
    ]
    choices = config["actions"][0]["choose"]
    assert len(choices) == 2
    by_kind = {choice["conditions"][0]["id"]: choice["sequence"] for choice in choices}
    assert [action["action"] for action in by_kind["beginning"]] == [
        "notify.mobile_app_phone"
    ]
    assert [action["action"] for action in by_kind["jamaat"]] == [
        "notify.send_message",
        "media_player.volume_set",
        "media_player.play_media",
    ]
    assert by_kind["jamaat"][-1]["data"]["media_content_id"] == "library://track/jamaat"
    assert all(
        action["continue_on_error"]
        for sequence in by_kind.values()
        for action in sequence
    )
    assert config["actions"][0].get("default", []) == []
    assert not any(destinations.values())
    assert not hass.states.async_all("automation")


@pytest.mark.parametrize("missing", ["beginning", "jamaat"])
async def test_selected_category_requires_its_own_delivery(
    entry, destinations, reminder_client, missing
):
    payload = request(entry)
    payload["delivery"] = {
        "beginning": {"notification_actions": ["notify.mobile_app_phone"]},
        "jamaat": {"notification_entities": ["notify.phone"]},
    }
    del payload["delivery"][missing]
    result = await send(reminder_client, payload)
    assert not result["success"]
    assert result["error"]["code"] == "invalid_reminder"
    assert not any(destinations.values())


@pytest.mark.parametrize(
    "kind,field", [("beginning", "fajr_begin"), ("jamaat", "jumuah")]
)
async def test_only_selected_delivery_category_is_validated_and_generated(
    entry, destinations, reminder_client, kind, field
):
    payload = request(entry)
    payload["mosques"][0]["fields"] = [field]
    unused = "jamaat" if kind == "beginning" else "beginning"
    payload["delivery"] = {
        kind: {"notification_actions": ["notify.mobile_app_phone"]},
        unused: {"notification_actions": ["notify.removed_destination"]},
    }
    result = await send(reminder_client, payload)
    assert result["success"], result
    config = result["result"]["config"]
    assert len(config["triggers"]) == 1
    assert config["triggers"][0]["id"] == kind
    choices = config["actions"][0]["choose"]
    assert len(choices) == 1
    assert choices[0]["conditions"][0]["id"] == kind
    assert choices[0]["sequence"][0]["action"] == "notify.mobile_app_phone"
    assert not any(destinations.values())


@pytest.mark.parametrize("empty", ["beginning", "jamaat"])
async def test_each_selected_delivery_category_must_have_a_destination(
    entry, destinations, reminder_client, empty
):
    payload = request(entry)
    payload["delivery"] = {
        "beginning": {"notification_actions": ["notify.mobile_app_phone"]},
        "jamaat": {"notification_entities": ["notify.phone"]},
    }
    payload["delivery"][empty] = {}
    result = await send(reminder_client, payload)
    assert not result["success"]
    assert result["error"]["code"] == "invalid_reminder"
    assert not any(destinations.values())


async def test_scheduled_beginning_and_jamaat_use_independent_destinations_and_sounds(
    hass, entry, destinations, freezer
):
    """Real scheduler runs only the delivery branch belonging to that prayer kind."""
    freezer.move_to("2026-11-02T04:00:00Z")
    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    await storage.async_replace(
        (
            Timetable(
                "annual-2026",
                "annual",
                (
                    DailyPrayers(
                        date(2026, 11, 2),
                        {
                            PrayerField.FAJR_BEGIN: (time(5),),
                            PrayerField.FAJR_JAMAAT: (time(5, 30),),
                        },
                        {},
                    ),
                ),
            ),
        )
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    config = reminder_automation(
        hass,
        "Separate prayer delivery",
        [
            {
                "id": entry.entry_id,
                "fields": ["fajr_begin", "fajr_jamaat"],
                "begin_minutes": 10,
                "jamaat_minutes": 15,
            }
        ],
        _DELIVERIES(
            {
                "beginning": {
                    "notification_actions": ["notify.mobile_app_phone"],
                    "media_players": ["media_player.hall"],
                    "media_content_id": "beginning.mp3",
                    "volume": 0.2,
                },
                "jamaat": {
                    "notification_entities": ["notify.phone"],
                    "media_players": ["media_player.hall"],
                    "media_content_id": "jamaat.mp3",
                    "volume": 0.7,
                },
            }
        ),
    )
    assert await async_setup_component(hass, "automation", {"automation": [config]})
    await hass.async_start()
    await hass.async_block_till_done()
    assert not any(destinations.values())

    freezer.move_to("2026-11-02T04:50:00Z")
    async_fire_time_changed(hass, dt_util.parse_datetime("2026-11-02T04:50:00Z"))
    await hass.async_block_till_done()
    assert len(destinations["phone"]) == 1
    assert "Fajr beginning" in destinations["phone"][0].data["message"]
    assert "10 minutes remaining" in destinations["phone"][0].data["message"]
    assert not destinations["notify_entity"]
    assert [call.data["media_content_id"] for call in destinations["play"]] == [
        "beginning.mp3"
    ]
    assert [call.data["volume_level"] for call in destinations["volume"]] == [0.2]

    freezer.move_to("2026-11-02T05:14:59Z")
    async_fire_time_changed(hass, dt_util.parse_datetime("2026-11-02T05:14:59Z"))
    await hass.async_block_till_done()
    assert len(destinations["play"]) == 1
    freezer.move_to("2026-11-02T05:15:00Z")
    async_fire_time_changed(hass, dt_util.parse_datetime("2026-11-02T05:15:00Z"))
    await hass.async_block_till_done()
    assert len(destinations["phone"]) == 1
    assert len(destinations["notify_entity"]) == 1
    assert "Fajr Jamaat" in destinations["notify_entity"][0].data["message"]
    assert "15 minutes remaining" in destinations["notify_entity"][0].data["message"]
    assert [call.data["media_content_id"] for call in destinations["play"]] == [
        "beginning.mp3",
        "jamaat.mp3",
    ]
    assert [call.data["volume_level"] for call in destinations["volume"]] == [0.2, 0.7]


async def test_manual_grouped_run_does_not_broadcast_both_delivery_categories(
    hass, entry, destinations
):
    config = reminder_automation(
        hass,
        "Separate manual delivery",
        [
            {
                "id": entry.entry_id,
                "fields": ["fajr_begin", "fajr_jamaat"],
                "begin_minutes": 10,
                "jamaat_minutes": 10,
            }
        ],
        _DELIVERIES(
            {
                "beginning": {"notification_actions": ["notify.mobile_app_phone"]},
                "jamaat": {"notification_entities": ["notify.phone"]},
            }
        ),
    )
    assert await async_setup_component(hass, "automation", {"automation": [config]})
    await hass.async_start()
    await hass.async_block_till_done()
    await hass.services.async_call(
        "automation",
        "trigger",
        {
            "entity_id": hass.states.async_all("automation")[0].entity_id,
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    assert not any(destinations.values())
    # Testing a selected category explicitly still uses the safe manual message.
    await Script(
        hass, cv.SCRIPT_SCHEMA(config["actions"]), "Jamaat test", DOMAIN
    ).async_run(
        {"trigger": {"id": "jamaat"}},
        context=Context(),
    )
    assert not destinations["phone"]
    assert len(destinations["notify_entity"]) == 1
    assert (
        destinations["notify_entity"][0].data["message"].startswith("Test notification")
    )
