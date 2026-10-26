"""Strict adapter for the inspected MOSQUE_A May/June 2022 monthly pages.

Printed Gregorian month/year headings provide every source date. Printed Hijri
dates and the source's moonsighting note never activate Ramadan. This adapter
shares the inspected annual layout's column meanings, not its page structure.
"""

import calendar
import csv
import io
import re
from datetime import date

from .csv_parser import DITTO_MARKERS
from .import_model import ImportValidationError
from .mosque_a_layout import (
    _MONTH_PATTERN,
    _RAW_NAMES,
    _ROW_PATTERN,
    _TABLE_MARKER,
    _WEEKDAYS,
    MOSQUE_A_COLUMNS,
    _check_order,
    _clock,
    _compact_header,
    _format,
    published_second_khutbah,
)

MOSQUE_A_MONTHLY_COLUMNS = dict(MOSQUE_A_COLUMNS)
_HEADER = (
    "Date Day Hijri Sehri Ends Dawn Sunrise Istewa (Noon) Dhuhr Start Asr Start "
    "Sunset Esha Start x Fajr Dhuhr / Jumu'ah Asr Maghrib (Iftaar) Esha"
)
_MOONSIGHTING = "*Hijri Date is subject to Moonsighting"
_KHUTBAH = re.compile(
    r"Second Jumu'ah Khutbah will commence at (?:[1-9]|1[0-2]):[0-5][0-9](?:am|pm) "
    r"in the Masjid Dining Hall"
)


class MosqueAMonthlyLayout:
    """One to twelve complete consecutive monthly pages in one printed year."""

    def to_csv(self, pages: tuple[str, ...]) -> str:
        if not 1 <= len(pages) <= 12 or any(
            not isinstance(page, str) or not page.strip() for page in pages
        ):
            raise ImportValidationError(
                "MOSQUE_A monthly layout needs 1 to 12 text pages"
            )
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(
            [
                "Date",
                *MOSQUE_A_MONTHLY_COLUMNS,
                *(f"Published {name}" for name in _RAW_NAMES),
                "Published Day",
                "Published Hijri",
                "Published Second Khutbah",
            ]
        )
        previous_month = None
        for page in pages:
            titles = _MONTH_PATTERN.findall(page)
            if len(titles) != 1:
                raise ImportValidationError(
                    "Each MOSQUE_A monthly page needs one explicit month and year"
                )
            month_name, year_text = titles[0]
            month = list(calendar.month_name).index(month_name)
            year = int(year_text)
            if not 1900 <= year <= 2199:
                raise ImportValidationError(
                    "MOSQUE_A monthly year is outside the supported range"
                )
            if previous_month is not None and (year, month) != (
                previous_month[0],
                previous_month[1] + 1,
            ):
                raise ImportValidationError(
                    "MOSQUE_A monthly pages must be consecutive and use the same printed year"
                )
            previous_month = (year, month)
            lines = [line.strip() for line in page.splitlines() if line.strip()]
            row_indices = [
                index
                for index, line in enumerate(lines)
                if _ROW_PATTERN.fullmatch(line)
            ]
            count = calendar.monthrange(year, month)[1]
            if len(row_indices) != count or row_indices != list(
                range(row_indices[0], row_indices[0] + count)
            ):
                raise ImportValidationError(
                    "MOSQUE_A month must contain every dated row exactly once without interruptions"
                )
            if lines[0] != _MOONSIGHTING or _compact_header(
                "\n".join(lines[1 : row_indices[0]])
            ) != _compact_header(_HEADER):
                raise ImportValidationError(
                    "MOSQUE_A monthly table columns differ from the supported layout"
                )
            footer = lines[row_indices[-1] + 1 :]
            # The inspected June extraction contains one non-time separator after
            # its final row. It is not a source value and cannot stand for a time.
            if footer and footer[0] == "x":
                footer = footer[1:]
            # The table and dated rows determine the adapter, not the publisher's
            # address, logo or decorative footer artwork. Keep the explicitly
            # printed month and separately labelled khutbah as required context.
            if (
                f"{month_name} {year_text}" not in footer
                or _TABLE_MARKER not in footer
                or not any(_KHUTBAH.fullmatch(line) for line in footer)
            ):
                raise ImportValidationError(
                    "MOSQUE_A monthly headings or footer are not recognized"
                )
            khutbah = published_second_khutbah(" ".join(footer))
            assert khutbah is not None
            prior: dict[int, int] = {}
            for expected_day, index in enumerate(row_indices, start=1):
                match = _ROW_PATTERN.fullmatch(lines[index])
                assert match is not None
                day_number, weekday, hijri, body = match.groups()
                day = date(year, month, expected_day)
                if (
                    int(day_number) != expected_day
                    or weekday != _WEEKDAYS[day.weekday()]
                    or not 1 <= int(hijri) <= 30
                ):
                    raise ImportValidationError(
                        "MOSQUE_A row date, weekday or Hijri day is invalid"
                    )
                cells = body.split()
                if len(cells) != 14 or cells[8] != "x":
                    raise ImportValidationError(
                        "MOSQUE_A monthly row needs thirteen published time cells and its x separator"
                    )
                raw = cells[:8] + cells[9:]
                values = []
                for column, value in enumerate(raw):
                    if value in DITTO_MARKERS:
                        if column < 8 or column not in prior:
                            raise ImportValidationError(
                                "MOSQUE_A Jamaat quotation mark has no preceding explicit value in this month"
                            )
                        minute = prior[column]
                    else:
                        minute = _clock(value, column)
                        prior[column] = minute
                    values.append(minute)
                _check_order(values)
                clocks = [_format(value) for value in values]
                # Resolve the physical-column ditto before assigning its Friday
                # meaning. The separately printed Khutbah note is not Jamaat.
                midday = ["", clocks[9]] if day.weekday() == 4 else [clocks[9], ""]
                normalized = [*clocks[:9], *midday, *clocks[10:], clocks[11]]
                writer.writerow(
                    [
                        day.isoformat(),
                        *normalized,
                        *raw,
                        weekday,
                        hijri,
                        khutbah if day.weekday() == 4 else "",
                    ]
                )
        return output.getvalue()
