"""Exercise shipped blueprint expansion and HA's real automation scheduler."""

import asyncio
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.components.automation.config import AUTOMATION_BLUEPRINT_SCHEMA
from homeassistant.components.blueprint.models import Blueprint, BlueprintInputs
from homeassistant.core import Context
from homeassistant.helpers.template import Template
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
    for player in ["media_player.hall", "media_player.kitchen"]:
        hass.states.async_set(player, "idle")
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


@pytest.mark.parametrize(
    ("quiet_enabled", "disabled", "expected_playback"),
    [
        (False, False, True),
        (True, False, False),
        (False, True, False),
    ],
)
async def test_adhan_quiet_hours_and_disabled_sensor_gate_playback(
    hass, freezer, quiet_enabled, disabled, expected_playback
):
    """Exercise the expanded blueprint against HA's time trigger and conditions."""
    freezer.move_to("2026-10-23T04:59:00Z")
    playback = async_mock_service(hass, "media_player", "play_media")
    hass.states.async_set("sensor.mosque_fajr", "2026-10-23T05:00:00+00:00", ATTRS)
    hass.states.async_set("media_player.hall", "idle")
    config = expanded(
        "adhan",
        {
            "prayer_sensors": ["sensor.mosque_fajr"],
            "disabled_prayer_sensors": ["sensor.mosque_fajr"] if disabled else [],
            "media_players": ["media_player.hall"],
            "adhan_media": {
                "media_content_id": "media-source://media_source/local/normal.mp3",
                "media_content_type": "audio/mpeg",
            },
            "quiet_enabled": quiet_enabled,
            "quiet_start": "04:00:00",
            "quiet_end": "06:00:00",
            "quiet_timezone": "utc",
        },
    )
    await start(hass, [config])
    await advance(hass, freezer, "2026-10-23T05:00:00Z")
    assert bool(playback) is expected_playback


async def test_adhan_fajr_media_and_volume_override(hass, freezer):
    """A configured Fajr override changes media and volume without extra triggers."""
    freezer.move_to("2026-10-23T04:59:00Z")
    playback = async_mock_service(hass, "media_player", "play_media")
    volume = async_mock_service(hass, "media_player", "volume_set")
    hass.states.async_set("sensor.mosque_fajr", "2026-10-23T05:00:00+00:00", ATTRS)
    hass.states.async_set("media_player.hall", "idle")
    config = expanded(
        "adhan",
        {
            "prayer_sensors": ["sensor.mosque_fajr"],
            "media_players": ["media_player.hall"],
            "adhan_media": {
                "media_content_id": "media-source://media_source/local/normal.mp3",
                "media_content_type": "audio/mpeg",
            },
            "set_volume": True,
            "volume": 0.5,
            "use_fajr_media": True,
            "fajr_sensor": "sensor.mosque_fajr",
            "fajr_media": {
                "media_content_id": "media-source://media_source/local/fajr.mp3",
                "media_content_type": "audio/mpeg",
            },
            "use_per_prayer_volume": True,
            "fajr_volume": 0.2,
        },
    )
    await start(hass, [config])
    await advance(hass, freezer, "2026-10-23T05:00:00Z")
    assert len(playback) == 1
    assert playback[0].data["media_content_id"] == (
        "media-source://media_source/local/fajr.mp3"
    )
    assert len(volume) == 1
    assert volume[0].data["volume_level"] == 0.2


async def test_pause_resume_skips_players_not_playing_at_beginning(hass, freezer):
    """A prayer beginning must not pause or later resume an already-paused player."""
    freezer.move_to("2026-10-23T04:59:00Z")
    paused = async_mock_service(hass, "media_player", "media_pause")
    resumed = async_mock_service(hass, "media_player", "media_play")
    hass.states.async_set("sensor.prayer_begin", "2026-10-23T05:00:00+00:00", ATTRS)
    hass.states.async_set("sensor.prayer_jamaat", "2026-10-23T05:05:00+00:00", ATTRS)
    hass.states.async_set("media_player.hall", "paused", {"media_content_id": "song-a"})
    config = expanded(
        "pause_resume_media",
        {
            "prayer_beginning": "sensor.prayer_begin",
            "resume_anchor": "sensor.prayer_jamaat",
            "resume_delay": 0,
            "media_players": ["media_player.hall"],
        },
    )
    await start(hass, [config])
    await advance(hass, freezer, "2026-10-23T05:00:00Z")
    assert not paused
    await advance(hass, freezer, "2026-10-23T05:06:00Z")
    assert not resumed


