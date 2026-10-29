"""Acceptance fixtures and adversarial inputs for the manual CSV adapter."""

import csv
import io
from datetime import date, time
from pathlib import Path

import pytest

from custom_components.salah_timetable.csv_parser import (
    MAX_CELL_LENGTH,
    MAX_COLUMNS,
    CsvParser,
)
from custom_components.salah_timetable.import_model import (
    MAX_SOURCE_BYTES,
    ImportCandidate,
    ImportValidationError,
)
from custom_components.salah_timetable.model import PrayerField

FIXTURES = Path(__file__).parents[1] / "fixtures" / "csv"


def parse(content, **overrides):
    options = {
        "timetable_id": "annual-2026",
        "kind": "annual",
        "year": 2026,
        "date_column": "Date",
        "columns": {"Fajr": "fajr_begin"},
    }
    return CsvParser().parse(content, **(options | overrides))


def make_csv(rows):
    output = io.StringIO(newline="")
    csv.writer(output).writerows(rows)
    return output.getvalue().encode()


def test_annual_fixture_preserves_source_and_resolves_only_explicit_ditto():
    content = (FIXTURES / "annual.csv").read_bytes()
    parser = CsvParser()
    assert parser.inspect(content) == (
        "Date",
        "Fajr Start",
        "Fajr Jamaat",
        "Zuhr Start",
        "Zuhr Jamaat",
        "Jumu'ah",
        "Notes",
    )
    candidate = parse(
        content,
        columns={
            "Fajr Start": "fajr_begin",
            "Fajr Jamaat": "fajr_jamaat",
            "Zuhr Start": "dhuhr_begin",
            "Zuhr Jamaat": "dhuhr_jamaat",
            "Jumu'ah": "jumuah",
        },
    )
    rows = candidate.timetable.days
    assert rows[1].times[PrayerField.FAJR_JAMAAT] == (time(6, 15),)
    assert rows[1].times[PrayerField.DHUHR_JAMAAT] == (time(13),)
    assert rows[1].times[PrayerField.JUMUAH] == (time(13), time(14))
    assert rows[1].original["Fajr Jamaat"] == '"'
    assert rows[0].original["Notes"] == "Annual source, preserved"
    assert candidate.source_text.encode() == content
    assert candidate.coverage.row_count == 3
    assert len(candidate.coverage.missing_dates) == 362
    assert candidate.coverage.missing_fields["jumuah"] == 2
    assert candidate.coverage.missing_fields["isha_begin"] == 3
    assert "fajr_begin" not in candidate.coverage.missing_fields
    assert len(candidate.warnings) == 2
    assert ImportCandidate.from_dict(candidate.as_dict()) == candidate


def test_ramadan_fixture_uses_exact_dates_and_keeps_missing_events_absent():
    candidate = parse(
        (FIXTURES / "ramadan.csv").read_bytes(),
        timetable_id="ramadan-2028",
        kind="ramadan",
        year=2028,
        columns={
            "Sehri ends": "sehri_ends",
            "Iftar": "iftar",
            "Taraweeh": "taraweeh",
            "Maghrib Start": "maghrib_begin",
        },
    )
    assert candidate.coverage.missing_dates == (date(2028, 3, 1),)
    assert candidate.coverage.start_date == date(2028, 2, 28)
    assert candidate.coverage.end_date == date(2028, 3, 2)
    assert PrayerField.TARAWEEH not in candidate.timetable.days[0].times
    assert PrayerField.IFTAR not in candidate.timetable.days[-1].times
    assert PrayerField.MAGHRIB_BEGIN in candidate.timetable.days[-1].times


def test_utf8_bom_retained_and_checksum_survives_serialization():
    content = b"\xef\xbb\xbfDate,Fajr\r\n2026-01-01,05:45\r\n"
    candidate = parse(content)
    assert candidate.source_text.startswith("\ufeff")
    assert CsvParser().inspect(content) == ("Date", "Fajr")
    assert ImportCandidate.from_dict(candidate.as_dict()) == candidate


