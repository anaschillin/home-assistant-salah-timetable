"""Absolute event entities and effective Ramadan records in a real HA instance."""

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.salah_timetable.const import DOMAIN
from custom_components.salah_timetable.domain.model import (
    DailyPrayers,
    PrayerField,
    Timetable,
)
from custom_components.salah_timetable.persistence.storage import TimetableStorage


def daily(day, *, fajr=time(6), fajr_jamaat=time(6, 30), extra=None):
    times = {
        PrayerField.SEHRI_ENDS: (time(5, 55),),
        PrayerField.FAJR_BEGIN: (fajr,),
        PrayerField.FAJR_JAMAAT: (fajr_jamaat,),
        PrayerField.SUNRISE: (time(7),),
        PrayerField.DHUHR_BEGIN: (time(12),),
        PrayerField.DHUHR_JAMAAT: (time(13),),
        PrayerField.ASR_BEGIN: (time(15),),
        PrayerField.ASR_JAMAAT: (time(15, 30),),
        PrayerField.MAGHRIB_BEGIN: (time(18),),
        PrayerField.MAGHRIB_JAMAAT: (time(18, 5),),
        PrayerField.ISHA_BEGIN: (time(20),),
        PrayerField.ISHA_JAMAAT: (time(20, 30),),
    }
    times.update(extra or {})
    return DailyPrayers(day, times, {"Published date": day.isoformat()})


@pytest.fixture
async def event_tables(hass, entry):
    annual = Timetable(
        "annual-2026",
        "annual",
        (
            daily(date(2026, 3, 9)),
            daily(date(2026, 3, 10)),
            daily(date(2026, 3, 11), fajr=time(6, 3), fajr_jamaat=time(6, 33)),
        ),
    )
    ramadan = Timetable(
        "ramadan-2026",
        "ramadan",
        (
            DailyPrayers(
                date(2026, 3, 10),
                {
                    PrayerField.FAJR_BEGIN: (time(5, 45),),
                    PrayerField.FAJR_JAMAAT: (time(6, 5),),
                    PrayerField.MAGHRIB_BEGIN: (time(18, 15),),
                },
                {"Ramadan Fajr": "05:45", "Ramadan Maghrib": "18:15"},
            ),
        ),
    )
    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    await storage.async_replace((annual, ramadan))
    return annual, ramadan


def state(hass, key):
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"example_{key}"
    )
    assert entity_id is not None, f"Missing {key} entity"
    result = hass.states.get(entity_id)
    assert result is not None
    return result


async def tick(hass, freezer, instant):
    freezer.move_to(instant)
    async_fire_time_changed(
        hass, datetime.fromisoformat(instant).astimezone(timezone.utc)
    )
    await hass.async_block_till_done()


async def test_event_entities_transition_at_exact_beginning_and_jamaat(
    hass, entry, event_tables, freezer
):
    freezer.move_to("2026-03-10T05:50:00+00:00")
    er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, "example_previous_jamaat", config_entry=entry
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert state(hass, "next_salah").state == "2026-03-10T06:00:00+00:00"
    assert state(hass, "next_jamaat").state == "2026-03-10T06:30:00+00:00"
    assert state(hass, "previous_jamaat").state == "2026-03-09T20:30:00+00:00"
    dashboard = state(hass, "dashboard")
    assert dashboard.attributes["context_mode"] == "previous"
    assert dashboard.attributes["date"] == "2026-03-10"
    assert len(dashboard.attributes["prayers"]) == 5
    assert dashboard.attributes["time_zone"] == "Europe/London"

    # Only the integration's scheduled point-in-time refresh moves these states.
    await tick(hass, freezer, "2026-03-10T06:00:00+00:00")
    assert state(hass, "next_salah").state == "2026-03-10T12:00:00+00:00"
    assert state(hass, "dashboard").attributes["context_mode"] == "upcoming"
    assert state(hass, "dashboard").attributes["context_jamaat"]["prayer"] == "fajr"

    await tick(hass, freezer, "2026-03-10T06:30:00+00:00")
    assert state(hass, "previous_jamaat").state == "2026-03-10T06:30:00+00:00"
    assert state(hass, "next_jamaat").state == "2026-03-10T13:00:00+00:00"
    assert state(hass, "dashboard").attributes["context_mode"] == "previous"


