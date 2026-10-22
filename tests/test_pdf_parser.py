"""Original PDF fixtures exercise isolated extraction and explicit layout parsing."""

import base64
import importlib.util
import io
import json
import subprocess
from datetime import date, time
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

from custom_components.salah_timetable.import_model import (
    ImportCandidate,
    ImportValidationError,
)
from custom_components.salah_timetable.model import PrayerField
from custom_components.salah_timetable.pdf_parser import (
    MAX_PDF_BYTES,
    MAX_PDF_PAGES,
    MAX_TEXT_BYTES,
    MAX_WORKER_OUTPUT_BYTES,
    PDF_TIMEOUT_SECONDS,
    PdfParser,
    PipeTableLayout,
    extract_pdf_pages,
)

FIXTURES = Path(__file__).parent / "fixtures" / "pdf"


def sample_pdf():
    return (FIXTURES / "sample_table.pdf").read_bytes()


def parse_sample(content=None):
    return PdfParser().parse(
        content or sample_pdf(),
        timetable_id="annual-2026",
        kind="annual",
        year=2026,
        date_column="Date",
        columns={
            "Fajr Begin": "fajr_begin",
            "Fajr Jamaat": "fajr_jamaat",
            "Sunrise": "sunrise",
            "Jumuah": "jumuah",
        },
    )


def generate_pdf(pages):
    spec = importlib.util.spec_from_file_location(
        "pdf_fixture_generator", FIXTURES / "generate.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.make_pdf(pages)


def test_real_fixture_inspection_and_golden_extraction():
    parser = PdfParser()
    content = sample_pdf()
    assert parser.inspect(content) == (
        "Date",
        "Fajr Begin",
        "Fajr Jamaat",
        "Sunrise",
        "Jumuah",
    )
    assert parser._csv(content) == (FIXTURES / "sample_table.expected.csv").read_text()
    assert len(extract_pdf_pages(content)) == 2


def test_real_fixture_values_ditto_and_binary_provenance():
    content = sample_pdf()
    candidate = parse_sample(content)
    assert candidate.source_format == "pdf"
    assert candidate.parser_id == "pdf_table_v1"
    assert base64.b64decode(candidate.source_base64, validate=True) == content
    assert candidate.sha256 == sha256(content).hexdigest()
    assert candidate.source_text == candidate.extracted_text
    assert candidate.timetable.days[1].times[PrayerField.FAJR_JAMAAT] == (time(6, 45),)
    assert candidate.timetable.days[1].original["Fajr Jamaat"] == '"'
    assert candidate.timetable.days[1].times[PrayerField.JUMUAH] == (time(13), time(14))
    assert candidate.timetable.days[0].day == date(2026, 1, 1)
    assert PrayerField.MAGHRIB_BEGIN not in candidate.timetable.days[0].times
    assert ImportCandidate.from_dict(candidate.as_dict()) == candidate


def test_invalid_selected_year_does_not_guess():
    with pytest.raises(ImportValidationError, match="declared year"):
        PdfParser().parse(
            sample_pdf(),
            timetable_id="annual-2027",
            kind="annual",
            year=2027,
            date_column="Date",
            columns={"Fajr Begin": "fajr_begin"},
        )


@pytest.mark.parametrize(
    "content",
    [b"", b"not a pdf", b"%PDF-1.4\ninvalid", b"%PDF-" + b"x" * MAX_PDF_BYTES],
)
def test_invalid_or_oversized_pdf(content):
    with pytest.raises(ImportValidationError):
        PdfParser().inspect(content)


def test_unsupported_layout_does_not_extract_guesses():
    content = (FIXTURES / "unsupported_layout.pdf").read_bytes()
    with pytest.raises(ImportValidationError, match="Unsupported PDF layout"):
        PdfParser().inspect(content)
    with pytest.raises(ImportValidationError, match="Unsupported PDF layout"):
        PdfParser("guess-anything")


def test_encrypted_pdf_rejected_even_with_empty_password():
    reader = PdfReader(io.BytesIO(sample_pdf()))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt("")
    output = io.BytesIO()
    writer.write(output)
    with pytest.raises(ImportValidationError, match="encrypted"):
        PdfParser().inspect(output.getvalue())


def test_textless_pdf_rejected_no_ocr():
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=400)
    output = io.BytesIO()
    writer.write(output)
    with pytest.raises(ImportValidationError, match="scanned"):
        PdfParser().inspect(output.getvalue())


