"""Run the pause/resume blueprint through HA's real automation scheduler."""

import asyncio
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
    Path(__file__).parents[1]s[2]
    / "blueprints/automation/salah_timetable/pause_resume_media.yaml"
)
TIMESTAMP = {"device_class": "timestamp"}
CONTENT = {"media_content_id": "selected-track", "app_id": "test-player"}


def config(
    *, alias="Prayer media", beginning="sensor.begin", anchor="sensor.anchor", delay=5
):
    blueprint = Blueprint(
        yaml_util.load_yaml_dict(BLUEPRINT),
        expected_domain="automation",
        schema=AUTOMATION_BLUEPRINT_SCHEMA,
    )
    assert blueprint.validate() is None
    instance = BlueprintInputs(
        blueprint,
        {
            "alias": alias,
            "use_blueprint": {
                "path": "pause_resume_media.yaml",
                "input": {
                    "prayer_beginning": beginning,
                    "resume_anchor": anchor,
                    "resume_delay": delay,
                    "media_players": [
                        "media_player.playing",
                        "media_player.already_paused",
                        "media_player.stopped",
                        "media_player.offline",
                    ],
                },
            },
        },
    )
    instance.validate()
    return instance.async_substitute()


async def start(hass, configs):
    assert await async_setup_component(hass, "automation", {"automation": configs})
    await hass.async_start()
    await hass.async_block_till_done()
    assert len(hass.states.async_all("automation")) == len(configs)
    assert all(state.state == "on" for state in hass.states.async_all("automation"))


async def advance(hass, freezer, instant):
    freezer.move_to(instant)
    async_fire_time_changed(hass, dt_util.parse_datetime(instant))
    await settle_actions()


async def settle_actions():
    """Run queued steps without awaiting the automation's intentional long delay."""
    for _ in range(20):
        await asyncio.sleep(0)


def players(hass):
    hass.states.async_set("media_player.playing", "playing", CONTENT)
    hass.states.async_set("media_player.already_paused", "paused", CONTENT)
    hass.states.async_set("media_player.stopped", "idle", CONTENT)
    hass.states.async_set("media_player.offline", "unavailable")


def anchors(hass, *, beginning="sensor.begin", anchor="sensor.anchor"):
    hass.states.async_set(beginning, "2026-10-23T12:00:00+00:00", TIMESTAMP)
    hass.states.async_set(anchor, "2026-10-23T12:30:00+00:00", TIMESTAMP)


def services(hass):
    paused, resumed = [], []

    async def pause(call):
        targets = call.data["entity_id"]
        if isinstance(targets, str):
            targets = [targets]
        paused.extend(targets)
        for entity in targets:
            current = hass.states.get(entity)
            hass.states.async_set(
                entity, "paused", current.attributes, context=call.context
            )

    async def play(call):
        target = call.data["entity_id"]
        targets = [target] if isinstance(target, str) else target
        resumed.extend(targets)
        for entity in targets:
            current = hass.states.get(entity)
            hass.states.async_set(
                entity, "playing", current.attributes, context=call.context
            )

    hass.services.async_register("media_player", "media_pause", pause)
    hass.services.async_register("media_player", "media_play", play)
    return paused, resumed


async def test_only_owned_originally_playing_media_resumes_after_published_anchor(
    hass, freezer
):
    freezer.move_to("2026-10-23T11:59:00Z")
    players(hass)
    anchors(hass)
    paused, resumed = services(hass)
    await start(hass, [config()])
    await advance(hass, freezer, "2026-10-23T11:59:59Z")
    assert not paused
    await advance(hass, freezer, "2026-10-23T12:00:00Z")
    assert paused == ["media_player.playing"]
    assert hass.states.get("media_player.playing").state == "paused"
    await advance(hass, freezer, "2026-10-23T12:34:59Z")
    assert not resumed
    await advance(hass, freezer, "2026-10-23T12:35:00Z")
    assert resumed == ["media_player.playing"]
    assert hass.states.get("media_player.already_paused").state == "paused"
    assert hass.states.get("media_player.stopped").state == "idle"
    assert hass.states.get("media_player.offline").state == "unavailable"


@pytest.mark.parametrize(
    "anchor",
    [
        "unknown",
        "unavailable",
        "invalid",
        "2026-10-23T11:59:00+00:00",
        "2026-10-23T12:00:00+00:00",
    ],
)
async def test_invalid_or_missing_resume_anchor_skips_before_pausing(
    hass, freezer, anchor
):
    freezer.move_to("2026-10-23T11:59:00Z")
    players(hass)
    anchors(hass)
    hass.states.async_set("sensor.anchor", anchor, TIMESTAMP)
    paused, resumed = services(hass)
    await start(hass, [config()])
    await advance(hass, freezer, "2026-10-23T12:00:00Z")
    assert not paused
    assert not resumed
    assert hass.states.get("media_player.playing").state == "playing"


