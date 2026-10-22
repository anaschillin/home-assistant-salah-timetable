"""Nuneaton Muslim Society's inspected annual-calendar text layout.

This adapter encodes the identified column convention of that layout. It does not
recognize arbitrary mosque tables, derive lunar dates, calculate prayer times, or
interpret the separately printed second-Jumu'ah khutbah notes as congregations.
"""

import calendar
import csv
import io
import re
from datetime import date

from .csv_parser import DITTO_MARKERS
from .import_model import ImportValidationError

NMS_COLUMNS = {
    "Sehri Ends": "sehri_ends",
    "Fajr Begin": "fajr_begin",
    "Sunrise": "sunrise",
    "Istewa": "istewa",
    "Dhuhr Begin": "dhuhr_begin",
    "Asr Begin": "asr_begin",
    "Maghrib Begin": "maghrib_begin",
    "Isha Begin": "isha_begin",
    "Fajr Jamaat": "fajr_jamaat",
    "Dhuhr Jamaat": "dhuhr_jamaat",
    "Jumuah": "jumuah",
    "Asr Jamaat": "asr_jamaat",
    "Maghrib Jamaat": "maghrib_jamaat",
    "Isha Jamaat": "isha_jamaat",
    "Iftar": "iftar",
}
_RAW_NAMES = (
    "Sehri Ends",
    "Dawn",
    "Sunrise",
    "Istewa",
    "Dhuhr Start",
    "Asr Start",
    "Sunset",
    "Esha Start",
    "Fajr Jamaat",
    "Dhuhr or Jumuah",
    "Asr Jamaat",
    "Maghrib Iftaar",
    "Esha Jamaat",
)
_WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTH_PATTERN = re.compile(
    r"^(" + "|".join(calendar.month_name[1:]) + r") ([0-9]{4})$", re.MULTILINE
)
_ROW_PATTERN = re.compile(
    r"^([0-9]{1,2}) (Mon|Tue|Wed|Thu|Fri|Sat|Sun) ([0-9]{1,2}) (.+)$"
)
_HEADER = (
    "Date Day Hijri Sehri Ends Dawn Sunrise Istewa (Noon) Dhuhr Start Asr Start "
    "Sunset Esha Start Fajr Dhuhr/Jumu'ah Asr Maghrib (Iftaar) Esha"
)
_TABLE_MARKER = "Dates Beginning / End Times Jamaat Times"


def _compact_header(value: str) -> str:
    value = value.replace("’", "'").replace("Sun-\nrise", "Sunrise")
    return re.sub(r"\s+", "", value)


def _clock(value: str, column: int) -> int:
    """Use this published layout's morning/noon/afternoon column convention."""
    if not re.fullmatch(r"(?:[1-9]|1[0-2]):[0-5][0-9]", value):
        raise ImportValidationError("NMS table contains an invalid published time")
    hour, minute = map(int, value.split(":"))
    if column in {0, 1, 2, 8}:
        hour %= 12  # Sehri, dawn, sunrise and Fajr Jamaat are morning columns.
    elif column in {3, 4}:
        # Istewa/Dhuhr can be before noon in late autumn; never turn 11:xx into 23:xx.
        if hour not in {11, 12, 1}:
            raise ImportValidationError("NMS noon column has an unsupported hour")
        hour = 13 if hour == 1 else hour
    else:
        hour = hour % 12 + 12
    return hour * 60 + minute


