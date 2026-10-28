"""Persisted import provenance and report validation."""

from datetime import date

import pytest

from custom_components.salah_timetable.csv_parser import CsvParser
from custom_components.salah_timetable.import_model import (
    ImportCandidate,
    ImportCoverage,
    ImportValidationError,
)


def candidate():
    return CsvParser().parse(
        b"Date,Fajr\n2026-01-01,05:30\n",
        timetable_id="annual-2026",
        kind="annual",
        year=2026,
        date_column="Date",
        columns={"Fajr": "fajr_begin"},
    )


def test_candidate_report_is_immutable():
    source = candidate()
    with pytest.raises(TypeError):
        source.coverage.missing_fields["sunrise"] = 0
    assert source.as_dict()["source_text"] == "Date,Fajr\n2026-01-01,05:30\n"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda data: data.update(sha256="0" * 64),
        lambda data: data.update(source_text="tampered"),
        lambda data: data.update(year=2027),
        lambda data: data.update(warnings=[]),
        lambda data: data["coverage"].update(row_count=2),
        lambda data: data["coverage"].update(missing_dates=[]),
        lambda data: data["timetable"]["days"][0].update(date="2026-02-30"),
        lambda data: data.update(timetable=[]),
        lambda data: data.update(coverage={}),
        lambda data: data["coverage"].update(missing_fields={"unknown": 1}),
        lambda data: data["coverage"].update(missing_fields={"sunrise": 0}),
    ],
)
def test_tampered_stored_candidates_are_rejected(mutation):
    data = candidate().as_dict()
    mutation(data)
    with pytest.raises(ImportValidationError, match="Stored import data"):
        ImportCandidate.from_dict(data)


@pytest.mark.parametrize(
    "options",
    [
        {"row_count": 0},
        {"start_date": date(2026, 1, 3)},
        {"missing_dates": [date(2026, 1, 2), date(2026, 1, 1)]},
        {"missing_dates": ["2026-01-01"]},
        {"missing_fields": {"fajr_begin": 2}},
        {"missing_fields": {"fajr_begin": True}},
    ],
)
def test_invalid_coverage_is_rejected(options):
    base = {
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 1, 1),
        "row_count": 1,
        "missing_dates": (),
        "missing_fields": {},
    }
    with pytest.raises(ImportValidationError):
        ImportCoverage(**(base | options))


def test_parser_provenance_is_persisted_and_immutable():
    source = candidate()
    assert source.parser_id == "csv_v1"
    assert source.date_column == "Date"
    assert source.time_format == "24h"
    assert source.columns == {"Fajr": "fajr_begin"}
    with pytest.raises(TypeError):
        source.columns["Fajr"] = "fajr_jamaat"
    restored = ImportCandidate.from_dict(source.as_dict())
    assert restored == source
    assert restored.as_dict()["columns"] == {"Fajr": "fajr_begin"}


@pytest.mark.parametrize(
    "mutation",
    [
        lambda data: data.update(parser_id="unknown_parser"),
        lambda data: data.update(time_format="guess"),
        lambda data: data.update(date_column="Unknown"),
        lambda data: data.update(columns={}),
        lambda data: data.update(columns={"Unknown": "fajr_begin"}),
        lambda data: data.update(columns={"Fajr": "unknown_field"}),
        lambda data: data.update(columns={"Fajr": "fajr_jamaat"}),
        lambda data: data.update(columns={"Date": "fajr_begin"}),
        lambda data: data.update(columns=[]),
    ],
)
def test_invalid_parser_provenance_is_rejected(mutation):
    data = candidate().as_dict()
    mutation(data)
    with pytest.raises(ImportValidationError, match="Stored import data"):
        ImportCandidate.from_dict(data)


def test_previous_publication_profile_metadata_loads_without_catalogue():
    """Removing the profile picker must not invalidate existing approved data."""
    original = candidate()
    saved = original.as_dict()
    saved["publication_profile_id"] = "mosque_a_annual_2026_v1"
    restored = ImportCandidate.from_dict(saved)
    assert restored == original
    assert "publication_profile_id" not in restored.as_dict()
