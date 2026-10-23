"""Ramadan needs user confirmation; source values remain immutable."""

from dataclasses import FrozenInstanceError
from datetime import date, datetime, time

import pytest

from custom_components.salah_timetable.model import DailyPrayers, PrayerField, Timetable
from custom_components.salah_timetable.ramadan import (
    TARAWEEH_AFTER_ISHA,
    RamadanSettings,
    resolve_day,
)

DAY = date(2026, 2, 20)
START = date(2026, 2, 18)
END = date(2026, 3, 19)


def row(day=DAY, **values):
    return DailyPrayers(
        day,
        {
            PrayerField(field): (time.fromisoformat(value),)
            for field, value in values.items()
        },
        {field: value for field, value in values.items()},
    )


def annual(*rows, source_id="annual-2026"):
    return Timetable(source_id, "annual", tuple(rows))


def ramadan(*rows, source_id="ramadan-2026"):
    return Timetable(source_id, "ramadan", tuple(rows))


def confirmed(**overrides):
    options = {"confirmed_start": START, "confirmed_end": END}
    options.update(overrides)
    return RamadanSettings(**options)


def test_default_settings_are_unconfirmed():
    settings = RamadanSettings.from_options({"time_zone": "Europe/London"})
    assert settings == RamadanSettings()
    assert not settings.is_active(DAY)
    assert settings.as_options() == {
        "ramadan_mode": "auto",
        "ramadan_start": None,
        "ramadan_end": None,
        "ramadan_adjustment": 0,
        "ramadan_source_id": None,
    }


def test_options_round_trip_and_clear():
    settings = confirmed(date_adjustment=1, source_id="ramadan-2026")
    assert RamadanSettings.from_options(settings.as_options()) == settings
    assert (
        RamadanSettings.from_options(
            {
                "ramadan_start": "",
                "ramadan_end": "",
                "ramadan_source_id": "",
                "ramadan_adjustment": 0.0,
            }
        )
        == RamadanSettings()
    )
    with pytest.raises(FrozenInstanceError):
        settings.mode = "off"


@pytest.mark.parametrize(
    "values",
    [
        {"mode": "guess"},
        {"mode": []},
        {"mode": {}},
        {"confirmed_start": START},
        {"confirmed_end": END},
        {"confirmed_start": END, "confirmed_end": START},
        {"confirmed_start": date(2026, 1, 1), "confirmed_end": date(2026, 2, 5)},
        {"date_adjustment": True},
        {"date_adjustment": 0.5},
        {"date_adjustment": 4},
        {"date_adjustment": -4},
        {"source_id": ""},
        {"source_id": 5},
        {"source_id": "x" * 129},
        {"confirmed_start": datetime(2026, 2, 18), "confirmed_end": END},
        {"confirmed_start": date.min, "confirmed_end": date.min, "date_adjustment": -1},
        {"confirmed_start": date.max, "confirmed_end": date.max, "date_adjustment": 1},
    ],
)
def test_invalid_settings(values):
    with pytest.raises(ValueError):
        RamadanSettings(**values)


@pytest.mark.parametrize(
    "options",
    [
        {"ramadan_adjustment": 10**400},
        {"ramadan_adjustment": -(10**400)},
        {"ramadan_adjustment": float("nan")},
        {"ramadan_adjustment": float("inf")},
        {"ramadan_adjustment": -0.5},
        {"ramadan_adjustment": True},
        {"ramadan_adjustment": "1"},
        {"ramadan_start": "2026-02-30", "ramadan_end": "2026-03-19"},
        {"ramadan_start": "20260218", "ramadan_end": "2026-03-19"},
        {"ramadan_start": "18/02/2026", "ramadan_end": "2026-03-19"},
        {"ramadan_start": 20260218, "ramadan_end": "2026-03-19"},
        [],
        None,
    ],
)
def test_invalid_options(options):
    with pytest.raises(ValueError):
        RamadanSettings.from_options(options)


def test_confirmation_includes_both_boundaries():
    settings = confirmed()
    assert settings.is_active(START)
    assert settings.is_active(END)
    assert not settings.is_active(date(2026, 2, 17))
    assert not settings.is_active(date(2026, 3, 20))
    assert confirmed(mode="off").is_active(DAY) is False
    assert confirmed(mode="on").is_active(date(2026, 6, 1)) is True


