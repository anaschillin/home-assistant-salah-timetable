"""Published annual values, missing fields and strict Zakariyya date handling."""

import csv
import io
from datetime import date, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from pypdf import PdfReader

from custom_components.salah_timetable.csv_parser import CsvParser
from custom_components.salah_timetable.import_model import ImportValidationError
from custom_components.salah_timetable.model import PrayerField
from custom_components.salah_timetable.ramadan import RamadanSettings, resolve_day
from custom_components.salah_timetable.zak_annual_layout import (
    MAY_DATE_INTERPRETATION,
    ZAK_ANNUAL_COLUMNS,
    ZakAnnualLayout,
)

FIXTURE = Path(__file__).parent / "fixtures/pdf/zak.pdf"


@pytest.fixture(scope="module")
def pages():
    return tuple(page.extract_text() for page in PdfReader(FIXTURE, strict=True).pages)


def parsed(pages, year=2026):
    return CsvParser().parse(
        ZakAnnualLayout().to_csv(pages).encode(),
        timetable_id=f"annual-{year}",
        kind="annual",
        year=year,
        date_column="Date",
        columns=ZAK_ANNUAL_COLUMNS,
    )


def changed(pages, page, old, new):
    value = list(pages)
    assert old in value[page]
    value[page] = value[page].replace(old, new, 1)
    return tuple(value)


def test_real_publication_has_every_date_once_and_only_published_fields(pages):
    candidate = parsed(pages)
    rows = candidate.timetable.days
    assert [row.day for row in rows] == [
        date(2026, 1, 1) + timedelta(days=offset) for offset in range(365)
    ]
    assert candidate.coverage.missing_dates == ()
    assert candidate.coverage.missing_fields == {
        "sehri_ends": 245,
        "jumuah": 365,
        "maghrib_jamaat": 365,
        "istewa": 365,
        "iftar": 365,
        "taraweeh": 365,
    }
    assert sum(len(row.times) for row in rows) == 3770
    assert all(len(row.original) == 27 for row in rows)
    assert all(
        (PrayerField.SEHRI_ENDS in row.times) == (2 <= row.day.month <= 5)
        for row in rows
    )
    assert all(
        not {
            PrayerField.JUMUAH,
            PrayerField.MAGHRIB_JAMAAT,
            PrayerField.IFTAR,
            PrayerField.TARAWEEH,
            PrayerField.ISTEWA,
        }
        & set(row.times)
        for row in rows
    )


def test_january_all_ten_published_times_and_friday_meaning(pages):
    rows = parsed(pages).timetable.days
    assert rows[0].times == {
        PrayerField.FAJR_BEGIN: (time(6, 46),),
        PrayerField.FAJR_JAMAAT: (time(7, 15),),
        PrayerField.SUNRISE: (time(8, 26),),
        PrayerField.DHUHR_BEGIN: (time(12, 18),),
        PrayerField.DHUHR_JAMAAT: (time(12, 40),),
        PrayerField.ASR_BEGIN: (time(14, 14),),
        PrayerField.ASR_JAMAAT: (time(14, 45),),
        PrayerField.MAGHRIB_BEGIN: (time(16, 6),),
        PrayerField.ISHA_BEGIN: (time(17, 48),),
        PrayerField.ISHA_JAMAAT: (time(18, 15),),
    }
    assert rows[0].original["Published Sehri End"] == ""
    assert rows[0].original["Published Fajr Start"] == "6:46"
    friday = rows[1]
    assert friday.day == date(2026, 1, 2)
    assert friday.original["Published Day"] == "ﻪﻌﻤﺟ"
    assert friday.times[PrayerField.DHUHR_JAMAAT] == (time(12, 40),)
    assert PrayerField.JUMUAH not in friday.times


