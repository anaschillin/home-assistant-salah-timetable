"""Exercise wizard-generated reminders against HA's real automation scheduler."""

from datetime import date, time
from unittest.mock import patch
from zoneinfo import ZoneInfo

import probatio
import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import trigger as trigger_helper
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
)

from custom_components.salah_timetable.const import DOMAIN
from custom_components.salah_timetable.domain.model import (
    DailyPrayers,
    PrayerField,
    Timetable,
)
from custom_components.salah_timetable.persistence.storage import TimetableStorage


def row(day, **fields):
    return DailyPrayers(
        date.fromisoformat(day),
        {
            PrayerField(field): tuple(time.fromisoformat(value) for value in values)
            for field, values in fields.items()
        },
        {},
    )


def config(entry, fields, minutes=10, alias="Prayer reminders"):
    return {
        "alias": alias,
        "triggers": [
            {
                "trigger": "salah_timetable.prayer_time",
                "id": "published",
                "options": {
                    "mosque_id": entry.entry_id,
                    "fields": fields,
                    "minutes_before": minutes,
                },
            }
        ],
        "actions": [
            {
                "event": "test_prayer_reminder",
                "event_data": {
                    "mosque": "{{ trigger.mosque }}",
                    "prayer": "{{ trigger.prayer }}",
                    "field": "{{ trigger.field }}",
                    "time": "{{ trigger.scheduled_time }}",
                    "minutes": "{{ trigger.minutes_before }}",
                    "id": "{{ trigger.id }}",
                },
            }
        ],
        "mode": "parallel",
        "max": 100,
    }


async def approve(hass, entry, *rows):
    coordinator = getattr(entry, "runtime_data", None)
    storage = (
        coordinator.storage
        if coordinator
        else TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    )
    await storage.async_replace((Timetable("annual", "annual", rows),))
    if coordinator:
        await coordinator.async_refresh()
    await hass.async_block_till_done()


async def start(hass, configs):
    assert await async_setup_component(hass, "automation", {"automation": configs})
    await hass.async_start()
    await hass.async_block_till_done()
    assert len(hass.states.async_all("automation")) == len(configs)
    assert all(state.state == "on" for state in hass.states.async_all("automation"))


async def advance(hass, freezer, instant):
    freezer.move_to(instant)
    async_fire_time_changed(hass, dt_util.parse_datetime(instant))
    await hass.async_block_till_done()