@pytest.mark.parametrize("day", [datetime(2026, 2, 20), "2026-02-20", None])
def test_calendar_date_required(day):
    with pytest.raises(ValueError):
        RamadanSettings().is_active(day)
    with pytest.raises(ValueError):
        resolve_day(day, (), RamadanSettings())


def test_imported_ramadan_coverage_does_not_confirm_dates():
    base = row(fajr_begin="05:30", maghrib_begin="17:45")
    override = row(fajr_begin="05:00", sehri_ends="04:55")
    result = resolve_day(DAY, (annual(base), ramadan(override)), RamadanSettings())
    assert result.row is base
    assert not result.ramadan_active
    assert result.ramadan_row is None
    assert PrayerField.IFTAR not in result.row.times
    assert result.taraweeh_text is None


def test_confirmed_overlay_keeps_sources_and_defaults_separate():
    base = row(
        fajr_begin="05:30",
        maghrib_begin="17:45",
        maghrib_jamaat="17:48",
        isha_jamaat="20:00",
    )
    override = row(fajr_begin="05:00", sehri_ends="04:55")
    base_before, override_before = base.as_dict(), override.as_dict()
    result = resolve_day(DAY, (annual(base), ramadan(override)), confirmed())
    assert result.ramadan_active
    assert result.source_id == "ramadan-2026"
    assert result.row.times[PrayerField.FAJR_BEGIN] == (time(5),)
    assert result.row.times[PrayerField.SEHRI_ENDS] == (time(4, 55),)
    assert result.row.times[PrayerField.IFTAR] == (time(17, 45),)
    assert PrayerField.TARAWEEH not in result.row.times
    assert result.taraweeh_text == TARAWEEH_AFTER_ISHA
    assert result.annual_row is base
    assert result.ramadan_row is override
    assert result.row.original == base.original
    assert base.as_dict() == base_before
    assert override.as_dict() == override_before


@pytest.mark.parametrize("source", ["annual", "ramadan"])
def test_published_iftar_overrides_maghrib_default(source):
    base_values = {"maghrib_begin": "17:45", "maghrib_jamaat": "17:48"}
    override_values = {"fajr_begin": "05:00"}
    if source == "annual":
        base_values["iftar"] = "17:48"
    else:
        override_values["iftar"] = "17:50"
    result = resolve_day(
        DAY, (annual(row(**base_values)), ramadan(row(**override_values))), confirmed()
    )
    assert result.row.times[PrayerField.IFTAR] == (
        time(17, 48) if source == "annual" else time(17, 50),
    )


def test_explicit_ramadan_iftar_replaces_explicit_annual_iftar():
    result = resolve_day(
        DAY, (annual(row(iftar="17:48")), ramadan(row(iftar="17:50"))), confirmed()
    )
    assert result.row.times[PrayerField.IFTAR] == (time(17, 50),)


def test_effective_maghrib_supplies_default_not_jamaat():
    result = resolve_day(
        DAY,
        (
            annual(row(maghrib_begin="17:45", maghrib_jamaat="17:48")),
            ramadan(row(maghrib_begin="17:46")),
        ),
        confirmed(),
    )
    assert result.row.times[PrayerField.IFTAR] == (time(17, 46),)


def test_missing_maghrib_does_not_invent_iftar():
    result = resolve_day(DAY, (annual(row(maghrib_jamaat="17:48")),), confirmed())
    assert PrayerField.IFTAR not in result.row.times
    assert PrayerField.TARAWEEH not in result.row.times


def test_explicit_taraweeh_retains_real_timestamp():
    result = resolve_day(
        DAY,
        (annual(row(isha_jamaat="20:00")), ramadan(row(taraweeh="20:30"))),
        confirmed(),
    )
    assert result.row.times[PrayerField.TARAWEEH] == (time(20, 30),)
    assert result.taraweeh_text is None


