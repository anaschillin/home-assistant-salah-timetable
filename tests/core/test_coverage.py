"""Approved date coverage and its real HA diagnostic entity."""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.salah_timetable.const import DOMAIN
from custom_components.salah_timetable.domain.completeness import (
    DEFAULT_REQUIRED_FIELDS,
    calculate_completeness,
    required_fields_from_options,
)
from custom_components.salah_timetable.domain.coverage import calculate_coverage
from custom_components.salah_timetable.domain.model import (
    DailyPrayers,
    PrayerField,
    Timetable,
)
from custom_components.salah_timetable.domain.ramadan import RamadanSettings
from custom_components.salah_timetable.parsers.csv_parser import CsvParser
from custom_components.salah_timetable.persistence.storage import TimetableStorage

TODAY = date(2026, 10, 21)


def row(day):
    # Coverage promises published dates, not a complete set of prayer fields.
    return DailyPrayers(day, {PrayerField.SUNRISE: (time(7),)}, {})


def table(days, *, kind="annual", source_id="annual-2026"):
    return Timetable(source_id, kind, tuple(row(day) for day in days))


def days(count, first=TODAY):
    return [first + timedelta(days=offset) for offset in range(count)]


@pytest.mark.parametrize(
    ("tables", "status", "today", "tomorrow", "through", "remaining"),
    [
        ((), "not_configured", False, False, None, 0),
        ((table([TODAY - timedelta(days=1)]),), "missing_today", False, False, None, 0),
        ((table([TODAY + timedelta(days=1)]),), "missing_today", False, True, None, 0),
        ((table([TODAY]),), "missing_tomorrow", True, False, TODAY, 0),
        ((table(days(2)),), "expiring", True, True, TODAY + timedelta(days=1), 1),
        ((table(days(8)),), "expiring", True, True, TODAY + timedelta(days=7), 7),
        ((table(days(9)),), "covered", True, True, TODAY + timedelta(days=8), 8),
    ],
)
def test_coverage_status_boundaries(
    tables, status, today, tomorrow, through, remaining
):
    result = calculate_coverage(TODAY, tables, RamadanSettings())
    assert result.status == status
    assert result.attributes() == {
        "today_available": today,
        "tomorrow_available": tomorrow,
        "available_through": through.isoformat() if through else None,
        "days_remaining": remaining,
        "warning_days": 7,
        "unresolved_date": None,
    }


def test_a_later_publication_cannot_hide_a_gap():
    dates = days(3) + days(30, TODAY + timedelta(days=4))
    result = calculate_coverage(TODAY, (table(dates),), RamadanSettings())
    assert result.status == "expiring"
    assert result.available_through == TODAY + timedelta(days=2)
    assert result.days_remaining == 2


def test_consecutive_coverage_crosses_sources_and_calendar_years():
    start = date(2026, 12, 30)
    tables = (
        table(days(2, start)),
        table(days(10, date(2027, 1, 1)), source_id="annual-2027"),
    )
    before = [item.as_dict() for item in tables]
    result = calculate_coverage(start, tables, RamadanSettings())
    assert result.status == "covered"
    assert result.available_through == date(2027, 1, 10)
    assert result.days_remaining == 11
    assert [item.as_dict() for item in tables] == before


def test_ramadan_dates_extend_coverage_only_when_they_are_active_and_selected():
    tables = (
        table([TODAY]),
        table(days(3), kind="ramadan", source_id="ramadan-2026"),
    )
    for settings in (RamadanSettings(), RamadanSettings(mode="off")):
        result = calculate_coverage(TODAY, tables, settings)
        assert result.status == "missing_tomorrow"
    settings = RamadanSettings(
        confirmed_start=TODAY,
        confirmed_end=TODAY + timedelta(days=2),
        source_id="ramadan-2026",
    )
    result = calculate_coverage(TODAY, tables, settings)
    assert result.available_through == TODAY + timedelta(days=2)
    assert result.days_remaining == 2
    shifted = RamadanSettings(
        confirmed_start=TODAY,
        confirmed_end=TODAY + timedelta(days=2),
        date_adjustment=3,
    )
    assert calculate_coverage(TODAY, tables, shifted).status == "missing_tomorrow"
    selected_other = RamadanSettings(mode="on", source_id="another-source")
    assert (
        calculate_coverage(TODAY, tables, selected_other).status == "missing_tomorrow"
    )
    assert (
        calculate_coverage(TODAY, tables, RamadanSettings(mode="on")).days_remaining
        == 2
    )


def test_rows_without_any_published_fields_do_not_supply_coverage():
    empty = Timetable("annual-2026", "annual", (DailyPrayers(TODAY, {}, {}),))
    assert (
        calculate_coverage(TODAY, (empty,), RamadanSettings()).status == "missing_today"
    )


