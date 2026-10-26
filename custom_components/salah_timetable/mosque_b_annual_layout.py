"""Strict annual tables in the inspected Mosque B 2026 publication.

The final Ramadan page is a separate source and supplies no annual values. The
known clipped May first-date label is resolved only from the complete Gregorian
month, ordered remaining dates and printed weekdays; no prayer time is inferred.
"""

import calendar
import csv
import io
import re
from datetime import date

from .import_model import ImportValidationError
from .mosque_b_ramadan_layout import (
    _FRIDAY,
    _PAGE_PREFIX,
    _PUBLISHED_NAMES,
    _SITE,
    _WEEKDAYS,
    MOSQUE_B_RAMADAN_COLUMNS,
    _check_order,
    _clock,
    _publication_year,
)

MOSQUE_B_ANNUAL_COLUMNS = dict(MOSQUE_B_RAMADAN_COLUMNS)
MAY_DATE_INTERPRETATION = (
    "Clipped May first-date label; day 1 verified from the complete May 2026 "
    "table, ordered dates 2–31 and printed weekdays"
)
_PLAIN_HEADER = (
    "DATE FAJR ZOHAR ASAR MAGRIB ISHA",
    "DATE DAY ISLAMIC START JAMAAT SUNRISE START JAMAAT START JAMAAT START START JAMAAT",
)
_SEHRI_HEADER = (
    "DATE SEHRI FAJR ZOHAR ASAR MAGRIB ISHA",
    "DATE DAY ISLAMIC END START JAMAAT SUNRISE START JAMAAT START JAMAAT START START JAMAAT",
)
_FEBRUARY_HEADER = (
    _PLAIN_HEADER[0],
    "DATE DAY ISLAMIC SEHRI START JAMAAT SUNRISE START JAMAAT START JAMAAT START START JAMAAT",
)
_ROW = re.compile(
    r"^(?P<date>[0-9]{1,2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
    r"[0-9]{1,2},?\s*(?:…|\.{3})|May (?:…|\.{3})) "
    r"(?P<weekday>Mon|Tue|Wed|Thu|Fri|Sat|Sun|" + _FRIDAY + r") "
    r"(?P<hijri>[0-9]{1,2}) (?P<times>.+)$"
)
_CONTACT_LABELS = ("Contact Number:", "Email:")
_SHOP_PREFIX = "Please Visit on - https://"
# Preserve the publication's actual captions, including its printed May 1446
# discrepancy. They establish known page structure, never Gregorian dates or
# Ramadan activation. Correcting the publisher's Hijri text would invent data.
_HIJRI_CAPTIONS = (
    "Rajab - Sha'ban 1447 AH",
    "Sha'ban - Ramadhan 1447 AH",
    "Ramadhan - Shawwal 1447 AH",
    "Shawwal - Zul Qa'dah 1447 AH",
    "Zul Qa'dah - Zul Hijjah 1446 AH",
    "Zul Hijjah - Muharram 1448 AH",
    "Muharram - Safar 1448 AH",
    "Safar - Rabi' ul Awwal 1448 AH",
    "Rabi' ul Awwal - Rabi' ul Akhir 1448 AH",
    "Rabi' ul Akhir - Jamadul Awwal 1448 AH",
    "Jamadul Awwal - Jamadul Akhir 1448 AH",
    "Jamadul Akhir - Rajab 1448 AH",
)


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", value)


def _day_number(token: str, month: int, position: int) -> tuple[int, str]:
    """Accept the one inspected clipping only at May's complete first row."""
    if token in {"May …", "May ..."}:
        if month != 5 or position != 1:
            raise ImportValidationError(
                "Mosque B clipped date is supported only for May's first row"
            )
        return 1, MAY_DATE_INTERPRETATION
    if token.isdecimal():
        if position == 1 and month != 1:
            raise ImportValidationError(
                "Mosque B first row needs its printed Gregorian month label"
            )
        return int(token), ""
    if position != 1:
        raise ImportValidationError(
            "Mosque B Gregorian month labels must appear only on the first row"
        )
    match = re.fullmatch(r"([A-Z][a-z]{2}) ([0-9]{1,2}),?\s*(?:…|\.{3})", token)
    if match is None or match[1] != calendar.month_abbr[month]:
        raise ImportValidationError("Mosque B row Gregorian month is inconsistent")
    return int(match[2]), ""


