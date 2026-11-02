"""Admin-only reminder discovery and normal Home Assistant automation previews."""

from math import isfinite
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .trigger import FIELD_LABELS, REMINDER_FIELDS


def _integer(value: Any) -> int:
    if type(value) is not int or not 0 <= value <= 180:
        raise vol.Invalid("Minutes must be a whole number from 0 to 180")
    return value


def _volume(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise vol.Invalid("Volume must be a number")
    if not isfinite(value) or not 0 <= value <= 1:
        raise vol.Invalid("Volume must be from 0 to 1")
    return float(value)


_SELECTION = vol.Schema(
    {
        vol.Required("id"): cv.string,
        vol.Required("fields"): vol.All(
            [vol.In([field.value for field in REMINDER_FIELDS])],
            vol.Length(min=1, max=11),
        ),
        vol.Optional("begin_minutes", default=10): _integer,
        vol.Optional("jamaat_minutes", default=10): _integer,
    }
)
_DELIVERY = vol.Schema(
    {
        vol.Optional("notification_actions", default=list): vol.All(
            [cv.string], vol.Length(max=50)
        ),
        vol.Optional("notification_entities", default=list): vol.All(
            [cv.entity_id], vol.Length(max=50)
        ),
        vol.Optional("media_players", default=list): vol.All(
            [cv.entity_id], vol.Length(max=50)
        ),
        vol.Optional("media_content_id", default=""): vol.All(
            cv.string, vol.Length(max=2048)
        ),
        vol.Optional("media_content_type", default="audio/mpeg"): vol.All(
            cv.string, vol.Length(min=1, max=100)
        ),
        vol.Optional("volume", default=None): _volume,
    }
)


def _mosque(hass: HomeAssistant, entry_id: str):
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN or entry.disabled_by is not None:
        raise ValueError("A selected masjid is no longer configured")
    return entry


def _notifications(hass: HomeAssistant) -> list[str]:
    return [
        f"notify.{name}"
        for name in hass.services.async_services().get("notify", {})
        if name != "send_message"
    ]


def reminder_automation(hass: HomeAssistant, name, selections, delivery):
    """Build a preview only; the browser saves through HA's admin config API."""
    name = name.strip()
    if not name:
        raise ValueError("Enter a name for the reminder automation")
    triggers = []
    for selection in selections:
        entry = _mosque(hass, selection["id"])
        for beginning in (True, False):
            fields = sorted(
                {
                    field
                    for field in selection["fields"]
                    if field.endswith("_begin") == beginning
                }
            )
            if fields:
                triggers.append(
                    {
                        "trigger": f"{DOMAIN}.prayer_time",
                        "options": {
                            "mosque_id": entry.entry_id,
                            "fields": fields,
                            "minutes_before": selection[
                                "begin_minutes" if beginning else "jamaat_minutes"
                            ],
                        },
                    }
                )
    available_actions = set(_notifications(hass))
    message = (
        "{% if trigger is defined and trigger.mosque is defined "
        "and trigger.prayer is defined and trigger.scheduled_time is defined "
        "and trigger.minutes_before is defined %}"
        "{{ trigger.mosque }}: {{ trigger.prayer }} at "
        "{{ as_datetime(trigger.scheduled_time).strftime('%H:%M') }} "
        "({{ trigger.minutes_before }} minutes remaining)."
        "{% else %}Test notification from Salah Timetable. "
        "No prayer event triggered this test.{% endif %}"
    )
    actions = []
    for action in dict.fromkeys(delivery["notification_actions"]):
        if action not in available_actions:
            raise ValueError("A selected notification action is no longer available")
        actions.append({"action": action, "data": {"message": message}})
    for domain, entities in (
        ("notify", delivery["notification_entities"]),
        ("media_player", delivery["media_players"]),
    ):
        for entity_id in entities:
            if (
                not entity_id.startswith(f"{domain}.")
                or hass.states.get(entity_id) is None
            ):
                raise ValueError("A selected delivery entity is no longer available")
    if delivery["notification_entities"]:
        if not hass.services.has_service("notify", "send_message"):
            raise ValueError("Notification entities do not support sending messages")
        for entity_id in dict.fromkeys(delivery["notification_entities"]):
            actions.append(
                {
                    "action": "notify.send_message",
                    "target": {"entity_id": entity_id},
                    "data": {"message": message},
                }
            )
    if delivery["media_players"]:
        media_id = delivery["media_content_id"].strip()
        if not media_id:
            raise ValueError(
                "Select a recording or enter a media URL for sound playback"
            )
        if not hass.services.has_service("media_player", "play_media"):
            raise ValueError("Media playback is not available")
        if delivery["volume"] is not None and not hass.services.has_service(
            "media_player", "volume_set"
        ):
            raise ValueError("Setting media player volume is not available")
        for entity_id in dict.fromkeys(delivery["media_players"]):
            target = {"entity_id": entity_id}
            if delivery["volume"] is not None:
                actions.append(
                    {
                        "action": "media_player.volume_set",
                        "target": target,
                        "data": {"volume_level": delivery["volume"]},
                    }
                )
            actions.append(
                {
                    "action": "media_player.play_media",
                    "target": target,
                    "data": {
                        "media_content_id": media_id,
                        "media_content_type": delivery["media_content_type"],
                    },
                }
            )
    if not actions:
        raise ValueError("Select at least one notification destination or media player")
    # A failed phone or speaker must not prevent delivery to another destination.
    for action in actions:
        action["continue_on_error"] = True
    return {
        "alias": name,
        "description": (
            "Created with Salah Timetable Prayer reminders. Edit, disable or delete "
            "in Home Assistant Automations. Existing blueprint reminders are unchanged."
        ),
        "triggers": triggers,
        "conditions": [],
        "actions": actions,
        "mode": "parallel",
        "max": 100,
    }


@websocket_api.websocket_command(
    {vol.Required("type"): "salah_timetable/reminder_options"}
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_reminder_options(hass, connection, msg):
    """List configured masjids and destinations without changing anything."""
    fields = [
        {"value": field.value, "label": FIELD_LABELS[field]}
        for field in REMINDER_FIELDS
    ]
    connection.send_result(
        msg["id"],
        {
            "mosques": [
                {
                    "id": entry.entry_id,
                    "name": entry.title,
                    "time_zone": entry.options.get(
                        "time_zone", entry.data.get("time_zone", "UTC")
                    ),
                    "ready": entry.state is ConfigEntryState.LOADED
                    and getattr(entry, "runtime_data", None) is not None
                    and entry.runtime_data.last_update_success,
                    "fields": fields,
                }
                for entry in hass.config_entries.async_entries(DOMAIN)
                if entry.disabled_by is None
            ],
            "notification_actions": [
                {
                    "value": action,
                    "label": action.removeprefix("notify.").replace("_", " "),
                }
                for action in sorted(_notifications(hass))
            ],
            "notification_entities": [
                {"value": state.entity_id, "label": state.name}
                for state in hass.states.async_all("notify")
            ],
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "salah_timetable/reminder_preview",
        vol.Required("name"): vol.All(cv.string, vol.Length(min=1, max=100)),
        vol.Required("mosques"): vol.All([_SELECTION], vol.Length(min=1, max=20)),
        vol.Required("delivery"): _DELIVERY,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_reminder_preview(hass, connection, msg):
    """Return automation YAML data for explicit review/save, never write it here."""
    try:
        if not hass.services.has_service("automation", "reload"):
            raise ValueError(
                "Enable Home Assistant automation configuration before saving reminders"
            )
        ids = [item["id"] for item in msg["mosques"]]
        if len(set(ids)) != len(ids):
            raise ValueError("Each masjid should be selected once")
        config = reminder_automation(hass, msg["name"], msg["mosques"], msg["delivery"])
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_reminder", str(err))
        return
    connection.send_result(msg["id"], {"config": config})