def test_explicit_ampm_fixture():
    candidate = parse(
        (FIXTURES / "explicit_ampm.csv").read_bytes(),
        year=2027,
        time_format="12h",
        columns={
            "Fajr Start": "fajr_begin",
            "Zuhr Jamaat": "dhuhr_jamaat",
            "Isha Jamaat": "isha_jamaat",
        },
    )
    assert candidate.timetable.days[0].times[PrayerField.DHUHR_JAMAAT] == (time(13),)
    assert candidate.timetable.days[0].times[PrayerField.ISHA_JAMAAT] == (time(20),)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("12:00 AM", time(0)),
        ("12:00 PM", time(12)),
        ("01:23 AM", time(1, 23)),
        ("11:59 PM", time(23, 59)),
    ],
)
def test_ampm_boundaries(value, expected):
    assert parse(
        make_csv([["Date", "Fajr"], ["2026-01-01", value]]), time_format="12h"
    ).timetable.days[0].times[PrayerField.FAJR_BEGIN] == (expected,)


@pytest.mark.parametrize(
    ("value", "time_format"),
    [
        ("24:00", "24h"),
        ("7:30", "24h"),
        ("07:30 PM", "24h"),
        ("13:30 PM", "12h"),
        ("07:30", "12h"),
        ("00:00 AM", "12h"),
        ("7:30 AM", "12h"),
        ("07:30 am", "12h"),
    ],
)
def test_time_interpretation_is_never_guessed(value, time_format):
    with pytest.raises(ImportValidationError, match="selected time format"):
        parse(
            make_csv([["Date", "Fajr"], ["2026-01-01", value]]), time_format=time_format
        )


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"Date,Fajr\n",
        b"Date,Fajr\n2026-01-01,\xff\n",
        b"Date,Fajr\n2026-01-01,05:30\x00\n",
        b"Date,Fajr\n2026-01-01,\x7f\n",
        b'"Date,Fajr\n2026-01-01,05:30\n',
        b"Date,Fajr\n2026-01-01,05:30,extra\n",
        b"Date,Fajr\n2026-01-01\n",
        b"Date,Fajr,Fajr\n2026-01-01,05:30,06:00\n",
        b"Date,\n2026-01-01,05:30\n",
        b"Date, Fajr\n2026-01-01,05:30\n",
    ],
)
def test_invalid_csv_shape_encoding_and_controls(content):
    with pytest.raises(ImportValidationError):
        CsvParser().inspect(content)


def test_limits_are_enforced_before_parse():
    with pytest.raises(ImportValidationError, match="512 KiB"):
        CsvParser().inspect(b"x" * (MAX_SOURCE_BYTES + 1))
    with pytest.raises(ImportValidationError, match="1–32"):
        CsvParser().inspect(
            make_csv(
                [
                    [f"c{n}" for n in range(MAX_COLUMNS + 1)],
                    ["" for n in range(MAX_COLUMNS + 1)],
                ]
            )
        )
    with pytest.raises(ImportValidationError, match="256"):
        CsvParser().inspect(
            make_csv([["Date", "Fajr"], ["2026-01-01", "x" * (MAX_CELL_LENGTH + 1)]])
        )
    with pytest.raises(ImportValidationError, match="366"):
        CsvParser().inspect(
            make_csv([["Date", "Fajr"]] + [["2026-01-01", "05:30"]] * 367)
        )


@pytest.mark.parametrize(
    "value",
    ["2026-02-29", "2028-02-29", "2026-13-01", "20260101", "01/01/2026", "01-01", ""],
)
def test_dates_are_explicit_valid_and_in_declared_year(value):
    with pytest.raises(ImportValidationError):
        parse(make_csv([["Date", "Fajr"], [value, "05:30"]]))


def test_leap_year_coverage():
    candidate = parse(b"Date,Fajr\n2028-02-29,05:30\n", year=2028)
    assert len(candidate.coverage.missing_dates) == 365
    assert date(2028, 2, 29) not in candidate.coverage.missing_dates


