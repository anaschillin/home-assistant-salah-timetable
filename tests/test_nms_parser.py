"""The NMS adapter's semantic field contract survives the PDF parser boundary."""

from pathlib import Path

import pytest

from custom_components.salah_timetable.import_model import (
    ImportCandidate,
    ImportValidationError,
)
from custom_components.salah_timetable.nms_layout import NMS_COLUMNS
from custom_components.salah_timetable.pdf_parser import PdfParser
from custom_components.salah_timetable.source_model import RemoteSource

FIXTURE = Path(__file__).parent / "fixtures/pdf/nms_synthetic_2026.pdf"


@pytest.mark.parametrize(
    "override",
    [
        {"kind": "ramadan"},
        {"year": 2027},
        {"date_column": "Published Day"},
        {"time_format": "12h"},
        {"columns": {"Fajr Begin": "isha_begin"}},
        {"columns": {"Published Dawn": "fajr_begin"}},
    ],
)
def test_reject_wrong_nms_source_interpretation(override):
    arguments = {
        "timetable_id": "annual-2026",
        "kind": "annual",
        "year": 2026,
        "date_column": "Date",
        "columns": NMS_COLUMNS,
        "time_format": "24h",
    }
    arguments.update(override)
    with pytest.raises(ImportValidationError):
        PdfParser("nms_annual_v1").parse(FIXTURE.read_bytes(), **arguments)


def test_subset_mapping_preserves_provenance_and_source_profile():
    mapping = {"Fajr Begin": "fajr_begin", "Iftar": "iftar"}
    candidate = PdfParser("nms_annual_v1").parse(
        FIXTURE.read_bytes(),
        timetable_id="annual-2026",
        kind="annual",
        year=2026,
        date_column="Date",
        columns=mapping,
    )
    assert len(candidate.timetable.days) == 365
    assert set(candidate.timetable.days[0].times) == {"fajr_begin", "iftar"}
    assert len(candidate.timetable.days[0].original) == 32
    assert ImportCandidate.from_dict(candidate.as_dict()) == candidate
    source = RemoteSource(
        "annual-2026",
        "https://mosque.example.org/annual.pdf",
        "pdf",
        "annual",
        2026,
        "Date",
        mapping,
        parser_id="nms_annual_v1",
    )
    assert RemoteSource.from_dict(source.as_dict()) == source