@pytest.mark.parametrize("delay", [-1, 181, "invalid", "nan", "inf"])
async def test_invalid_yaml_delay_never_pauses_a_player(hass, freezer, delay):
    """UI selector bounds also apply when inputs are supplied directly in YAML."""
    freezer.move_to("2026-10-23T11:59:00Z")
    players(hass)
    anchors(hass)
    paused, resumed = services(hass)
    await start(hass, [config(delay=delay)])
    await advance(hass, freezer, "2026-10-23T12:00:00Z")
    assert not paused
    assert not resumed
    assert hass.states.get("media_player.playing").state == "playing"


async def test_zero_delay_and_changed_anchor_use_captured_timestamp(hass, freezer):
    freezer.move_to("2026-10-23T11:59:00Z")
    players(hass)
    anchors(hass)
    paused, resumed = services(hass)
    await start(hass, [config(delay=0)])
    await advance(hass, freezer, "2026-10-23T12:00:00Z")
    assert paused == ["media_player.playing"]
    hass.states.async_set("sensor.anchor", "unavailable", TIMESTAMP)
    await settle_actions()
    await advance(hass, freezer, "2026-10-23T12:29:59Z")
    assert not resumed
    await advance(hass, freezer, "2026-10-23T12:30:00Z")
    assert resumed == ["media_player.playing"]


async def test_pause_without_confirmed_automation_context_is_not_owned(hass, freezer):
    """A device which drops service context must be resumed manually."""
    freezer.move_to("2026-10-23T11:59:00Z")
    players(hass)
    anchors(hass)
    paused, resumed = services(hass)

    async def unconfirmed_pause(call):
        targets = call.data["entity_id"]
        targets = [targets] if isinstance(targets, str) else targets
        paused.extend(targets)
        for entity in targets:
            current = hass.states.get(entity)
            hass.states.async_set(
                entity, "paused", current.attributes, context=Context()
            )

    hass.services.async_register("media_player", "media_pause", unconfirmed_pause)
    await start(hass, [config()])
    await advance(hass, freezer, "2026-10-23T12:00:00Z")
    assert paused == ["media_player.playing"]
    await advance(hass, freezer, "2026-10-23T12:35:00Z")
    assert not resumed


@pytest.mark.parametrize(
    ("state", "attrs"),
    [
        ("idle", CONTENT),
        ("unavailable", {}),
        ("playing", {**CONTENT, "media_content_id": "user-new-track"}),
        ("paused", {**CONTENT, "media_content_id": "user-new-track"}),
        ("paused", {**CONTENT, "volume_level": 0.7}),
    ],
)
async def test_manual_intervention_is_never_resumed(hass, freezer, state, attrs):
    freezer.move_to("2026-10-23T11:59:00Z")
    players(hass)
    anchors(hass)
    paused, resumed = services(hass)
    await start(hass, [config()])
    await advance(hass, freezer, "2026-10-23T12:00:00Z")
    assert paused == ["media_player.playing"]
    freezer.move_to("2026-10-23T12:10:00Z")
    hass.states.async_set("media_player.playing", state, attrs, context=Context())
    await settle_actions()
    await advance(hass, freezer, "2026-10-23T12:35:00Z")
    assert not resumed
    assert hass.states.get("media_player.playing").state == state


async def test_removed_player_is_not_resumed(hass, freezer):
    freezer.move_to("2026-10-23T11:59:00Z")
    players(hass)
    anchors(hass)
    paused, resumed = services(hass)
    await start(hass, [config()])
    await advance(hass, freezer, "2026-10-23T12:00:00Z")
    assert paused == ["media_player.playing"]
    hass.states.async_remove("media_player.playing")
    await settle_actions()
    await advance(hass, freezer, "2026-10-23T12:35:00Z")
    assert not resumed


async def test_later_automation_pause_ownership_is_not_undone(hass, freezer):
    freezer.move_to("2026-10-23T11:59:00Z")
    players(hass)
    anchors(hass)
    paused, resumed = services(hass)
    await start(hass, [config()])
    await advance(hass, freezer, "2026-10-23T12:00:00Z")
    freezer.move_to("2026-10-23T12:10:00Z")
    # Another operation changes ownership while leaving the reported content paused.
    hass.states.async_set(
        "media_player.playing",
        "paused",
        {**CONTENT, "pause_operation": "another-automation"},
        context=Context(),
    )
    await settle_actions()
    await advance(hass, freezer, "2026-10-23T12:35:00Z")
    assert paused == ["media_player.playing"]
    assert not resumed


