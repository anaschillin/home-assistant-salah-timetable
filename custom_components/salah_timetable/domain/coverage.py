"""Date coverage of approved effective timetables, without inventing fields."""

from dataclasses import dataclass
from datetime import date, timedelta

from .model import Timetable
from .ramadan import RamadanSettings, resolve_day

WARNING_DAYS = 7


@dataclass(frozen=True)
class CoverageSnapshot:
    """Consecutive published dates from today; partial rows still count."""

    status: str
    today_available: bool
    tomorrow_available: bool
    available_through: date | None
    days_remaining: int
    warning_days: int = WARNING_DAYS
    unresolved_date: date | None = None

    def attributes(self) -> dict:
        return {
            "today_available": self.today_available,
            "tomorrow_available": self.tomorrow_available,
            "available_through": self.available_through.isoformat()
            if self.available_through
            else None,
            "days_remaining": self.days_remaining,
            "warning_days": self.warning_days,
            "unresolved_date": self.unresolved_date.isoformat()
            if self.unresolved_date
            else None,
        }


def calculate_coverage(
    today: date, timetables: tuple[Timetable, ...], settings: RamadanSettings
) -> CoverageSnapshot:
    """Use only approved tables and the same Ramadan resolution as prayer sensors.

    Index the dates once, then resolve one-row source views. Resolving each date
    against every complete annual table would repeatedly scan the same rows.
    Pending imports are deliberately absent from this interface.
    """
    if type(today) is not date:
        raise ValueError("Coverage requires a calendar date")
    if not timetables:
        return CoverageSnapshot("not_configured", False, False, None, 0)
    indexed: dict[date, list[Timetable]] = {}
    for table in timetables:
        for row in table.days:
            if row.day >= today:
                indexed.setdefault(row.day, []).append(
                    Timetable(table.timetable_id, table.kind, (row,))
                )

    tomorrow = today + timedelta(days=1) if today < date.max else None
    unresolved = None

    def available(day: date) -> bool:
        nonlocal unresolved
        try:
            row = resolve_day(day, tuple(indexed.get(day, ())), settings).row
        except ValueError:
            # Coverage looks further ahead than the live event window. A legacy
            # future source conflict must not disable valid current sensors, but
            # cannot count as verified coverage either. Live-window conflicts
            # remain errors rather than silently choosing a timetable.
            if tomorrow is None or day <= tomorrow:
                raise
            unresolved = day
            return False
        return row is not None and bool(row.times)

    today_available = available(today)
    tomorrow_available = tomorrow is not None and available(tomorrow)
    through = today if today_available else None
    if through is not None:
        while through < date.max:
            following = through + timedelta(days=1)
            if following not in indexed or not available(following):
                break
            through = following
    remaining = (through - today).days if through is not None else 0
    if not today_available:
        status = "missing_today"
    elif not tomorrow_available:
        status = "missing_tomorrow"
    elif remaining <= WARNING_DAYS:
        status = "expiring"
    else:
        status = "covered"
    return CoverageSnapshot(
        status,
        today_available,
        tomorrow_available,
        through,
        remaining,
        unresolved_date=unresolved,
    )
