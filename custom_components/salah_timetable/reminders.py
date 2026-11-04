"""Admin-only reminder discovery and normal Home Assistant automation previews."""

from math import isfinite
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import label_registry as lr
from homeassistant.util import slugify

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


_DELIVERY_BY_KIND = vol.All(
    vol.Schema(
        {
            vol.Optional("beginning"): _DELIVERY,
            vol.Optional("jamaat"): _DELIVERY,
        }
    ),
    vol.Length(min=1),
)
_DELIVERIES = vol.Any(_DELIVERY_BY_KIND, _DELIVERY)


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


_UNKNOWN = "Other / unknown"
_DEVICE_TYPES = {
    "phone": "Phone",
    "tablet": "Tablet",
    "speaker": "Speaker",
    "tv": "TV",
    "receiver": "Receiver",
    "computer": "Computer",
    "wearable": "Wearable",
    "display": "Display",
}
_INTEGRATION_NAMES = {
    "mobile_app": "Companion app",
    "music_assistant": "Music Assistant",
    "cast": "Google Cast",
    "sonos": "Sonos",
    "androidtv": "Android Debug Bridge",
    "androidtv_remote": "Android TV Remote",
    "roku": "Roku",
    "unknown": _UNKNOWN,
}


def _filter_metadata(integration: str, device_type: str) -> dict[str, str]:
    """Use registered providers and reported or explicitly labelled device types."""
    return {
        "integration": integration,
        "integration_name": _INTEGRATION_NAMES.get(
            integration, integration.replace("_", " ").title()
        ),
        "device_type": device_type,
        "device_type_name": _DEVICE_TYPES.get(device_type, _UNKNOWN),
    }


def _labelled_type(hass: HomeAssistant, label_ids: set[str]) -> str:
    labels = lr.async_get(hass)
    types = {
        label.name.strip().casefold()
        for label_id in label_ids
        if (label := labels.async_get_label(label_id)) is not None
        and label.name.strip().casefold() in _DEVICE_TYPES
    }
    # Contradictory labels do not identify a reliable device category.
    return types.pop() if len(types) == 1 else "unknown"


def _entity_filter_metadata(hass: HomeAssistant, entity_id: str) -> dict[str, str]:
    registry_entry = er.async_get(hass).async_get(entity_id)
    state = hass.states.get(entity_id)
    reported_type = state.attributes.get("device_class") if state else None
    integration = registry_entry.platform if registry_entry else "unknown"
    labels = set(registry_entry.labels) if registry_entry else set()
    if registry_entry and registry_entry.device_id:
        if device := dr.async_get(hass).async_get(registry_entry.device_id):
            labels.update(device.labels)
    device_type = (
        reported_type
        if isinstance(reported_type, str) and reported_type in _DEVICE_TYPES
        else _labelled_type(hass, labels)
    )
    return _filter_metadata(integration, device_type)


def _action_filter_metadata(hass: HomeAssistant, action: str) -> dict[str, str]:
    """Correlate Companion actions only when their registration is unambiguous."""
    if not action.startswith("notify.mobile_app_"):
        return _filter_metadata("unknown", "unknown")
    matches = [
        entry
        for entry in hass.config_entries.async_entries("mobile_app")
        if entry.disabled_by is None
        and isinstance(entry.data.get("device_name"), str)
        and f"notify.mobile_app_{slugify(entry.data['device_name'])}" == action
    ]
    if len(matches) != 1:
        return _filter_metadata("mobile_app", "unknown")
    entry = matches[0]
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    entities = [
        entity
        for entity in er.async_entries_for_config_entry(entity_registry, entry.entry_id)
        if entity.domain == "notify" and entity.disabled_by is None
    ]
    labels = set()
    reported_types = set()
    for entity in entities:
        labels.update(entity.labels)
        if entity.device_id and (device := device_registry.async_get(entity.device_id)):
            labels.update(device.labels)
        if state := hass.states.get(entity.entity_id):
            reported = state.attributes.get("device_class")
            if isinstance(reported, str) and reported in _DEVICE_TYPES:
                reported_types.add(reported)
    for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        labels.update(device.labels)
    if len(reported_types) == 1:
        device_type = next(iter(reported_types))
    elif reported_types:
        device_type = "unknown"
    else:
        device_type = _labelled_type(hass, labels)
    return _filter_metadata("mobile_app", device_type)


def _delivery_actions(
    hass: HomeAssistant, delivery: dict[str, Any]
) -> list[dict[str, Any]]:
    """Validate one delivery configuration and build independent destination actions."""
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
    return actions


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
                        "id": "beginning" if beginning else "jamaat",
                        "options": {
                            "mosque_id": entry.entry_id,
                            "fields": fields,
                            "minutes_before": selection[
                                "begin_minutes" if beginning else "jamaat_minutes"
                            ],
                        },
                    }
                )
    if any(kind in delivery for kind in ("beginning", "jamaat")):
        choices = []
        for kind in dict.fromkeys(trigger["id"] for trigger in triggers):
            label = "Beginning" if kind == "beginning" else "Jamaat"
            if kind not in delivery:
                raise ValueError(f"Choose delivery for {label.lower()} reminders")
            try:
                sequence = _delivery_actions(hass, delivery[kind])
            except ValueError as err:
                raise ValueError(f"{label} reminders: {err}") from err
            choices.append(
                {
                    "alias": f"{label} reminders",
                    "conditions": [{"condition": "trigger", "id": kind}],
                    "sequence": sequence,
                }
            )
        actions = [{"choose": choices}]
    else:
        # Keep previews from an older open wizard compatible with their shared
        # delivery format. Existing saved automations are never rewritten.
        actions = _delivery_actions(hass, delivery)
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
                    **_action_filter_metadata(hass, action),
                }
                for action in sorted(_notifications(hass))
            ],
            "notification_entities": [
                {
                    "value": state.entity_id,
                    "label": state.name,
                    **_entity_filter_metadata(hass, state.entity_id),
                }
                for state in hass.states.async_all("notify")
            ],
            "media_players": [
                {
                    "value": state.entity_id,
                    "label": state.name,
                    **_entity_filter_metadata(hass, state.entity_id),
                }
                for state in hass.states.async_all("media_player")
            ],
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "salah_timetable/reminder_preview",
        vol.Required("name"): vol.All(cv.string, vol.Length(min=1, max=100)),
        vol.Required("mosques"): vol.All([_SELECTION], vol.Length(min=1, max=20)),
        vol.Required("delivery"): _DELIVERIES,
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
