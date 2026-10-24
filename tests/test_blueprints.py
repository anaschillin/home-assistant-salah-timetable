"""Exercise shipped blueprint expansion and HA's real automation scheduler."""

from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.components.automation.config import AUTOMATION_BLUEPRINT_SCHEMA
from homeassistant.components.blueprint.models import Blueprint, BlueprintInputs
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from homeassistant.util import yaml as yaml_util
from pytest_homeassistant_custom_component.common import (
    async_capture_events,
    async_fire_time_changed,
    async_mock_service,
)

BLUEPRINTS = Path(__file__).parents[1] / "blueprints/automation/salah_timetable"
ATTRS = {"device_class": "timestamp"}


def expanded(name, inputs, alias="Blueprint acceptance"):
    """Use HA's blueprint validation/defaults/substitution, not hand-copied YAML."""
    blueprint = Blueprint(
        yaml_util.load_yaml_dict(BLUEPRINTS / f"{name}.yaml"),
        expected_domain="automation",
        schema=AUTOMATION_BLUEPRINT_SCHEMA,
    )
    assert blueprint.validate() is None
    instance = BlueprintInputs(
        blueprint,
        {"alias": alias, "use_blueprint": {"path": f"{name}.yaml", "input": inputs}},
    )
    instance.validate()
    return instance.async_substitute()


async def start(hass, configs):
    assert await async_setup_component(hass, "automation", {"automation": configs})
    await hass.async_start()
    await hass.async_block_till_done()
    assert all(state.state == "on" for state in hass.states.async_all("automation"))
    assert len(hass.states.async_all("automation")) == len(configs)


async def advance(hass, freezer, instant):
    freezer.move_to(instant)
    async_fire_time_changed(hass, dt_util.parse_datetime(instant))
    await hass.async_block_till_done()


def reminder(name, entity, alias="Reminder"):
    return expanded(
        name,
        {
            "next_jamaat" if name == "jamaat_reminder" else "next_sehri": entity,
            "offset": -10,
            "reminder_actions": [
                {
                    "event": "test_reminder",
                    "event_data": {
                        "mosque": alias,
                        "scheduled_time": "{{ scheduled_time }}",
                        "prayer": "{{ prayer | default('sehri') }}",
                    },
                }
            ],
        },
        alias,
    )


@pytest.mark.parametrize("set_volume", [False, True])
async def test_adhan_plays_selected_media_and_targets_at_published_beginning(
    hass, freezer, set_volume
):
    freezer.move_to("2026-10-23T04:59:00Z")
    playback = async_mock_service(hass, "media_player", "play_media")
    volume = async_mock_service(hass, "media_player", "volume_set")
    hass.states.async_set("sensor.mosque_fajr", "2026-10-23T05:00:00+00:00", ATTRS)
    config = expanded(
        "adhan",
        {
            "prayer_sensors": ["sensor.mosque_fajr"],
            "media_players": ["media_player.hall", "media_player.kitchen"],
            "adhan_media": {
                "media_content_id": "media-source://media_source/local/selected.mp3",
                "media_content_type": "audio/mpeg",
            },
            "set_volume": set_volume,
            "volume": 0.35,
        },
    )
    await start(hass, [config])
    await advance(hass, freezer, "2026-10-23T04:59:59Z")
    assert not playback
    await advance(hass, freezer, "2026-10-23T05:00:00Z")
    assert len(playback) == 1
    assert playback[0].data == {
        "entity_id": ["media_player.hall", "media_player.kitchen"],
        "media_content_id": "media-source://media_source/local/selected.mp3",
        "media_content_type": "audio/mpeg",
    }
    assert len(volume) == int(set_volume)
    if set_volume:
        assert volume[0].data["volume_level"] == 0.35
    await advance(hass, freezer, "2026-10-23T05:00:01Z")
    assert len(playback) == 1


async def test_jamaat_reminder_reschedules_changed_approved_time_and_each_friday_event(
    hass, freezer
):
    freezer.move_to("2026-10-23T11:00:00Z")
    events = async_capture_events(hass, "test_reminder")
    entity = "sensor.first_next_jamaat"
    hass.states.async_set(
        entity, "2026-10-23T12:00:00+00:00", {**ATTRS, "prayer": "jumuah"}
    )
    await start(hass, [reminder("jamaat_reminder", entity)])
    # An approved replacement must cancel the old reminder rather than trigger both.
    hass.states.async_set(
        entity, "2026-10-23T12:15:00+00:00", {**ATTRS, "prayer": "jumuah"}
    )
    await hass.async_block_till_done()
    await advance(hass, freezer, "2026-10-23T11:50:00Z")
    assert not events
    await advance(hass, freezer, "2026-10-23T12:05:00Z")
    assert len(events) == 1
    assert events[0].data["scheduled_time"] == "2026-10-23T12:15:00+00:00"
    assert events[0].data["prayer"] == "jumuah"
    await advance(hass, freezer, "2026-10-23T12:15:00Z")
    hass.states.async_set(
        entity, "2026-10-23T13:00:00+00:00", {**ATTRS, "prayer": "jumuah"}
    )
    await hass.async_block_till_done()
    await advance(hass, freezer, "2026-10-23T12:50:00Z")
    assert len(events) == 2
    assert events[1].data["scheduled_time"] == "2026-10-23T13:00:00+00:00"


