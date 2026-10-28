"""Exercise Adhan controls using HA's blueprint expansion and real scheduler."""

import asyncio
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from homeassistant.components.automation.config import AUTOMATION_BLUEPRINT_SCHEMA
from homeassistant.components.blueprint.models import Blueprint, BlueprintInputs
from homeassistant.core import Context
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from homeassistant.util import yaml as yaml_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

BLUEPRINT = (
    Path(__file__).parents[1]s[2] / "blueprints/automation/salah_timetable/adhan.yaml"
)
TIMESTAMP = {"device_class": "timestamp"}
NORMAL = {"media_content_id": "local/adhan.mp3", "media_content_type": "audio/mpeg"}
FAJR = {"media_content_id": "local/fajr.mp3", "media_content_type": "audio/mpeg"}


@pytest.fixture(autouse=True)
async def stop_scheduled_automations(hass, freezer):
    """Detach future daily triggers and cancel intentional restoration delays."""
    yield
    entities = [state.entity_id for state in hass.states.async_all("automation")]
    if entities:
        await hass.services.async_call(
            "automation", "turn_off", {"entity_id": entities}, blocking=True
        )
        await hass.async_block_till_done()


def config(**overrides):
    blueprint = Blueprint(
        yaml_util.load_yaml_dict(BLUEPRINT),
        expected_domain="automation",
        schema=AUTOMATION_BLUEPRINT_SCHEMA,
    )
    assert blueprint.validate() is None
    instance = BlueprintInputs(
        blueprint,
        {
            "alias": "Adhan controls",
            "use_blueprint": {
                "path": "adhan.yaml",
                "input": {
                    "prayer_sensors": ["sensor.fajr", "sensor.dhuhr"],
                    "media_players": ["media_player.hall", "media_player.offline"],
                    "adhan_media": NORMAL,
                    **overrides,
                },
            },
        },
    )
    instance.validate()
    return instance.async_substitute()


async def start(hass, config):
    assert await async_setup_component(hass, "automation", {"automation": [config]})
    await hass.async_start()
    await hass.async_block_till_done()
    assert len(hass.states.async_all("automation")) == 1
    assert hass.states.async_all("automation")[0].state == "on"


async def advance(hass, freezer, instant):
    freezer.move_to(instant)
    async_fire_time_changed(hass, dt_util.parse_datetime(instant))
    await settle_actions()


async def settle_actions():
    """Flush queued script steps while an intentional future delay is pending."""
    for _ in range(20):
        await asyncio.sleep(0)


def initial(hass):
    hass.states.async_set("sensor.fajr", "2026-10-23T05:00:00+00:00", TIMESTAMP)
    hass.states.async_set("sensor.dhuhr", "2026-10-23T12:00:00+00:00", TIMESTAMP)
    hass.states.async_set("media_player.hall", "idle", {"volume_level": 0.2})
    hass.states.async_set("media_player.offline", "unavailable")


def services(hass, *, update=True):
    played, volumes = [], []

    async def play(call):
        played.append(dict(call.data))
        if update:
            for target in call.data["entity_id"]:
                state = hass.states.get(target)
                hass.states.async_set(
                    target,
                    "playing",
                    {
                        **state.attributes,
                        "media_content_id": call.data["media_content_id"],
                        "app_id": "adhan-player",
                    },
                    context=call.context,
                )

    async def volume(call):
        volumes.append(dict(call.data))
        if update:
            targets = call.data["entity_id"]
            if isinstance(targets, str):
                targets = [targets]
            for target in targets:
                state = hass.states.get(target)
                hass.states.async_set(
                    target,
                    state.state,
                    {**state.attributes, "volume_level": call.data["volume_level"]},
                    context=call.context,
                )

    hass.services.async_register("media_player", "play_media", play)
    hass.services.async_register("media_player", "volume_set", volume)
    return played, volumes


async def test_fajr_audio_and_prayer_volume_overrides_skip_unavailable_players(
    hass, freezer
):
    freezer.move_to("2026-10-23T04:59:00Z")
    initial(hass)
    played, volumes = services(hass)
    await start(
        hass,
        config(
            use_fajr_media=True,
            fajr_media=FAJR,
            fajr_sensor="sensor.fajr",
            dhuhr_sensor="sensor.dhuhr",
            set_volume=True,
            use_per_prayer_volume=True,
            fajr_volume=0.3,
            dhuhr_volume=0.65,
        ),
    )
    await advance(hass, freezer, "2026-10-23T05:00:00Z")
    assert played == [{"entity_id": ["media_player.hall"], **FAJR}]
    assert volumes == [{"entity_id": ["media_player.hall"], "volume_level": 0.3}]
    await advance(hass, freezer, "2026-10-23T12:00:00Z")
    assert played[-1] == {"entity_id": ["media_player.hall"], **NORMAL}
    assert volumes[-1]["volume_level"] == 0.65
    assert hass.states.get("sensor.fajr").state == "2026-10-23T05:00:00+00:00"


