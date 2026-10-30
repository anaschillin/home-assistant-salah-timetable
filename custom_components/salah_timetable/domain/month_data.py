"""Bounded read-only views of approved effective prayer timetables."""

import calendar
import csv
import io
from datetime import date, timedelta

from .model import PrayerField, Timetable
from .ramadan import RamadanSettings, resolve_day


def effective_range(
    tables: tuple[Timetable, ...],
    settings: RamadanSettings,
    start: date,
    end: date,
) -> list[dict]:
    """Return a bounded Gregorian range without merging pending imports."""
    if type(start) is not date or type(end) is not date:
        raise ValueError("Choose valid Gregorian dates")
    length = (end - start).days
    if not 0 <= length <= 365:
        raise ValueError("Timetable query cannot exceed 366 dates")
    indexed: dict[date, list[Timetable]] = {}
    for table in tables:
        for row in table.days:
            if start <= row.day <= end:
                indexed.setdefault(row.day, []).append(
                    Timetable(table.timetable_id, table.kind, (row,))
                )
    result = []
    for offset in range(length + 1):
        current = start + timedelta(days=offset)
        effective = resolve_day(current, tuple(indexed.get(current, ())), settings)
        times = (
            {
                field.value: [value.strftime("%H:%M") for value in values]
                for field, values in effective.row.times.items()
            }
            if effective.row
            else {}
        )
        result.append(
            {
                "date": current.isoformat(),
                "published": effective.row is not None and bool(times),
                "ramadan_active": effective.ramadan_active,
                "times": times,
            }
        )
    return result


def approved_month(
    tables: tuple[Timetable, ...],
    settings: RamadanSettings,
    year: int,
    month: int,
) -> list[dict]:
    """One month's effective approved rows, with explicit missing dates."""
    if type(year) is not int or type(month) is not int or not 1 <= year <= 9999 or not 1 <= month <= 12:
        raise ValueError("Choose a valid Gregorian month")
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    return effective_range(tables, settings, first, last)


def approved_year_csv(
    tables: tuple[Timetable, ...],
    settings: RamadanSettings,
    year: int,
    time_zone: str,
) -> str:
    """CSV includes only canonical published fields and the effective Ramadan overlay."""
    if type(year) is not int or not 1 <= year <= 9999:
        raise ValueError("Choose a valid Gregorian year")
    rows = effective_range(tables, settings, date(year, 1, 1), date(year, 12, 31))
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    fields = tuple(field.value for field in PrayerField)
    writer.writerow(("date", "time_zone", *fields))
    for item in rows:
        writer.writerow(
            (
                item["date"],
                time_zone,
                *("; ".join(item["times"].get(field, ())) for field in fields),
            )
        )
    return output.getvalue()


def approved_source_details(storage) -> list[dict]:
    """Safe source provenance; intentionally never return URLs or original PDFs."""
    result = []
    for table in storage.timetables:
        approved = storage.approved_sources.get(table.timetable_id)
        remote = storage.remote_sources.get(table.timetable_id)
        check = storage.remote_checks.get(table.timetable_id, {})
        result.append(
            {
                "source_id": table.timetable_id,
                "kind": table.kind,
                "first_date": table.days[0].day.isoformat(),
                "last_date": table.days[-1].day.isoformat(),
                "rows": len(table.days),
                "format": approved.source_format if approved else None,
                "year": approved.year if approved else None,
                "parser_id": approved.parser_id if approved else None,
                "sha256_prefix": approved.sha256[:12] if approved else None,
                "remote": remote is not None,
                "check_status": check.get("status", "not_configured"),
                "last_checked": check.get("last_checked"),
            }
        )
    return result