@pytest.mark.parametrize(
    "anchor", ["unknown", "unavailable", "2026-10-23T04:55:00+00:00"]
)
async def test_pause_resume_rejects_invalid_or_early_anchor(hass, freezer, anchor):
    """Invalid anchors must be rejected before any media player is paused."""
    freezer.move_to("2026-10-23T04:59:00Z")
    paused = async_mock_service(hass, "media_player", "media_pause")
    hass.states.async_set("sensor.prayer_begin", "2026-10-23T05:00:00+00:00", ATTRS)
    hass.states.async_set("sensor.prayer_jamaat", anchor, ATTRS)
    hass.states.async_set(
        "media_player.hall", "playing", {"media_content_id": "song-a"}
    )
    config = expanded(
        "pause_resume_media",
        {
            "prayer_beginning": "sensor.prayer_begin",
            "resume_anchor": "sensor.prayer_jamaat",
            "resume_delay": 0,
            "media_players": ["media_player.hall"],
        },
    )
    await start(hass, [config])
    await advance(hass, freezer, "2026-10-23T05:00:00Z")
    assert not paused


async def test_pause_resume_does_not_claim_unavailable_player(hass, freezer):
    """Unavailable players cannot be paused or resumed by the blueprint."""
    freezer.move_to("2026-10-23T04:59:00Z")
    paused = async_mock_service(hass, "media_player", "media_pause")
    resumed = async_mock_service(hass, "media_player", "media_play")
    hass.states.async_set("sensor.prayer_begin", "2026-10-23T05:00:00+00:00", ATTRS)
    hass.states.async_set("sensor.prayer_jamaat", "2026-10-23T05:05:00+00:00", ATTRS)
    hass.states.async_set("media_player.hall", "unavailable")
    config = expanded(
        "pause_resume_media",
        {
            "prayer_beginning": "sensor.prayer_begin",
            "resume_anchor": "sensor.prayer_jamaat",
            "resume_delay": 0,
            "media_players": ["media_player.hall"],
        },
    )
    await start(hass, [config])
    await advance(hass, freezer, "2026-10-23T05:00:00Z")
    assert not paused
    await advance(hass, freezer, "2026-10-23T05:06:00Z")
    assert not resumed


@pytest.mark.parametrize(
    ("state", "volume", "content", "same_context", "expected"),
    [
        ("playing", 0.6, "adhan.mp3", True, True),
        ("playing", 0.4, "adhan.mp3", True, False),
        ("playing", 0.6, "other.mp3", False, False),
        ("paused", 0.6, "adhan.mp3", True, False),
        ("unavailable", 0.6, "adhan.mp3", True, False),
    ],
)
async def test_adhan_restore_guard_is_deterministic(
    hass, freezer, state, volume, content, same_context, expected
):
    """Render the actual delayed-restoration guard without starting a timer."""
    freezer.move_to("2026-10-23T05:00:00Z")
    config = expanded(
        "adhan",
        {
            "prayer_sensors": ["sensor.mosque_fajr"],
            "media_players": ["media_player.hall"],
            "adhan_media": {
                "media_content_id": "adhan.mp3",
                "media_content_type": "audio/mpeg",
            },
        },
    )
    restore = config["actions"][-1]["then"][-1]["repeat"]["sequence"][0]["if"][0][
        "value_template"
    ]
    owner = Context()
    hass.states.async_set(
        "media_player.hall",
        state,
        {"volume_level": volume, "media_content_id": content},
        context=owner if same_context else Context(),
    )
    player = hass.states.get("media_player.hall")
    saved = {
        "entity": "media_player.hall",
        "content": "adhan.mp3",
        "app": None,
        "updated": player.last_updated.isoformat(),
    }
    result = Template(restore, hass).async_render(
        {
            "repeat": {"item": saved},
            "effective_volume": 0.6,
            "run_context": owner.id,
        },
        parse_result=True,
    )
    assert result is expected


