"""Annual parser tests using only independently generated fictional PDF data."""

import csv
import io
from datetime import date, time, timedelta
from pathlib import Path

import pytest

from custom_components.salah_timetable.domain.model import PrayerField
from custom_components.salah_timetable.parsers.csv_parser import CsvParser
from custom_components.salah_timetable.parsers.import_model import ImportValidationError
from custom_components.salah_timetable.parsers.mosque_b_annual_layout import (
    MAY_DATE_INTERPRETATION,
    MOSQUE_B_ANNUAL_COLUMNS,
    MosqueBAnnualLayout,
)
from custom_components.salah_timetable.parsers.pdf_parser import extract_pdf_pages

FIXTURE = Path(__file__).parents[1] / "fixtures/pdf/mosque_b_2026.pdf"


@pytest.fixture(scope="module")
def pages():
    return extract_pdf_pages(FIXTURE.read_bytes())


def parsed(pages, year=2026):
    return CsvParser().parse(
        MosqueBAnnualLayout().to_csv(pages).encode(),
        timetable_id="annual-2026",
        kind="annual",
        year=year,
        date_column="Date",
        columns=MOSQUE_B_ANNUAL_COLUMNS,
    )


def test_annual_year_and_full_date_coverage(pages):
    candidate = parsed(pages)
    rows = candidate.timetable.days
    assert len(pages) == 14
    assert [r.day for r in rows] == [
        date(2026, 1, 1) + timedelta(days=n) for n in range(365)
    ]
    assert candidate.coverage.missing_dates == ()
    assert sum(len(row.times) for row in rows) == 3770
    assert sum(PrayerField.SEHRI_ENDS in row.times for row in rows) == 120
    assert all(PrayerField.IFTAR not in row.times for row in rows)
    assert rows[0].times[PrayerField.FAJR_BEGIN] == (time(5, 7),)
    assert rows[0].times[PrayerField.DHUHR_BEGIN] == (time(12, 5),)
    assert rows[0].times[PrayerField.ISHA_JAMAAT] == (time(21, 7),)


def test_clipped_first_of_may_has_structural_provenance(pages):
    rows = {row.day: row for row in parsed(pages).timetable.days}
    may = rows[date(2026, 5, 1)]
    assert may.original["Published Date"] == "May ..."
    assert may.original["Published Date Interpretation"] == MAY_DATE_INTERPRETATION
    assert may.times[PrayerField.SEHRI_ENDS] == (time(5),)
    assert rows[date(2026, 5, 2)].original["Published Date"] == "2"


def test_full_csv_shape_and_declared_year(pages):
    rows = list(csv.DictReader(io.StringIO(MosqueBAnnualLayout().to_csv(pages))))
    assert len(rows) == 365
    assert len(rows[0]) == 27
    assert rows[0]["Date"] == "2026-01-01"
    assert rows[-1]["Date"] == "2026-12-31"
    with pytest.raises(ImportValidationError):
        parsed(pages, year=2027)


@pytest.mark.parametrize(
    "page,old,new",
    [
        (0, "2026", "2027"),
        (1, "JANUARY 2026", "JANUARY 2027"),
        (1, "DATE FAJR ZOHAR", "DATE FAJR UNKNOWN"),
        (1, "Jan 1,...", "Jan 2,..."),
        (1, "1,... Thu", "1,... Fri"),
        (1, "5:07", "5:99"),
        (5, "May ... Fri", "May ... Sat"),
        (13, "RAMADHAN 2026", "RAMADHAN 2027"),
    ],
)
def test_invalid_dates_headers_and_times_are_rejected(pages, page, old, new):
    assert old in pages[page]
    changed = list(pages)
    changed[page] = changed[page].replace(old, new, 1)
    with pytest.raises(ImportValidationError):
        MosqueBAnnualLayout().to_csv(tuple(changed))


def test_reject_incomplete_and_reordered_publications(pages):
    with pytest.raises(ImportValidationError):
        MosqueBAnnualLayout().to_csv(pages[:13])
    changed = list(pages)
    changed[1], changed[2] = changed[2], changed[1]
    with pytest.raises(ImportValidationError):
        MosqueBAnnualLayout().to_csv(tuple(changed))
