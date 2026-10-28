"""Remote source and redacted check metadata validation boundaries."""

from collections.abc import Mapping

import pytest

from custom_components.salah_timetable.download import DownloadError
from custom_components.salah_timetable.import_model import ImportValidationError
from custom_components.salah_timetable.source_model import (
    RemoteSource,
    validate_check,
    validate_source_url,
    validate_validator,
)

SOURCE = {
    "source_id": "annual-2026",
    "url": "https://example.org/prayer-times.csv",
    "media_type": "csv",
    "kind": "annual",
    "year": 2026,
    "date_column": "Date",
    "columns": {"Fajr": "fajr_begin"},
    "time_format": "24h",
    "parser_id": "csv_v1",
}


def test_remote_source_round_trip_preserves_immutable_mapping():
    source = RemoteSource(**SOURCE)
    assert source.as_dict() == SOURCE
    assert RemoteSource.from_dict(source.as_dict()) == source
    with pytest.raises(TypeError):
        source.columns["Other"] = "isha_begin"


@pytest.mark.parametrize(
    "changes",
    [
        {"source_id": ""},
        {"source_id": "a/b"},
        {"media_type": "other"},
        {"kind": "weekly"},
        {"year": True},
        {"year": 0},
        {"year": 10000},
        {"time_format": "guess"},
        {"parser_id": "pdf_table_v1"},
        {"date_column": ""},
        {"date_column": " "},
        {"columns": {}},
        {"columns": {"Date": "fajr_begin"}},
        {"columns": {"Fajr": "fajr_begin", "Duplicate": "fajr_begin"}},
        {"columns": {"Fajr": "unknown_event"}},
        {"columns": {"": "fajr_begin"}},
        {"columns": None},
    ],
    ids=[
        "missing-source-id",
        "unsafe-source-id",
        "invalid-media-type",
        "invalid-kind",
        "boolean-year",
        "low-year",
        "high-year",
        "unsupported-time-format",
        "wrong-parser-for-csv",
        "empty-date-column",
        "blank-date-column",
        "empty-column-map",
        "date-column-collision",
        "duplicate-prayer-field",
        "unknown-prayer-field",
        "empty-source-heading",
        "missing-column-map",
    ],
)
def test_remote_source_rejects_invalid_profiles(changes):
    with pytest.raises(ImportValidationError):
        RemoteSource(**{**SOURCE, **changes})


def test_stored_source_requires_all_reproducibility_fields():
    missing = SOURCE.copy()
    missing.pop("parser_id")
    with pytest.raises(ImportValidationError, match="Stored remote source"):
        RemoteSource.from_dict(missing)


@pytest.mark.parametrize(
    ("bad_url", "error_type"),
    [
        (42, ImportValidationError),
        ("x" * 2049, ImportValidationError),
        ("http://example.org/test.csv", DownloadError),
    ],
)
def test_source_url_validation_rejects_invalid_input(bad_url, error_type):
    with pytest.raises(error_type):
        validate_source_url(bad_url)


@pytest.mark.parametrize("bad_validator", [7, "x" * 513, "has\nnewline", "has\x7fdel"])
def test_http_validator_disallows_unsafe_values(bad_validator):
    with pytest.raises(ImportValidationError, match="Invalid HTTP validator"):
        validate_validator(bad_validator)


def test_check_metadata_accepts_only_immutable_safe_fields():
    digest = "a" * 64
    stored = {
        "status": "approved",
        "last_checked": "2026-10-27T20:00:00+00:00",
        "last_success": "2026-10-27T20:00:00+00:00",
        "last_seen_sha256": digest,
        "rejected_sha256": None,
        "etag": '"revision-1"',
        "last_modified": None,
        "error_code": "not_found",
    }
    validated = validate_check(stored)
    assert isinstance(validated, Mapping)
    assert dict(validated) == stored
    with pytest.raises(TypeError):
        validated["status"] = "error"


@pytest.mark.parametrize(
    "invalid",
    [
        None,
        [],
        {"url": "https://example.org/secret"},
        {"status": "unexpected"},
        {"status": []},
        {"status": {"nested": True}},
        {"last_checked": "not-a-time"},
        {"last_checked": "2026-10-27T20:00:00"},
        {"last_checked": 1},
        {"last_success": "2026-10-27T20:00:00"},
        {"last_success": "x" * 41},
        {"last_seen_sha256": "a" * 63},
        {"rejected_sha256": "A" * 64},
        {"etag": "has\rreturn"},
        {"last_modified": "x" * 513},
        {"error_code": "Invalid-Code"},
        {"error_code": []},
    ],
    ids=[
        "not-mapping-none",
        "not-mapping-array",
        "unallowlisted-url",
        "unknown-status",
        "unhashable-status-array",
        "unhashable-status-map",
        "invalid-timestamp",
        "naive-checked-time",
        "wrong-timestamp-type",
        "naive-success-time",
        "oversized-timestamp",
        "short-sha256",
        "uppercase-sha256",
        "validator-control-character",
        "oversized-validator",
        "noncanonical-error-code",
        "unhashable-error-code",
    ],
)
def test_check_metadata_rejects_malformed_or_sensitive_values(invalid):
    with pytest.raises(ImportValidationError):
        validate_check(invalid)