@pytest.mark.parametrize(
    "rows",
    [
        [["2026-01-01", "05:30"], ["2026-01-01", "05:31"]],
        [["2026-01-02", "05:30"], ["2026-01-01", "05:31"]],
    ],
)
def test_duplicate_or_unsorted_dates_are_rejected(rows):
    with pytest.raises(ImportValidationError, match="unique and in increasing order"):
        parse(make_csv([["Date", "Fajr"]] + rows))


@pytest.mark.parametrize("field", ["fajr_begin", "sunrise", "iftar", "jumuah"])
def test_quotation_marks_cannot_fill_non_jamaat_fields(field):
    content = make_csv([["Date", "Fajr"], ["2026-01-01", "05:30"], ["2026-01-02", '"']])
    with pytest.raises(ImportValidationError, match="unresolved"):
        parse(content, columns={"Fajr": field})


@pytest.mark.parametrize("prior_values", [[], [""], ["06:30", ""]])
def test_ditto_needs_prior_explicit_nonblank_value_in_same_column(prior_values):
    rows = [
        [f"2026-01-{n:02}", "05:30", value]
        for n, value in enumerate([*prior_values, '"'], start=1)
    ]
    content = make_csv([["Date", "Fajr", "Jamaat"], *rows])
    with pytest.raises(ImportValidationError, match="unresolved"):
        parse(content, columns={"Fajr": "fajr_begin", "Jamaat": "fajr_jamaat"})


def test_repeated_ditto_uses_last_explicit_same_column():
    candidate = parse(
        make_csv(
            [
                ["Date", "Fajr", "Jamaat"],
                ["2026-01-01", "05:30", "06:30"],
                ["2026-01-02", "05:31", '"'],
                ["2026-01-03", "05:32", "”"],
            ]
        ),
        columns={"Fajr": "fajr_begin", "Jamaat": "fajr_jamaat"},
    )
    assert all(
        row.times[PrayerField.FAJR_JAMAAT] == (time(6, 30),)
        for row in candidate.timetable.days
    )
    assert candidate.timetable.days[2].times[PrayerField.FAJR_BEGIN] == (time(5, 32),)


@pytest.mark.parametrize("times", ["14:00;13:00", "13:00;13:00", "13:00;"])
def test_jumuah_events_must_be_distinct_ordered_explicit_times(times):
    with pytest.raises(ImportValidationError):
        parse(
            make_csv([["Date", "Fajr"], ["2026-01-01", times]]),
            columns={"Fajr": "jumuah"},
        )


@pytest.mark.parametrize(
    "options",
    [
        {"columns": {}},
        {"date_column": "Absent"},
        {"columns": {"Date": "fajr_begin"}},
        {"columns": {"Fajr": "unknown"}},
        {"columns": {"Unknown": "fajr_begin"}},
        {"columns": {"Fajr": "fajr_begin", "Other": "fajr_begin"}},
        {"year": True},
        {"year": 0},
        {"time_format": "guess"},
        {"kind": "unknown"},
    ],
)
def test_invalid_mapping_and_metadata(options):
    with pytest.raises(ImportValidationError):
        parse(b"Date,Fajr,Other\n2026-01-01,05:30,06:00\n", **options)


def test_rows_without_mapped_prayer_times_are_rejected():
    with pytest.raises(ImportValidationError, match="no published prayer"):
        parse(b"Date,Fajr,Notes\n2026-01-01,,missing source\n")


def test_blank_lines_are_not_counted_as_dated_rows():
    candidate = parse(b"Date,Fajr\n\n2026-01-01,05:30\n\n")
    assert candidate.coverage.row_count == 1


def test_original_raw_values_survive_normalization():
    candidate = parse(b"Date,Fajr,Notes\n2026-01-01, 05:30 ,  mosque source  \n")
    row = candidate.timetable.days[0]
    assert row.times[PrayerField.FAJR_BEGIN] == (time(5, 30),)
    assert row.original["Fajr"] == " 05:30 "
    assert row.original["Notes"] == "  mosque source  "
