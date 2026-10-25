"""Native read-only prayer calendars, API queries and actual calendar triggers."""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
)

from custom_components.salah_timetable.calendar import _next_event, calendar_events
from custom_components.salah_timetable.const import DOMAIN
from custom_components.salah_timetable.csv_parser import CsvParser
from custom_components.salah_timetable.model import DailyPrayers, PrayerField, Timetable
from custom_components.salah_timetable.ramadan import RamadanSettings
from custom_components.salah_timetable.storage import TimetableStorage

UTC = ZoneInfo("UTC")
LONDON = ZoneInfo("Europe/London")


def instant(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def row(day, **fields):
    return DailyPrayers(
        date.fromisoformat(day),
        {
            PrayerField(field): tuple(time.fromisoformat(value) for value in values)
            for field, values in fields.items()
        },
        {},
    )


def table(*rows, source="annual-2026", kind="annual"):
    return Timetable(source, kind, rows)


def query(tables, start, end, *, settings=None, zone=UTC, mosque="example"):
    return calendar_events(
        mosque,
        tables,
        settings or RamadanSettings(),
        zone,
        instant(start),
        instant(end),
    )


def calendar_id(hass, unique_id="example"):
    entity_id = er.async_get(hass).async_get_entity_id(
        "calendar", DOMAIN, f"{unique_id}_prayer_calendar"
    )
    assert entity_id is not None
    return entity_id


def calendar_entity(hass, unique_id="example"):
    return hass.data["calendar"].get_entity(calendar_id(hass, unique_id))


async def approve_tables(hass, entry, tables, zone=LONDON):
    storage = TimetableStorage(hass, entry.entry_id, zone)
    await storage.async_replace(tables)
    return storage


def test_distinct_display_intervals_preserve_all_friday_congregations():
    tables = (
        table(
            row(
                "2026-10-23",
                fajr_begin=["05:00"],
                fajr_jamaat=["05:30"],
                sunrise=["07:00"],
                dhuhr_begin=["12:00"],
                jumuah=["12:30", "13:30", "14:30"],
            )
        ),
    )
    events = query(tables, "2026-10-23T00:00Z", "2026-10-24T00:00Z")
    assert [event.summary for event in events] == [
        "Fajr beginning",
        "Fajr Jamaat",
        "Sunrise",
        "Dhuhr beginning",
        "Jumu’ah Jamaat 1",
        "Jumu’ah Jamaat 2",
        "Jumu’ah Jamaat 3",
    ]
    assert all(
        event.end - event.start == timedelta(minutes=1) and not event.all_day
        for event in events
    )
    assert len({event.uid for event in events}) == 7
    assert all(event.uid for event in events)
    assert len(events) == 7  # Absent Asr/Maghrib/Isha remain absent.


def test_query_start_inclusive_end_exclusive_and_equivalent_timezone_ranges():
    tables = (table(row("2026-10-23", fajr_begin=["06:00"], fajr_jamaat=["06:30"])),)
    first = query(tables, "2026-10-23T06:00Z", "2026-10-23T06:30Z")
    other = query(tables, "2026-10-23T08:00+02:00", "2026-10-23T08:30+02:00")
    assert [event.summary for event in first] == ["Fajr beginning"]
    assert first == other
    assert query(tables, "2026-10-24T00:00Z", "2026-10-25T00:00Z") == []


def test_calendar_queries_include_overlapping_intervals_not_only_starts():
    tables = (table(row("2026-10-23", fajr_begin=["06:00"])),)
    assert len(query(tables, "2026-10-23T06:00:30Z", "2026-10-23T06:00:40Z")) == 1
    assert query(tables, "2026-10-23T06:01:00Z", "2026-10-23T06:02:00Z") == []
    assert query(tables, "2026-10-23T05:59:00Z", "2026-10-23T06:00:00Z") == []


def test_midnight_boundary_excludes_events_ending_exactly_at_midnight():
    tables = (table(row("2026-10-23", isha_jamaat=["23:59"])),)
    overlap = query(tables, "2026-10-23T23:59:30Z", "2026-10-24T00:00:00Z")
    assert len(overlap) == 1
    assert overlap[0].start == instant("2026-10-23T23:59:00Z")
    assert overlap[0].end == instant("2026-10-24T00:00:00Z")
    assert query(tables, "2026-10-24T00:00:00Z", "2026-10-24T01:00:00Z") == []
    assert (
        _next_event(
            "example", tables, RamadanSettings(), UTC, instant("2026-10-23T23:59:45Z")
        )
        == overlap[0]
    )
    assert (
        _next_event(
            "example", tables, RamadanSettings(), UTC, instant("2026-10-24T00:00:00Z")
        )
        is None
    )


def test_next_event_remains_current_until_display_interval_ends():
    tables = (table(row("2026-10-23", fajr_begin=["06:00"], fajr_jamaat=["06:30"])),)
    for now in ("2026-10-23T06:00:00Z", "2026-10-23T06:00:59Z"):
        assert _next_event(
            "example", tables, RamadanSettings(), UTC, instant(now)
        ).start == instant("2026-10-23T06:00:00Z")
    assert _next_event(
        "example", tables, RamadanSettings(), UTC, instant("2026-10-23T06:01:00Z")
    ).start == instant("2026-10-23T06:30:00Z")


@pytest.mark.parametrize(
    ("start", "end"),
    [
        (datetime(2026, 1, 1), datetime(2026, 1, 2, tzinfo=timezone.utc)),
        (
            datetime(2026, 1, 2, tzinfo=timezone.utc),
            datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
        (
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
        (
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2027, 1, 3, tzinfo=timezone.utc),
        ),
    ],
)
def test_invalid_or_unbounded_queries_fail_explicitly(start, end):
    with pytest.raises(HomeAssistantError):
        calendar_events("example", (), RamadanSettings(), UTC, start, end)


def test_leap_year_and_future_sources_do_not_assume_current_year():
    tables = (
        table(row("2028-02-29", fajr_begin=["06:00"]), source="annual-2028"),
        table(row("2027-01-01", fajr_begin=["05:01"]), source="annual-2027"),
        table(row("2026-12-31", isha_jamaat=["20:00"])),
    )
    leap = query(tables, "2028-01-01T00:00Z", "2029-01-01T00:00Z")
    assert len(leap) == 1
    assert leap[0].start.date() == date(2028, 2, 29)
    across = query(tables, "2026-12-31T19:00Z", "2027-01-01T06:00Z")
    assert [event.summary for event in across] == ["Isha Jamaat", "Fajr beginning"]


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        ("2026-03-29", "2026-03-29T04:00:00+00:00"),
        ("2026-10-25", "2026-10-25T05:00:00+00:00"),
    ],
)
def test_timestamp_instants_follow_mosque_dst(day, expected):
    tables = (table(row(day, fajr_begin=["05:00"])),)
    events = query(tables, day + "T00:00Z", day + "T23:00Z", zone=LONDON)
    assert events[0].start.astimezone(timezone.utc).isoformat() == expected
    assert events[0].end.astimezone(timezone.utc) - events[0].start.astimezone(
        timezone.utc
    ) == timedelta(minutes=1)


