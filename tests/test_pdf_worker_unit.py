"""Exercise the PDF worker's decisions without weakening real-process isolation.

Existing parser tests still launch python -I and enforce subprocess sandboxing.
This suite instruments worker.main in-process with mocked I/O and rlimits so
coverage can see each bounded/rejected path.
"""

import io
import json
import runpy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pypdf
import pytest

from custom_components.salah_timetable import pdf_worker


class FakePage:
    """Expose only the page methods the isolated extractor is allowed to use."""

    def __init__(self, text="Date|Fajr Begin", stream=b"BT ET"):
        self.text = text
        self.stream = stream

    def get_contents(self):
        if self.stream is None:
            return None
        return SimpleNamespace(get_data=lambda: self.stream)

    def extract_text(self):
        return self.text


@pytest.fixture
def bounded_worker(monkeypatch):
    """Prevent in-process rlimits and restore pypdf filter constants afterward."""
    applied_limits = []
    monkeypatch.setattr(
        pdf_worker.resource,
        "setrlimit",
        lambda name, limits: applied_limits.append((name, limits)),
    )
    for name in (
        "FLATE_MAX_BUFFER_SIZE",
        "JBIG2_MAX_OUTPUT_LENGTH",
        "LZW_MAX_OUTPUT_LENGTH",
        "MAX_ARRAY_BASED_STREAM_OUTPUT_LENGTH",
        "MAX_DECLARED_STREAM_LENGTH",
        "RUN_LENGTH_MAX_OUTPUT_LENGTH",
        "ZLIB_MAX_OUTPUT_LENGTH",
        "FLATE_MAX_COLUMNS",
        "FLATE_MAX_ROW_LENGTH",
        "ZLIB_MAX_RECOVERY_INPUT_LENGTH",
    ):
        monkeypatch.setattr(pypdf.filters, name, getattr(pypdf.filters, name))
    output = io.StringIO()
    monkeypatch.setattr(pdf_worker.sys, "stdout", output)
    return applied_limits, output


def configure_worker(monkeypatch, *, content=b"%PDF-1.7\n", pages=None, encrypted=False):
    """Feed fake pages while exercising the real worker bounds."""
    monkeypatch.setattr(
        pdf_worker.sys, "stdin", SimpleNamespace(buffer=io.BytesIO(content))
    )
    reader = SimpleNamespace(
        is_encrypted=encrypted,
        pages=[FakePage()] if pages is None else pages,
    )
    monkeypatch.setattr(pypdf, "PdfReader", lambda *_args, **_kwargs: reader)


def test_valid_pages_produce_unicode_json_and_hard_limits(monkeypatch, bounded_worker):
    applied_limits, output = bounded_worker
    configure_worker(
        monkeypatch, pages=[FakePage("الفجر"), FakePage("Fajr 05:30")]
    )
    assert pdf_worker.main() == 0
    assert json.loads(output.getvalue()) == {"pages": ["الفجر", "Fajr 05:30"]}
    assert len(applied_limits) == 4
    assert pypdf.filters.FLATE_MAX_BUFFER_SIZE == 8 * 1024 * 1024
    assert pypdf.filters.FLATE_MAX_COLUMNS == 1024


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"not a PDF",
        b"%PDF-" + b"x" * (pdf_worker.MAX_PDF_BYTES - 4),
    ],
)
def test_invalid_input_is_rejected_before_parsing(
    monkeypatch, bounded_worker, content
):
    _limits, output = bounded_worker
    configure_worker(monkeypatch, content=content)
    assert pdf_worker.main() == 2
    assert output.getvalue() == ""


@pytest.mark.parametrize(
    ("pages", "encrypted"),
    [
        ([], False),
        ([FakePage()] * (pdf_worker.MAX_PAGES + 1), False),
        ([FakePage()], True),
        ([FakePage(stream=None)], False),
        ([FakePage(stream=b"x" * (pdf_worker.MAX_PAGE_STREAM_BYTES + 1))], False),
        ([FakePage(text="")], False),
        ([FakePage(text="   ")], False),
        ([FakePage(text=None)], False),
        ([FakePage(text="x" * (pdf_worker.MAX_TEXT_BYTES + 1))], False),
        ([FakePage(text="x" * pdf_worker.MAX_TEXT_BYTES), FakePage("a")], False),
    ],
    ids=[
        "no-pages",
        "too-many-pages",
        "encrypted",
        "no-content-stream",
        "oversized-stream",
        "empty-text",
        "whitespace-only",
        "non-string-text",
        "single-page-overflow",
        "combined-text-overflow",
    ],
)
def test_untrusted_pdf_page_bounds_reject_without_output(
    monkeypatch, bounded_worker, pages, encrypted
):
    _limits, output = bounded_worker
    configure_worker(monkeypatch, pages=pages, encrypted=encrypted)
    assert pdf_worker.main() == 2
    assert output.getvalue() == ""


def test_invalid_pdf_worker_standalone_exit_leaks_nothing(monkeypatch, bounded_worker):
    """The standalone exception handler never prints untrusted document text."""
    _limits, output = bounded_worker
    configure_worker(monkeypatch)
    monkeypatch.setattr(
        pypdf,
        "PdfReader",
        Mock(side_effect=RuntimeError("SECRET PDF contents and private path")),
    )
    worker_path = Path(pdf_worker.__file__)
    with pytest.raises(SystemExit) as error:
        runpy.run_path(str(worker_path), run_name="__main__")
    assert error.value.code == 2
    assert output.getvalue() == ""
