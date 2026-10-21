"""Validated, dependency-free timetable model; no inferred prayer times."""

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping
from zoneinfo import ZoneInfo


class PrayerField(StrEnum):
    FAJR_BEGIN = "fajr_begin"
    FAJR_JAMAAT = "fajr_jamaat"
    SUNRISE = "sunrise"
    SEHRI_ENDS = "sehri_ends"
    DHUHR_BEGIN = "dhuhr_begin"
    DHUHR_JAMAAT = "dhuhr_jamaat"
    JUMUAH = "jumuah"
    ASR_BEGIN = "asr_begin"
    ASR_JAMAAT = "asr_jamaat"
    MAGHRIB_BEGIN = "maghrib_begin"
    MAGHRIB_JAMAAT = "maghrib_jamaat"
    ISHA_BEGIN = "isha_begin"
    ISHA_JAMAAT = "isha_jamaat"
    ISTEWA = "istewa"
    IFTAR = "iftar"
    TARAWEEH = "taraweeh"


def normalize_field(value: str) -> PrayerField:
    """Normalize explicit field labels, never infer a beginning or Jamaat."""
    key = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    for alias, canonical in {
        "zuhr": "dhuhr",
        "zohar": "dhuhr",
        "asar": "asr",
        "esha": "isha",
        "start": "begin",
        "noon": "istewa",
    }.items():
        key = "_".join(canonical if part == alias else part for part in key.split("_"))
    if key in {"jumu_ah", "jummah"}:
        key = "jumuah"
    return PrayerField(key)


def parse_time(value: str) -> time:
    """Require unambiguous 24-hour HH:MM input."""
    if not isinstance(value, str) or not re.fullmatch(
        r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", value
    ):
        raise ValueError("Time must use HH:MM")
    return time.fromisoformat(value)


@dataclass(frozen=True)
class DailyPrayers:
    """Canonical values and untouched source labels/values for one date."""

    day: date
    times: Mapping[PrayerField, tuple[time, ...]]
    original: Mapping[str, str]

    def __post_init__(self) -> None:
        if type(self.day) is not date:
            raise ValueError("A calendar date is required")
        times = {}
        for field, values in self.times.items():
            field = PrayerField(field)
            values = tuple(values)
            if not values or (field != PrayerField.JUMUAH and len(values) != 1):
                raise ValueError("Only Jumu'ah supports multiple times")
            if any(
                type(value) is not time
                or value.tzinfo is not None
                or value.second
                or value.microsecond
                for value in values
            ):
                raise ValueError("Times must be local wall-clock minutes")
            if len(set(values)) != len(values) or tuple(sorted(values)) != values:
                raise ValueError("Times must be unique and ordered")
            times[field] = values
        if any(
            not isinstance(k, str) or not isinstance(v, str)
            for k, v in self.original.items()
        ):
            raise ValueError("Original values must be strings")
        object.__setattr__(self, "times", MappingProxyType(times))
        object.__setattr__(self, "original", MappingProxyType(dict(self.original)))

    def timestamps(self, field: PrayerField, zone: ZoneInfo) -> tuple[datetime, ...]:
        """Reject ambiguous/nonexistent DST times instead of guessing a fold."""
        result = []
        for value in self.times.get(field, ()):
            naive = datetime.combine(self.day, value)
            candidates = set()
            for fold in (0, 1):
                candidate = naive.replace(tzinfo=zone, fold=fold)
                utc = candidate.astimezone(timezone.utc)
                if utc.astimezone(zone).replace(tzinfo=None) == naive:
                    candidates.add(utc)
            if len(candidates) != 1:
                raise ValueError("Ambiguous or nonexistent local prayer time")
            result.append(candidates.pop().astimezone(zone))
        return tuple(result)

    def as_dict(self) -> dict:
        return {
            "date": self.day.isoformat(),
            "times": {
                field.value: [v.strftime("%H:%M") for v in values]
                for field, values in self.times.items()
            },
            "original": dict(self.original),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DailyPrayers":
        return cls(
            date.fromisoformat(data["date"]),
            {
                PrayerField(k): tuple(parse_time(v) for v in values)
                for k, values in data["times"].items()
            },
            data["original"],
        )


@dataclass(frozen=True)
class Timetable:
    """One annual or Ramadan source; selection/overrides arrive separately."""

    timetable_id: str
    kind: str
    days: tuple[DailyPrayers, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.timetable_id, str) or not self.timetable_id.strip():
            raise ValueError("Timetable ID is required")
        if self.kind not in {"annual", "ramadan"}:
            raise ValueError("Unsupported timetable kind")
        object.__setattr__(self, "days", tuple(self.days))
        if not self.days or len({row.day for row in self.days}) != len(self.days):
            raise ValueError("Timetable needs distinct dated rows")

    def as_dict(self) -> dict:
        return {
            "id": self.timetable_id,
            "kind": self.kind,
            "days": [row.as_dict() for row in self.days],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Timetable":
        return cls(
            data["id"],
            data["kind"],
            tuple(DailyPrayers.from_dict(row) for row in data["days"]),
        )