@pytest.mark.parametrize("day", ["2026-03-29", "2026-10-25"])
def test_nonexistent_or_ambiguous_dst_events_fail_without_guessing(day):
    tables = (table(row(day, fajr_begin=["01:30"])),)
    with pytest.raises(HomeAssistantError, match="unresolved timetable data"):
        query(tables, day + "T00:00Z", day + "T23:00Z", zone=LONDON)


def test_conflicting_sources_fail_only_when_requested_and_do_not_choose_a_source():
    tables = (
        table(
            row("2026-10-23", fajr_begin=["05:00"]),
            row("2026-10-25", fajr_begin=["05:00"]),
        ),
        table(row("2026-10-25", fajr_begin=["06:00"]), source="other-annual"),
    )
    assert len(query(tables, "2026-10-23T00:00Z", "2026-10-24T00:00Z")) == 1
    with pytest.raises(HomeAssistantError, match="unresolved timetable data"):
        query(tables, "2026-10-25T00:00Z", "2026-10-26T00:00Z")


def test_next_event_keeps_exact_start_then_skips_unresolvable_future_date():
    tables = (
        table(
            row("2026-10-23", fajr_begin=["05:00"]),
            row("2026-10-25", fajr_begin=["01:30"]),
            row("2026-10-26", fajr_begin=["06:00"]),
        ),
    )
    event = _next_event(
        "example", tables, RamadanSettings(), LONDON, instant("2026-10-23T04:00Z")
    )
    assert event.start == instant("2026-10-23T04:00Z")
    later = _next_event(
        "example", tables, RamadanSettings(), LONDON, instant("2026-10-23T04:01Z")
    )
    assert later.start == instant("2026-10-26T06:00Z")