async def test_disabled_prayer_does_not_play_or_change_volume(hass, freezer):
    freezer.move_to("2026-10-23T04:59:00Z")
    initial(hass)
    played, volumes = services(hass)
    await start(hass, config(disabled_prayer_sensors=["sensor.fajr"], set_volume=True))
    await advance(hass, freezer, "2026-10-23T05:00:00Z")
    assert not played
    assert not volumes
    await advance(hass, freezer, "2026-10-23T12:00:00Z")
    assert len(played) == len(volumes) == 1


@pytest.mark.parametrize(
    ("instant", "timezone", "quiet_start", "quiet_end", "blocked"),
    [
        ("2026-10-23T05:00:00Z", "homeassistant", "22:00:00", "07:00:00", True),
        ("2026-10-23T06:00:00Z", "homeassistant", "22:00:00", "07:00:00", False),
        ("2026-10-23T12:00:00Z", "utc", "12:00:00", "13:00:00", True),
        ("2026-10-23T13:00:00Z", "utc", "12:00:00", "13:00:00", False),
        ("2026-10-23T05:00:00Z", "utc", "05:00:00", "05:00:00", False),
        # Both occurrences of the repeated London 01:30 fall in the quiet window.
        ("2026-10-25T00:30:00Z", "homeassistant", "01:00:00", "02:00:00", True),
        ("2026-10-25T01:30:00Z", "homeassistant", "01:00:00", "02:00:00", True),
    ],
)
async def test_quiet_hours_use_selected_clock_and_dst(
    hass, freezer, instant, timezone, quiet_start, quiet_end, blocked
):
    await hass.config.async_set_time_zone("Europe/London")
    target = dt_util.parse_datetime(instant)
    freezer.move_to(target.replace(second=0) - timedelta(minutes=1))
    initial(hass)
    hass.states.async_set("sensor.fajr", instant, TIMESTAMP)
    hass.states.async_set("sensor.dhuhr", "unknown", TIMESTAMP)
    played, volumes = services(hass)
    await start(
        hass,
        config(
            quiet_enabled=True,
            quiet_start=quiet_start,
            quiet_end=quiet_end,
            quiet_timezone=timezone,
        ),
    )
    await advance(hass, freezer, instant)
    assert bool(played) is not blocked
    assert not volumes


async def test_empty_fajr_override_falls_back_and_volume_requires_opt_in(hass, freezer):
    freezer.move_to("2026-10-23T04:59:00Z")
    initial(hass)
    played, volumes = services(hass)
    await start(
        hass,
        config(
            use_fajr_media=True,
            fajr_sensor="sensor.fajr",
            use_per_prayer_volume=True,
            fajr_volume=0.8,
        ),
    )
    await advance(hass, freezer, "2026-10-23T05:00:00Z")
    assert played == [{"entity_id": ["media_player.hall"], **NORMAL}]
    assert not volumes


async def test_owned_playback_restores_previous_volume_after_selected_delay(
    hass, freezer
):
    freezer.move_to("2026-10-23T04:59:00Z")
    initial(hass)
    played, volumes = services(hass)
    await start(
        hass, config(set_volume=True, volume=0.6, restore_volume=True, restore_delay=60)
    )
    await advance(hass, freezer, "2026-10-23T05:00:00Z")
    assert len(played) == len(volumes) == 1
    await advance(hass, freezer, "2026-10-23T05:00:59Z")
    assert len(volumes) == 1
    await advance(hass, freezer, "2026-10-23T05:01:00Z")
    assert [call["volume_level"] for call in volumes] == [0.6, 0.2]