def test_calendar_end_does_not_overflow():
    result = calculate_coverage(date.max, (table([date.max]),), RamadanSettings())
    assert result.status == "missing_tomorrow"
    assert result.available_through == date.max
    assert result.days_remaining == 0


def coverage_state(hass, key="example"):
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{key}_coverage_status"
    )
    assert entity_id is not None
    result = hass.states.get(entity_id)
    assert result is not None
    return result


async def test_empty_setup_exposes_a_stable_diagnostic(hass, entry, freezer):
    freezer.move_to("2026-10-21T12:00:00+00:00")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    state = coverage_state(hass)
    assert state.state == "not_configured"
    assert state.attributes["today_available"] is False
    assert state.attributes["available_through"] is None
    registry_entry = er.async_get(hass).async_get(state.entity_id)
    assert registry_entry.entity_category.value == "diagnostic"
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert coverage_state(hass).entity_id == state.entity_id


async def test_pending_replacement_does_not_extend_approved_coverage(
    hass, entry, freezer
):
    freezer.move_to("2026-10-21T12:00:00+00:00")
    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    await storage.async_replace((table([TODAY]),))
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert coverage_state(hass).state == "missing_tomorrow"
    coordinator = entry.runtime_data
    proposal = CsvParser().parse(
        b"Date,Fajr Begin\n2026-10-21,06:00\n2026-10-22,06:01\n",
        timetable_id="annual-2026",
        kind="annual",
        year=2026,
        date_column="Date",
        columns={"Fajr Begin": "fajr_begin"},
    )
    stage_id = await coordinator.storage.async_stage(proposal)
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert coverage_state(hass).state == "missing_tomorrow"
    assert coverage_state(hass).attributes["available_through"] == "2026-10-21"
    await coordinator.storage.async_approve(stage_id)
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    result = coverage_state(hass)
    assert result.state == "expiring"
    assert result.attributes["days_remaining"] == 1
    assert result.attributes["available_through"] == "2026-10-22"
    assert coordinator.storage.timetables == (proposal.timetable,)
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert coverage_state(hass).attributes["available_through"] == "2026-10-22"


async def test_coverage_rolls_at_mosque_midnight_without_per_minute_state_writes(
    hass, populated, freezer
):
    freezer.move_to("2026-10-21T22:58:00+00:00")
    assert await hass.config_entries.async_setup(populated.entry_id)
    await hass.async_block_till_done()
    previous = coverage_state(hass)
    assert previous.state == "expiring"
    freezer.tick(60)
    await populated.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert coverage_state(hass) is previous
    freezer.move_to("2026-10-21T23:00:00+00:00")
    async_fire_time_changed(hass, datetime(2026, 10, 21, 23, tzinfo=timezone.utc))
    await hass.async_block_till_done()
    result = coverage_state(hass)
    assert result.state == "missing_tomorrow"
    assert result.attributes["today_available"] is True
    assert result.attributes["tomorrow_available"] is False
    assert result.attributes["available_through"] == "2026-10-22"
    assert result.attributes["days_remaining"] == 0