def test_ramadan_uses_exact_confirmed_dates_and_effective_fallback_without_inventing_taraweeh():
    tables = (
        table(
            row(
                "2026-03-10",
                fajr_begin=["06:00"],
                maghrib_begin=["18:00"],
                sehri_ends=["05:30"],
            )
        ),
        table(
            row("2026-03-10", fajr_begin=["05:50"], iftar=["18:05"]),
            source="ramadan-2026",
            kind="ramadan",
        ),
    )
    inactive = query(tables, "2026-03-10T00:00Z", "2026-03-11T00:00Z")
    assert [event.summary for event in inactive] == [
        "Fajr beginning",
        "Maghrib beginning",
    ]
    settings = RamadanSettings(
        confirmed_start=date(2026, 3, 10), confirmed_end=date(2026, 3, 10)
    )
    active = query(tables, "2026-03-10T00:00Z", "2026-03-11T00:00Z", settings=settings)
    by_name = {event.summary: event for event in active}
    assert by_name["Fajr beginning"].start.hour == 5
    assert by_name["Iftar"].start.minute == 5
    assert "Sehri ends" in by_name
    assert "Taraweeh" not in by_name
    fallback = query(
        tables[:1], "2026-03-10T00:00Z", "2026-03-11T00:00Z", settings=settings
    )
    assert (
        next(event for event in fallback if event.summary == "Iftar").start.hour == 18
    )
    assert (
        "effective Maghrib beginning"
        in next(event for event in fallback if event.summary == "Iftar").description
    )
    assert "Published event: iftar" in by_name["Iftar"].description
    assert tables[0].days[0].times[PrayerField.FAJR_BEGIN] == (time(6),)


def test_calendar_uids_do_not_depend_on_query_range_but_distinguish_mosques():
    tables = (table(row("2026-10-23", fajr_begin=["05:00"])),)
    first = query(tables, "2026-10-23T00:00Z", "2026-10-24T00:00Z")[0]
    expanded = query(tables, "2026-10-01T00:00Z", "2026-11-01T00:00Z")[0]
    second = query(tables, "2026-10-23T00:00Z", "2026-10-24T00:00Z", mosque="other")[0]
    assert first.uid == expanded.uid
    assert first.uid != second.uid


def test_jumuah_uid_uses_published_time_rather_than_display_slot_number():
    initial = query(
        (table(row("2026-10-23", jumuah=["13:30"])),),
        "2026-10-23T00:00Z",
        "2026-10-24T00:00Z",
    )
    expanded = query(
        (table(row("2026-10-23", jumuah=["12:30", "13:30"])),),
        "2026-10-23T00:00Z",
        "2026-10-24T00:00Z",
    )
    assert initial[0].uid == expanded[1].uid


async def test_empty_calendar_is_read_only_device_linked_and_survives_reload(
    hass, entry
):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entity_id = calendar_id(hass)
    state = hass.states.get(entity_id)
    assert state.state == "off"
    assert state.attributes["supported_features"] == 0
    registry = er.async_get(hass)
    assert (
        registry.async_get(entity_id).device_id
        == registry.async_get("sensor.example_mosque_fajr_beginning").device_id
    )
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert calendar_id(hass) == entity_id
    assert calendar_entity(hass).event is None