class MosqueBAnnualLayout:
    """Complete twelve annual monthly tables from the tested 2026 edition only."""

    def to_csv(self, pages: tuple[str, ...]) -> str:
        if len(pages) != 14:
            raise ImportValidationError(
                "Mosque B annual layout needs its cover, twelve months and final Ramadan context page"
            )
        year = _publication_year(pages)
        # The publication's separate Ramadan page remains context, not a second
        # copy of these dates. Do not silently accept an unrelated final page.
        if (
            "RAMADHAN 2026" not in pages[-1]
            or "Ramadhan Kareem 1447 AH" not in pages[-1]
            or _SITE not in pages[-1]
        ):
            raise ImportValidationError(
                "Mosque B final Ramadan context page is not recognized"
            )
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(
            [
                "Date",
                *MOSQUE_B_ANNUAL_COLUMNS,
                *(f"Published {name}" for name in _PUBLISHED_NAMES),
                "Published Date",
                "Published Day",
                "Published Hijri",
                "Published Date Interpretation",
            ]
        )
        for month, page in enumerate(pages[1:13], start=1):
            has_sehri = 2 <= month <= 5
            header = (
                _FEBRUARY_HEADER
                if month == 2
                else _SEHRI_HEADER
                if has_sehri
                else _PLAIN_HEADER
            )
            lines = [line.strip() for line in page.splitlines() if line.strip()]
            prefix_length = len(_PAGE_PREFIX) - 1
            if tuple(lines[prefix_length : prefix_length + 2]) != header:
                raise ImportValidationError(
                    "Mosque B annual table columns or preamble are not recognized"
                )
            first = prefix_length + 2
            count = calendar.monthrange(year, month)[1]
            rows = lines[first : first + count]
            footer = lines[first + count :]
            title = f"{calendar.month_name[month].upper()} {year}"
            if (
                len(rows) != count
                or len(footer) not in {5, 6}
                or not footer[0].startswith(_SITE)
                or not footer[1].startswith(_CONTACT_LABELS[0])
                or not footer[2].startswith(_CONTACT_LABELS[1])
                or not footer[-1].startswith(_SHOP_PREFIX)
                or _compact("".join(footer[3:-1])).startswith(_compact(title * 2))
                is False
            ):
                raise ImportValidationError(
                    "Mosque B annual month needs every dated row and its known footer"
                )
            for position, line in enumerate(rows, start=1):
                match = _ROW.fullmatch(line)
                if match is None:
                    raise ImportValidationError(
                        "Mosque B annual dated row is not recognized"
                    )
                day_number, interpretation = _day_number(match["date"], month, position)
                day = date(year, month, position)
                weekday = "Fri" if match["weekday"] == _FRIDAY else match["weekday"]
                if (
                    day_number != position
                    or weekday != _WEEKDAYS[day.weekday()]
                    or not 1 <= int(match["hijri"]) <= 30
                ):
                    raise ImportValidationError(
                        "Mosque B annual Gregorian dates or weekdays are inconsistent"
                    )
                raw = match["times"].split()
                if len(raw) != (11 if has_sehri else 10):
                    raise ImportValidationError(
                        "Mosque B annual row has the wrong number of published time cells"
                    )
                values = [
                    _clock(value, column if has_sehri else column + 1)
                    for column, value in enumerate(raw)
                ]
                _check_order(values)
                clocks = [f"{value // 60:02d}:{value % 60:02d}" for value in values]
                if not has_sehri:
                    clocks.insert(0, "")
                    raw.insert(0, "")
                writer.writerow(
                    [
                        day.isoformat(),
                        *clocks,
                        *raw,
                        match["date"],
                        match["weekday"],
                        match["hijri"],
                        interpretation,
                    ]
                )
        return output.getvalue()