async def test_ramadan_options_reload_updates_coverage(hass, entry, freezer):
    freezer.move_to("2026-10-21T12:00:00+00:00")
    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    await storage.async_replace(
        (table(days(3), kind="ramadan", source_id="ramadan-2026"),)
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert coverage_state(hass).state == "missing_today"
    hass.config_entries.async_update_entry(entry, options={"ramadan_mode": "on"})
    await hass.async_block_till_done()
    assert coverage_state(hass).state == "expiring"
    assert coverage_state(hass).attributes["days_remaining"] == 2


def test_future_legacy_ramadan_conflict_stops_verified_coverage_until_selected():
    conflict_day = TODAY + timedelta(days=3)
    tables = (
        table(days(5)),
        table([conflict_day], kind="ramadan", source_id="legacy-first"),
        table([conflict_day], kind="ramadan", source_id="legacy-second"),
    )
    original = [item.as_dict() for item in tables]
    result = calculate_coverage(TODAY, tables, RamadanSettings(mode="on"))
    assert result.status == "expiring"
    assert result.today_available is True
    assert result.tomorrow_available is True
    assert result.available_through == TODAY + timedelta(days=2)
    assert result.days_remaining == 2
    assert result.unresolved_date == conflict_day
    assert result.attributes()["unresolved_date"] == conflict_day.isoformat()
    assert "legacy" not in str(result.attributes())
    selected = calculate_coverage(
        TODAY, tables, RamadanSettings(mode="on", source_id="legacy-first")
    )
    assert selected.available_through == TODAY + timedelta(days=4)
    assert selected.days_remaining == 4
    assert selected.unresolved_date is None
    assert selected.attributes()["unresolved_date"] is None
    assert [item.as_dict() for item in tables] == original


@pytest.mark.parametrize("offset", [0, 1])
def test_live_window_ramadan_conflicts_still_raise(offset):
    conflict_day = TODAY + timedelta(days=offset)
    tables = (
        table(days(5)),
        table([conflict_day], kind="ramadan", source_id="legacy-first"),
        table([conflict_day], kind="ramadan", source_id="legacy-second"),
    )
    with pytest.raises(ValueError, match="Select a Ramadan source"):
        calculate_coverage(TODAY, tables, RamadanSettings(mode="on"))


async def test_future_legacy_conflict_preserves_live_sensors_and_clears_on_selection(
    hass, entry, freezer
):
    freezer.move_to("2026-10-21T12:00:00+00:00")
    conflict_day = TODAY + timedelta(days=3)
    approved = (
        Timetable(
            "annual-2026",
            "annual",
            tuple(
                DailyPrayers(day, {PrayerField.FAJR_BEGIN: (time(5, 45),)}, {})
                for day in days(5)
            ),
        ),
        table([conflict_day], kind="ramadan", source_id="legacy-first"),
        table([conflict_day], kind="ramadan", source_id="legacy-second"),
    )
    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    await storage.async_replace(approved)
    hass.config_entries.async_update_entry(entry, options={"ramadan_mode": "on"})
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coverage = coverage_state(hass)
    assert coverage.state == "expiring"
    assert coverage.attributes["unresolved_date"] == conflict_day.isoformat()
    assert coverage.attributes["available_through"] == "2026-10-23"
    assert coverage.attributes["today_available"] is True
    assert coverage.attributes["tomorrow_available"] is True
    registry = er.async_get(hass)
    fajr = registry.async_get_entity_id("sensor", DOMAIN, "example_fajr_begin")
    next_salah = registry.async_get_entity_id("sensor", DOMAIN, "example_next_salah")
    assert hass.states.get(fajr).state == "2026-10-21T04:45:00+00:00"
    assert hass.states.get(next_salah).state == "2026-10-22T04:45:00+00:00"
    assert entry.runtime_data.storage.timetables == approved
    hass.config_entries.async_update_entry(
        entry,
        options={"ramadan_mode": "on", "ramadan_source_id": "legacy-first"},
    )
    await hass.async_block_till_done()
    selected = coverage_state(hass)
    assert selected.entity_id == coverage.entity_id
    assert selected.attributes["unresolved_date"] is None
    assert selected.attributes["available_through"] == "2026-10-25"
    assert selected.attributes["days_remaining"] == 4
    assert hass.states.get(fajr).state == "2026-10-21T04:45:00+00:00"
    assert hass.states.get(next_salah).state == "2026-10-22T04:45:00+00:00"
    assert entry.runtime_data.storage.timetables == approved


def complete_row(day):
    return DailyPrayers(
        day,
        {field: (time(6 + i),) for i, field in enumerate(DEFAULT_REQUIRED_FIELDS)},
        {},
    )


def completeness_state(hass, key="example"):
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{key}_completeness_status"
    )
    assert entity_id is not None
    result = hass.states.get(entity_id)
    assert result is not None
    return result


def test_prayer_completeness_remains_separate_from_date_coverage():
    approved = (table(days(3)),)
    date_coverage = calculate_coverage(TODAY, approved, RamadanSettings())
    report = calculate_completeness(TODAY, approved, RamadanSettings())
    assert date_coverage.days_remaining == 2
    assert report.status == "partial"
    assert report.missing_today == DEFAULT_REQUIRED_FIELDS
    assert report.attributes()["first_incomplete_date"] == TODAY.isoformat()
    assert report.complete_days_remaining == 0


def test_complete_today_and_missing_tomorrow_are_independent():
    report = calculate_completeness(
        TODAY,
        (Timetable("approved", "annual", (complete_row(TODAY),)),),
        RamadanSettings(),
    )
    assert report.status == "complete"
    assert report.missing_today == ()
    assert report.missing_tomorrow == DEFAULT_REQUIRED_FIELDS
    assert report.first_incomplete_date == TODAY + timedelta(days=1)


def test_complete_fields_cross_calendar_years_without_requiring_jamaat():
    start = date(2026, 12, 31)
    tables = (
        Timetable("year-2026", "annual", (complete_row(start),)),
        Timetable(
            "year-2027",
            "annual",
            (complete_row(start + timedelta(days=1)),),
        ),
    )
    result = calculate_completeness(start, tables, RamadanSettings())
    assert result.status == "complete"
    assert result.complete_days_remaining == 1
    assert result.first_incomplete_date == date(2027, 1, 2)
    assert not result.missing_tomorrow


