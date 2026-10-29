from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

import pytest

from custom_components.salah_timetable.model import (
    DailyPrayers,
    PrayerField,
    Timetable,
    normalize_field,
    parse_time,
)


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Zuhr Start", "dhuhr_begin"),
        ("Zohar Jamaat", "dhuhr_jamaat"),
        ("Asar Begin", "asr_begin"),
        ("Esha Jamaat", "isha_jamaat"),
        ("Jumu'ah", "jumuah"),
        ("Noon", "istewa"),
    ],
)
def test_normalization(label, expected):
    assert normalize_field(label) == expected


@pytest.mark.parametrize("label", ["Fajr", "Unknown", "Zuhr"])
def test_no_inferred_field(label):
    with pytest.raises(ValueError):
        normalize_field(label)


@pytest.mark.parametrize("value", ["24:00", "12:60", "7:00", "07:00 PM", '"', "", None])
def test_invalid_time(value):
    with pytest.raises(ValueError):
        parse_time(value)


def test_round_trip_and_immutable(timetable):
    restored = Timetable.from_dict(timetable.as_dict())
    assert restored == timetable
    with pytest.raises(TypeError):
        restored.days[0].original["Fajr Start"] = "06:00"
    assert PrayerField.ISHA_BEGIN not in restored.days[0].times


def test_leap_year():
    row = DailyPrayers.from_dict(
        {"date": "2028-02-29", "times": {"sunrise": ["06:30"]}, "original": {}}
    )
    assert row.day == date(2028, 2, 29)
    with pytest.raises(ValueError):
        DailyPrayers.from_dict({"date": "2027-02-29", "times": {}, "original": {}})


@pytest.mark.parametrize("day", [date(2026, 3, 29), date(2026, 10, 25)])
def test_reject_dst_gaps_and_folds(day):
    row = DailyPrayers(day, {PrayerField.FAJR_BEGIN: (time(1, 30),)}, {})
    with pytest.raises(ValueError, match="Ambiguous or nonexistent"):
        row.timestamps(PrayerField.FAJR_BEGIN, ZoneInfo("Europe/London"))


def test_timestamp_offset(timetable):
    assert (
        timetable.days[0]
        .timestamps(PrayerField.FAJR_BEGIN, ZoneInfo("Europe/London"))[0]
        .isoformat()
        == "2026-10-21T05:45:00+01:00"
    )


@pytest.mark.parametrize("times", [(), (time(12), time(13)), (time(12, 0, 1),)])
def test_invalid_single_prayer(times):
    with pytest.raises(ValueError):
        DailyPrayers(date(2026, 1, 1), {PrayerField.FAJR_BEGIN: times}, {})


def test_duplicate_dates(timetable):
    with pytest.raises(ValueError):
        Timetable("duplicate", "annual", (timetable.days[0], timetable.days[0]))


def test_date_subclasses_preserve_calendar_date_round_trip():
    class CalendarDate(date):
        pass

    row = DailyPrayers(CalendarDate(2026, 10, 24), {}, {})
    assert row.as_dict()["date"] == "2026-10-24"
    assert DailyPrayers.from_dict(row.as_dict()) == row


@pytest.mark.parametrize(
    "day",
    [datetime(2026, 10, 24, 12), datetime(2026, 10, 24, tzinfo=timezone.utc)],
)
def test_datetime_is_not_a_canonical_calendar_date(day):
    with pytest.raises(ValueError, match="calendar date"):
        DailyPrayers(day, {}, {})