async def test_sehri_reminder_before_midnight_uses_next_event_not_today_activation(
    hass, freezer
):
    freezer.move_to("2026-10-23T23:00:00Z")
    events = async_capture_events(hass, "test_reminder")
    hass.states.async_set("sensor.today_ramadan_status", "inactive")
    hass.states.async_set("sensor.next_sehri", "2026-10-24T00:05:00+00:00", ATTRS)
    await start(hass, [reminder("sehri_reminder", "sensor.next_sehri")])
    await advance(hass, freezer, "2026-10-23T23:55:00Z")
    assert len(events) == 1
    assert events[0].data["scheduled_time"] == "2026-10-24T00:05:00+00:00"
    assert hass.states.get("sensor.today_ramadan_status").state == "inactive"


@pytest.mark.parametrize("unavailable", ["unknown", "unavailable"])
async def test_missing_timestamps_cancel_reminders_and_other_mosque_is_independent(
    hass, freezer, unavailable
):
    freezer.move_to("2026-10-23T11:00:00Z")
    events = async_capture_events(hass, "test_reminder")
    for mosque in ["first", "second"]:
        hass.states.async_set(f"sensor.{mosque}", "2026-10-23T12:00:00+00:00", ATTRS)
    await start(
        hass,
        [
            reminder("jamaat_reminder", f"sensor.{mosque}", mosque)
            for mosque in ["first", "second"]
        ],
    )
    hass.states.async_set("sensor.first", unavailable, ATTRS)
    await hass.async_block_till_done()
    await advance(hass, freezer, "2026-10-23T11:50:00Z")
    assert [event.data["mosque"] for event in events] == ["second"]


async def test_late_known_target_and_reenabled_automation_do_not_catch_up(
    hass, freezer
):
    freezer.move_to("2026-10-23T11:51:00Z")
    events = async_capture_events(hass, "test_reminder")
    # The 11:50 offset instant passed before loading the automation.
    hass.states.async_set("sensor.next_jamaat", "2026-10-23T12:00:00+00:00", ATTRS)
    config = reminder("jamaat_reminder", "sensor.next_jamaat")
    await start(hass, [config])
    await advance(hass, freezer, "2026-10-23T11:52:00Z")
    assert not events
    entity = hass.states.async_all("automation")[0].entity_id
    await hass.services.async_call(
        "automation", "turn_off", {"entity_id": entity}, blocking=True
    )
    await hass.services.async_call(
        "automation", "turn_on", {"entity_id": entity}, blocking=True
    )
    with patch(
        "homeassistant.config.async_hass_config_yaml",
        return_value={"automation": [config]},
    ):
        await hass.services.async_call("automation", "reload", {}, blocking=True)
        await hass.async_block_till_done()
    await advance(hass, freezer, "2026-10-23T12:00:00Z")
    assert not events
    hass.states.async_set("sensor.next_jamaat", "2026-10-23T12:30:00+00:00", ATTRS)
    await hass.async_block_till_done()
    await advance(hass, freezer, "2026-10-23T12:20:00Z")
    assert len(events) == 1


async def test_health_alert_deduplicates_refreshes_and_allows_recovery_reentry(hass):
    events = async_capture_events(hass, "test_health")
    coverage = "sensor.coverage"
    source = "sensor.source_status"
    config = expanded(
        "timetable_health_alert",
        {
            "coverage_sensor": coverage,
            "source_status_sensor": source,
            "alert_actions": [
                {
                    "event": "test_health",
                    "event_data": {
                        "kind": "{{ alert_kind }}",
                        "days": "{{ days_remaining }}",
                        "pending": "{{ pending_review }}",
                    },
                }
            ],
        },
    )
    # Existing warnings are not replayed on startup.
    hass.states.async_set(coverage, "expiring", {"days_remaining": 5})
    hass.states.async_set(source, "pending_review", {"pending_review": True})
    await start(hass, [config])
    assert not events
    hass.states.async_set(coverage, "expiring", {"days_remaining": 4})
    hass.states.async_set(
        source, "pending_review", {"pending_review": True, "last_checked": "changed"}
    )
    await hass.async_block_till_done()
    assert not events
    hass.states.async_set(coverage, "covered", {"days_remaining": 20})
    hass.states.async_set(source, "up_to_date", {"pending_review": False})
    await hass.async_block_till_done()
    hass.states.async_set(coverage, "expiring", {"days_remaining": 7})
    await hass.async_block_till_done()
    assert [event.data["kind"] for event in events] == ["expiring"]
    assert events[0].data["days"] == 7
    hass.states.async_set(source, "pending_review", {"pending_review": True})
    await hass.async_block_till_done()
    assert [event.data["kind"] for event in events] == ["expiring", "pending_review"]
    for entity, recovered, attrs in [
        (coverage, "missing_today", {"days_remaining": 0}),
        (source, "pending_review", {"pending_review": True}),
    ]:
        hass.states.async_set(entity, "unavailable")
        await hass.async_block_till_done()
        hass.states.async_set(entity, recovered, attrs)
        await hass.async_block_till_done()
    assert len(events) == 2
    hass.states.async_set(coverage, "covered")
    await hass.async_block_till_done()
    hass.states.async_set(coverage, "missing_today")
    await hass.async_block_till_done()
    assert events[-1].data["kind"] == "missing_today"
