"""Every published value matches an independent Poppler extraction.

The checked-in CSV oracles were built from ``pdftotext -layout`` output, rather
than the integration's pypdf extraction or layout helpers. Their AM/PM meanings
follow the inspected physical columns. The original PDFs remain attributed to
their respective publishers; these fixtures do not confirm Ramadan activation.
"""

import csv
from pathlib import Path

import pytest

from custom_components.salah_timetable.nms_monthly_layout import NMS_MONTHLY_COLUMNS
from custom_components.salah_timetable.pdf_parser import PdfParser
from custom_components.salah_timetable.zak_ramadan_layout import ZAK_RAMADAN_COLUMNS

FIXTURES = Path(__file__).parent / "fixtures/pdf"


@pytest.mark.parametrize(
    "pdf,oracle,layout,year,columns,row_count,event_count",
    [
        (
            "nms ramadhan.pdf",
            "nms_monthly_2022.expected.csv",
            "nms_monthly_v1",
            2022,
            NMS_MONTHLY_COLUMNS,
            61,
            854,
        ),
        (
            "zak.pdf",
            "zak_ramadan_2026.expected.csv",
            "zak_ramadan_v1",
            2026,
            ZAK_RAMADAN_COLUMNS,
            31,
            341,
        ),
    ],
)
def test_all_published_dates_and_values_match_independent_oracle(
    pdf, oracle, layout, year, columns, row_count, event_count
):
    candidate = PdfParser(layout).parse(
        (FIXTURES / pdf).read_bytes(),
        timetable_id=f"ramadan-{year}",
        kind="ramadan",
        year=year,
        date_column="Date",
        columns=columns,
    )
    with (FIXTURES / oracle).open(newline="") as handle:
        expected = [
            {key: value for key, value in row.items() if value}
            for row in csv.DictReader(handle)
        ]
    actual = [
        {
            "Date": row.day.isoformat(),
            **{
                field.value: ";".join(value.strftime("%H:%M") for value in times)
                for field, times in row.times.items()
            },
        }
        for row in candidate.timetable.days
    ]
    assert len(actual) == len(expected) == row_count
    assert sum(len(row) - 1 for row in expected) == event_count
    assert actual == expected
