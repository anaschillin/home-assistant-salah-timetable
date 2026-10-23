"""All annual values match a separate Poppler spatial-text extraction.

The expected CSV was constructed without production pypdf extraction or adapter
helpers. Each physical column was read against the rendered publication. The
clipped May-first date is identified by its explicit May 2026 title, Friday,
complete 31-row month and following 2–31 dates; no prayer time is inferred.
"""

import csv
from datetime import date, time
from pathlib import Path

from custom_components.salah_timetable.model import PrayerField
from custom_components.salah_timetable.pdf_parser import PdfParser
from custom_components.salah_timetable.zak_annual_layout import ZAK_ANNUAL_COLUMNS

FIXTURES = Path(__file__).parent / "fixtures/pdf"


def test_all_zakariyya_annual_dates_and_values_match_independent_oracle():
    candidate = PdfParser("zak_annual_v1").parse(
        (FIXTURES / "zak.pdf").read_bytes(),
        timetable_id="annual-2026",
        kind="annual",
        year=2026,
        date_column="Date",
        columns=ZAK_ANNUAL_COLUMNS,
    )
    with (FIXTURES / "zak_annual_2026.expected.csv").open(newline="") as handle:
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
    assert len(actual) == len(expected) == 365
    assert sum(len(row) - 1 for row in expected) == 3770
    assert actual == expected
    rows = {row.day: row for row in candidate.timetable.days}
    assert sum(PrayerField.SEHRI_ENDS in row.times for row in rows.values()) == 120
    assert rows[date(2026, 5, 1)].times[PrayerField.FAJR_BEGIN] == (time(3, 55),)
    assert rows[date(2026, 11, 1)].times[PrayerField.DHUHR_BEGIN] == (time(11, 58),)
    assert all(
        not {
            PrayerField.JUMUAH,
            PrayerField.MAGHRIB_JAMAAT,
            PrayerField.IFTAR,
            PrayerField.TARAWEEH,
            PrayerField.ISTEWA,
        }.intersection(row.times)
        for row in rows.values()
    )
