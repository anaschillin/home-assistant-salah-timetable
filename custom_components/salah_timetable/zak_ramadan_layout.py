"""The final Ramadan page in Zakariyya Jaam'e Masjid's inspected calendar.

The annual pages establish the publication and year; only the final, explicitly
labelled Ramadan table supplies records. Printed Hijri days are provenance, never
activation instructions. The final Shawwal/Eid row remains its own Gregorian date.
"""

import calendar
import csv
import io
import re
from datetime import date, timedelta

from .import_model import ImportValidationError

ZAK_RAMADAN_COLUMNS = {
    "Sehri Ends": "sehri_ends",
    "Fajr Begin": "fajr_begin",
    "Fajr Jamaat": "fajr_jamaat",
    "Sunrise": "sunrise",
    "Dhuhr Begin": "dhuhr_begin",
    "Dhuhr Jamaat": "dhuhr_jamaat",
    "Asr Begin": "asr_begin",
    "Asr Jamaat": "asr_jamaat",
    "Maghrib Begin": "maghrib_begin",
    "Isha Begin": "isha_begin",
    "Isha Jamaat": "isha_jamaat",
}
_PUBLISHED_NAMES = (
    "Sehri End",
    "Fajr Start",
    "Fajr Jamaat",
    "Sunrise",
    "Zohar Start",
    "Zohar Jamaat",
    "Asar Start",
    "Asar Jamaat",
    "Magrib Start",
    "Isha Start",
    "Isha Jamaat",
)
_WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
# The Friday day-cell is printed in Arabic, rather than labelling a prayer column.
_FRIDAY = "ﻪﻌﻤﺟ"
_MONTHS = {name: number for number, name in enumerate(calendar.month_abbr) if name}
_ROW = re.compile(
    r"^(?:(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
    r"(?P<month_day>[0-9]{1,2}),\s*…|(?P<day>[0-9]{1,2})) "
    r"(?P<weekday>Mon|Tue|Wed|Thu|Fri|Sat|Sun|" + _FRIDAY + r") "
    r"(?P<hijri>[0-9]{1,2}) (?P<times>.+)$"
)
_HEADER = (
    "DATE SEHRI FAJR ZOHAR ASAR MAGRIB ISHA",
    "DATE DAY ISLAMIC END START JAMAAT SUNRISE START JAMAAT START JAMAAT START START JAMAAT",
)
_SITE = "www.zakariyyamasjid.co.uk"
_PAGE_PREFIX = (
    "B o l t o n  U K",
    "Z a k a r i y y a  J a a m ' e  M a s j i dZakariyya Jaam'e Masjid",
    "0 7 8 7 8 8 8 9 3 6 9",
    "@zakariyyamasjid",
    "zakariyyamasjid",
    "zakariyyamasjid",
    "zakariyya masjid",
    "zakariyya-masjid",
    "Receiver No: 454.275",
    "Ramadhan Kareem 1447 AH",
)


def _publication_year(pages: tuple[str, ...]) -> int:
    """Recognize the complete publication; do not treat a random page as its table."""
    if len(pages) != 14:
        raise ImportValidationError(
            "Zakariyya Ramadan layout needs its cover, twelve months and final Ramadan page"
        )
    cover = pages[0]
    years = re.findall(r"^([0-9]{4})$", cover, re.MULTILINE)
    if (
        _SITE not in cover
        or "CALENDAR&TIMETABLE" not in re.sub(r"\s+", "", cover)
        or len(years) != 1
        or years != ["2026"]
    ):
        raise ImportValidationError("Zakariyya calendar cover is not recognized")
    year = int(years[0])
    for month, page in enumerate(pages[1:13], start=1):
        # Monthly pages are context, not a second source of times. Validate their
        # identity and ordered Gregorian titles, including the repeated headings
        # present in the inspected export. Do not infer anything from Hijri text.
        titles = re.findall(
            r"("
            + "|".join(name.upper() for name in calendar.month_name[1:])
            + r") ([0-9]{4})",
            page,
        )
        if (
            _SITE not in page
            or "Zakariyya Jaam'e Masjid" not in page
            or titles != [(calendar.month_name[month].upper(), str(year))] * 2
        ):
            raise ImportValidationError(
                "Zakariyya monthly pages must be recognized, ordered and agree with the cover year"
            )
    return year