def test_page_limit_is_enforced_in_actual_worker():
    content = generate_pdf(
        [["Date|Fajr Begin", "2026-01-01|05:45"]] * (MAX_PDF_PAGES + 1)
    )
    with pytest.raises(ImportValidationError, match="limits"):
        PdfParser().inspect(content)


def test_compressed_stream_limit_is_enforced_in_actual_worker():
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=400)
    stream = DecodedStreamObject()
    stream.set_data(b" " * (9 * 1024 * 1024))
    page[NameObject("/Contents")] = writer._add_object(stream.flate_encode())
    output = io.BytesIO()
    writer.write(output)
    assert len(output.getvalue()) < MAX_PDF_BYTES
    with pytest.raises(ImportValidationError, match="limits"):
        PdfParser().inspect(output.getvalue())


def test_extraction_timeout_kills_worker_and_is_safe():
    with patch(
        "custom_components.salah_timetable.pdf_parser.subprocess.run",
        side_effect=subprocess.TimeoutExpired("secret-url", PDF_TIMEOUT_SECONDS),
    ) as run:
        with pytest.raises(ImportValidationError, match="time limit") as err:
            extract_pdf_pages(sample_pdf())
    assert "secret" not in str(err.value)
    assert run.call_args.kwargs["timeout"] == PDF_TIMEOUT_SECONDS
    assert run.call_args.args[0][1] == "-I"
    assert run.call_args.kwargs["stderr"] == subprocess.DEVNULL
    assert set(run.call_args.kwargs["env"]) == {"PATH", "PYTHONIOENCODING"}


def test_worker_launch_failure_is_safe():
    with (
        patch(
            "custom_components.salah_timetable.pdf_parser.subprocess.run",
            side_effect=OSError("private-path"),
        ),
        pytest.raises(ImportValidationError, match="could not start") as err,
    ):
        extract_pdf_pages(sample_pdf())
    assert "private" not in str(err.value)


@pytest.mark.parametrize(
    "payload",
    [
        b"not-json",
        b"null",
        b"{}",
        b'{"pages": []}',
        b'{"pages": [null]}',
        b'{"pages": [""]}',
        json.dumps({"pages": ["x"] * (MAX_PDF_PAGES + 1)}).encode(),
        json.dumps({"pages": ["x" * (MAX_TEXT_BYTES + 1)]}).encode(),
    ],
)
def test_worker_result_validation(payload):
    with (
        patch(
            "custom_components.salah_timetable.pdf_parser.subprocess.run",
            return_value=SimpleNamespace(returncode=0, stdout=payload),
        ),
        pytest.raises(ImportValidationError),
    ):
        extract_pdf_pages(sample_pdf())


def test_worker_output_bound():
    with (
        patch(
            "custom_components.salah_timetable.pdf_parser.subprocess.run",
            return_value=SimpleNamespace(
                returncode=0, stdout=b"x" * (MAX_WORKER_OUTPUT_BYTES + 1)
            ),
        ),
        pytest.raises(ImportValidationError, match="text limit"),
    ):
        extract_pdf_pages(sample_pdf())


@pytest.mark.parametrize(
    "pages",
    [
        ("Unknown preamble\nDate|Fajr Begin\n2026-01-01|05:45",),
        ("2026-01-01|05:45",),
        ("Date|Fajr Begin\n2026-01-01|05:45", "Date|Sunrise\n2026-01-02|08:00"),
        ("Date|Fajr Begin\n2026-01-01|05:45|extra",),
        ("Date|Fajr Begin\n01/01/2026|05:45",),
        ("Date|Fajr Begin",),
        ("Salah Timetable\nYear 2026",),
    ],
)
def test_layout_rejects_unaccounted_or_incomplete_text(pages):
    with pytest.raises(ImportValidationError):
        PipeTableLayout().to_csv(pages)


def test_repeated_header_within_page_preserves_rows():
    converted = PipeTableLayout().to_csv(
        ("Date|Fajr Begin\n2026-01-01|05:45\nDate|Fajr Begin\n2026-01-02|05:46",)
    )
    assert converted.count("Date,") == 1
    assert "2026-01-02,05:46" in converted


def test_declared_pdf_year_must_match_rows_and_other_pages():
    with pytest.raises(ImportValidationError, match="declared year"):
        PipeTableLayout().to_csv(("Year 2025\nDate|Fajr Begin\n2026-01-01|05:45",))
    with pytest.raises(ImportValidationError, match="different years"):
        PipeTableLayout().to_csv(
            (
                "Year 2026\nDate|Fajr Begin\n2026-01-01|05:45",
                "Year 2027\nDate|Fajr Begin\n2027-01-01|05:45",
            )
        )
