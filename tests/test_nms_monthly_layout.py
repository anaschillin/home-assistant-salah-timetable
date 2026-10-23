"""Real NMS monthly source values and fail-closed layout validation."""

import calendar
import csv
import io
from datetime import date, time, timedelta
from pathlib import Path

import pytest

from custom_components.salah_timetable.csv_parser import CsvParser
from custom_components.salah_timetable.import_model import ImportValidationError
from custom_components.salah_timetable.model import PrayerField
from custom_components.salah_timetable.nms_monthly_layout import (
    NMS_MONTHLY_COLUMNS,
    NmsMonthlyLayout,
)
from custom_components.salah_timetable.pdf_parser import extract_pdf_pages
from custom_components.salah_timetable.ramadan import RamadanSettings, resolve_day

FIXTURE = Path(__file__).parent / "fixtures/pdf/nms ramadhan.pdf"


@pytest.fixture(scope="module")
def pages():
    return extract_pdf_pages(FIXTURE.read_bytes())


def parsed(pages, year=2022, kind="ramadan"):
    return CsvParser().parse(
        NmsMonthlyLayout().to_csv(pages).encode(),
        timetable_id=f"{kind}-{year}",
        kind=kind,
        year=year,
        date_column="Date",
        columns=NMS_MONTHLY_COLUMNS,
    )


def mutate(pages, page, old, new):
    changed = list(pages)
    assert old in changed[page]
    changed[page] = changed[page].replace(old, new, 1)
    return tuple(changed)


def test_real_source_is_may_june_2022_not_a_full_ramadan(pages):
    candidate = parsed(pages)
    assert len(pages) == 2
    assert tuple(row.day for row in candidate.timetable.days) == tuple(
        date(2022, 5, 1) + timedelta(days=offset) for offset in range(61)
    )
    assert candidate.coverage.row_count == 61
    assert candidate.coverage.missing_dates == ()
    assert sum(len(row.times) for row in candidate.timetable.days) == 854
    assert candidate.timetable.days[0].original["Published Hijri"] == "30"
    assert candidate.timetable.days[1].original["Published Hijri"] == "1"
    # A filename, Ramadan kind or printed Hijri heading is not confirmation.
    effective = resolve_day(date(2022, 5, 1), (candidate.timetable,), RamadanSettings())
    assert not effective.ramadan_active
    assert effective.row is None
    with pytest.raises(ImportValidationError, match="declared year"):
        parsed(pages, year=2026)


def test_real_source_selected_golden_values_and_provenance(pages):
    rows = {row.day: row for row in parsed(pages).timetable.days}
    first = rows[date(2022, 5, 1)]
    assert first.times == {
        PrayerField.SEHRI_ENDS: (time(2, 53),),
        PrayerField.FAJR_BEGIN: (time(2, 58),),
        PrayerField.SUNRISE: (time(5, 35),),
        PrayerField.ISTEWA: (time(13, 3),),
        PrayerField.DHUHR_BEGIN: (time(13, 8),),
        PrayerField.ASR_BEGIN: (time(18, 11),),
        PrayerField.MAGHRIB_BEGIN: (time(20, 32),),
        PrayerField.ISHA_BEGIN: (time(21, 49),),
        PrayerField.FAJR_JAMAAT: (time(3, 20),),
        PrayerField.DHUHR_JAMAAT: (time(13, 30),),
        PrayerField.ASR_JAMAAT: (time(19, 15),),
        PrayerField.MAGHRIB_JAMAAT: (time(20, 35),),
        PrayerField.ISHA_JAMAAT: (time(22, 10),),
        PrayerField.IFTAR: (time(20, 35),),
    }
    assert len(first.original) == 31
    assert first.original["Published Dawn"] == "2:58"
    assert first.original["Published Day"] == "Sun"
    assert rows[date(2022, 5, 3)].original["Published Fajr Jamaat"] == '"'
    assert rows[date(2022, 5, 3)].times[PrayerField.FAJR_JAMAAT] == (time(5),)
    assert rows[date(2022, 6, 1)].times[PrayerField.FAJR_JAMAAT] == (time(4, 20),)
    assert rows[date(2022, 6, 11)].original["Published Maghrib Iftaar"] == '"'
    assert rows[date(2022, 6, 11)].times[PrayerField.IFTAR] == (time(21, 31),)
    assert rows[date(2022, 6, 30)].times[PrayerField.IFTAR] == (time(21, 35),)
    assert all(PrayerField.TARAWEEH not in row.times for row in rows.values())


def test_friday_midday_column_is_jumuah_and_khutbah_is_not_jamaat(pages):
    rows = {row.day: row for row in parsed(pages).timetable.days}
    assert rows[date(2022, 5, 5)].times[PrayerField.DHUHR_JAMAAT] == (time(13, 30),)
    assert PrayerField.JUMUAH not in rows[date(2022, 5, 5)].times
    friday = rows[date(2022, 5, 6)]
    assert friday.times[PrayerField.JUMUAH] == (time(13, 30),)
    assert PrayerField.DHUHR_JAMAAT not in friday.times
    assert friday.times[PrayerField.FAJR_JAMAAT] == (time(4, 45),)
    assert rows[date(2022, 6, 3)].times[PrayerField.JUMUAH] == (time(13, 30),)
    assert all(
        time(16, 30) not in row.times.get(PrayerField.JUMUAH, ())
        for row in rows.values()
    )