def test_ramadan_completeness_uses_approved_effective_field_overrides():
    annual = Timetable(
        "annual",
        "annual",
        (
            DailyPrayers(
                TODAY,
                {
                    field: values
                    for field, values in complete_row(TODAY).times.items()
                    if field != PrayerField.ISHA_BEGIN
                },
                {},
            ),
        ),
    )
    override = Timetable(
        "ramadan",
        "ramadan",
        (DailyPrayers(TODAY, {PrayerField.ISHA_BEGIN: (time(20),)}, {}),),
    )
    assert (
        calculate_completeness(TODAY, (annual, override), RamadanSettings()).status
        == "partial"
    )
    assert (
        calculate_completeness(
            TODAY, (annual, override), RamadanSettings(mode="on")
        ).status
        == "complete"
    )


def test_future_completeness_conflict_is_reported_not_guessed():
    future = TODAY + timedelta(days=3)
    annual = Timetable("annual", "annual", tuple(complete_row(day) for day in days(5)))
    competing = tuple(
        Timetable(source_id, "ramadan", (row(future),))
        for source_id in ("first", "second")
    )
    result = calculate_completeness(
        TODAY, (annual, *competing), RamadanSettings(mode="on")
    )
    assert result.status == "complete"
    assert result.complete_days_remaining == 2
    assert result.first_incomplete_date == future
    assert result.unresolved_date == future
    with pytest.raises(ValueError, match="Select a Ramadan source"):
        calculate_completeness(
            future - timedelta(days=1),
            (annual, *competing),
            RamadanSettings(mode="on"),
        )


def test_required_fields_validation_and_no_approved_data():
    assert required_fields_from_options({}) == DEFAULT_REQUIRED_FIELDS
    assert required_fields_from_options(
        {"completeness_required_fields": ["fajr_begin", "sunrise"]}
    ) == (PrayerField.FAJR_BEGIN, PrayerField.SUNRISE)
    for invalid in (
        [],
        ["fajr_begin", "fajr_begin"],
        ["jumuah"],
        ["fajr_begin", 1],
    ):
        with pytest.raises(ValueError, match="unique supported"):
            required_fields_from_options({"completeness_required_fields": invalid})
    empty = calculate_completeness(TODAY, (), RamadanSettings())
    assert empty.status == "not_configured"
    assert empty.attributes()["first_incomplete_date"] is None


async def test_completeness_diagnostic_follows_per_mosque_policy_on_reload(
    hass, entry, freezer
):
    freezer.move_to("2026-10-21T12:00:00+00:00")
    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    await storage.async_replace(
        (
            Timetable(
                "approved",
                "annual",
                (DailyPrayers(TODAY, {PrayerField.FAJR_BEGIN: (time(6),)}, {}),),
            ),
        )
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    sensor = completeness_state(hass)
    assert sensor.state == "partial"
    assert sensor.attributes["missing_today"] == [
        field.value for field in DEFAULT_REQUIRED_FIELDS[1:]
    ]
    assert (
        er.async_get(hass).async_get(sensor.entity_id).entity_category.value
        == "diagnostic"
    )
    hass.config_entries.async_update_entry(
        entry, options={"completeness_required_fields": ["fajr_begin"]}
    )
    await hass.async_block_till_done()
    assert completeness_state(hass).state == "complete"
    assert completeness_state(hass).entity_id == sensor.entity_id
    assert coverage_state(hass).state == "missing_tomorrow"


@pytest.mark.parametrize("invalid_day", ["2026-10-21", datetime(2026, 10, 21)])
def test_completeness_rejects_non_date_inputs(invalid_day):
    with pytest.raises(ValueError, match="calendar date"):
        calculate_completeness(invalid_day, (), RamadanSettings())


@pytest.mark.parametrize(
    "required",
    [(), (PrayerField.FAJR_BEGIN, PrayerField.FAJR_BEGIN), (PrayerField.JUMUAH,)],
)
def test_completeness_rejects_invalid_required_field_sets(required):
    with pytest.raises(ValueError, match="unique supported"):
        calculate_completeness(TODAY, (), RamadanSettings(), required)


def test_completeness_at_maximum_supported_date_does_not_overflow():
    latest = date.max
    approved = Timetable("last-day", "annual", (complete_row(latest),))
    report = calculate_completeness(latest, (approved,), RamadanSettings())
    assert report.status == "complete"
    assert report.missing_tomorrow == ()
    assert report.complete_days_remaining == 0
    assert report.first_incomplete_date is None