async def test_midnight_offset_and_all_selected_congregations(hass, entry, freezer):
    freezer.move_to("2026-10-22T22:00:00Z")
    await approve(
        hass, entry, row("2026-10-23", fajr_begin=["00:05"], jumuah=["12:30", "13:30"])
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    events = async_capture_events(hass, "test_prayer_reminder")
    await start(hass, [config(entry, ["fajr_begin", "jumuah"])])
    await advance(hass, freezer, "2026-10-22T22:54:59Z")
    assert not events
    await advance(hass, freezer, "2026-10-22T22:55:00Z")
    assert events[0].data == {
        "mosque": "Example Mosque",
        "prayer": "Fajr beginning",
        "field": "fajr_begin",
        "time": "2026-10-23T00:05:00+01:00",
        "minutes": 10,
        "id": "published",
    }
    await advance(hass, freezer, "2026-10-23T11:20:00Z")
    await advance(hass, freezer, "2026-10-23T12:20:00Z")
    assert [event.data["prayer"] for event in events] == [
        "Fajr beginning",
        "Jumu’ah Jamaat 1",
        "Jumu’ah Jamaat 2",
    ]


async def test_replacements_deletions_and_unavailability_cancel_timers(
    hass, entry, freezer
):
    freezer.move_to("2026-10-23T03:00:00Z")
    await approve(
        hass, entry, row("2026-10-23", fajr_begin=["05:00"], fajr_jamaat=["05:30"])
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    events = async_capture_events(hass, "test_prayer_reminder")
    await start(hass, [config(entry, ["fajr_begin", "fajr_jamaat"])])
    await approve(hass, entry, row("2026-10-23", fajr_begin=["05:15"]))
    await advance(hass, freezer, "2026-10-23T03:50:00Z")
    assert not events
    await advance(hass, freezer, "2026-10-23T04:05:00Z")
    assert len(events) == 1
    assert events[0].data["time"] == "2026-10-23T05:15:00+01:00"
    await advance(hass, freezer, "2026-10-23T04:20:00Z")
    assert len(events) == 1
    await approve(hass, entry, row("2026-10-23", fajr_jamaat=["06:00"]))
    coordinator = entry.runtime_data
    coordinator.last_update_success = False
    coordinator.async_update_listeners()
    # Avoid the normal minute poll recovering the deliberately unavailable source.
    with patch.object(
        coordinator, "_async_update_data", side_effect=RuntimeError("Unavailable")
    ):
        await advance(hass, freezer, "2026-10-23T04:50:00Z")
    assert len(events) == 1


async def test_reload_unload_and_automation_cleanup(hass, entry, freezer):
    freezer.move_to("2026-10-23T03:00:00Z")
    await approve(
        hass, entry, row("2026-10-23", fajr_begin=["05:00"], fajr_jamaat=["05:30"])
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    events = async_capture_events(hass, "test_prayer_reminder")
    automation = config(entry, ["fajr_begin", "fajr_jamaat"])
    await start(hass, [automation])
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    with patch(
        "homeassistant.config.async_hass_config_yaml",
        return_value={"automation": [automation]},
    ):
        await hass.services.async_call("automation", "reload", {}, blocking=True)
        await hass.async_block_till_done()
    await advance(hass, freezer, "2026-10-23T03:50:00Z")
    assert len(events) == 1
    assert await hass.config_entries.async_unload(entry.entry_id)
    await advance(hass, freezer, "2026-10-23T04:20:00Z")
    assert len(events) == 1
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    await advance(hass, freezer, "2026-10-23T04:21:00Z")
    assert len(events) == 1
    await hass.services.async_call(
        "automation",
        "turn_off",
        {
            "entity_id": hass.states.async_all("automation")[0].entity_id,
        },
        blocking=True,
    )
    await approve(hass, entry, row("2026-10-23", fajr_begin=["06:00"]))
    await advance(hass, freezer, "2026-10-23T04:50:00Z")
    assert len(events) == 1


async def test_startup_order_and_simultaneous_masjids(hass, entry, freezer):
    freezer.move_to("2026-10-23T03:00:00Z")
    other = MockConfigEntry(
        domain=DOMAIN,
        title="Other Masjid",
        unique_id="other",
        data={
            "name": "Other Masjid",
            "mosque_id": "other",
            "time_zone": "Europe/London",
        },
    )
    other.add_to_hass(hass)
    for mosque in (entry, other):
        await approve(hass, mosque, row("2026-10-23", fajr_begin=["05:00"]))
    assert all(mosque.state is ConfigEntryState.NOT_LOADED for mosque in (entry, other))
    events = async_capture_events(hass, "test_prayer_reminder")
    await start(
        hass,
        [
            config(entry, ["fajr_begin"], alias="First"),
            config(other, ["fajr_begin"], alias="Other"),
        ],
    )
    # Load the masjids after their automation listeners have already attached.
    # Setting up the domain can also load its other configured entries.
    for mosque in (entry, other):
        if mosque.state is ConfigEntryState.NOT_LOADED:
            assert await hass.config_entries.async_setup(mosque.entry_id)
    await hass.async_block_till_done()
    assert all(mosque.state is ConfigEntryState.LOADED for mosque in (entry, other))
    await advance(hass, freezer, "2026-10-23T03:50:00Z")
    assert {event.data["mosque"] for event in events} == {
        "Example Mosque",
        "Other Masjid",
    }


@pytest.mark.parametrize("minutes", [0, 10])
async def test_exact_due_update_retains_unchanged_timer(hass, entry, freezer, minutes):
    freezer.move_to("2026-10-23T03:00:00Z")
    await approve(
        hass, entry, row("2026-10-23", fajr_begin=["05:00"], fajr_jamaat=["05:00"])
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    events = async_capture_events(hass, "test_prayer_reminder")
    await start(hass, [config(entry, ["fajr_begin", "fajr_jamaat"], minutes)])
    instant = "2026-10-23T04:00:00Z" if minutes == 0 else "2026-10-23T03:50:00Z"
    freezer.move_to(instant)
    # Force the coordinator update before HA dispatches the due point callbacks.
    await entry.runtime_data.async_refresh()
    async_fire_time_changed(hass, dt_util.parse_datetime(instant))
    await hass.async_block_till_done()
    assert {event.data["field"] for event in events} == {"fajr_begin", "fajr_jamaat"}
    await advance(hass, freezer, "2026-10-23T04:01:00Z")
    assert len(events) == 2


@pytest.mark.parametrize(
    "options",
    [
        {"fields": [], "minutes_before": 10},
        {"fields": ["sunrise"], "minutes_before": 10},
        {"fields": ["fajr_begin"], "minutes_before": -1},
        {"fields": ["fajr_begin"], "minutes_before": 181},
        {"fields": ["fajr_begin"], "minutes_before": 2.5},
        {"fields": ["fajr_begin"], "minutes_before": True},
    ],
)
async def test_invalid_trigger_selections_rejected(hass, entry, options):
    with pytest.raises(probatio.Invalid):
        await trigger_helper.async_validate_trigger_config(
            hass,
            [
                {
                    "platform": "salah_timetable.prayer_time",
                    "options": {"mosque_id": entry.entry_id, **options},
                }
            ],
        )


async def test_trigger_description_loads_for_home_assistant_editor(hass, entry):
    await trigger_helper.async_validate_trigger_config(
        hass,
        [
            {
                "platform": "salah_timetable.prayer_time",
                "options": {
                    "mosque_id": entry.entry_id,
                    "fields": ["fajr_begin"],
                    "minutes_before": 10,
                },
            }
        ],
    )
    descriptions = await trigger_helper.async_get_all_descriptions(hass)
    assert descriptions["salah_timetable.prayer_time"]["fields"]["fields"]["selector"][
        "select"
    ]["multiple"]
