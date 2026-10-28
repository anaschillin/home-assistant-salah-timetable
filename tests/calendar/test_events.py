"""Behavioral event-boundary matrix using explicit published calendar rows."""

from dataclasses import FrozenInstanceError
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from custom_components.salah_timetable.domain.events import calculate_events
from custom_components.salah_timetable.domain.model import DailyPrayers, PrayerField

ZONE = ZoneInfo("Europe/London")
DAY = date(2026, 10, 21)
BEGIN = {
    "fajr": "05:00",
    "dhuhr": "12:00",
    "asr": "15:00",
    "maghrib": "18:00",
    "isha": "20:00",
}
JAMAAT = {
    "fajr": "05:30",
    "dhuhr": "12:30",
    "asr": "15:30",
    "maghrib": "18:05",
    "isha": "20:30",
}
ORDER = tuple(BEGIN)


def row(day=DAY, *, overrides=None, omit=()):
    values = {
        **{
            f"{prayer}_begin": (time.fromisoformat(value),)
            for prayer, value in BEGIN.items()
        },
        **{
            f"{prayer}_jamaat": (time.fromisoformat(value),)
            for prayer, value in JAMAAT.items()
        },
    }
    values.update({"sehri_ends": (time(4, 55),), "iftar": (time(18, 3),)})
    values.update(overrides or {})
    for field in omit:
        values.pop(field, None)
    return DailyPrayers(day, values, {})


def instant(value, day=DAY, zone=ZONE):
    return datetime.combine(day, time.fromisoformat(value), zone)


def engine(now, rows=None, zone=ZONE):
    if rows is None:
        rows = {
            day: row(day)
            for day in (DAY - timedelta(days=1), DAY, DAY + timedelta(days=1))
        }
    return calculate_events(now, zone, rows.get)


@pytest.mark.parametrize("prayer", ORDER)
@pytest.mark.parametrize("position", ["before", "begin", "between", "jamaat", "after"])
def test_context_and_independent_next_events(prayer, position):
    beginning = instant(BEGIN[prayer])
    congregation = instant(JAMAAT[prayer])
    now = {
        "before": beginning - timedelta(seconds=1),
        "begin": beginning,
        "between": beginning + timedelta(seconds=1),
        "jamaat": congregation,
        "after": congregation + timedelta(seconds=1),
    }[position]
    result = engine(now)
    index = ORDER.index(prayer)
    if position in {"before", "begin", "between"}:
        assert result.next_jamaat.field == PrayerField(f"{prayer}_jamaat")
        assert result.next_jamaat.timestamp == congregation
    elif prayer != "isha":
        assert result.next_jamaat.field == PrayerField(f"{ORDER[index + 1]}_jamaat")
    else:
        assert result.next_jamaat.timestamp.date() == DAY + timedelta(days=1)
    if position == "before":
        assert result.next_salah.field == PrayerField(f"{prayer}_begin")
    elif prayer == "isha":
        assert result.next_salah.field == PrayerField.FAJR_BEGIN
        assert result.next_salah.timestamp.date() == DAY + timedelta(days=1)
    else:
        assert result.next_salah.field == PrayerField(f"{ORDER[index + 1]}_begin")
    if position in {"begin", "between"}:
        assert result.context_mode == "upcoming"
        assert result.context_jamaat.timestamp == congregation
    else:
        assert result.context_mode == "previous"
        assert result.context_jamaat == result.previous_jamaat
        expected_prayer = prayer if position != "before" else ORDER[index - 1]
        assert result.context_jamaat.prayer == expected_prayer
    if position == "jamaat":
        assert result.previous_jamaat.timestamp == now
        assert result.context_jamaat.timestamp == now


def test_after_isha_uses_actual_tomorrow_fajr_not_today():
    tomorrow = DAY + timedelta(days=1)
    rows = {
        DAY: row(),
        tomorrow: row(
            tomorrow,
            overrides={"fajr_begin": (time(5, 17),), "fajr_jamaat": (time(5, 49),)},
        ),
    }
    result = engine(instant("23:59"), rows)
    assert result.next_salah.timestamp == instant("05:17", tomorrow)
    assert result.next_jamaat.timestamp == instant("05:49", tomorrow)
    assert result.previous_jamaat.timestamp == instant("20:30")
    assert result.context_mode == "previous"


def test_missing_tomorrow_does_not_repeat_today_or_scan_future():
    consulted = []
    rows = {DAY: row(), DAY + timedelta(days=2): row(DAY + timedelta(days=2))}

    def lookup(day):
        consulted.append(day)
        return rows.get(day)

    result = calculate_events(instant("23:59"), ZONE, lookup)
    assert result.next_salah is None
    assert result.next_jamaat is None
    assert result.next_sehri is None
    assert result.next_iftar is None
    assert set(consulted) == {DAY - timedelta(days=1), DAY, DAY + timedelta(days=1)}