def _clock(value: str, column: int) -> int:
    """Apply only the inspected layout's morning/noon/evening column convention."""
    if not re.fullmatch(r"(?:[1-9]|1[0-2]):[0-5][0-9]", value):
        raise ImportValidationError(
            "Zakariyya table contains an invalid published time"
        )
    hour, minute = map(int, value.split(":"))
    if column < 4:
        hour %= 12
    elif column in {4, 5}:
        if hour not in {11, 12, 1}:
            raise ImportValidationError("Zakariyya noon column has an unsupported hour")
        hour = 13 if hour == 1 else hour
    else:
        hour = hour % 12 + 12
    return hour * 60 + minute


def _check_order(values: list[int]) -> None:
    # Reject contradictions in this explicit AM/PM interpretation; never correct
    # a source value or use a calculated time to make a row pass.
    if not all(a <= b for a, b in zip(values, values[1:], strict=False)):
        raise ImportValidationError(
            "Zakariyya times do not match the inspected daily column convention"
        )


class ZakRamadanLayout:
    """Strict extraction of the inspected calendar's final Ramadan table only."""

    def to_csv(self, pages: tuple[str, ...]) -> str:
        year = _publication_year(pages)
        page = pages[-1]
        titles = re.findall(r"\bRAMADHAN ([0-9]{4})\b", page)
        if (
            titles != [str(year)]
            or _SITE not in page
            or "Zakariyya Jaam'e Masjid" not in page
            or "Ramadhan Kareem 1447 AH" not in page
        ):
            raise ImportValidationError(
                "Zakariyya Ramadan page or year is not recognized"
            )
        lines = [line.strip() for line in page.splitlines() if line.strip()]
        markers = [i for i, line in enumerate(lines) if line == _HEADER[0]]
        if (
            len(markers) != 1
            or markers[0] + 1 >= len(lines)
            or tuple(lines[: markers[0]]) != _PAGE_PREFIX
            or lines[markers[0] + 1] != _HEADER[1]
        ):
            raise ImportValidationError(
                "Zakariyya Ramadan table columns are not recognized"
            )
        start = markers[0] + 2
        try:
            end = lines.index(_SITE, start)
        except ValueError as err:
            raise ImportValidationError(
                "Zakariyya Ramadan table footer is missing"
            ) from err
        rows = lines[start:end]
        # The inspected publication explicitly includes thirty Ramadan dates and
        # one subsequent dated row. Completeness is a layout check, not activation.
        if len(rows) != 31 or any(_ROW.fullmatch(line) for line in lines[end:]):
            raise ImportValidationError(
                "Zakariyya Ramadan table has an unsupported row count"
            )
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(
            [
                "Date",
                *ZAK_RAMADAN_COLUMNS,
                *(f"Published {name}" for name in _PUBLISHED_NAMES),
                "Published Date",
                "Published Day",
                "Published Hijri",
            ]
        )
        current_month = None
        previous_day = None
        for line in rows:
            match = _ROW.fullmatch(line)
            if match is None:
                raise ImportValidationError("Zakariyya Ramadan row is not recognized")
            if month := match["month"]:
                current_month = _MONTHS[month]
            if current_month is None:
                raise ImportValidationError(
                    "Zakariyya first row needs its printed Gregorian month"
                )
            try:
                day = date(year, current_month, int(match["month_day"] or match["day"]))
            except ValueError as err:
                raise ImportValidationError(
                    "Zakariyya row has an invalid Gregorian date"
                ) from err
            weekday = "Fri" if match["weekday"] == _FRIDAY else match["weekday"]
            if (
                weekday != _WEEKDAYS[day.weekday()]
                or not 1 <= int(match["hijri"]) <= 30
                or (
                    previous_day is not None and day != previous_day + timedelta(days=1)
                )
                or (previous_day is None and day != date(2026, 2, 18))
            ):
                raise ImportValidationError(
                    "Zakariyya Gregorian dates or printed weekdays are inconsistent"
                )
            raw = match["times"].split()
            if len(raw) != 11:
                raise ImportValidationError(
                    "Zakariyya Ramadan row needs eleven published time cells"
                )
            values = [_clock(value, column) for column, value in enumerate(raw)]
            _check_order(values)
            clocks = [f"{value // 60:02d}:{value % 60:02d}" for value in values]
            date_text = line[: match.start("weekday")].strip()
            writer.writerow(
                [
                    day.isoformat(),
                    *clocks,
                    *raw,
                    date_text,
                    match["weekday"],
                    match["hijri"],
                ]
            )
            previous_day = day
        return output.getvalue()