async def test_two_mosques_do_not_claim_or_extend_an_existing_pause(hass, freezer):
    freezer.move_to("2026-10-23T11:59:00Z")
    players(hass)
    anchors(hass)
    anchors(hass, beginning="sensor.second_begin", anchor="sensor.second_anchor")
    hass.states.async_set("sensor.second_begin", "2026-10-23T12:05:00+00:00", TIMESTAMP)
    hass.states.async_set(
        "sensor.second_anchor", "2026-10-23T12:40:00+00:00", TIMESTAMP
    )
    paused, resumed = services(hass)
    await start(
        hass,
        [
            config(alias="First mosque"),
            config(
                alias="Second mosque",
                beginning="sensor.second_begin",
                anchor="sensor.second_anchor",
            ),
        ],
    )
    await advance(hass, freezer, "2026-10-23T12:00:00Z")
    await advance(hass, freezer, "2026-10-23T12:05:00Z")
    assert paused == ["media_player.playing"]
    await advance(hass, freezer, "2026-10-23T12:35:00Z")
    assert resumed == ["media_player.playing"]
    await advance(hass, freezer, "2026-10-23T12:45:00Z")
    assert resumed == ["media_player.playing"]


async def test_overlapping_trigger_is_skipped_while_the_same_window_is_active(
    hass, freezer
):
    freezer.move_to("2026-10-23T11:59:00Z")
    players(hass)
    anchors(hass)
    paused, resumed = services(hass)
    await start(hass, [config()])
    await advance(hass, freezer, "2026-10-23T12:00:00Z")
    hass.states.async_set("sensor.begin", "2026-10-23T12:05:00+00:00", TIMESTAMP)
    hass.states.async_set("sensor.anchor", "2026-10-23T12:40:00+00:00", TIMESTAMP)
    await settle_actions()
    await advance(hass, freezer, "2026-10-23T12:05:00Z")
    assert paused == ["media_player.playing"]
    await advance(hass, freezer, "2026-10-23T12:35:00Z")
    assert resumed == ["media_player.playing"]
    await advance(hass, freezer, "2026-10-23T12:45:00Z")
    assert resumed == ["media_player.playing"]


@pytest.mark.parametrize("cancellation", ["turn_off", "reload"])
async def test_cancellation_does_not_resume_after_the_window(
    hass, freezer, cancellation
):
    freezer.move_to("2026-10-23T11:59:00Z")
    players(hass)
    anchors(hass)
    paused, resumed = services(hass)
    blueprint = config()
    await start(hass, [blueprint])
    await advance(hass, freezer, "2026-10-23T12:00:00Z")
    assert paused == ["media_player.playing"]
    if cancellation == "reload":
        changed = {**blueprint, "alias": "Reloaded prayer media"}
        with patch(
            "homeassistant.config.async_hass_config_yaml",
            return_value={"automation": [changed]},
        ):
            await hass.services.async_call("automation", "reload", {}, blocking=True)
    else:
        entity_id = hass.states.async_all("automation")[0].entity_id
        await hass.services.async_call(
            "automation", "turn_off", {"entity_id": entity_id}, blocking=True
        )
    await settle_actions()
    await advance(hass, freezer, "2026-10-23T12:35:00Z")
    assert not resumed
    assert hass.states.get("media_player.playing").state == "paused"


async def test_late_start_never_catches_up_a_past_beginning(hass, freezer):
    freezer.move_to("2026-10-23T12:01:00Z")
    players(hass)
    anchors(hass)
    paused, resumed = services(hass)
    await start(hass, [config()])
    await advance(hass, freezer, "2026-10-23T12:35:00Z")
    assert not paused
    assert not resumed


async def test_unchanged_incremental_reload_retains_pending_resumption(hass, freezer):
    freezer.move_to("2026-10-23T11:59:00Z")
    players(hass)
    anchors(hass)
    paused, resumed = services(hass)
    blueprint = config()
    await start(hass, [blueprint])
    await advance(hass, freezer, "2026-10-23T12:00:00Z")
    assert paused == ["media_player.playing"]
    await advance(hass, freezer, "2026-10-23T12:00:01Z")
    with patch(
        "homeassistant.config.async_hass_config_yaml",
        return_value={"automation": [blueprint]},
    ):
        await hass.services.async_call("automation", "reload", {}, blocking=True)
    await settle_actions()
    await advance(hass, freezer, "2026-10-23T12:35:00Z")
    assert resumed == ["media_player.playing"]