def test_manual_on_can_use_annual_without_separate_ramadan_source():
    result = resolve_day(
        DAY,
        (annual(row(maghrib_begin="17:45")),),
        RamadanSettings(mode="on", source_id="missing"),
    )
    assert result.ramadan_active
    assert result.source_id is None
    assert result.ramadan_row is None
    assert result.row.times[PrayerField.IFTAR] == (time(17, 45),)
    assert result.taraweeh_text == TARAWEEH_AFTER_ISHA


def test_manual_on_uses_only_exact_date_without_remapping():
    different_date = row(date(2026, 2, 21), fajr_begin="05:00")
    result = resolve_day(
        DAY,
        (annual(row(fajr_begin="05:30")), ramadan(different_date)),
        confirmed(mode="on"),
    )
    assert result.row.times[PrayerField.FAJR_BEGIN] == (time(5, 30),)
    assert result.ramadan_row is None


def test_ramadan_source_without_annual_requires_confirmation():
    override = row(maghrib_begin="17:45")
    assert resolve_day(DAY, (ramadan(override),), RamadanSettings()).row is None
    result = resolve_day(DAY, (ramadan(override),), confirmed())
    assert result.row.times[PrayerField.IFTAR] == (time(17, 45),)
    assert result.row.original == override.original
    assert result.annual_row is None


def test_no_sources_preserves_active_status_without_event_times():
    result = resolve_day(DAY, (), confirmed())
    assert result.ramadan_active
    assert result.row is None
    assert result.taraweeh_text == TARAWEEH_AFTER_ISHA
    assert resolve_day(DAY, (), RamadanSettings()).row is None


def test_adjustment_moves_confirmation_only_not_source_dates():
    first = date(2026, 2, 18)
    source_row = row(first, fajr_begin="05:00")
    settings = RamadanSettings(
        confirmed_start=first, confirmed_end=first, date_adjustment=1
    )
    tables = (
        annual(
            row(first, fajr_begin="05:30"), row(date(2026, 2, 19), fajr_begin="05:29")
        ),
        ramadan(source_row),
    )
    original_day = resolve_day(first, tables, settings)
    adjusted_day = resolve_day(date(2026, 2, 19), tables, settings)
    assert not original_day.ramadan_active
    assert original_day.row.times[PrayerField.FAJR_BEGIN] == (time(5, 30),)
    assert adjusted_day.ramadan_active
    assert adjusted_day.ramadan_row is None
    assert adjusted_day.row.times[PrayerField.FAJR_BEGIN] == (time(5, 29),)


def test_explicit_source_resolves_overlap_and_missing_choice_does_not_guess():
    tables = (
        annual(row(fajr_begin="05:30")),
        ramadan(row(fajr_begin="05:00")),
        ramadan(row(fajr_begin="04:55"), source_id="other"),
    )
    with pytest.raises(ValueError, match="Select a Ramadan source"):
        resolve_day(DAY, tables, confirmed())
    assert resolve_day(DAY, tables, confirmed(source_id="other")).row.times[
        PrayerField.FAJR_BEGIN
    ] == (time(4, 55),)
    assert resolve_day(DAY, tables, confirmed(source_id="absent")).row.times[
        PrayerField.FAJR_BEGIN
    ] == (time(5, 30),)
    assert not resolve_day(DAY, tables, RamadanSettings()).ramadan_active


def test_duplicate_sources_and_overlapping_annual_rows_reject():
    source = annual(row(fajr_begin="05:30"))
    with pytest.raises(ValueError, match="identities"):
        resolve_day(DAY, (source, source), confirmed())
    with pytest.raises(ValueError, match="More than one annual"):
        resolve_day(
            DAY,
            (source, annual(row(fajr_begin="05:40"), source_id="another")),
            confirmed(),
        )


def test_calendar_year_boundary_and_leap_day():
    start, end = date(2027, 12, 20), date(2028, 1, 18)
    assert RamadanSettings(confirmed_start=start, confirmed_end=end).is_active(
        date(2028, 1, 1)
    )
    leap = date(2028, 2, 29)
    result = resolve_day(
        leap,
        (ramadan(row(leap, maghrib_begin="18:00"), source_id="ramadan-2028"),),
        RamadanSettings(confirmed_start=leap, confirmed_end=leap),
    )
    assert result.row.day == leap
    assert result.row.times[PrayerField.IFTAR] == (time(18),)
    assert result.source_id == "ramadan-2028"