def _format(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


def _check_order(values: list[int]) -> None:
    # These checks validate the fixed AM/PM interpretation; they never repair times.
    if not all(a < b for a, b in zip(values[:8], values[1:8], strict=False)):
        raise ImportValidationError("NMS beginning/end times are not in daily order")
    if not (
        values[1] <= values[8] <= values[2]
        and values[4] <= values[9] < values[6]
        and values[5] <= values[10] < values[6]
        and values[6] <= values[11] < values[7]
        and values[7] <= values[12]
    ):
        raise ImportValidationError(
            "NMS Jamaat times do not match the known daily convention"
        )


class NmsLayout:
    """A complete, explicitly dated NMS annual calendar with two front pages."""

    def to_csv(self, pages: tuple[str, ...]) -> str:
        if len(pages) != 14:
            raise ImportValidationError(
                "NMS annual layout needs its cover, contact page and twelve months"
            )
        cover = pages[0]
        cover_years = re.findall(r"^([0-9]{4})$", cover, re.MULTILINE)
        if (
            "SALAH TIMETABLE" not in cover
            or "MUSLIM SOCIETY" not in cover
            or len(cover_years) != 1
        ):
            raise ImportValidationError("NMS annual cover is not recognized")
        year = int(cover_years[0])
        if not 1900 <= year <= 2199:
            raise ImportValidationError(
                "NMS annual cover year is outside the supported range"
            )
        if "Nuneaton Muslim Society" not in pages[1] or "www.nmsuk.org" not in pages[1]:
            raise ImportValidationError("NMS contact page is not recognized")
        output = io.StringIO(newline="")
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(
            [
                "Date",
                *NMS_COLUMNS,
                *(f"Published {name}" for name in _RAW_NAMES),
                "Published Day",
                "Published Hijri",
            ]
        )
        for month, page in enumerate(pages[2:], start=1):
            titles = _MONTH_PATTERN.findall(page)
            if titles != [(calendar.month_name[month], str(year))]:
                raise ImportValidationError(
                    "NMS monthly pages must be ordered and agree with the cover year"
                )
            lines = page.splitlines()
            markers = [
                i for i, line in enumerate(lines) if line.strip() == _TABLE_MARKER
            ]
            if len(markers) != 1:
                raise ImportValidationError("NMS table header is not recognized")
            row_indices = [
                i
                for i, line in enumerate(lines)
                if _ROW_PATTERN.fullmatch(line.strip())
            ]
            count = calendar.monthrange(year, month)[1]
            if len(row_indices) != count or row_indices != list(
                range(row_indices[0], row_indices[0] + count)
            ):
                raise ImportValidationError(
                    "NMS month must contain every dated row exactly once"
                )
            if row_indices[0] <= markers[0]:
                raise ImportValidationError(
                    "NMS dated rows appear before the table header"
                )
            header = _compact_header("\n".join(lines[markers[0] + 1 : row_indices[0]]))
            expected = _compact_header(_HEADER)
            # The inspected October page omits the visible Date heading, but keeps
            # the same date/day/Hijri cells and all thirteen physical time columns.
            if header not in {expected, expected.removeprefix("Date")}:
                raise ImportValidationError(
                    "NMS table columns differ from the supported layout"
                )
            prior: dict[int, int] = {}
            for expected_day, index in enumerate(row_indices, start=1):
                match = _ROW_PATTERN.fullmatch(lines[index].strip())
                assert match is not None
                day_number, weekday, hijri, body = match.groups()
                day = date(year, month, expected_day)
                if (
                    int(day_number) != expected_day
                    or weekday != _WEEKDAYS[day.weekday()]
                    or not 1 <= int(hijri) <= 30
                ):
                    raise ImportValidationError(
                        "NMS row date, weekday or Hijri day is invalid"
                    )
                raw = body.split()
                if len(raw) != 13:
                    raise ImportValidationError(
                        "NMS row does not contain thirteen published time cells"
                    )
                values = []
                for column, value in enumerate(raw):
                    if value in DITTO_MARKERS:
                        if column < 8 or column not in prior:
                            raise ImportValidationError(
                                "NMS Jamaat quotation mark has no preceding explicit value"
                            )
                        minute = prior[column]
                    else:
                        minute = _clock(value, column)
                        prior[column] = minute
                    values.append(minute)
                _check_order(values)
                clocks = [_format(value) for value in values]
                # The printed physical midday column changes its meaning on Friday.
                # Preserve physical-column ditto before splitting its canonical fields.
                midday = ["", clocks[9]] if day.weekday() == 4 else [clocks[9], ""]
                normalized = [*clocks[:9], *midday, *clocks[10:], clocks[11]]
                writer.writerow([day.isoformat(), *normalized, *raw, weekday, hijri])
        return output.getvalue()
