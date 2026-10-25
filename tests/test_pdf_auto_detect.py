"""Strict auto-recognition selects only one inspected PDF adapter per source type."""

from pathlib import Path
from unittest.mock import patch

import pytest

from custom_components.salah_timetable import pdf_parser
from custom_components.salah_timetable.import_model import ImportValidationError
from custom_components.salah_timetable.pdf_parser import PdfParser

FIXTURES = Path(__file__).parent / "fixtures" / "pdf"


@pytest.mark.parametrize(
    ("file", "import_type", "layout"),
    [
        ("nms_synthetic_2026.pdf", "annual", "nms_annual_v1"),
        ("nms ramadhan.pdf", "monthly", "nms_monthly_v1"),
        ("nms ramadhan.pdf", "ramadan", "nms_monthly_v1"),
        ("zak.pdf", "annual", "zak_annual_v1"),
        ("zak.pdf", "ramadan", "zak_ramadan_v1"),
        ("sample_table.pdf", "annual", "pdf_table_v1"),
        ("sample_table.pdf", "monthly", "pdf_table_v1"),
        ("sample_table.pdf", "ramadan", "pdf_table_v1"),
    ],
)
def test_detects_supported_pdf_and_retains_concrete_layout(
    file, import_type, layout
):
    content = (FIXTURES / file).read_bytes()
    parser = PdfParser(layout_id="auto", import_type=import_type)
    with patch.object(
        pdf_parser, "extract_pdf_pages", wraps=pdf_parser.extract_pdf_pages
    ) as extractor:
        assert "Date" in parser.inspect(content)
        extractor.assert_called_once_with(content)
    assert parser.layout_id == layout


@pytest.mark.parametrize(
    ("file", "import_type"),
    [
        ("nms ramadhan.pdf", "annual"),
        ("nms_synthetic_2026.pdf", "monthly"),
        ("zak.pdf", "monthly"),
    ],
)
def test_recognized_pdf_rejects_mismatched_type(file, import_type):
    parser = PdfParser("auto", import_type=import_type)
    with pytest.raises(ImportValidationError, match="does not match"):
        parser.inspect((FIXTURES / file).read_bytes())
    assert parser.layout_id == "auto"


def test_unknown_pdf_is_rejected_instead_of_guessing():
    parser = PdfParser("auto", import_type="annual")
    with pytest.raises(ImportValidationError, match="Unsupported PDF layout"):
        parser.inspect((FIXTURES / "unsupported_layout.pdf").read_bytes())
    assert parser.layout_id == "auto"


def test_ambiguous_pdf_is_rejected_without_selecting_an_adapter(monkeypatch):
    valid_csv = (FIXTURES / "sample_table.expected.csv").read_text()

    class FakeLayout:
        def to_csv(self, _pages):
            return valid_csv

    monkeypatch.setattr(
        pdf_parser,
        "_LAYOUTS",
        {"nms_annual_v1": FakeLayout(), "zak_annual_v1": FakeLayout()},
    )
    monkeypatch.setattr(pdf_parser, "extract_pdf_pages", lambda _content: ("page",))
    parser = PdfParser("auto", import_type="annual")
    with pytest.raises(ImportValidationError, match="Ambiguous PDF layout"):
        parser.inspect(b"%PDF-")
    assert parser.layout_id == "auto"


def test_auto_parsing_keeps_real_layout_provenance_and_unmodified_times():
    content = (FIXTURES / "sample_table.pdf").read_bytes()
    parser = PdfParser("auto", import_type="monthly")
    candidate = parser.parse(
        content,
        timetable_id="annual-2026",
        kind="annual",
        year=2026,
        date_column="Date",
        columns={"Fajr Begin": "fajr_begin", "Sunrise": "sunrise"},
    )
    assert candidate.parser_id == "pdf_table_v1"
    assert parser.layout_id == "pdf_table_v1"
    assert candidate.timetable.kind == "annual"
    assert candidate.timetable.days[0].original["Fajr Begin"]


def test_rejects_unrecognized_source_type_before_parsing():
    with pytest.raises(ImportValidationError, match="Unsupported timetable type"):
        PdfParser("auto", import_type="weekly")
