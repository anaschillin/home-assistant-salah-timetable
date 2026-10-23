"""Real-publication and fail-closed checks for Zakariyya's final Ramadan page."""

import csv
import io
from datetime import date, time, timedelta
from pathlib import Path

import pytest
from pypdf import PdfReader

from custom_components.salah_timetable.csv_parser import CsvParser
from custom_components.salah_timetable.import_model import ImportValidationError
from custom_components.salah_timetable.model import PrayerField
from custom_components.salah_timetable.ramadan import RamadanSettings, resolve_day
from custom_components.salah_timetable.zak_ramadan_layout import (
    ZAK_RAMADAN_COLUMNS,
    ZakRamadanLayout,
)

FIXTURE = Path(__file__).parent / "fixtures/pdf/zak.pdf"
# Transcribed from the rendered final page: Sehri End, Magrib Start, Isha Jamaat.
GOLDEN_CLOCKS = """05:37 17:31 19:45
05:35 17:33 19:45
05:33 17:35 19:45
05:31 17:37 19:45
05:29 17:39 19:45
05:26 17:41 19:45
05:24 17:43 19:45
05:22 17:45 19:45
05:20 17:46 19:45
05:17 17:48 20:00
05:15 17:50 20:00
05:13 17:52 20:00
05:10 17:54 20:00
05:08 17:56 20:00
05:06 17:58 20:00
05:03 18:00 20:00
05:01 18:02 20:15
04:59 18:04 20:15
04:56 18:06 20:15
04:54 18:07 20:15
04:52 18:09 20:15
04:49 18:11 20:15
04:47 18:13 20:15
04:44 18:15 20:30
04:42 18:17 20:30
04:40 18:19 20:30
04:37 18:21 20:30
04:35 18:22 20:30
04:32 18:24 20:30
04:30 18:26 20:30
04:28 18:28 20:30"""


@pytest.fixture(scope="module")
def pages():
    return tuple(page.extract_text() for page in PdfReader(FIXTURE, strict=True).pages)


def parsed(pages):
    return CsvParser().parse(
        ZakRamadanLayout().to_csv(pages).encode(),
        timetable_id="ramadan-2026",
        kind="ramadan",
        year=2026,
        date_column="Date",
        columns=ZAK_RAMADAN_COLUMNS,
    )


def changed(pages, original, replacement, page=-1):
    result = list(pages)
    assert original in result[page]
    result[page] = result[page].replace(original, replacement, 1)
    return tuple(result)


def test_real_final_page_exact_gregorian_dates_and_selected_golden_values(pages):
    candidate = parsed(pages)
    rows = candidate.timetable.days
    assert len(rows) == 31
    assert [row.day for row in rows] == [
        date(2026, 2, 18) + timedelta(days=offset) for offset in range(31)
    ]
    assert candidate.coverage.missing_dates == ()
    for row, golden in zip(rows, GOLDEN_CLOCKS.splitlines(), strict=True):
        assert [
            row.times[field][0].strftime("%H:%M")
            for field in (
                PrayerField.SEHRI_ENDS,
                PrayerField.MAGHRIB_BEGIN,
                PrayerField.ISHA_JAMAAT,
            )
        ] == golden.split()
    assert sum(len(row.times) for row in rows) == 341
    assert all(set(row.times) == set(ZAK_RAMADAN_COLUMNS.values()) for row in rows)


def test_first_row_all_eleven_meanings_and_published_values(pages):
    row = parsed(pages).timetable.days[0]
    assert row.times == {
        PrayerField.SEHRI_ENDS: (time(5, 37),),
        PrayerField.FAJR_BEGIN: (time(5, 42),),
        PrayerField.FAJR_JAMAAT: (time(5, 57),),
        PrayerField.SUNRISE: (time(7, 22),),
        PrayerField.DHUHR_BEGIN: (time(12, 29),),
        PrayerField.DHUHR_JAMAAT: (time(12, 40),),
        PrayerField.ASR_BEGIN: (time(15, 34),),
        PrayerField.ASR_JAMAAT: (time(16, 15),),
        PrayerField.MAGHRIB_BEGIN: (time(17, 31),),
        PrayerField.ISHA_BEGIN: (time(19, 5),),
        PrayerField.ISHA_JAMAAT: (time(19, 45),),
    }
    assert len(row.original) == 26
    assert row.original["Published Date"] == "Feb 18,…"
    assert row.original["Published Day"] == "Wed"
    assert row.original["Published Hijri"] == "1"
    assert row.original["Published Magrib Start"] == "5:31"
    assert row.original["Published Zohar Jamaat"] == "12:40"
    assert row.original["Published Asar Jamaat"] == "4:15"