async def test_authenticated_calendar_api_and_reload_preserve_event_ids(
    hass, entry, hass_client, hass_admin_user, freezer
):
    freezer.move_to("2026-10-23T04:00:00Z")
    await hass.config.async_set_time_zone("UTC")
    await approve_tables(
        hass,
        entry,
        (table(row("2026-10-23", fajr_begin=["06:00"], jumuah=["13:00", "14:00"])),),
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entity_id = calendar_id(hass)
    # The default client token was issued by its fixture before the clock moved.
    # Issue this authenticated request's token at the same frozen time as HA.
    refresh_token = await hass.auth.async_create_refresh_token(
        hass_admin_user, client_id="https://example.com"
    )
    client = await hass_client(hass.auth.async_create_access_token(refresh_token))
    response = await client.get(
        f"/api/calendars/{entity_id}?start=2026-10-23T00:00:00Z&end=2026-10-24T00:00:00Z"
    )
    assert response.status == 200
    events = await response.json()
    assert len(events) == 3
    # HA serializes calendar API times in its own timezone, independently of the
    # mosque's London wall-clock publication. Both represent the same instant.
    assert events[0]["start"]["dateTime"] == "2026-10-23T05:00:00+00:00"
    assert instant(events[0]["start"]["dateTime"]) == calendar_entity(hass).event.start
    assert calendar_entity(hass).event.start.isoformat() == "2026-10-23T06:00:00+01:00"
    assert events[0]["end"]["dateTime"] == "2026-10-23T05:01:00+00:00"
    uids = [event["uid"] for event in events]
    hass.config.language = "ar"
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    response = await client.get(
        f"/api/calendars/{entity_id}?start=2026-10-23T00:00:00Z&end=2026-10-24T00:00:00Z"
    )
    assert [event["uid"] for event in await response.json()] == uids


async def test_future_approval_updates_next_event_even_beyond_missing_coverage(
    hass, entry, freezer
):
    freezer.move_to("2026-10-21T12:00:00Z")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert calendar_entity(hass).event is None
    coordinator = entry.runtime_data
    proposal = CsvParser().parse(
        b"Date,Fajr Begin\n2027-01-01,06:00\n",
        timetable_id="annual-2027",
        kind="annual",
        year=2027,
        date_column="Date",
        columns={"Fajr Begin": "fajr_begin"},
    )
    stage = await coordinator.storage.async_stage(proposal)
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert calendar_entity(hass).event is None
    await coordinator.storage.async_approve(stage)
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert hass.states.get(calendar_id(hass)).attributes["message"] == "Fajr beginning"
    assert calendar_entity(hass).event.start == instant("2027-01-01T06:00Z")
    result = await calendar_entity(hass).async_get_events(
        hass, instant("2027-01-01T00:00Z"), instant("2027-01-02T00:00Z")
    )
    assert len(result) == 1


async def test_calendar_advances_at_sunrise_without_sensor_event_changes(
    hass, entry, freezer
):
    freezer.move_to("2026-10-23T05:45:00Z")
    await approve_tables(
        hass,
        entry,
        (table(row("2026-10-23", sunrise=["07:00"], dhuhr_begin=["12:00"])),),
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entity_id = calendar_id(hass)
    assert hass.states.get(entity_id).attributes["message"] == "Sunrise"
    before = entry.runtime_data.data
    freezer.move_to("2026-10-23T06:00:00Z")
    async_fire_time_changed(hass, instant("2026-10-23T06:00:00Z"))
    await hass.async_block_till_done()
    assert entry.runtime_data.data == before
    state = hass.states.get(entity_id)
    assert state.state == "on"  # Presentation interval, not prayer duration.
    assert state.attributes["message"] == "Sunrise"
    assert calendar_entity(hass).event.start == instant("2026-10-23T06:00Z")
    freezer.move_to("2026-10-23T06:01:00Z")
    async_fire_time_changed(hass, instant("2026-10-23T06:01:00Z"))
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "off"
    assert calendar_entity(hass).event.start == instant("2026-10-23T11:00Z")


async def test_pending_replacement_never_changes_calendar_until_approved(
    hass, entry, freezer
):
    freezer.move_to("2026-10-23T03:00:00Z")
    approved = (table(row("2026-10-23", fajr_begin=["06:00"])),)
    await approve_tables(hass, entry, approved)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    entity = calendar_entity(hass)
    before = entity.event
    proposal = CsvParser().parse(
        b"Date,Fajr Begin\n2026-10-23,06:15\n",
        timetable_id="annual-2026",
        kind="annual",
        year=2026,
        date_column="Date",
        columns={"Fajr Begin": "fajr_begin"},
    )
    stage = await entry.runtime_data.storage.async_stage(proposal)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert entity.event == before
    await entry.runtime_data.storage.async_reject(stage)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert entity.event == before
    stage = await entry.runtime_data.storage.async_stage(proposal)
    await entry.runtime_data.storage.async_approve(stage)
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert entity.event.start.minute == 15
    assert entity.event.uid != before.uid


async def test_calendar_trigger_offset_before_local_midnight_uses_next_date(
    hass, entry, freezer
):
    # Start within HA's 15-minute calendar-trigger polling window, so the offset
    # timer is already installed when its exact boundary is reached.
    freezer.move_to("2026-10-23T22:45:00Z")  # 23:45 in London.
    await approve_tables(hass, entry, (table(row("2026-10-24", fajr_begin=["00:05"])),))
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    events = async_capture_events(hass, "calendar_reminder")
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": [
                {
                    "alias": "Calendar before next local day",
                    "triggers": [
                        {
                            "trigger": "calendar",
                            "entity_id": calendar_id(hass),
                            "event": "start",
                            "offset": "-00:10:00",
                        }
                    ],
                    "actions": [
                        {
                            "event": "calendar_reminder",
                            "event_data": {
                                "summary": "{{ trigger.calendar_event.summary }}",
                                "phase": "start",
                            },
                        }
                    ],
                },
                {
                    "alias": "Calendar presentation ends",
                    "triggers": [
                        {
                            "trigger": "calendar",
                            "entity_id": calendar_id(hass),
                            "event": "end",
                        }
                    ],
                    "actions": [
                        {
                            "event": "calendar_reminder",
                            "event_data": {
                                "summary": "{{ trigger.calendar_event.summary }}",
                                "phase": "end",
                            },
                        }
                    ],
                },
            ]
        },
    )
    await hass.async_start()
    await hass.async_block_till_done()
    freezer.move_to("2026-10-23T22:55:00Z")
    async_fire_time_changed(hass, instant("2026-10-23T22:55:00Z"))
    await hass.async_block_till_done()
    assert len(events) == 1
    assert events[0].data["summary"] == "Fajr beginning"
    assert events[0].data["phase"] == "start"
    freezer.tick(1)
    async_fire_time_changed(hass, instant("2026-10-23T22:55:01Z"))
    await hass.async_block_till_done()
    assert len(events) == 1
    freezer.move_to("2026-10-23T23:05:00Z")
    async_fire_time_changed(hass, instant("2026-10-23T23:05:00Z"))
    await hass.async_block_till_done()
    assert hass.states.get(calendar_id(hass)).state == "on"
    freezer.move_to("2026-10-23T23:06:00Z")
    async_fire_time_changed(hass, instant("2026-10-23T23:06:00Z"))
    await hass.async_block_till_done()
    assert len(events) == 2
    assert events[1].data == {"summary": "Fajr beginning", "phase": "end"}
    assert hass.states.get(calendar_id(hass)).state == "off"

    automation_ids = [state.entity_id for state in hass.states.async_all("automation")]
    await hass.services.async_call(
        "automation", "turn_off", {"entity_id": automation_ids}, blocking=True
    )
    await hass.async_block_till_done()
    assert all(
        hass.states.get(entity_id).state == "off" for entity_id in automation_ids
    )


async def test_calendars_keep_mosques_isolated_and_removal_preserves_other(
    hass, entry, freezer
):
    freezer.move_to("2026-10-23T03:00:00Z")
    await approve_tables(hass, entry, (table(row("2026-10-23", fajr_begin=["06:00"])),))
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    other = MockConfigEntry(
        domain=DOMAIN,
        title="Other Mosque",
        unique_id="other",
        data={"name": "Other Mosque", "mosque_id": "other", "time_zone": "UTC"},
    )
    other.add_to_hass(hass)
    await approve_tables(
        hass, other, (table(row("2026-10-23", fajr_begin=["07:00"])),), UTC
    )
    assert await hass.config_entries.async_setup(other.entry_id)
    await hass.async_block_till_done()
    first = calendar_entity(hass).event
    second = calendar_entity(hass, "other").event
    assert first.start != second.start
    assert first.uid != second.uid
    second_id = calendar_id(hass, "other")
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(second_id) is not None
    assert calendar_entity(hass, "other").event == second