@pytest.mark.parametrize(
    "intervention", ["volume", "content", "context", "unavailable"]
)
async def test_manual_or_other_automation_changes_skip_restoration(
    hass, freezer, intervention
):
    freezer.move_to("2026-10-23T04:59:00Z")
    initial(hass)
    _, volumes = services(hass)
    await start(
        hass, config(set_volume=True, volume=0.6, restore_volume=True, restore_delay=60)
    )
    await advance(hass, freezer, "2026-10-23T05:00:00Z")
    current = hass.states.get("media_player.hall")
    attrs = dict(current.attributes)
    if intervention == "volume":
        attrs["volume_level"] = 0.8
    elif intervention == "content":
        attrs["media_content_id"] = "user-track"
    hass.states.async_set(
        "media_player.hall",
        "unavailable" if intervention == "unavailable" else current.state,
        attrs,
        # Some devices keep the original HA context for hardware changes. Guard
        # content/volume independently as well as explicitly changed contexts.
        context=Context() if intervention == "context" else current.context,
        force_update=True,
    )
    await advance(hass, freezer, "2026-10-23T05:01:00Z")
    assert len(volumes) == 1


@pytest.mark.parametrize("intervention", ["volume", "content"])
async def test_same_context_away_and_back_changes_skip_restoration(
    hass, freezer, intervention
):
    """Hardware updates may retain HA context even when the user changes playback."""
    freezer.move_to("2026-10-23T04:59:00Z")
    initial(hass)
    _, volumes = services(hass)
    await start(
        hass, config(set_volume=True, volume=0.6, restore_volume=True, restore_delay=60)
    )
    await advance(hass, freezer, "2026-10-23T05:00:00Z")
    original = hass.states.get("media_player.hall")
    changed = dict(original.attributes)
    if intervention == "volume":
        changed["volume_level"] = 0.8
    else:
        changed["media_content_id"] = "user-track"
    freezer.move_to("2026-10-23T05:00:02Z")
    hass.states.async_set(
        original.entity_id, original.state, changed, context=original.context
    )
    await settle_actions()
    freezer.move_to("2026-10-23T05:00:03Z")
    hass.states.async_set(
        original.entity_id,
        original.state,
        original.attributes,
        context=original.context,
    )
    await settle_actions()
    assert hass.states.get(original.entity_id).context == original.context
    await advance(hass, freezer, "2026-10-23T05:01:00Z")
    assert len(volumes) == 1
    assert hass.states.get(original.entity_id).attributes["volume_level"] == 0.6


async def test_players_without_owned_updates_never_restore(hass, freezer):
    freezer.move_to("2026-10-23T04:59:00Z")
    initial(hass)
    _, volumes = services(hass, update=False)
    await start(hass, config(set_volume=True, restore_volume=True, restore_delay=60))
    await advance(hass, freezer, "2026-10-23T05:00:00Z")
    await advance(hass, freezer, "2026-10-23T05:01:00Z")
    assert len(volumes) == 1


async def test_delayed_player_acknowledgement_is_captured_before_restoring(
    hass, freezer
):
    freezer.move_to("2026-10-23T04:59:00Z")
    initial(hass)
    played, volumes = services(hass)
    pending = []

    async def delayed_play(call):
        pending.append(call)

    hass.services.async_register("media_player", "play_media", delayed_play)
    await start(
        hass,
        config(set_volume=True, volume=0.6, restore_volume=True, restore_delay=60),
    )
    await advance(hass, freezer, "2026-10-23T05:00:00Z")
    assert len(pending) == len(volumes) == 1
    assert not played
    freezer.move_to("2026-10-23T05:00:02Z")
    hass.states.async_set(
        "media_player.hall",
        "playing",
        {"volume_level": 0.6, "media_content_id": NORMAL["media_content_id"]},
        context=pending[0].context,
    )
    await settle_actions()
    await advance(hass, freezer, "2026-10-23T05:01:00Z")
    assert len(volumes) == 1
    await advance(hass, freezer, "2026-10-23T05:01:02Z")
    assert [call["volume_level"] for call in volumes] == [0.6, 0.2]


