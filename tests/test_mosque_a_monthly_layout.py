"""Synthetic monthly-layout regression tests: no third-party publication assets."""

import csv
import io
from datetime import date, time, timedelta
from pathlib import Path

import pytest

from custom_components.salah_timetable.csv_parser import CsvParser
from custom_components.salah_timetable.import_model import ImportValidationError
from custom_components.salah_timetable.model import PrayerField
from custom_components.salah_timetable.mosque_a_monthly_layout import (
    MOSQUE_A_MONTHLY_COLUMNS,
    MosqueAMonthlyLayout,
)
from custom_components.salah_timetable.pdf_parser import extract_pdf_pages

FIXTURE = Path(__file__).parent / "fixtures/pdf/mosque_a_monthly_2022.pdf"


@pytest.fixture(scope="module")
def pages():
    return extract_pdf_pages(FIXTURE.read_bytes())


def parsed(pages, year=2022):
    return CsvParser().parse(
        MosqueAMonthlyLayout().to_csv(pages).encode(),
        timetable_id=f"ramadan-{year}",
        kind="ramadan",
        year=year,
        date_column="Date",
        columns=MOSQUE_A_MONTHLY_COLUMNS,
    )


def test_synthetic_two_months_are_complete_and_fictional(pages):
    candidate = parsed(pages)
    assert len(pages) == 2
    assert [row.day for row in candidate.timetable.days] == [
        date(2022, 5, 1) + timedelta(days=n) for n in range(61)
    ]
    assert candidate.coverage.row_count == 61
    assert candidate.coverage.missing_dates == ()
    assert sum(len(row.times) for row in candidate.timetable.days) == 854
    first = candidate.timetable.days[0]
    assert first.times[PrayerField.FAJR_BEGIN] == (time(5, 7),)
    assert first.times[PrayerField.SUNRISE] == (time(7, 0),)
    assert first.times[PrayerField.MAGHRIB_BEGIN] == (time(18, 17),)
    assert first.times[PrayerField.IFTAR] == (time(18, 22),)
    assert first.original["Published Dawn"] == "5:07"
    assert all(PrayerField.TARAWEEH not in row.times for row in candidate.timetable.days)


def test_friday_field_and_khutbah_annotation_remain_separate(pages):
    rows = {row.day: row for row in parsed(pages).timetable.days}
    friday = rows[date(2022, 5, 6)]
    thursday = rows[date(2022, 5, 5)]
    assert friday.times[PrayerField.JUMUAH] == (time(13, 45),)
    assert PrayerField.DHUHR_JAMAAT not in friday.times
    assert thursday.times[PrayerField.DHUHR_JAMAAT] == (time(13, 45),)
    assert friday.original["Published Second Khutbah"] == "16:15"
    assert thursday.original["Published Second Khutbah"] == ""


def test_monthly_csv_provenance_and_wrong_year(pages):
    rows = list(csv.DictReader(io.StringIO(MosqueAMonthlyLayout().to_csv(pages))))
    assert len(rows) == 61
    assert rows[0]["Date"] == "2022-05-01"
    assert rows[-1]["Date"] == "2022-06-30"
    assert rows[0]["Published Day"] == "Sun"
    with pytest.raises(ImportValidationError):
        parsed(pages, year=2026)


@pytest.mark.parametrize("page,old,new", [
    (0, "May 2022", "May 2023"),
    (0, "1 Sun", "1 Mon"),
    (0, "1 Sun", "2 Sun"),
    (0, "5:07", "5:99"),
    (0, "Dawn Sunrise", "Dawn Moonrise"),
    (0, "Dates Beginning / End Times Jamaat Times", "Unknown footer"),
])
def test_reject_modified_structure_and_times(pages, page, old, new):
    assert old in pages[page]
    changed = list(pages)
    changed[page] = changed[page].replace(old, new, 1)
    with pytest.raises(ImportValidationError):
        MosqueAMonthlyLayout().to_csv(tuple(changed))


def test_reject_duplicate_missing_or_reordered_rows(pages):
    lines = pages[0].splitlines()
    first = next(i for i, line in enumerate(lines) if line.startswith("1 Sun"))
    for variant in (
        lines[:first] + lines[first + 1:],
        lines[:first] + [lines[first]] + lines[first:],
        lines[:first] + [lines[first + 1], lines[first]] + lines[first + 2:],
    ):
        with pytest.raises(ImportValidationError):
            MosqueAMonthlyLayout().to_csv(("\n".join(variant), pages[1]))


def test_monthly_layout_does_not_depend_on_a_specific_publisher_url(pages):
    changed = tuple(page.replace("www.mosque-a.example.org", "www.other-example.test") for page in pages)
    assert MosqueAMonthlyLayout().to_csv(changed) == MosqueAMonthlyLayout().to_csv(pages)
