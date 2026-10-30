"""Check required published prayer fields independently of date coverage."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta

from ..const import CONF_COMPLETENESS_REQUIRED_FIELDS
from .coverage import index_sources_by_date
from .model import PrayerField, Timetable
from .ramadan import RamadanSettings, resolve_day

DEFAULT_REQUIRED_FIELDS = (
    PrayerField.FAJR_BEGIN,
    PrayerField.DHUHR_BEGIN,
    PrayerField.ASR_BEGIN,
    PrayerField.MAGHRIB_BEGIN,
    PrayerField.ISHA_BEGIN,
)
SELECTABLE_REQUIRED_FIELDS = (
    *DEFAULT_REQUIRED_FIELDS,
    PrayerField.FAJR_JAMAAT,
    PrayerField.DHUHR_JAMAAT,
    PrayerField.ASR_JAMAAT,
    PrayerField.MAGHRIB_JAMAAT,
    PrayerField.ISHA_JAMAAT,
    PrayerField.SUNRISE,
)
_SELECTABLE_VALUES = frozenset(field.value for field in SELECTABLE_REQUIRED_FIELDS)


def required_fields_from_options(options: Mapping) -> tuple[PrayerField, ...]:
    """Reject invalid field policies rather than silently changing their meaning."""
    fields = options.get(
        CONF_COMPLETENESS_REQUIRED_FIELDS,
        [field.value for field in DEFAULT_REQUIRED_FIELDS],
    )
    if (
        not isinstance(fields, (list, tuple))
        or not fields
        or len(fields) > len(SELECTABLE_REQUIRED_FIELDS)
        or any(
            not isinstance(value, str) or value not in _SELECTABLE_VALUES
            for value in fields
        )
        or len(set(fields)) != len(fields)
    ):
        raise ValueError("Choose unique supported fields for prayer completeness")
    return tuple(PrayerField(field) for field in fields)


@dataclass(frozen=True)
class CompletenessSnapshot:
    """Small, immutable summary with no full-year prayer data."""

    status: str
    required_fields: tuple[PrayerField, ...]
    missing_today: tuple[PrayerField, ...]
    missing_tomorrow: tuple[PrayerField, ...]
    complete_days_remaining: int
    first_incomplete_date: date | None
    unresolved_date: date | None = None

    def attributes(self) -> dict:
        return {
            "required_fields": [field.value for field in self.required_fields],
            "missing_today": [field.value for field in self.missing_today],
            "missing_tomorrow": [field.value for field in self.missing_tomorrow],
            "complete_days_remaining": self.complete_days_remaining,
            "first_incomplete_date": (
                self.first_incomplete_date.isoformat()
                if self.first_incomplete_date
                else None
            ),
            "unresolved_date": (
                self.unresolved_date.isoformat() if self.unresolved_date else None
            ),
        }


def calculate_completeness(
    today: date,
    timetables: tuple[Timetable, ...],
    settings: RamadanSettings,
    required_fields: tuple[PrayerField, ...] = DEFAULT_REQUIRED_FIELDS,
) -> CompletenessSnapshot:
    """Inspect only approved effective fields.

    Status describes today. The separate tomorrow and future fields report
    upcoming gaps. Future conflicts do not disable valid current prayer values.
    """
    if type(today) is not date:
        raise ValueError("Completeness requires a calendar date")
    if (
        not required_fields
        or len(set(required_fields)) != len(required_fields)
        or any(field not in SELECTABLE_REQUIRED_FIELDS for field in required_fields)
    ):
        raise ValueError("Choose unique supported fields for prayer completeness")
    if not timetables:
        return CompletenessSnapshot(
            "not_configured", required_fields, (), (), 0, None
        )

    indexed = index_sources_by_date(today, timetables)
    tomorrow = today + timedelta(days=1) if today < date.max else None
    resolved = {}
    unresolved = None

    def missing(day: date) -> tuple[tuple[PrayerField, ...], bool]:
        nonlocal unresolved
        if day in resolved:
            return resolved[day]
        try:
            row = resolve_day(day, indexed.get(day, ()), settings).row
        except ValueError:
            if tomorrow is None or day <= tomorrow:
                raise
            unresolved = day
            result = (required_fields, False)
        else:
            result = (
                tuple(
                    field
                    for field in required_fields
                    if row is None or field not in row.times
                ),
                row is not None,
            )
        resolved[day] = result
        return result

    missing_today, has_today = missing(today)
    missing_tomorrow = missing(tomorrow)[0] if tomorrow else ()
    if not has_today:
        status = "missing_today"
    elif missing_today:
        status = "partial"
    else:
        status = "complete"

    first_incomplete = today if missing_today else None
    remaining = 0
    if not missing_today:
        cursor = today
        while cursor < date.max:
            following = cursor + timedelta(days=1)
            if following not in indexed or missing(following)[0]:
                first_incomplete = following
                break
            remaining += 1
            cursor = following
    return CompletenessSnapshot(
        status,
        required_fields,
        missing_today,
        missing_tomorrow,
        remaining,
        first_incomplete,
        unresolved,
    )
