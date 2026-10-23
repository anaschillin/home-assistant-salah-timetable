"""Bounded PDF adapters; only explicitly tested text layouts are supported."""

import base64
import csv
import io
import json
import os
import re
import subprocess
import sys
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from threading import BoundedSemaphore
from typing import Protocol

from .csv_parser import CsvParser
from .import_model import MAX_PDF_BYTES, ImportCandidate, ImportValidationError
from .nms_layout import NMS_COLUMNS, NmsLayout
from .nms_monthly_layout import NMS_MONTHLY_COLUMNS, NmsMonthlyLayout
from .zak_annual_layout import ZAK_ANNUAL_COLUMNS, ZakAnnualLayout
from .zak_ramadan_layout import ZAK_RAMADAN_COLUMNS, ZakRamadanLayout

MAX_PDF_PAGES = 16
MAX_TEXT_BYTES = 256 * 1024
MAX_WORKER_OUTPUT_BYTES = 2 * MAX_TEXT_BYTES + 1024
PDF_TIMEOUT_SECONDS = 8
_WORKERS = BoundedSemaphore(2)


class PdfLayout(Protocol):
    """A layout adapter must account for every extracted, nonempty line."""

    def to_csv(self, pages: tuple[str, ...]) -> str:
        """Convert a known layout to explicit source columns without inference."""
        ...


class PipeTableLayout:
    """Strict sample layout with ISO dates and visible pipe-delimited columns.

    This is a synthetic, documented test layout, not a compatibility claim for a
    real mosque. Unknown layouts, scanned pages and unrelated text are rejected.
    """

    def to_csv(self, pages: tuple[str, ...]) -> str:
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        header = None
        declared_year = None
        for page in pages:
            page_header = False
            page_rows = 0
            for raw_line in page.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                if not page_header and re.fullmatch(r"Year [0-9]{4}", line):
                    value = int(line[5:])
                    if declared_year is not None and value != declared_year:
                        raise ImportValidationError("PDF pages declare different years")
                    declared_year = value
                    continue
                if not page_header and (
                    line == "Salah Timetable"
                    or re.fullmatch(r"Mosque: [^\r\n|]{1,100}", line)
                ):
                    continue
                if "|" not in line:
                    raise ImportValidationError(
                        "Unsupported PDF layout; expected the documented pipe-delimited table"
                    )
                cells = tuple(cell.strip() for cell in line.split("|"))
                if cells[0] == "Date":
                    if header is None:
                        header = cells
                        writer.writerow(header)
                    elif cells != header:
                        raise ImportValidationError(
                            "PDF table headers differ between pages"
                        )
                    page_header = True
                    continue
                if not page_header or header is None or len(cells) != len(header):
                    raise ImportValidationError(
                        "PDF table rows do not match the documented header"
                    )
                if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", cells[0]):
                    raise ImportValidationError(
                        "PDF table needs explicit YYYY-MM-DD dates"
                    )
                if declared_year is not None and int(cells[0][:4]) != declared_year:
                    raise ImportValidationError(
                        "PDF row dates do not match the declared year"
                    )
                writer.writerow(cells)
                page_rows += 1
            if not page_header or not page_rows:
                raise ImportValidationError(
                    "Each PDF page must contain a supported text table with dated rows"
                )
        return output.getvalue()


_LAYOUTS: dict[str, PdfLayout] = {
    "pdf_table_v1": PipeTableLayout(),
    "nms_annual_v1": NmsLayout(),
    "nms_monthly_v1": NmsMonthlyLayout(),
    "zak_ramadan_v1": ZakRamadanLayout(),
    "zak_annual_v1": ZakAnnualLayout(),
}


