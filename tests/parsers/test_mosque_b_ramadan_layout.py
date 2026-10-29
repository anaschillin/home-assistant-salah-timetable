"""Ramadan parser checks based on original synthetic fixture pages."""

import csv
import io
from datetime import date, time, timedelta
from pathlib import Path

import pytest

from custom_components.salah_timetable.csv_parser import CsvParser
from custom_components.salah_timetable.import_model import ImportValidationError
from custom_components.salah_timetable.model import PrayerField
from custom_components.salah_timetable.mosque_b_ramadan_layout import (
    MOSQUE_B_RAMADAN_COLUMNS,
    MosqueBRamadanLayout,
)
from custom_components.salah_timetable.pdf_parser import extract_pdf_pages

FIXTURE = Path(__file__).parents[1] / "fixtures/pdf/mosque_b_2026.pdf"


@pytest.fixture(scope="module")
def pages():
    return extract_pdf_pages(FIXTURE.read_bytes())


def parsed(pages):
    return CsvParser().parse(
        MosqueBRamadanLayout().to_csv(pages).encode(),
        timetable_id="ramadan-2026",
        kind="ramadan",
        year=2026,
        date_column="Date",
        columns=MOSQUE_B_RAMADAN_COLUMNS,
    )


def test_fictional_ramadan_page_and_final_shawwal_row(pages):
    candidate = parsed(pages)
    rows = candidate.timetable.days
    assert len(rows) == 31
    assert [r.day for r in rows] == [
        date(2026, 2, 18) + timedelta(days=i) for i in range(31)
    ]
    assert candidate.coverage.row_count == 31
    assert sum(len(row.times) for row in rows) == 341
    assert all(len(row.times) == 11 for row in rows)
    assert rows[0].times[PrayerField.SEHRI_ENDS] == (time(5),)
    assert rows[0].times[PrayerField.ISHA_JAMAAT] == (time(21, 7),)
    assert all(PrayerField.IFTAR not in row.times for row in rows)
    assert rows[-1].original["Published Hijri"] == "1"


def test_csv_has_independently_labeled_prayer_fields(pages):
    rows = list(csv.DictReader(io.StringIO(MosqueBRamadanLayout().to_csv(pages))))
    assert len(rows) == 31
    assert rows[0]["Date"] == "2026-02-18"
    assert rows[-1]["Date"] == "2026-03-20"
    assert rows[0]["Published Sehri End"] == "5:00"


@pytest.mark.parametrize(
    "page,old,new",
    [
        (0, "2026", "2027"),
        (13, "RAMADHAN 2026", "RAMADHAN 2027"),
        (13, "Ramadhan Kareem", "Unknown"),
        (13, "Feb 18,...", "Feb 19,..."),
        (13, "5:07", "5:99"),
        (13, "DATE SEHRI", "DATE UNKNOWN"),
        (13, "www.mosque-b.example.org", "not-a-site.example"),
    ],
)
def test_reject_malformed_ramadan_publications(pages, page, old, new):
    assert old in pages[page]
    changed = list(pages)
    changed[page] = changed[page].replace(old, new, 1)
    with pytest.raises(ImportValidationError):
        MosqueBRamadanLayout().to_csv(tuple(changed))


def test_month_swap_and_missing_page_are_rejected(pages):
    with pytest.raises(ImportValidationError):
        MosqueBRamadanLayout().to_csv(pages[:-1])
    swapped = list(pages)
    swapped[1], swapped[2] = swapped[2], swapped[1]
    with pytest.raises(ImportValidationError):
        MosqueBRamadanLayout().to_csv(tuple(swapped))
