"""The annual source cannot be reclassified as a Ramadan override."""

from pathlib import Path

import pytest

from custom_components.salah_timetable.import_model import ImportValidationError
from custom_components.salah_timetable.pdf_parser import PdfParser
from custom_components.salah_timetable.zak_annual_layout import ZAK_ANNUAL_COLUMNS

FIXTURE = Path(__file__).parent / "fixtures/pdf/zak.pdf"


@pytest.mark.parametrize(
    "overrides",
    [
        {"kind": "ramadan"},
        {"year": 2027},
        {"date_column": "Published Date"},
        {"time_format": "12h"},
    ],
)
def test_annual_publication_requires_its_documented_interpretation(overrides):
    arguments = {
        "timetable_id": "annual-2026",
        "kind": "annual",
        "year": 2026,
        "date_column": "Date",
        "columns": ZAK_ANNUAL_COLUMNS,
        "time_format": "24h",
    }
    arguments.update(overrides)
    with pytest.raises(ImportValidationError):
        PdfParser("zak_annual_v1").parse(FIXTURE.read_bytes(), **arguments)