def test_may_clipped_date_has_explicit_structural_provenance(pages):
    rows = {row.day: row for row in parsed(pages).timetable.days}
    may = rows[date(2026, 5, 1)]
    assert may.times == {
        PrayerField.SEHRI_ENDS: (time(3, 50),),
        PrayerField.FAJR_BEGIN: (time(3, 55),),
        PrayerField.FAJR_JAMAAT: (time(4, 45),),
        PrayerField.SUNRISE: (time(5, 35),),
        PrayerField.DHUHR_BEGIN: (time(13, 12),),
        PrayerField.DHUHR_JAMAAT: (time(13, 40),),
        PrayerField.ASR_BEGIN: (time(18, 16),),
        PrayerField.ASR_JAMAAT: (time(19, 45),),
        PrayerField.MAGHRIB_BEGIN: (time(20, 45),),
        PrayerField.ISHA_BEGIN: (time(21, 51),),
        PrayerField.ISHA_JAMAAT: (time(22, 15),),
    }
    assert may.original["Published Date"] == "May …"
    assert may.original["Published Day"] == "ﻪﻌﻤﺟ"
    assert may.original["Published Date Interpretation"] == MAY_DATE_INTERPRETATION
    assert [
        row.day
        for row in rows.values()
        if row.original["Published Date Interpretation"]
    ] == [date(2026, 5, 1)]
    assert rows[date(2026, 5, 2)].original["Published Date"] == "2"


def test_printed_hijri_discrepancy_does_not_change_gregorian_dates(pages):
    assert "MAY 2026MAY 2026 Zul Qa'dah - Zul Hijjah 1446 AH" in pages[5]
    table = parsed(pages).timetable
    effective = resolve_day(date(2026, 5, 1), (table,), RamadanSettings())
    assert not effective.ramadan_active
    assert effective.row.day == date(2026, 5, 1)
    assert effective.row.original["Published Hijri"] == "14"
    assert PrayerField.IFTAR not in effective.row.times


def test_pre_noon_dhuhr_and_dst_changes_keep_actual_local_times(pages):
    rows = {row.day: row for row in parsed(pages).timetable.days}
    assert rows[date(2026, 11, 1)].times[PrayerField.DHUHR_BEGIN] == (time(11, 58),)
    assert rows[date(2026, 3, 28)].times[PrayerField.FAJR_BEGIN] == (time(4, 17),)
    assert rows[date(2026, 3, 29)].times[PrayerField.FAJR_BEGIN] == (time(5, 14),)
    assert rows[date(2026, 10, 24)].times[PrayerField.FAJR_BEGIN] == (time(6, 16),)
    assert rows[date(2026, 10, 25)].times[PrayerField.FAJR_BEGIN] == (time(5, 18),)
    zone = ZoneInfo("Europe/London")
    for row in rows.values():
        for field in row.times:
            timestamp = row.timestamps(field, zone)[0]
            assert timestamp.date() == row.day
            assert timestamp.time() == row.times[field][0]
    assert rows[date(2026, 3, 28)].timestamps(PrayerField.FAJR_BEGIN, zone)[
        0
    ].utcoffset() == timedelta(0)
    assert rows[date(2026, 3, 29)].timestamps(PrayerField.FAJR_BEGIN, zone)[
        0
    ].utcoffset() == timedelta(hours=1)


def test_separate_ramadan_times_are_not_used_as_annual_values(pages):
    baseline = parsed(pages).timetable
    altered = changed(pages, -1, "Feb 18,… Wed 1 5:37", "Feb 18,… Wed 1 5:36")
    assert parsed(altered).timetable == baseline
    assert baseline.days[48].times[PrayerField.SEHRI_ENDS] == (time(5, 37),)


@pytest.mark.parametrize("count", [0, 1, 12, 13, 15])
def test_reject_incomplete_or_extra_publication_pages(pages, count):
    with pytest.raises(ImportValidationError):
        ZakAnnualLayout().to_csv((pages * 2)[:count])


