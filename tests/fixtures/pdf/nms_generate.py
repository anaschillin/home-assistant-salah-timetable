"""Original MIT-licensed synthetic fixtures for the inspected NMS table structure.

No published mosque times, PDF graphics, address or contact details are copied.
The NMS name/URL identify the adapter's required document signature only.
Run from the repository root to regenerate deterministic PDF/golden fixtures.
"""

import calendar
import csv
import importlib.util
import io
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
HEADER = (
    "Date Day Hijri Sehri Ends Dawn Sunrise Istewa (Noon) Dhuhr Start Asr Start "
    "Sunset Esha Start Fajr Dhuhr/Jumu'ah Asr Maghrib (Iftaar) Esha"
)
CANONICAL = (
    "Date",
    "Sehri Ends",
    "Fajr Begin",
    "Sunrise",
    "Istewa",
    "Dhuhr Begin",
    "Asr Begin",
    "Maghrib Begin",
    "Isha Begin",
    "Fajr Jamaat",
    "Dhuhr Jamaat",
    "Jumuah",
    "Asr Jamaat",
    "Maghrib Jamaat",
    "Isha Jamaat",
    "Iftar",
)
RAW_NAMES = (
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
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def synthetic_data(year=2026):
    """Return document pages and an independent explicit 24-hour golden CSV."""
    pages = [
        ["SALAH TIMETABLE", str(year), "MUSLIM SOCIETY", "SYNTHETIC TEST DATA"],
        ["Nuneaton Muslim Society", "www.nmsuk.org", "SYNTHETIC TEST DATA"],
    ]
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            *CANONICAL,
            *(f"Published {name}" for name in RAW_NAMES),
            "Published Day",
            "Published Hijri",
            "Published Second Khutbah",
        ]
    )
    for month in range(1, 13):
        # Exercise the inspected header wrapping/omission independently of month rows.
        header = HEADER.removeprefix("Date ") if month == 10 else HEADER
        if month == 8:
            header = header.replace("Sunrise", "Sun-\nrise")
        lines = [
            f"{calendar.month_name[month]} {year}",
            "Dates Beginning / End Times Jamaat Times",
            *header.splitlines(),
        ]
        previous = None
        for number in range(1, calendar.monthrange(year, month)[1] + 1):
            day = date(year, month, number)
            weekday = WEEKDAYS[day.weekday()]
            hijri = str((number + 8) % 30 + 1)
            noon = (
                ("11:45", "11:52")
                if month in {10, 11}
                else ("13:05", "13:12")
                if 4 <= month <= 9
                else ("12:05", "12:12")
            )
            midday = "13:35" if day.weekday() == 4 else "13:45"
            isha = "20:40" if day.weekday() in {5, 6} else "21:07"
            canonical_times = [
                "05:00",
                "05:07",
                "07:00",
                *noon,
                "15:15",
                "18:17",
                "20:11",
                "06:05",
                midday,
                "16:20",
                "18:22",
                isha,
            ]
            raw = []
            for index, value in enumerate(canonical_times):
                hour, minute = map(int, value.split(":"))
                printed = f"{hour % 12 or 12}:{minute:02d}"
                raw.append(
                    '"'
                    if index >= 8 and previous is not None and previous[index] == value
                    else printed
                )
            previous = canonical_times
            lines.append(f"{number} {weekday} {hijri} " + " ".join(raw))
            split_midday = ["", midday] if day.weekday() == 4 else [midday, ""]
            expected = [
                *canonical_times[:9],
                *split_midday,
                *canonical_times[10:],
                canonical_times[11],
            ]
            writer.writerow([
                day.isoformat(), *expected, *raw, weekday, hijri,
                "16:15" if day.weekday() == 4 else "",
            ])
        # These are deliberately khutbah notes, not congregation timestamps.
        lines.extend(
            [
                "Second Jumu'ah Khutbah will commence at 4:15pm",
                "SYNTHETIC TEST DATA - NOT A PRAYER TIMETABLE",
            ]
        )
        pages.append(lines)
    return pages, output.getvalue()


def make_pdf(pages):
    spec = importlib.util.spec_from_file_location(
        "base_pdf_fixture", ROOT / "generate.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.make_pdf(pages)


if __name__ == "__main__":
    pages, expected = synthetic_data()
    (ROOT / "nms_synthetic_2026.pdf").write_bytes(make_pdf(pages))
    (ROOT / "nms_synthetic_2026.expected.csv").write_text(expected)