@pytest.mark.parametrize(
    ("state", "content", "same_context", "changed_since_pause", "expected"),
    [
        ("paused", "song-a", True, False, True),
        ("playing", "song-a", True, False, False),
        ("paused", "song-b", True, False, False),
        ("paused", "song-a", False, False, False),
        ("paused", "song-a", True, True, False),
        ("unavailable", "song-a", True, False, False),
    ],
)
async def test_resume_guard_requires_unchanged_owned_player(
    hass, freezer, state, content, same_context, changed_since_pause, expected
):
    """Render the shipped resume guard against real HA state and context."""
    freezer.move_to("2026-10-23T05:00:00Z")
    config = expanded(
        "pause_resume_media",
        {
            "prayer_beginning": "sensor.prayer_begin",
            "resume_anchor": "sensor.prayer_jamaat",
            "media_players": ["media_player.hall"],
        },
    )
    guard = config["actions"][-1]["repeat"]["sequence"][0]["value_template"]
    owner = Context()
    hass.states.async_set(
        "media_player.hall",
        state,
        {"media_content_id": content, "app_id": "music"},
        context=owner if same_context else Context(),
    )
    player = hass.states.get("media_player.hall")
    saved = {
        "entity_id": "media_player.hall",
        "content": "song-a",
        "app": "music",
        "context": owner.id,
        "updated": (
            "2026-10-23T04:59:00+00:00"
            if changed_since_pause
            else player.last_updated.isoformat()
        ),
    }
    result = Template(guard, hass).async_render(
        {"repeat": {"item": saved}}, parse_result=True
    )
    assert result is expected


@pytest.mark.parametrize("blueprint", ["adhan", "pause_resume_media"])
async def test_media_ownership_is_per_player_and_rejects_replaced_run(
    hass, freezer, blueprint
):
    """One interrupted player must not block a still-owned second player.

    A new automation context, as after a reload/restart, must never claim
    media state left behind by an earlier run.
    """
    freezer.move_to("2026-10-23T05:00:00Z")
    if blueprint == "adhan":
        config = expanded(
            "adhan",
            {
                "prayer_sensors": ["sensor.mosque_fajr"],
                "media_players": ["media_player.hall", "media_player.kitchen"],
                "adhan_media": {
                    "media_content_id": "adhan.mp3",
                    "media_content_type": "audio/mpeg",
                },
            },
        )
        guard = config["actions"][-1]["then"][-1]["repeat"]["sequence"][0]["if"][0][
            "value_template"
        ]
        state = "playing"
        attrs = {"volume_level": 0.6, "media_content_id": "adhan.mp3"}
    else:
        config = expanded(
            "pause_resume_media",
            {
                "prayer_beginning": "sensor.prayer_begin",
                "resume_anchor": "sensor.prayer_jamaat",
                "media_players": ["media_player.hall", "media_player.kitchen"],
            },
        )
        guard = config["actions"][-1]["repeat"]["sequence"][0]["value_template"]
        state = "paused"
        attrs = {"media_content_id": "song-a", "app_id": "music"}

    original_run = Context()
    interrupted_run = Context()
    for entity, context in [
        ("media_player.hall", original_run),
        ("media_player.kitchen", interrupted_run),
    ]:
        hass.states.async_set(entity, state, attrs, context=context)

    def allowed(entity, run_context):
        player = hass.states.get(entity)
        if blueprint == "adhan":
            saved = {
                "entity": entity,
                "content": "adhan.mp3",
                "app": None,
                "updated": player.last_updated.isoformat(),
            }
            variables = {
                "repeat": {"item": saved},
                "effective_volume": 0.6,
                "run_context": run_context,
            }
        else:
            saved = {
                "entity_id": entity,
                "content": "song-a",
                "app": "music",
                "context": run_context,
                "updated": player.last_updated.isoformat(),
            }
            variables = {"repeat": {"item": saved}}
        return Template(guard, hass).async_render(variables, parse_result=True)

    assert allowed("media_player.hall", original_run.id) is True
    assert allowed("media_player.kitchen", original_run.id) is False
    # A reloaded automation has a new run context; it must not inherit ownership.
    assert allowed("media_player.hall", Context().id) is False


