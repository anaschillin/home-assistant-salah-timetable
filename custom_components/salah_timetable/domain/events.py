"""Pure selection of published prayer events, with no inferred durations or times."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from zoneinfo import ZoneInfo

from .model import DailyPrayers, PrayerField

_BEGIN_FIELDS = (
    PrayerField.FAJR_BEGIN,
    PrayerField.DHUHR_BEGIN,
    PrayerField.ASR_BEGIN,
    PrayerField.MAGHRIB_BEGIN,
    PrayerField.ISHA_BEGIN,
)
_JAMAAT_FIELDS = (
    PrayerField.FAJR_JAMAAT,
    PrayerField.DHUHR_JAMAAT,
    PrayerField.JUMUAH,
    PrayerField.ASR_JAMAAT,
    PrayerField.MAGHRIB_JAMAAT,
    PrayerField.ISHA_JAMAAT,
)
_PRAYERS = {
    PrayerField.FAJR_BEGIN: "fajr",
    PrayerField.FAJR_JAMAAT: "fajr",
    PrayerField.DHUHR_BEGIN: "dhuhr",
    PrayerField.DHUHR_JAMAAT: "dhuhr",
    PrayerField.JUMUAH: "jumuah",
    PrayerField.ASR_BEGIN: "asr",
    PrayerField.ASR_JAMAAT: "asr",
    PrayerField.MAGHRIB_BEGIN: "maghrib",
    PrayerField.MAGHRIB_JAMAAT: "maghrib",
    PrayerField.ISHA_BEGIN: "isha",
    PrayerField.ISHA_JAMAAT: "isha",
    PrayerField.SEHRI_ENDS: "sehri",
    PrayerField.IFTAR: "iftar",
}


@dataclass(frozen=True)
class PrayerEvent:
    """A single scheduled instant, never a congregation start/end interval."""

    timestamp: datetime
    field: PrayerField
    prayer: str

    def as_dict(self) -> dict[str, str]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "field": self.field.value,
            "prayer": self.prayer,
        }


@dataclass(frozen=True)
class EventSnapshot:
    """Selected absolute events; a frontend can derive countdowns locally."""

    next_salah: PrayerEvent | None
    next_jamaat: PrayerEvent | None
    previous_jamaat: PrayerEvent | None
    context_jamaat: PrayerEvent | None
    context_mode: Literal["upcoming", "previous", "unavailable"]
    next_sehri: PrayerEvent | None
    next_iftar: PrayerEvent | None

    def as_dict(self) -> dict:
        return {
            "next_salah": self.next_salah.as_dict() if self.next_salah else None,
            "next_jamaat": self.next_jamaat.as_dict() if self.next_jamaat else None,
            "previous_jamaat": self.previous_jamaat.as_dict()
            if self.previous_jamaat
            else None,
            "context_jamaat": self.context_jamaat.as_dict()
            if self.context_jamaat
            else None,
            "context_mode": self.context_mode,
            "next_sehri": self.next_sehri.as_dict() if self.next_sehri else None,
            "next_iftar": self.next_iftar.as_dict() if self.next_iftar else None,
        }


def _utc(event: PrayerEvent) -> datetime:
    return event.timestamp.astimezone(timezone.utc)


def _family(event: PrayerEvent) -> str:
    return "dhuhr" if event.prayer == "jumuah" else event.prayer


def _day_offset(day: date, offset: int) -> date | None:
    try:
        return day + timedelta(days=offset)
    except OverflowError:
        return None


def calculate_events(
    now: datetime,
    zone: ZoneInfo,
    lookup: Callable[[date], DailyPrayers | None],
    *,
    ramadan_lookup: Callable[[date], DailyPrayers | None] | None = None,
) -> EventSnapshot:
    """Select the next published events from today and tomorrow's actual rows.

    Yesterday is consulted only for previous congregation context. Missing dates or
    fields yield no events and are never filled from another day's wall times. A
    missing tomorrow does not cause a search into later dates. Exact beginnings
    have begun; exact congregation times are previous events with zero elapsed.
    Comparisons use UTC so DST transitions do not create wall-clock ordering bugs.
    Optional ramadan_lookup limits countdown events to independently confirmed
    Ramadan rows; it never changes the ordinary prayer event lookup.
    """
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Event calculation requires a timezone-aware current time")
    now_utc = now.astimezone(timezone.utc)
    today = now.astimezone(zone).date()
    beginnings = []
    congregations = []
    sehri = []
    iftar = []
    for offset in (-1, 0, 1):
        day = _day_offset(today, offset)
        if day is None:
            continue
        row = lookup(day)
        if row is not None and row.day != day:
            raise ValueError("Timetable lookup returned a different calendar date")
        if row is not None:
            for field in (*_BEGIN_FIELDS, *_JAMAAT_FIELDS):
                target = beginnings if field in _BEGIN_FIELDS else congregations
                for timestamp in row.timestamps(field, zone):
                    target.append(PrayerEvent(timestamp, field, _PRAYERS[field]))
        if offset < 0:
            continue
        countdown_row = row if ramadan_lookup is None else ramadan_lookup(day)
        if countdown_row is None:
            continue
        if countdown_row.day != day:
            raise ValueError("Ramadan lookup returned a different calendar date")
        for field, target in (
            (PrayerField.SEHRI_ENDS, sehri),
            (PrayerField.IFTAR, iftar),
        ):
            for timestamp in countdown_row.timestamps(field, zone):
                target.append(PrayerEvent(timestamp, field, _PRAYERS[field]))
    for events in (beginnings, congregations, sehri, iftar):
        events.sort(key=_utc)

    def next_event(events: list[PrayerEvent]) -> PrayerEvent | None:
        return next((event for event in events if _utc(event) > now_utc), None)

    next_salah = next_event(beginnings)
    next_jamaat = next_event(congregations)
    previous_jamaat = next(
        (event for event in reversed(congregations) if _utc(event) <= now_utc), None
    )
    latest_begin = next(
        (event for event in reversed(beginnings) if _utc(event) <= now_utc), None
    )
    context_jamaat = None
    if latest_begin is not None:
        context_jamaat = next(
            (
                event
                for event in congregations
                if _utc(event) > now_utc
                and event.timestamp.date() == latest_begin.timestamp.date()
                and _family(event) == _family(latest_begin)
            ),
            None,
        )
    if context_jamaat is not None:
        mode = "upcoming"
    elif previous_jamaat is not None:
        context_jamaat, mode = previous_jamaat, "previous"
    else:
        mode = "unavailable"
    return EventSnapshot(
        next_salah,
        next_jamaat,
        previous_jamaat,
        context_jamaat,
        mode,
        next_event(sehri),
        next_event(iftar),
    )