async def test_removed_player_during_acknowledgement_does_not_block_healthy_restore(
    hass, freezer
):
    freezer.move_to("2026-10-23T04:59:00Z")
    initial(hass)
    hass.states.async_set("media_player.removable", "idle", {"volume_level": 0.4})
    played, volumes = services(hass)

    async def partial_acknowledgement(call):
        played.append(dict(call.data))
        hall = hass.states.get("media_player.hall")
        hass.states.async_set(
            hall.entity_id,
            "playing",
            {
                **hall.attributes,
                "media_content_id": call.data["media_content_id"],
                "app_id": "adhan-player",
            },
            context=call.context,
        )

    hass.services.async_register("media_player", "play_media", partial_acknowledgement)
    await start(
        hass,
        config(
            media_players=["media_player.hall", "media_player.removable"],
            set_volume=True,
            volume=0.6,
            restore_volume=True,
            restore_delay=60,
        ),
    )
    await advance(hass, freezer, "2026-10-23T05:00:00Z")
    assert played == [
        {"entity_id": ["media_player.hall", "media_player.removable"], **NORMAL}
    ]
    assert volumes == [
        {
            "entity_id": ["media_player.hall", "media_player.removable"],
            "volume_level": 0.6,
        }
    ]
    assert hass.states.get("media_player.hall").state == "playing"
    assert hass.states.get("media_player.removable").state == "idle"

    # Removing the player which never acknowledged playback completes the wait.
    freezer.move_to("2026-10-23T05:00:02Z")
    hass.states.async_remove("media_player.removable")
    await settle_actions()
    await advance(hass, freezer, "2026-10-23T05:01:01Z")
    assert len(volumes) == 1
    await advance(hass, freezer, "2026-10-23T05:01:02Z")
    assert volumes[-1] == {"entity_id": ["media_player.hall"], "volume_level": 0.2}
    assert len(volumes) == 2
    assert hass.states.get("media_player.hall").attributes["volume_level"] == 0.2
    assert hass.states.get("media_player.removable") is None


async def test_no_available_players_skips_playback_and_volume(hass, freezer):
    freezer.move_to("2026-10-23T04:59:00Z")
    initial(hass)
    hass.states.async_set("media_player.hall", "unknown")
    played, volumes = services(hass)
    await start(hass, config(set_volume=True, restore_volume=True, restore_delay=60))
    await advance(hass, freezer, "2026-10-23T05:00:00Z")
    assert not played
    assert not volumes


async def test_unknown_previous_volume_is_not_guessed_for_restoration(hass, freezer):
    freezer.move_to("2026-10-23T04:59:00Z")
    initial(hass)
    hass.states.async_set("media_player.hall", "idle")
    played, volumes = services(hass)
    await start(hass, config(set_volume=True, restore_volume=True, restore_delay=60))
    await advance(hass, freezer, "2026-10-23T05:00:00Z")
    await advance(hass, freezer, "2026-10-23T05:01:00Z")
    assert len(played) == len(volumes) == 1


@pytest.mark.parametrize("cancellation", ["changed_reload", "turn_off"])
async def test_changed_reload_or_disabling_cancels_pending_volume_restoration(
    hass, freezer, cancellation
):
    freezer.move_to("2026-10-23T04:59:00Z")
    initial(hass)
    _, volumes = services(hass)
    selected = config(set_volume=True, restore_volume=True, restore_delay=60)
    await start(hass, selected)
    await advance(hass, freezer, "2026-10-23T05:00:00Z")
    await advance(hass, freezer, "2026-10-23T05:00:01Z")
    assert len(volumes) == 1
    if cancellation == "changed_reload":
        changed = {**selected, "alias": "Changed Adhan controls"}
        with patch(
            "homeassistant.config.async_hass_config_yaml",
            return_value={"automation": [changed]},
        ):
            await hass.services.async_call("automation", "reload", {}, blocking=True)
    else:
        entity = hass.states.async_all("automation")[0].entity_id
        await hass.services.async_call(
            "automation", "turn_off", {"entity_id": entity}, blocking=True
        )
    await settle_actions()
    await advance(hass, freezer, "2026-10-23T05:01:00Z")
    assert len(volumes) == 1


async def test_unchanged_reload_preserves_pending_restoration(hass, freezer):
    freezer.move_to("2026-10-23T04:59:00Z")
    initial(hass)
    _, volumes = services(hass)
    selected = config(set_volume=True, restore_volume=True, restore_delay=60)
    await start(hass, selected)
    await advance(hass, freezer, "2026-10-23T05:00:00Z")
    await advance(hass, freezer, "2026-10-23T05:00:01Z")
    with patch(
        "homeassistant.config.async_hass_config_yaml",
        return_value={"automation": [selected]},
    ):
        await hass.services.async_call("automation", "reload", {}, blocking=True)
    await settle_actions()
    await advance(hass, freezer, "2026-10-23T05:01:00Z")
    assert [call["volume_level"] for call in volumes] == [0.5, 0.2]
