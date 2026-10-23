"""Explicit Ramadan confirmation and an immutable effective timetable layer.

Gregorian confirmation is independent of source coverage and printed Hijri dates.
The ``on`` mode is the user's explicit manual confirmation until switched off;
``auto`` applies only within the confirmed date window. Neither mode moves source
rows to other dates. A date adjustment changes the confirmed window only.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from .model import DailyPrayers, PrayerField, Timetable

TARAWEEH_AFTER_ISHA = "After Isha Jamaat"


def _optional_date(value: Any) -> date | None:
    """Read explicit ISO dates; blank values clear an existing confirmation."""
    if value is None or value == "":
        return None
    if type(value) is date:
        return value
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value
    ):
        raise ValueError("Ramadan dates must use YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as err:
        raise ValueError("Enter a valid Ramadan calendar date") from err


@dataclass(frozen=True)
class RamadanSettings:
    """User confirmation, never inferred from imported rows or lunar calculations."""

    mode: str = "auto"
    confirmed_start: date | None = None
    confirmed_end: date | None = None
    date_adjustment: int = 0
    source_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.mode, str) or self.mode not in {"auto", "on", "off"}:
            raise ValueError("Select automatic, manual on or off Ramadan mode")
        if type(self.date_adjustment) is not int or not -3 <= self.date_adjustment <= 3:
            raise ValueError(
                "Ramadan date adjustment must be a whole number from -3 to 3"
            )
        if (self.confirmed_start is None) != (self.confirmed_end is None):
            raise ValueError(
                "Confirm both Ramadan start and end dates, or leave both empty"
            )
        if self.confirmed_start is not None:
            if (
                type(self.confirmed_start) is not date
                or type(self.confirmed_end) is not date
            ):
                raise ValueError("Ramadan confirmation requires calendar dates")
            if not 0 <= (self.confirmed_end - self.confirmed_start).days < 35:
                raise ValueError("Ramadan confirmation must span 1 to 35 days")
            try:
                self.confirmed_start + timedelta(days=self.date_adjustment)
                self.confirmed_end + timedelta(days=self.date_adjustment)
            except OverflowError as err:
                raise ValueError(
                    "Adjusted Ramadan dates are outside the calendar"
                ) from err
        if self.source_id is not None and (
            not isinstance(self.source_id, str)
            or not self.source_id.strip()
            or len(self.source_id) > 128
        ):
            raise ValueError("Select a valid Ramadan timetable source")

    @classmethod
    def from_options(cls, options: Mapping[str, Any]) -> "RamadanSettings":
        """Read our option keys without changing unrelated mosque settings."""
        if not isinstance(options, Mapping):
            raise ValueError("Ramadan settings must be a mapping")
        adjustment = options.get("ramadan_adjustment", 0)
        # HA's numeric selector returns floats, including integral values. Do not
        # truncate fractions or accept booleans as date adjustments.
        if (
            isinstance(adjustment, bool)
            or not isinstance(adjustment, (int, float))
            or not -3 <= adjustment <= 3
            or not float(adjustment).is_integer()
        ):
            raise ValueError(
                "Ramadan date adjustment must be a whole number from -3 to 3"
            )
        source_id = options.get("ramadan_source_id")
        if source_id == "":
            source_id = None
        return cls(
            mode=options.get("ramadan_mode", "auto"),
            confirmed_start=_optional_date(options.get("ramadan_start")),
            confirmed_end=_optional_date(options.get("ramadan_end")),
            date_adjustment=int(adjustment),
            source_id=source_id,
        )

    def as_options(self) -> dict[str, Any]:
        """Include null optional values so saving can clear old settings."""
        return {
            "ramadan_mode": self.mode,
            "ramadan_start": self.confirmed_start.isoformat()
            if self.confirmed_start
            else None,
            "ramadan_end": self.confirmed_end.isoformat()
            if self.confirmed_end
            else None,
            "ramadan_adjustment": self.date_adjustment,
            "ramadan_source_id": self.source_id,
        }

    def is_active(self, day: date) -> bool:
        """Manual on is explicit confirmation; auto needs an inclusive window."""
        if type(day) is not date:
            raise ValueError("Ramadan resolution requires a calendar date")
        if self.mode == "off":
            return False
        if self.mode == "on":
            return True
        if self.confirmed_start is None:
            return False
        shift = timedelta(days=self.date_adjustment)
        return self.confirmed_start + shift <= day <= self.confirmed_end + shift


@dataclass(frozen=True)
class EffectiveTimetable:
    """Computed values plus untouched source records for provenance."""

    row: DailyPrayers | None
    ramadan_active: bool
    taraweeh_text: str | None
    source_id: str | None = None
    annual_row: DailyPrayers | None = None
    ramadan_row: DailyPrayers | None = None


def resolve_day(
    day: date,
    timetables: tuple[Timetable, ...],
    settings: RamadanSettings,
) -> EffectiveTimetable:
    """Merge only exact Gregorian dates and explicitly active Ramadan fields.

    A published Iftar time from either source takes precedence over the default.
    Missing Iftar can use the effective Maghrib beginning; no default timestamps
    are created for Taraweeh or for any other missing prayer field.
    """
    if type(day) is not date:
        raise ValueError("Timetable resolution requires a calendar date")
    if len({table.timetable_id for table in timetables}) != len(timetables):
        raise ValueError("Timetable source identities must be distinct")
    annual_rows = [
        row
        for table in timetables
        if table.kind == "annual"
        for row in table.days
        if row.day == day
    ]
    if len(annual_rows) > 1:
        raise ValueError("More than one annual timetable covers this date")
    annual = annual_rows[0] if annual_rows else None
    active = settings.is_active(day)
    if not active:
        return EffectiveTimetable(annual, False, None, annual_row=annual)
    candidates = [
        (table.timetable_id, row)
        for table in timetables
        if table.kind == "ramadan"
        and (settings.source_id is None or table.timetable_id == settings.source_id)
        for row in table.days
        if row.day == day
    ]
    if len(candidates) > 1:
        raise ValueError("Select a Ramadan source when more than one covers this date")
    source_id, override = candidates[0] if candidates else (None, None)
    if annual is None and override is None:
        return EffectiveTimetable(None, True, TARAWEEH_AFTER_ISHA)
    times = dict(annual.times) if annual else {}
    if override is not None:
        times.update(override.times)
    if PrayerField.IFTAR not in times and PrayerField.MAGHRIB_BEGIN in times:
        times[PrayerField.IFTAR] = times[PrayerField.MAGHRIB_BEGIN]
    original = annual.original if annual else override.original
    effective = DailyPrayers(day, times, original)
    return EffectiveTimetable(
        effective,
        True,
        None if PrayerField.TARAWEEH in times else TARAWEEH_AFTER_ISHA,
        source_id,
        annual,
        override,
    )