async def test_after_isha_uses_tomorrows_published_times(
    hass, entry, event_tables, freezer
):
    freezer.move_to("2026-03-10T21:00:00+00:00")
    er.async_get(hass).async_get_or_create(
        "sensor", DOMAIN, "example_previous_jamaat", config_entry=entry
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert state(hass, "next_salah").state == "2026-03-11T06:03:00+00:00"
    assert state(hass, "next_jamaat").state == "2026-03-11T06:33:00+00:00"
    assert state(hass, "previous_jamaat").state == "2026-03-10T20:30:00+00:00"
    assert state(hass, "dashboard").attributes["next_salah"]["prayer"] == "fajr"


async def test_missing_tomorrow_stays_unavailable(hass, entry, freezer):
    freezer.move_to("2026-03-10T21:00:00+00:00")
    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    await storage.async_replace(
        (Timetable("annual-2026", "annual", (daily(date(2026, 3, 10)),)),)
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert state(hass, "next_salah").state == "unavailable"
    assert state(hass, "next_jamaat").state == "unavailable"
    assert state(hass, "dashboard").attributes["next_salah"] is None


async def test_no_per_second_state_writes(hass, entry, event_tables, freezer):
    freezer.move_to("2026-03-10T06:01:00+00:00")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    before = {
        key: state(hass, key)
        for key in ("dashboard", "next_salah", "next_jamaat", "fajr_begin")
    }
    freezer.tick(1)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    for key, previous in before.items():
        assert state(hass, key) is previous
    assert all("countdown" not in value.attributes for value in before.values())


async def test_unconfirmed_ramadan_does_not_override_annual(
    hass, entry, event_tables, freezer
):
    freezer.move_to("2026-03-10T05:30:00+00:00")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert state(hass, "fajr_begin").state == "2026-03-10T06:00:00+00:00"
    assert state(hass, "ramadan_status").state == "inactive"
    assert state(hass, "next_sehri").state == "unavailable"
    assert state(hass, "next_iftar").state == "unavailable"
    assert state(hass, "dashboard").attributes["ramadan"]["active"] is False


async def test_confirmed_ramadan_effective_defaults_keep_sources_unchanged(
    hass, entry, event_tables, freezer
):
    freezer.move_to("2026-03-10T05:30:00+00:00")
    annual, ramadan = event_tables
    before = (annual.as_dict(), ramadan.as_dict())
    hass.config_entries.async_update_entry(
        entry,
        options={
            "ramadan_mode": "auto",
            "ramadan_start": "2026-03-10",
            "ramadan_end": "2026-03-10",
        },
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert state(hass, "ramadan_status").state == "active"
    assert state(hass, "fajr_begin").state == "2026-03-10T05:45:00+00:00"
    assert state(hass, "iftar").state == "2026-03-10T18:15:00+00:00"
    assert state(hass, "next_iftar").state == "2026-03-10T18:15:00+00:00"
    assert state(hass, "next_sehri").state == "2026-03-10T05:55:00+00:00"
    assert state(hass, "taraweeh").state == "unavailable"
    assert state(hass, "taraweeh_status").state == "after_isha_jamaat"
    info = state(hass, "dashboard").attributes["ramadan"]
    assert info["taraweeh"] is None
    assert info["taraweeh_text"] == "After Isha Jamaat"
    assert (annual.as_dict(), ramadan.as_dict()) == before
    assert entry.runtime_data.storage.for_date(date(2026, 3, 10)) == annual.days[1]
    assert (
        PrayerField.IFTAR
        not in entry.runtime_data.storage.for_date(date(2026, 3, 10)).times
    )
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert state(hass, "iftar").state == "2026-03-10T18:15:00+00:00"


async def test_published_iftar_and_taraweeh_take_precedence(hass, entry, freezer):
    freezer.move_to("2026-03-10T05:30:00+00:00")
    annual = Timetable(
        "annual-2026",
        "annual",
        (
            daily(
                date(2026, 3, 10),
                extra={
                    PrayerField.IFTAR: (time(18, 17),),
                    PrayerField.TARAWEEH: (time(21),),
                },
            ),
        ),
    )
    ramadan = Timetable(
        "ramadan-2026",
        "ramadan",
        (
            DailyPrayers(
                date(2026, 3, 10), {PrayerField.MAGHRIB_BEGIN: (time(18, 15),)}, {}
            ),
        ),
    )
    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    await storage.async_replace((annual, ramadan))
    hass.config_entries.async_update_entry(entry, options={"ramadan_mode": "on"})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert state(hass, "iftar").state == "2026-03-10T18:17:00+00:00"
    assert state(hass, "taraweeh").state == "2026-03-10T21:00:00+00:00"
    assert state(hass, "taraweeh_status").state == "scheduled"
    assert state(hass, "dashboard").attributes["ramadan"]["taraweeh_text"] is None


@pytest.mark.parametrize("last_confirmed_date", ["2026-03-10", "2026-03-11"])
async def test_published_ramadan_times_remain_visible_after_their_events(
    hass, entry, event_tables, freezer, last_confirmed_date
):
    freezer.move_to("2026-03-10T21:00:00+00:00")
    hass.config_entries.async_update_entry(
        entry,
        options={
            "ramadan_mode": "auto",
            "ramadan_start": "2026-03-10",
            "ramadan_end": last_confirmed_date,
        },
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    info = state(hass, "dashboard").attributes["ramadan"]
    assert info["active"] is True
    assert info["sehri"] == "2026-03-10T05:55:00+00:00"
    assert info["iftar"] == "2026-03-10T18:15:00+00:00"
    # Today's published information remains distinct from any next-day countdown.
    if last_confirmed_date == "2026-03-10":
        assert state(hass, "next_sehri").state == "unavailable"
        assert state(hass, "next_iftar").state == "unavailable"
    else:
        assert state(hass, "next_sehri").state == "2026-03-11T05:55:00+00:00"
        assert state(hass, "next_iftar").state == "2026-03-11T18:00:00+00:00"