@pytest.mark.parametrize("blueprint", ["adhan", "pause_resume_media"])
async def test_media_ownership_guard_rejects_removed_player(hass, freezer, blueprint):
    """A removed media player must not be reclaimed by a delayed action."""
    freezer.move_to("2026-10-23T05:00:00Z")
    if blueprint == "adhan":
        config = expanded(
            "adhan",
            {
                "prayer_sensors": ["sensor.mosque_fajr"],
                "media_players": ["media_player.hall"],
                "adhan_media": {
                    "media_content_id": "adhan.mp3",
                    "media_content_type": "audio/mpeg",
                },
            },
        )
        guard = config["actions"][-1]["then"][-1]["repeat"]["sequence"][0]["if"][0][
            "value_template"
        ]
        variables = {
            "repeat": {
                "item": {
                    "entity": "media_player.hall",
                    "content": "adhan.mp3",
                    "app": None,
                    "updated": "2026-10-23T05:00:00+00:00",
                }
            },
            "effective_volume": 0.6,
            "run_context": Context().id,
        }
    else:
        config = expanded(
            "pause_resume_media",
            {
                "prayer_beginning": "sensor.prayer_begin",
                "resume_anchor": "sensor.prayer_jamaat",
                "media_players": ["media_player.hall"],
            },
        )
        guard = config["actions"][-1]["repeat"]["sequence"][0]["value_template"]
        variables = {
            "repeat": {
                "item": {
                    "entity_id": "media_player.hall",
                    "content": "song-a",
                    "app": "music",
                    "context": Context().id,
                    "updated": "2026-10-23T05:00:00+00:00",
                }
            }
        }

    assert hass.states.get("media_player.hall") is None
    assert Template(guard, hass).async_render(variables, parse_result=True) is False


@pytest.mark.parametrize("blueprint", ["adhan", "pause_resume_media"])
async def test_media_blueprint_reload_does_not_replay_past_prayer(
    hass, freezer, blueprint
):
    """A real automation reload must not replay a missed prayer beginning."""
    freezer.move_to("2026-10-23T05:01:00Z")
    hass.states.async_set("sensor.prayer_begin", "2026-10-23T05:00:00+00:00", ATTRS)
    hass.states.async_set("sensor.prayer_jamaat", "2026-10-23T05:05:00+00:00", ATTRS)
    hass.states.async_set("media_player.hall", "playing")
    if blueprint == "adhan":
        config = expanded(
            "adhan",
            {
                "prayer_sensors": ["sensor.prayer_begin"],
                "media_players": ["media_player.hall"],
                "adhan_media": {
                    "media_content_id": "adhan.mp3",
                    "media_content_type": "audio/mpeg",
                },
            },
        )
        action = async_mock_service(hass, "media_player", "play_media")
    else:
        config = expanded(
            "pause_resume_media",
            {
                "prayer_beginning": "sensor.prayer_begin",
                "resume_anchor": "sensor.prayer_jamaat",
                "media_players": ["media_player.hall"],
            },
        )
        action = async_mock_service(hass, "media_player", "media_pause")

    await start(hass, [config])
    with patch(
        "homeassistant.config.async_hass_config_yaml",
        return_value={"automation": [config]},
    ):
        await hass.services.async_call("automation", "reload", {}, blocking=True)
        await hass.async_block_till_done()

    await advance(hass, freezer, "2026-10-23T05:02:00Z")
    assert not action