def test_single_month_and_curly_ditto_are_supported(pages):
    may = parsed((pages[0].replace('"', "“"),))
    assert len(may.timetable.days) == 31
    assert may.timetable.days[2].times[PrayerField.FAJR_JAMAAT] == (time(5),)
    assert may.timetable.days[2].original["Published Fajr Jamaat"] == "“"
    june = parsed((pages[1],), kind="annual")
    assert len(june.timetable.days) == 30
    assert len(june.coverage.missing_dates) == 335


def synthetic_month(template, year, month):
    """Reuse the known structure with explicit fictional dated rows for bounds."""
    lines = template.splitlines()
    first = next(index for index, line in enumerate(lines) if line.startswith("1 Sun"))
    last = next(index for index, line in enumerate(lines) if line.startswith("31 Tue"))
    body = lines[first].split(" ", 3)[3]
    rows = [
        f"{day} {date(year, month, day).strftime('%a')} {(day - 1) % 30 + 1} {body}"
        for day in range(1, calendar.monthrange(year, month)[1] + 1)
    ]
    return "\n".join(lines[:first] + rows + lines[last + 1 :]).replace(
        "May 2022", f"{calendar.month_name[month]} {year}"
    )


def test_complete_leap_month_and_twelve_sequential_months(pages):
    february = synthetic_month(pages[0], 2024, 2)
    result = parsed((february,), year=2024)
    assert len(result.timetable.days) == 29
    assert result.timetable.days[-1].day == date(2024, 2, 29)
    twelve = tuple(synthetic_month(pages[0], 2024, month) for month in range(1, 13))
    result = parsed(twelve, year=2024)
    assert len(result.timetable.days) == 366
    assert result.timetable.days[0].day == date(2024, 1, 1)
    assert result.timetable.days[-1].day == date(2024, 12, 31)


@pytest.mark.parametrize("pages", [(), ("",), (None,), ("unknown",) * 13])
def test_reject_invalid_page_count_or_empty_pages(pages):
    with pytest.raises(ImportValidationError, match="1 to 12"):
        NmsMonthlyLayout().to_csv(pages)


@pytest.mark.parametrize(
    ("page", "old", "new", "message"),
    [
        (0, "May 2022", "May 2026", "weekday"),
        (0, "May 2022", "May 2300", "supported range"),
        (1, "June 2022", "June 2023", "same printed year"),
        (1, "June 2022", "May 2022", "consecutive"),
        (1, "June 2022", "July 2022", "consecutive"),
        (0, "Dawn Sunrise", "Dawn Moonrise", "columns"),
        (0, "1 Sun 30", "1 Mon 30", "weekday"),
        (0, "1 Sun 30", "2 Sun 30", "date"),
        (0, "1 Sun 30", "1 Sun 31", "Hijri"),
        (0, "1 Sun 30 2:53", "1 Sun 30 2:60", "invalid published time"),
        (0, "1 Sun 30 2:53", '1 Sun 30 "', "quotation mark"),
        (0, "8:32 9:49 x", "10:32 9:49 x", "daily order"),
        (0, "x 3:20 1:30", "x 6:20 1:30", "Jamaat"),
        (0, "9:49 x 3:20", "9:49 y 3:20", "separator"),
        (0, "9:49 x 3:20", "9:49 x x 3:20", "thirteen"),
        (1, "x 4:20 1:30", 'x " 1:30', "this month"),
        (0, "Dates Beginning / End Times Jamaat Times", "Unknown table", "footer"),
        (0, "Ramaḍān 1443", "Unknown month 1443", "footer"),
        (0, "www.nmsuk.org", "different-mosque.example", "footer"),
        (0, "*Hijri Date is subject to Moonsighting", "Unknown preamble", "columns"),
    ],
)
def test_changed_layout_or_invalid_values_fail_closed(pages, page, old, new, message):
    changed = mutate(pages, page, old, new)
    with pytest.raises(ImportValidationError, match=message):
        NmsMonthlyLayout().to_csv(changed)


def test_missing_duplicate_reordered_or_interrupted_rows_fail_closed(pages):
    lines = pages[0].splitlines()
    first = next(index for index, line in enumerate(lines) if line.startswith("1 Sun"))
    variants = [
        lines[:first] + lines[first + 1 :],
        lines[:first] + [lines[first]] + lines[first:],
        lines[:first] + [lines[first + 1], lines[first]] + lines[first + 2 :],
        lines[: first + 1] + ["Unexpected line"] + lines[first + 1 :],
    ]
    for changed_lines in variants:
        with pytest.raises(ImportValidationError, match="every dated row|date"):
            NmsMonthlyLayout().to_csv(("\n".join(changed_lines), pages[1]))


def test_unknown_extra_footer_or_duplicate_heading_is_not_ignored(pages):
    for extra in ("Unexpected footer", "May 2022", "x"):
        with pytest.raises(ImportValidationError, match="footer|one explicit"):
            NmsMonthlyLayout().to_csv((pages[0] + "\n" + extra, pages[1]))


def test_canonical_headers_are_distinct_and_no_taraweeh_is_fabricated(pages):
    rows = list(csv.DictReader(io.StringIO(NmsMonthlyLayout().to_csv(pages))))
    assert len(rows[0]) == 31
    assert "Taraweeh" not in rows[0]
    assert set(NMS_MONTHLY_COLUMNS.values()) == {
        field.value for field in PrayerField
    } - {"taraweeh"}