@pytest.mark.parametrize(
    ("page", "old", "new"),
    [
        (0, "2026", "2027"),
        (1, "JANUARY 2026", "JANUARY 2027"),
        (1, "DATE FAJR ZOHAR", "DATE FAJR JUMUAH"),
        (2, "ISLAMIC SEHRI START", "ISLAMIC END START"),
        (3, "DATE SEHRI FAJR", "DATE FAJR"),
        (1, "1 Thu 12", "1 Fri 12"),
        (1, "1 Thu 12", "1 Thursday 12"),
        (1, "1 Thu 12", "2 Thu 12"),
        (1, "1 Thu 12", "1 Thu 31"),
        (1, "1 Thu 12", "1 Thu 0"),
        (1, "1 Thu 12 6:46", '1 Thu 12 "'),
        (1, "1 Thu 12 6:46", "1 Thu 12 6:99"),
        (1, "1 Thu 12 6:46 7:15", "1 Thu 12 6:46 6:15"),
        (1, "6:46 7:15 8:26", "6:46 7:15 8:26 8:26"),
        (1, "6:46 7:15 8:26", "6:46 8:26"),
        (2, "Feb 1,…", "Mar 1,…"),
        (2, "Feb 1,…", "1"),
        (3, "Mar 1…", "Mar 2…"),
        (5, "May … ﻪﻌﻤﺟ", "May … Sat"),
        (5, "May … ﻪﻌﻤﺟ", "May 2… ﻪﻌﻤﺟ"),
        (5, "2 Sat 15", "3 Sat 15"),
        (4, "Apr 1,…", "May …"),
        (5, "3 Sun 16", "May … Sun 16"),
        (1, "2 ﻪﻌﻤﺟ 13", "Jan 2,… ﻪﻌﻤﺟ 13"),
        (11, "11:58 12:40", "10:58 12:40"),
        (5, "Zul Hijjah 1446 AH", "Zul Hijjah 1447 AH"),
        (-1, "RAMADHAN 2026", "RAMADHAN 2027"),
        (-1, "Ramadhan Kareem 1447 AH", "Unknown Mosque"),
    ],
)
def test_reject_changed_columns_dates_unknown_clipping_or_invalid_times(
    pages, page, old, new
):
    with pytest.raises(ImportValidationError):
        ZakAnnualLayout().to_csv(changed(pages, page, old, new))


@pytest.mark.parametrize("month", [1, 2, 5, 12])
def test_reject_missing_duplicate_or_reordered_month_rows(pages, month):
    lines = pages[month].splitlines()
    first = next(i for i, line in enumerate(lines) if line.startswith("DATE DAY")) + 1
    variants = (
        lines[:first] + lines[first + 1 :],
        lines[:first] + [lines[first]] + lines[first:],
        lines[:first] + [lines[first + 1], lines[first]] + lines[first + 2 :],
    )
    for value in variants:
        changed_pages = list(pages)
        changed_pages[month] = "\n".join(value)
        with pytest.raises(ImportValidationError):
            ZakAnnualLayout().to_csv(tuple(changed_pages))


def test_reject_unrecognized_extra_lines_in_header_footer_or_rows(pages):
    for page, old, new in (
        (1, "DATE DAY", "Unknown instructions\nDATE DAY"),
        (1, "2 ﻪﻌﻤﺟ 13", "Unknown row\n2 ﻪﻌﻤﺟ 13"),
        (1, "Please Visit on", "Unknown footer\nPlease Visit on"),
        (1, "www.zakariyyamasjid.co.uk", "unknown.example.org"),
    ):
        with pytest.raises(ImportValidationError):
            ZakAnnualLayout().to_csv(changed(pages, page, old, new))


def test_complete_month_structure_cannot_be_reordered(pages):
    value = list(pages)
    value[1], value[2] = value[2], value[1]
    with pytest.raises(ImportValidationError):
        ZakAnnualLayout().to_csv(tuple(value))


def test_declared_year_and_csv_provenance_bounds(pages):
    with pytest.raises(ImportValidationError, match="declared year"):
        parsed(pages, year=2027)
    rows = list(csv.reader(io.StringIO(ZakAnnualLayout().to_csv(pages))))
    assert len(rows) == 366
    assert len(rows[0]) == 27
    assert len(set(rows[0])) == 27
    assert all(len(row) == 27 for row in rows)