def test_no_data_is_explicitly_unavailable():
    result = engine(instant("09:00"), {})
    assert result.context_mode == "unavailable"
    assert all(
        value is None
        for key, value in result.as_dict().items()
        if key != "context_mode"
    )


def test_missing_beginning_does_not_invent_upcoming_context():
    rows = {DAY: row(omit=("fajr_begin",))}
    result = engine(instant("05:15"), rows)
    assert result.next_jamaat.prayer == "fajr"
    assert result.context_mode == "unavailable"
    assert result.next_salah.prayer == "dhuhr"


def test_missing_jamaat_still_has_independent_next_beginning():
    result = engine(instant("05:10"), {DAY: row(omit=("fajr_jamaat",))})
    assert result.next_salah.prayer == "dhuhr"
    assert result.next_jamaat.prayer == "dhuhr"
    assert result.context_mode == "unavailable"


def test_previous_congregation_from_actual_yesterday():
    yesterday = DAY - timedelta(days=1)
    result = engine(
        instant("03:00"),
        {
            yesterday: row(yesterday, overrides={"isha_jamaat": (time(21, 7),)}),
            DAY: row(),
        },
    )
    assert result.previous_jamaat.timestamp == instant("21:07", yesterday)
    assert result.context_jamaat == result.previous_jamaat
    assert result.next_salah.timestamp == instant("05:00")


@pytest.mark.parametrize(
    ("current", "tomorrow"),
    [
        (date(2026, 12, 31), date(2027, 1, 1)),
        (date(2028, 2, 28), date(2028, 2, 29)),
        (date(2028, 2, 29), date(2028, 3, 1)),
    ],
)
def test_year_and_leap_boundaries(current, tomorrow):
    result = engine(
        instant("21:00", current),
        {
            current: row(current),
            tomorrow: row(tomorrow, overrides={"fajr_begin": (time(5, 12),)}),
        },
    )
    assert result.next_salah.timestamp == instant("05:12", tomorrow)


def test_multiple_friday_congregations_follow_dhuhr_beginning():
    friday = date(2026, 10, 23)
    rows = {
        friday: row(
            friday,
            overrides={
                "jumuah": (time(12, 35), time(14)),
            },
            omit=("dhuhr_jamaat",),
        )
    }
    before = engine(instant("11:59", friday), rows)
    assert before.context_mode == "previous"
    for value in ("12:00", "12:20", "12:35", "13:30"):
        result = engine(instant(value, friday), rows)
        assert result.context_mode == "upcoming"
        assert result.context_jamaat.prayer == "jumuah"
    first_exact = engine(instant("12:35", friday), rows)
    assert first_exact.previous_jamaat.timestamp == instant("12:35", friday)
    assert first_exact.next_jamaat.timestamp == instant("14:00", friday)
    second_exact = engine(instant("14:00", friday), rows)
    assert second_exact.context_mode == "previous"
    assert second_exact.context_jamaat.timestamp == instant("14:00", friday)


def test_late_jumuah_cannot_displace_current_asr_context():
    friday = date(2026, 10, 23)
    rows = {
        friday: row(
            friday,
            overrides={
                "jumuah": (time(12, 35), time(15, 15)),
            },
            omit=("dhuhr_jamaat",),
        )
    }
    result = engine(instant("15:00", friday), rows)
    assert result.next_jamaat.prayer == "jumuah"
    assert result.context_jamaat.prayer == "asr"
    assert result.context_jamaat.timestamp == instant("15:30", friday)


@pytest.mark.parametrize(
    ("day", "offset"), [(date(2026, 3, 29), 1), (date(2026, 10, 25), 0)]
)
def test_dst_transition_orders_absolute_instants(day, offset):
    rows = {day: row(day)}
    result = engine(
        datetime(day.year, day.month, day.day, 1, 59, tzinfo=timezone.utc), rows
    )
    assert result.next_salah.timestamp == instant("05:00", day)
    assert result.next_salah.timestamp.utcoffset() == timedelta(hours=offset)
    expected = datetime(day.year, day.month, day.day, 5 - offset, tzinfo=timezone.utc)
    assert result.next_salah.timestamp.astimezone(timezone.utc) == expected


