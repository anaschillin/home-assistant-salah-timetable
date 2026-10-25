"""Golden and malformed-layout checks for the inspected NMS annual structure."""

import csv
import importlib.util
import io
from datetime import date, time
from pathlib import Path

import pytest

from custom_components.salah_timetable.csv_parser import CsvParser
from custom_components.salah_timetable.import_model import ImportValidationError
from custom_components.salah_timetable.model import PrayerField
from custom_components.salah_timetable.nms_layout import NMS_COLUMNS, NmsLayout
from custom_components.salah_timetable.pdf_parser import extract_pdf_pages

FIXTURES = Path(__file__).parent / "fixtures" / "pdf"


def fixture_data(year=2026):
    spec = importlib.util.spec_from_file_location(
        "nms_fixture_generator", FIXTURES / "nms_generate.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.synthetic_data(year)


def text_pages(year=2026):
    return tuple("\n".join(lines) for lines in fixture_data(year)[0])


def parsed(pages=None, year=2026):
    content = NmsLayout().to_csv(pages or text_pages(year)).encode()
    return CsvParser().parse(
        content,
        timetable_id=f"annual-{year}",
        kind="annual",
        year=year,
        date_column="Date",
        columns=NMS_COLUMNS,
    )


def mutate_line(pages, page, original, replacement):
    changed = list(pages)
    assert original in changed[page]
    changed[page] = changed[page].replace(original, replacement, 1)
    return tuple(changed)


def test_real_pdf_golden_extraction():
    pages = extract_pdf_pages((FIXTURES / "nms_synthetic_2026.pdf").read_bytes())
    assert len(pages) == 14
    assert (
        NmsLayout().to_csv(pages)
        == (FIXTURES / "nms_synthetic_2026.expected.csv").read_text()
    )


def test_full_year_exact_values_friday_and_published_iftar():
    result = parsed()
    assert len(result.timetable.days) == 365
    assert result.coverage.missing_dates == ()
    rows = {row.day: row for row in result.timetable.days}
    friday = rows[date(2026, 1, 2)]
    assert friday.times[PrayerField.JUMUAH] == (time(13, 35),)
    assert PrayerField.DHUHR_JAMAAT not in friday.times
    saturday = rows[date(2026, 1, 3)]
    assert saturday.times[PrayerField.DHUHR_JAMAAT] == (time(13, 45),)
    assert PrayerField.JUMUAH not in saturday.times
    assert friday.times[PrayerField.MAGHRIB_BEGIN] == (time(18, 17),)
    assert (
        friday.times[PrayerField.MAGHRIB_JAMAAT]
        == friday.times[PrayerField.IFTAR]
        == (time(18, 22),)
    )
    assert saturday.times[PrayerField.ISHA_JAMAAT] == (time(20, 40),)
    assert rows[date(2026, 1, 5)].times[PrayerField.ISHA_JAMAAT] == (time(21, 7),)
    assert rows[date(2026, 4, 1)].times[PrayerField.ISTEWA] == (time(13, 5),)
    assert rows[date(2026, 10, 1)].times[PrayerField.ISTEWA] == (time(11, 45),)
    assert rows[date(2026, 10, 1)].times[PrayerField.DHUHR_BEGIN] == (time(11, 52),)
    assert rows[date(2026, 12, 31)].times[PrayerField.ISTEWA] == (time(12, 5),)


def test_preserved_raw_values_and_no_khutbah_congregation():
    row = parsed().timetable.days[1]
    assert len(row.original) == 32
    assert row.original["Published Second Khutbah"] == "16:15"
    assert row.original["Published Fajr Jamaat"] == '"'
    assert row.original["Published Dawn"] == "5:07"
    assert row.original["Published Dhuhr or Jumuah"] == "1:35"
    assert row.times[PrayerField.JUMUAH] != (time(16, 15),)
    assert PrayerField.TARAWEEH not in row.times


def test_curly_ditto_preserves_same_physical_column():
    pages = tuple(page.replace('"', "“") for page in text_pages())
    result = parsed(pages)
    assert result.timetable.days[1].original["Published Fajr Jamaat"] == "“"
    assert result.timetable.days[1].times[PrayerField.FAJR_JAMAAT] == (time(6, 5),)


def test_leap_year_has_february_29():
    result = parsed(year=2028)
    assert len(result.timetable.days) == 366
    assert any(row.day == date(2028, 2, 29) for row in result.timetable.days)


@pytest.mark.parametrize("count", [0, 1, 12, 13, 15])
def test_reject_missing_or_extra_pages(count):
    pages = text_pages()
    changed = pages[:count] if count <= 14 else pages + (pages[-1],)
    with pytest.raises(ImportValidationError, match="fourteen|twelve"):
        NmsLayout().to_csv(changed)


@pytest.mark.parametrize(
    ("page", "old", "new", "message"),
    [
        (0, "2026", "2027", "agree with the cover"),
        (0, "SALAH TIMETABLE", "OTHER TIMETABLE", "cover"),
        (1, "Nuneaton Muslim Society", "Different Mosque", "contact"),
        (2, "January 2026", "February 2026", "ordered"),
        (2, "Sunset Esha", "Iftar Esha", "columns"),
        (2, "1 Thu 10", "1 Fri 10", "weekday"),
        (2, "1 Thu 10", "2 Thu 10", "date"),
        (2, "1 Thu 10", "1 Thu 31", "Hijri"),
        (2, "1 Thu 10 5:00", "1 Thu 10 5:60", "invalid published"),
        (2, "1 Thu 10 5:00", '1 Thu 10 "', "quotation mark"),
        (2, "7:00 12:05", "7:00 2:05", "noon column"),
        (2, "3:15 6:17", "9:15 6:17", "daily order"),
        (2, "6:05 1:45 4:20", "8:05 1:45 4:20", "Jamaat"),
    ],
)
def test_malformed_source_fails_closed(page, old, new, message):
    pages = mutate_line(text_pages(), page, old, new)
    with pytest.raises(ImportValidationError, match=message):
        NmsLayout().to_csv(pages)


def test_missing_row_or_extra_cell_rejected():
    pages = list(text_pages())
    lines = pages[2].splitlines()
    first = next(i for i, line in enumerate(lines) if line.startswith("1 Thu"))
    removed = pages.copy()
    removed[2] = "\n".join(lines[:first] + lines[first + 1 :])
    with pytest.raises(ImportValidationError, match="every dated row"):
        NmsLayout().to_csv(tuple(removed))
    lines[first] += " 9:00"
    pages[2] = "\n".join(lines)
    with pytest.raises(ImportValidationError, match="thirteen"):
        NmsLayout().to_csv(tuple(pages))


def test_table_interruption_rejected():
    pages = text_pages()
    changed = mutate_line(
        pages, 2, "2 Fri 11", "Unexpected table interruption\n2 Fri 11"
    )
    with pytest.raises(ImportValidationError, match="every dated row"):
        NmsLayout().to_csv(changed)


def test_each_month_needs_explicit_first_jamaat():
    pages = text_pages()
    changed = mutate_line(pages, 2, "6:05 1:45 4:20", '" 1:45 4:20')
    with pytest.raises(ImportValidationError, match="no preceding explicit"):
        NmsLayout().to_csv(changed)


def test_no_duplicate_canonical_columns_or_inferred_fields():
    rows = list(csv.DictReader(io.StringIO(NmsLayout().to_csv(text_pages()))))
    assert len(rows[0]) == 32
    assert "Taraweeh" not in rows[0]
    assert set(NMS_COLUMNS.values()) == {field.value for field in PrayerField} - {
        "taraweeh"
    }