def extract_pdf_pages(content: bytes) -> tuple[str, ...]:
    """Run in an executor; terminate untrusted extraction at a hard wall limit."""
    if not isinstance(content, bytes) or not content.startswith(b"%PDF-"):
        raise ImportValidationError("The file is not a PDF")
    if len(content) > MAX_PDF_BYTES:
        raise ImportValidationError("PDF must be no larger than 4 MiB")
    worker = Path(__file__).with_name("pdf_worker.py")
    try:
        with _WORKERS:
            result = subprocess.run(
                [sys.executable, "-I", str(worker)],
                input=content,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=PDF_TIMEOUT_SECONDS,
                check=False,
                env={"PATH": os.defpath, "PYTHONIOENCODING": "utf-8"},
            )
    except subprocess.TimeoutExpired as err:
        raise ImportValidationError("PDF extraction exceeded its time limit") from err
    except OSError as err:
        raise ImportValidationError(
            "The isolated PDF extractor could not start"
        ) from err
    if result.returncode != 0:
        raise ImportValidationError(
            "PDF is invalid, encrypted, scanned, or exceeds extraction limits"
        )
    if len(result.stdout) > MAX_WORKER_OUTPUT_BYTES:
        raise ImportValidationError("PDF extraction exceeds the text limit")
    try:
        data = json.loads(result.stdout)
        pages = data["pages"]
        if (
            not isinstance(pages, list)
            or not 1 <= len(pages) <= MAX_PDF_PAGES
            or any(not isinstance(page, str) or not page.strip() for page in pages)
            or sum(len(page.encode("utf-8")) for page in pages) > MAX_TEXT_BYTES
        ):
            raise ValueError
    except (ValueError, TypeError, KeyError, UnicodeError) as err:
        raise ImportValidationError("PDF extraction returned invalid text") from err
    return tuple(pages)


class PdfParser:
    """Convert one explicit layout through the validated canonical CSV parser."""

    def __init__(self, layout_id: str = "pdf_table_v1") -> None:
        if layout_id not in _LAYOUTS:
            raise ImportValidationError("Unsupported PDF layout")
        self.layout_id = layout_id

    def _csv(self, content: bytes) -> str:
        return _LAYOUTS[self.layout_id].to_csv(extract_pdf_pages(content))

    def inspect(self, content: bytes) -> tuple[str, ...]:
        return CsvParser().inspect(self._csv(content).encode("utf-8"))

    def parse(
        self,
        content: bytes,
        *,
        timetable_id: str,
        kind: str,
        year: int,
        date_column: str,
        columns: dict[str, str],
        time_format: str = "24h",
    ) -> ImportCandidate:
        fixed_columns = {
            "nms_annual_v1": NMS_COLUMNS,
            "nms_monthly_v1": NMS_MONTHLY_COLUMNS,
            "zak_ramadan_v1": ZAK_RAMADAN_COLUMNS,
            "zak_annual_v1": ZAK_ANNUAL_COLUMNS,
        }.get(self.layout_id)
        if self.layout_id == "nms_annual_v1" and kind != "annual":
            raise ImportValidationError("Use Annual kind for the NMS annual layout")
        if self.layout_id == "zak_ramadan_v1" and kind != "ramadan":
            raise ImportValidationError(
                "Use Ramadan kind for the Zakariyya Ramadan page layout"
            )
        if self.layout_id == "zak_annual_v1" and kind != "annual":
            raise ImportValidationError(
                "Use Annual kind for the Zakariyya annual calendar layout"
            )
        if fixed_columns is not None and (
            date_column != "Date"
            or time_format != "24h"
            or any(fixed_columns.get(name) != field for name, field in columns.items())
        ):
            raise ImportValidationError(
                "Use Date, 24-hour format and the labelled prayer columns for this mosque layout"
            )
        canonical_csv = self._csv(content)
        candidate = CsvParser().parse(
            canonical_csv.encode("utf-8"),
            timetable_id=timetable_id,
            kind=kind,
            year=year,
            date_column=date_column,
            columns=columns,
            time_format=time_format,
        )
        return replace(
            candidate,
            source_format="pdf",
            source_base64=base64.b64encode(content).decode("ascii"),
            extracted_text=canonical_csv,
            source_text=canonical_csv,
            sha256=sha256(content).hexdigest(),
            parser_id=self.layout_id,
        )
