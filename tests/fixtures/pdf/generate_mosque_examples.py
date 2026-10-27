"""Recreate independent, fictional Mosque A monthly and Mosque B annual/Ramadan PDF samples.

No publisher graphics, addresses, or published prayer-time series are used.
All example times are invented and MUST NOT be used for worship.
Run: python tests/fixtures/pdf/generate_mosque_examples.py
"""

import calendar
from datetime import date, timedelta
from pathlib import Path

from generate import make_pdf

HERE = Path(__file__).parent
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
PRELUDE = [
    "Synthetic fixture, not a timetable",
    "Mosque B",
    "Local test publication",
    "Fictional times only",
    "No published data",
    "For testing only",
    "No external assets",
    "A sample layout",
    "Created by the project",
]
A_HEADER = (
    "Date Day Hijri Sehri Ends Dawn Sunrise Istewa (Noon) Dhuhr Start Asr Start "
    "Sunset Esha Start x Fajr Dhuhr / Jumu'ah Asr Maghrib (Iftaar) Esha"
)
A_VALUES = "5:00 5:07 7:00 12:05 12:12 3:15 6:17 8:11 x 6:05 1:45 4:20 6:22 9:07"
B_VALUES = (
    "5:00",
    "5:07",
    "6:05",
    "7:00",
    "12:05",
    "12:45",
    "3:15",
    "4:20",
    "6:17",
    "8:11",
    "9:07",
)
H0 = "DATE SEHRI FAJR ZOHAR ASAR MAGRIB ISHA"
H1 = "DATE DAY ISLAMIC END START JAMAAT SUNRISE START JAMAAT START JAMAAT START START JAMAAT"
P0 = "DATE FAJR ZOHAR ASAR MAGRIB ISHA"
P1 = (
    "DATE DAY ISLAMIC START JAMAAT SUNRISE START JAMAAT START JAMAAT START START JAMAAT"
)
FEB1 = "DATE DAY ISLAMIC SEHRI START JAMAAT SUNRISE START JAMAAT START JAMAAT START START JAMAAT"


def day_name(day: date) -> str:
    return WEEKDAYS[day.weekday()]


def monthly_a() -> list[list[str]]:
    result = []
    for month in (5, 6):
        page = ["*Hijri Date is subject to Moonsighting", A_HEADER]
        for number in range(1, calendar.monthrange(2022, month)[1] + 1):
            day = date(2022, month, number)
            page.append(f"{number} {day_name(day)} {(number + 8) % 30 + 1} {A_VALUES}")
        page += [
            "www.mosque-a.example.org / synthetic test fixture",
            "Mosque A - fictional timetable data",
            f"{calendar.month_name[month]} 2022",
            "Rajab 1443",
            "Dates Beginning / End Times Jamaat Times",
            "Second Jumu'ah Khutbah will commence at 4:15pm in the Masjid Dining Hall",
        ]
        result.append(page)
    return result


def annual_and_ramadan_b() -> list[list[str]]:
    pages = [
        [
            "MOSQUE B - SYNTHETIC CALENDAR & TIMETABLE",
            "2026",
            "www.mosque-b.example.org",
            "FICTIONAL TIMES - DO NOT USE",
        ]
    ]
    for month in range(1, 13):
        sehri = 2 <= month <= 5
        header = (P0, FEB1) if month == 2 else (H0, H1) if sehri else (P0, P1)
        page = [*PRELUDE, *header]
        for number in range(1, calendar.monthrange(2026, month)[1] + 1):
            day = date(2026, month, number)
            name = f"{calendar.month_abbr[month]} 1,..." if number == 1 else str(number)
            if month == 5 and number == 1:
                name = "May ..."
            values = B_VALUES if sehri else B_VALUES[1:]
            page.append(
                f"{name} {day_name(day)} {(number + 10) % 30 + 1} {' '.join(values)}"
            )
        title = f"{calendar.month_name[month].upper()} 2026"
        page += [
            "www.mosque-b.example.org",
            "Contact Number: Fictional",
            "Email: test@example.org",
            f"{title}{title} TEST 1447 AH TEST 1447 AH",
            "Please Visit on - https://www.mosque-b.example.org/fixture",
        ]
        pages.append(page)
    ramadan = [*PRELUDE, "Ramadhan Kareem 1447 AH", H0, H1]
    for offset in range(31):
        day = date(2026, 2, 18) + timedelta(days=offset)
        name = (
            f"{calendar.month_abbr[day.month]} {day.day},..."
            if offset == 0 or day.day == 1
            else str(day.day)
        )
        ramadan.append(
            f"{name} {day_name(day)} {offset + 1 if offset < 30 else 1} {' '.join(B_VALUES)}"
        )
    ramadan += ["www.mosque-b.example.org", "RAMADHAN 2026"]
    pages.append(ramadan)
    return pages


if __name__ == "__main__":
    (HERE / "mosque_a_monthly_2022.pdf").write_bytes(make_pdf(monthly_a()))
    (HERE / "mosque_b_2026.pdf").write_bytes(make_pdf(annual_and_ramadan_b()))
