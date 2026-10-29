"""Dashboard dates, Fajr end and published Friday khutbah remain distinct events."""

from datetime import date, time
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from custom_components.salah_timetable.domain.model import DailyPrayers, PrayerField
from custom_components.salah_timetable.domain.presentation import dashboard_attributes


def attributes(day, original, times=None, *, visible=True):
    row = DailyPrayers(
        day,
        times
        or {
            PrayerField.FAJR_BEGIN: (time(5, 20),),
            PrayerField.FAJR_JAMAAT: (time(6),),
            PrayerField.SUNRISE: (time(7, 30),),
            PrayerField.DHUHR_BEGIN: (time(12, 25),),
            PrayerField.JUMUAH: (time(13, 30),),
        },
        original,
    )
    effective = SimpleNamespace(
        row=row,
        annual_row=row,
        ramadan_active=False,
        taraweeh_text=None,
    )
    data = SimpleNamespace(
        day=day,
        effective=effective,
        days=(),
        events=SimpleNamespace(as_dict=lambda: {}),
    )
    return dashboard_attributes(
        data, ZoneInfo("Europe/London"), "Example Mosque", show_hijri_date=visible
    )


def test_fajr_end_is_published_sunrise_not_jamaat_or_computed():
    data = attributes(date(2026, 10, 23), {"Published Second Khutbah": "16:30"})
    fajr = next(row for row in data["prayers"] if row["key"] == "fajr")
    assert fajr["begin"].endswith("+01:00")
    assert fajr["end"] == "2026-10-23T07:30:00+01:00"
    assert fajr["jamaat"] == ["2026-10-23T06:00:00+01:00"]
    assert data["second_khutbah"] == "2026-10-23T16:30:00+01:00"
    dhuhr = next(row for row in data["prayers"] if row["key"] == "dhuhr")
    assert dhuhr["begin"] == "2026-10-23T12:25:00+01:00"
    assert dhuhr["jamaat"] == ["2026-10-23T13:30:00+01:00"]
    assert data["show_hijri_date"]


def test_mosque_preference_hides_only_hijri_and_omits_weekday_khutbah():
    data = attributes(
        date(2026, 10, 22),
        {"Published Second Khutbah": "16:30"},
        visible=False,
    )
    assert data["show_hijri_date"] is False
    assert data["second_khutbah"] is None
    assert data["prayers"][0]["end"] is not None


def test_fajr_end_unavailable_without_published_sunrise_and_malformed_notes_ignored():
    data = attributes(
        date(2026, 10, 23),
        {"Published Second Khutbah": "javascript:alert(1)"},
        times={PrayerField.FAJR_BEGIN: (time(5, 20),)},
    )
    assert data["prayers"][0]["end"] is None
    assert data["second_khutbah"] is None