def test_absolute_input_can_use_different_timezone():
    result = engine(datetime(2026, 10, 21, 4, 0, tzinfo=timezone.utc))
    assert result.context_mode == "upcoming"
    assert result.next_salah.timestamp == instant("12:00")
    assert result.next_jamaat.timestamp == instant("05:30")


def test_local_date_comes_from_mosque_zone_not_input_date():
    zone = ZoneInfo("Pacific/Auckland")
    day = date(2027, 1, 1)
    rows = {day: row(day)}
    result = engine(datetime(2026, 12, 31, 15, 59, tzinfo=timezone.utc), rows, zone)
    assert result.next_salah.timestamp == instant("05:00", day, zone)


@pytest.mark.parametrize("value", [datetime(2026, 1, 1), None, date(2026, 1, 1)])
def test_naive_or_non_datetime_now_rejected(value):
    with pytest.raises(ValueError, match="timezone-aware"):
        calculate_events(value, ZONE, {}.get)


def test_mismatched_lookup_date_is_not_silently_used():
    with pytest.raises(ValueError, match="different calendar date"):
        engine(instant("12:00"), {DAY: row(DAY + timedelta(days=1))})


def test_invalid_dst_source_time_is_not_repaired():
    day = date(2026, 3, 29)
    with pytest.raises(ValueError, match="Ambiguous or nonexistent"):
        engine(
            instant("00:00", day),
            {day: row(day, overrides={"fajr_begin": (time(1, 30),)})},
        )


def test_sehri_and_iftar_are_independent_published_events():
    result = engine(instant("04:54"))
    assert result.next_sehri.timestamp == instant("04:55")
    assert result.next_iftar.timestamp == instant("18:03")
    assert engine(instant("04:55")).next_sehri.timestamp.date() == DAY + timedelta(
        days=1
    )
    assert engine(instant("18:03")).next_iftar.timestamp.date() == DAY + timedelta(
        days=1
    )
    missing = engine(instant("04:00"), {DAY: row(omit=("sehri_ends", "iftar"))})
    assert missing.next_sehri is None
    assert missing.next_iftar is None


def test_snapshots_are_immutable_and_serialize_absolute_values():
    result = engine(instant("05:10"))
    with pytest.raises(FrozenInstanceError):
        result.next_salah = None
    with pytest.raises(FrozenInstanceError):
        result.next_salah.prayer = "isha"
    serialized = result.as_dict()
    assert serialized["next_salah"] == {
        "timestamp": "2026-10-21T12:00:00+01:00",
        "field": "dhuhr_begin",
        "prayer": "dhuhr",
    }
    assert "seconds" not in str(serialized)


@pytest.mark.parametrize(
    ("day", "now"),
    [
        (date.min, datetime.min.replace(tzinfo=timezone.utc)),
        (date.max, datetime.max.replace(tzinfo=timezone.utc)),
    ],
)
def test_calendar_bounds_do_not_overflow(day, now):
    result = engine(now, {}, ZoneInfo("UTC"))
    assert result.context_mode == "unavailable"


def test_confirmed_ramadan_lookup_is_separate_from_prayer_lookup():
    normal = {DAY: row()}
    confirmed = {
        DAY: row(
            overrides={
                "sehri_ends": (time(4, 50),),
                "iftar": (time(18, 7),),
                "fajr_begin": (time(4, 40),),
            }
        )
    }
    result = calculate_events(
        instant("04:45"), ZONE, normal.get, ramadan_lookup=confirmed.get
    )
    assert result.next_sehri.timestamp == instant("04:50")
    assert result.next_iftar.timestamp == instant("18:07")
    assert result.next_salah.timestamp == instant("05:00")
    disabled = calculate_events(
        instant("04:45"), ZONE, normal.get, ramadan_lookup={}.get
    )
    assert disabled.next_sehri is None
    assert disabled.next_iftar is None
    assert disabled.next_salah == result.next_salah


def test_ramadan_only_rows_can_supply_countdowns_without_inventing_prayers():
    result = calculate_events(
        instant("04:45"), ZONE, {}.get, ramadan_lookup={DAY: row()}.get
    )
    assert result.next_salah is None
    assert result.next_jamaat is None
    assert result.next_sehri.timestamp == instant("04:55")
    assert result.next_iftar.timestamp == instant("18:03")


def test_bad_ramadan_lookup_date_rejected():
    with pytest.raises(ValueError, match="Ramadan lookup returned"):
        calculate_events(
            instant("04:45"),
            ZONE,
            {}.get,
            ramadan_lookup={DAY: row(DAY + timedelta(days=1))}.get,
        )


def test_unchanged_instants_have_equal_snapshots_without_per_second_data():
    assert engine(instant("05:10")) == engine(instant("05:11"))
