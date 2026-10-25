"""Safe dashboard payloads made from absolute published/effective timestamps."""

import re
from datetime import datetime, time

from .events import PrayerEvent
from .model import PrayerField

PRAYERS = (
    ("fajr", "Fajr", PrayerField.FAJR_BEGIN, (PrayerField.FAJR_JAMAAT,)),
    (
        "dhuhr",
        "Dhuhr",
        PrayerField.DHUHR_BEGIN,
        (PrayerField.DHUHR_JAMAAT, PrayerField.JUMUAH),
    ),
    ("asr", "Asr", PrayerField.ASR_BEGIN, (PrayerField.ASR_JAMAAT,)),
    ("maghrib", "Maghrib", PrayerField.MAGHRIB_BEGIN, (PrayerField.MAGHRIB_JAMAAT,)),
    ("isha", "Isha", PrayerField.ISHA_BEGIN, (PrayerField.ISHA_JAMAAT,)),
)


def dashboard_attributes(data, zone, mosque_name, *, show_hijri_date=True):
    row = data.effective.row

    def stamps(field):
        return row.timestamps(field, zone) if row else ()

    sunrise = stamps(PrayerField.SUNRISE)
    prayers = []
    for key, name, beginning, congregations in PRAYERS:
        begin = stamps(beginning)
        jamaat = sorted(value for field in congregations for value in stamps(field))
        prayers.append(
            {
                "key": key,
                "name": name,
                "begin": begin[0].isoformat() if begin else None,
                "end": sunrise[0].isoformat() if key == "fajr" and sunrise else None,
                "jamaat": [value.isoformat() for value in jamaat],
            }
        )
    beginnings, jamaats, sehri, iftar = [], [], [], []
    for effective in data.days:
        if effective.row is None:
            continue
        for key, _name, beginning, congregations in PRAYERS:
            beginnings.extend(
                PrayerEvent(value, beginning, key).as_dict()
                for value in effective.row.timestamps(beginning, zone)
            )
            for field in congregations:
                jamaats.extend(
                    PrayerEvent(
                        value, field, "jumuah" if field == PrayerField.JUMUAH else key
                    ).as_dict()
                    for value in effective.row.timestamps(field, zone)
                )
        if effective.ramadan_active:
            sehri.extend(
                PrayerEvent(value, PrayerField.SEHRI_ENDS, "sehri").as_dict()
                for value in effective.row.timestamps(PrayerField.SEHRI_ENDS, zone)
            )
            iftar.extend(
                PrayerEvent(value, PrayerField.IFTAR, "iftar").as_dict()
                for value in effective.row.timestamps(PrayerField.IFTAR, zone)
            )
    active = data.effective.ramadan_active
    today_sehri = stamps(PrayerField.SEHRI_ENDS) if active else ()
    today_iftar = stamps(PrayerField.IFTAR) if active else ()
    taraweeh = stamps(PrayerField.TARAWEEH) if active else ()
    # Khutbah is a separate published Friday announcement, never a Jamaat.
    # Read preserved NMS publisher metadata, not an inferred prayer time.
    annual = data.effective.annual_row
    published = annual or row
    khutbah = (
        published.original.get("Published Second Khutbah")
        if published and data.day.weekday() == 4
        else None
    )
    if not isinstance(khutbah, str) or not re.fullmatch(
        r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", khutbah
    ):
        khutbah = None
    khutbah_at = (
        datetime.combine(data.day, time.fromisoformat(khutbah), zone).isoformat()
        if khutbah
        else None
    )
    return {
        "mosque_name": mosque_name,
        "show_hijri_date": show_hijri_date,
        "second_khutbah": khutbah_at,
        "date": data.day.isoformat(),
        "time_zone": zone.key,
        "prayers": prayers,
        **data.events.as_dict(),
        "beginning_events": beginnings,
        "jamaat_events": jamaats,
        "sehri_events": sehri,
        "iftar_events": iftar,
        "ramadan": {
            "active": data.effective.ramadan_active,
            "sehri": today_sehri[0].isoformat() if today_sehri else None,
            "iftar": today_iftar[0].isoformat() if today_iftar else None,
            "taraweeh": taraweeh[0].isoformat() if taraweeh else None,
            "taraweeh_text": data.effective.taraweeh_text,
        },
    }