@pytest.mark.parametrize("blueprint", ["adhan", "pause_resume_media"])
async def test_delayed_media_action_rejects_ownership_after_reload(
    hass, freezer, blueprint
):
    """A replacement run cannot claim media state from the cancelled run."""
    freezer.move_to("2026-10-23T05:00:00Z")
    if blueprint == "adhan":
        config = expanded(
            "adhan",
            {
                "prayer_sensors": ["sensor.prayer_begin"],
                "media_players": ["media_player.hall"],
                "adhan_media": {
                    "media_content_id": "adhan.mp3",
                    "media_content_type": "audio/mpeg",
                },
            },
        )
        guard = config["actions"][-1]["then"][-1]["repeat"]["sequence"][0]["if"][0][
            "value_template"
        ]
        state = "playing"
        attributes = {"media_content_id": "adhan.mp3", "volume_level": 0.6}
    else:
        config = expanded(
            "pause_resume_media",
            {
                "prayer_beginning": "sensor.prayer_begin",
                "resume_anchor": "sensor.prayer_jamaat",
                "media_players": ["media_player.hall"],
            },
        )
        guard = config["actions"][-1]["repeat"]["sequence"][0]["value_template"]
        state = "paused"
        attributes = {"media_content_id": "song-a", "app_id": "music"}

    original_run = Context()
    replacement_run = Context()
    hass.states.async_set("media_player.hall", state, attributes, context=original_run)
    player = hass.states.get("media_player.hall")

    if blueprint == "adhan":
        saved = {
            "entity": "media_player.hall",
            "content": "adhan.mp3",
            "app": None,
            "updated": player.last_updated.isoformat(),
        }

        def permitted(context):
            return Template(guard, hass).async_render(
                {
                    "repeat": {"item": saved},
                    "effective_volume": 0.6,
                    "run_context": context.id,
                },
                parse_result=True,
            )

    else:
        saved = {
            "entity_id": "media_player.hall",
            "content": "song-a",
            "app": "music",
            "context": original_run.id,
            "updated": player.last_updated.isoformat(),
        }

        def permitted(context):
            return Template(guard, hass).async_render(
                {"repeat": {"item": {**saved, "context": context.id}}},
                parse_result=True,
            )

    assert permitted(original_run) is True
    assert permitted(replacement_run) is False

    # A subsequent state update also invalidates the original run's claim.
    hass.states.async_set("media_player.hall", "unavailable", context=replacement_run)
    assert permitted(original_run) is False


async def test_changed_reload_cancels_active_adhan_volume_restore(hass, freezer):
    """Reload must cancel a pending volume restoration without replaying Adhan."""
    freezer.move_to("2026-10-23T04:59:00Z")
    volume = async_mock_service(hass, "media_player", "volume_set")
    playback = async_mock_service(hass, "media_player", "play_media")
    hass.states.async_set("sensor.prayer_begin", "2026-10-23T05:00:00+00:00", ATTRS)
    hass.states.async_set(
        "media_player.hall",
        "idle",
        {"volume_level": 0.3, "media_content_id": "previous.mp3"},
    )
    inputs = {
        "prayer_sensors": ["sensor.prayer_begin"],
        "media_players": ["media_player.hall"],
        "adhan_media": {
            "media_content_id": "adhan.mp3",
            "media_content_type": "audio/mpeg",
        },
        "set_volume": True,
        "volume": 0.6,
        "restore_volume": True,
        "restore_delay": 120,
    }
    config = expanded("adhan", inputs)
    await start(hass, [config])

    # Do not block on HA's task queue while the automation is in a long delay.
    freezer.move_to("2026-10-23T05:00:00Z")
    async_fire_time_changed(hass, dt_util.parse_datetime("2026-10-23T05:00:00Z"))
    for _ in range(30):
        if playback and volume:
            break
        await asyncio.sleep(0)
    assert len(playback) == 1
    assert len(volume) == 1

    # Simulate a player acknowledging Adhan playback and the volume change.
    hass.states.async_set(
        "media_player.hall",
        "playing",
        {"volume_level": 0.6, "media_content_id": "adhan.mp3"},
        context=playback[0].context,
    )
    for _ in range(30):
        await asyncio.sleep(0)

    changed = expanded("adhan", {**inputs, "volume": 0.5})
    with patch(
        "homeassistant.config.async_hass_config_yaml",
        return_value={"automation": [changed]},
    ):
        await asyncio.wait_for(
            hass.services.async_call("automation", "reload", {}, blocking=True),
            timeout=10,
        )

    # Drive HA time beyond the restore delay without waiting on pending tasks.
    freezer.move_to("2026-10-23T05:03:00Z")
    async_fire_time_changed(hass, dt_util.parse_datetime("2026-10-23T05:03:00Z"))
    for _ in range(30):
        await asyncio.sleep(0)
    assert len(volume) == 1
    assert len(playback) == 1
