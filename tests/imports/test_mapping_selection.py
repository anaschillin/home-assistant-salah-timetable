"""Focused tests for the pure column mapping selector used by import flows."""

import pytest

from custom_components.salah_timetable.imports.import_flow import CsvImportOptionsFlow


def test_mapping_selection_retains_published_source_header_order():
    assert CsvImportOptionsFlow._selected_columns(
        {
            "date_column": "Published date",
            "fajr_begin": "Dawn",
            "fajr_jamaat": "Congregation",
            "isha_begin": "__ignore__",
        }
    ) == {"Dawn": "fajr_begin", "Congregation": "fajr_jamaat"}


@pytest.mark.parametrize(
    "mapping",
    [
        {"date_column": "Date"},
        {"date_column": "Date", "fajr_begin": "Date"},
        {"date_column": "Date", "fajr_begin": "Dawn", "isha_begin": "Dawn"},
    ],
    ids=["no-prayer-fields", "date-column-collision", "duplicate-time-column"],
)
def test_mapping_selection_rejects_empty_or_ambiguous_mappings(mapping):
    assert CsvImportOptionsFlow._selected_columns(mapping) is None