def test_friday_day_label_is_not_a_jumuah_time_and_absent_fields_stay_absent(pages):
    rows = parsed(pages).timetable.days
    friday = rows[2]
    assert friday.day == date(2026, 2, 20)
    assert friday.original["Published Day"] == "ﻪﻌﻤﺟ"
    assert friday.times[PrayerField.DHUHR_JAMAAT] == (time(12, 40),)
    for row in rows:
        assert not {
            PrayerField.JUMUAH,
            PrayerField.MAGHRIB_JAMAAT,
            PrayerField.IFTAR,
            PrayerField.TARAWEEH,
            PrayerField.ISTEWA,
        } & set(row.times)


def test_ramadan_and_subsequent_eid_row_never_confirm_activation(pages):
    table = parsed(pages).timetable
    assert table.days[-1].day == date(2026, 3, 20)
    assert table.days[-1].original["Published Hijri"] == "1"
    assert resolve_day(date(2026, 2, 18), (table,), RamadanSettings()).row is None
    confirmed = RamadanSettings(
        confirmed_start=date(2026, 2, 18), confirmed_end=date(2026, 3, 19)
    )
    effective = resolve_day(date(2026, 3, 19), (table,), confirmed)
    assert effective.ramadan_active
    assert effective.row.times[PrayerField.IFTAR] == (time(18, 26),)
    assert effective.taraweeh_text == "After Isha Jamaat"
    assert PrayerField.IFTAR not in effective.ramadan_row.times
    assert not resolve_day(date(2026, 3, 20), (table,), confirmed).ramadan_active


def test_hijri_day_does_not_change_gregorian_date(pages):
    candidate = parsed(changed(pages, "Feb 18,… Wed 1 ", "Feb 18,… Wed 29 "))
    assert candidate.timetable.days[0].day == date(2026, 2, 18)
    assert candidate.timetable.days[0].original["Published Hijri"] == "29"


@pytest.mark.parametrize("count", [0, 1, 12, 13, 15])
def test_reject_incomplete_or_added_publication_pages(pages, count):
    value = (pages * 2)[:count]
    with pytest.raises(ImportValidationError):
        ZakRamadanLayout().to_csv(value)


@pytest.mark.parametrize(
    ("page", "original", "replacement"),
    [
        (0, "2026", "2027"),
        (1, "JANUARY 2026", "JANUARY 2027"),
        (1, "JANUARY 2026", "FEBRUARY 2026"),
        (1, "Zakariyya Jaam'e Masjid", "Unknown Mosque"),
        (-1, "RAMADHAN 2026", "RAMADHAN 2027"),
        (-1, "Ramadhan Kareem 1447 AH", "Ramadhan Kareem 1448 AH"),
        (-1, "DATE SEHRI FAJR ZOHAR", "DATE SEHRI FAJR JUMUAH"),
        (-1, "END START JAMAAT SUNRISE", "START END JAMAAT SUNRISE"),
        (-1, "Feb 18,… Wed 1 ", "18 Wed 1 "),
        (-1, "Feb 18,… Wed 1 ", "Feb 18,… Thu 1 "),
        (-1, "Feb 18,… Wed 1 ", "Feb 18,… Wed 0 "),
        (-1, "Mar 1, … Sun 12 ", "Apr 1, … Sun 12 "),
        (-1, "19 Thu 2 5:35", "19 Thu 2 5:99"),
        (-1, "19 Thu 2 5:35", "19 Thu 2 5:35 5:35"),
        (-1, "19 Thu 2 5:35 5:40", "19 Thu 2 5:35"),
        (-1, "5:35 5:40 5:55", "5:35 5:40 5:30"),
        (-1, "12:29 12:40 3:35", "2:29 12:40 3:35"),
        (-1, "19 Thu 2 5:35", '19 Thu 2 "'),
    ],
)
def test_reject_changed_interpretation_dates_and_cells(
    pages, page, original, replacement
):
    with pytest.raises(ImportValidationError):
        ZakRamadanLayout().to_csv(changed(pages, original, replacement, page))


def test_reject_reordered_monthly_context(pages):
    value = list(pages)
    value[1], value[2] = value[2], value[1]
    with pytest.raises(ImportValidationError):
        ZakRamadanLayout().to_csv(tuple(value))


@pytest.mark.parametrize("offset", [0, 10, 30])
def test_reject_removed_or_duplicated_dated_rows(pages, offset):
    lines = pages[-1].splitlines()
    first = next(i for i, line in enumerate(lines) if line.startswith("Feb 18,…"))
    index = first + offset
    for value in (
        lines[:index] + lines[index + 1 :],
        lines[:index] + [lines[index]] + lines[index:],
    ):
        with pytest.raises(ImportValidationError):
            ZakRamadanLayout().to_csv((*pages[:-1], "\n".join(value)))


def test_csv_header_remains_bounded_and_matches_original_cell_count(pages):
    rows = list(csv.reader(io.StringIO(ZakRamadanLayout().to_csv(pages))))
    assert len(rows) == 32
    assert len(rows[0]) == 26
    assert all(len(row) == 26 for row in rows)
