"""Read-only calendars of explicitly dated approved prayer instants."""

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .domain.model import PrayerField, Timetable
from .domain.ramadan import RamadanSettings, resolve_day

# Read-only calendar queries and coordinator snapshots need no throttling.
PARALLEL_UPDATES = 0

MAX_QUERY_DAYS = 366
# Calendar interoperability only: prayer and Jamaat remain exact start instants.
CALENDAR_PRESENTATION_INTERVAL = timedelta(minutes=1)
_NAMES = {
    PrayerField.FAJR_BEGIN: "Fajr beginning",
    PrayerField.FAJR_JAMAAT: "Fajr Jamaat",
    PrayerField.SUNRISE: "Sunrise",
    PrayerField.DHUHR_BEGIN: "Dhuhr beginning",
    PrayerField.DHUHR_JAMAAT: "Dhuhr Jamaat",
    PrayerField.JUMUAH: "Jumu’ah Jamaat",
    PrayerField.ASR_BEGIN: "Asr beginning",
    PrayerField.ASR_JAMAAT: "Asr Jamaat",
    PrayerField.MAGHRIB_BEGIN: "Maghrib beginning",
    PrayerField.MAGHRIB_JAMAAT: "Maghrib Jamaat",
    PrayerField.ISHA_BEGIN: "Isha beginning",
    PrayerField.ISHA_JAMAAT: "Isha Jamaat",
    PrayerField.SEHRI_ENDS: "Sehri ends",
    PrayerField.IFTAR: "Iftar",
    PrayerField.TARAWEEH: "Taraweeh",
}
_RAMADAN_FIELDS = frozenset(
    {PrayerField.SEHRI_ENDS, PrayerField.IFTAR, PrayerField.TARAWEEH}
)


def _index(tables: tuple[Timetable, ...], first: date, last: date | None = None):
    indexed = defaultdict(list)
    for table in tables:
        for row in table.days:
            if row.day >= first and (last is None or row.day <= last):
                indexed[row.day].append(
                    Timetable(table.timetable_id, table.kind, (row,))
                )
    return indexed


def _day_events(mosque_id, day, tables, settings, zone):
    effective = resolve_day(day, tuple(tables), settings)
    if effective.row is None:
        return []
    events = []
    for field, summary in _NAMES.items():
        if field in _RAMADAN_FIELDS and not effective.ramadan_active:
            continue
        stamps = effective.row.timestamps(field, zone)
        for position, stamp in enumerate(stamps, 1):
            instant = stamp.astimezone(timezone.utc)
            identity = (
                f"{mosque_id}|{day.isoformat()}|{field.value}|{instant.isoformat()}"
            )
            name = f"{summary} {position}" if len(stamps) > 1 else summary
            description = (
                f"Published event: {field.value}; timetable date: {day.isoformat()}"
            )
            if field == PrayerField.IFTAR and not any(
                source is not None and PrayerField.IFTAR in source.times
                for source in (effective.annual_row, effective.ramadan_row)
            ):
                description = (
                    "Iftar uses effective Maghrib beginning because no separate "
                    f"Iftar time is published; timetable date: {day.isoformat()}"
                )
            description += (
                "; 60-second calendar display interval (not a prayer duration)"
            )
            events.append(
                CalendarEvent(
                    start=stamp,
                    end=(instant + CALENDAR_PRESENTATION_INTERVAL).astimezone(zone),
                    summary=name,
                    description=description,
                    uid=sha256(identity.encode()).hexdigest(),
                )
            )
    return sorted(
        events, key=lambda event: (event.start.astimezone(timezone.utc), event.uid)
    )


def calendar_events(mosque_id, tables, settings, zone, start, end):
    """Return events overlapping [start, end), not just starting within it."""
    for value in (start, end):
        if (
            not isinstance(value, datetime)
            or value.tzinfo is None
            or value.utcoffset() is None
        ):
            raise HomeAssistantError(
                "Calendar queries require timezone-aware datetimes"
            )
    start_utc, end_utc = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
    if end_utc <= start_utc:
        raise HomeAssistantError("Calendar query end must be after its start")
    first_query_day = start_utc.astimezone(zone).date()
    last = (end_utc - timedelta(microseconds=1)).astimezone(zone).date()
    if (last - first_query_day).days >= MAX_QUERY_DAYS:
        raise HomeAssistantError(
            f"Calendar queries may cover at most {MAX_QUERY_DAYS} local dates"
        )
    # An event just before local midnight can overlap a query starting tomorrow.
    first = (start_utc - CALENDAR_PRESENTATION_INTERVAL).astimezone(zone).date()
    events = []
    try:
        for day, sources in sorted(_index(tables, first, last).items()):
            events.extend(
                event
                for event in _day_events(mosque_id, day, sources, settings, zone)
                if (
                    event.end.astimezone(timezone.utc) > start_utc
                    and event.start.astimezone(timezone.utc) < end_utc
                )
            )
    except ValueError as err:
        raise HomeAssistantError(
            "Calendar dates contain unresolved timetable data; review mosque source and timezone settings"
        ) from err
    return events


def _next_event(mosque_id, tables, settings, zone, now):
    """Search actual stored future dates, including beyond tomorrow/year end."""
    now_utc = now.astimezone(timezone.utc)
    first = (now_utc - CALENDAR_PRESENTATION_INTERVAL).astimezone(zone).date()
    for day, sources in sorted(_index(tables, first).items()):
        try:
            events = _day_events(mosque_id, day, sources, settings, zone)
        except ValueError:
            # Future ambiguities are exposed by coverage. Do not choose a source
            # or disable otherwise valid current calendar data.
            continue
        if event := next(
            (event for event in events if event.end.astimezone(timezone.utc) > now_utc),
            None,
        ):
            return event
    return None


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([PrayerCalendar(entry.runtime_data, entry)])


class PrayerCalendar(CoordinatorEntity, CalendarEntity):
    """One immutable prayer-event calendar per mosque."""

    _attr_has_entity_name = True
    _attr_translation_key = "prayer_calendar"
    _attr_icon = "mdi:calendar-clock"
    _attr_supported_features = 0

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self.entry = entry
        self._attr_unique_id = f"{entry.unique_id}_prayer_calendar"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)})
        self._next_key = None
        self._next = None
        self._computed_at = None

    @property
    def event(self):
        now = dt_util.utcnow()
        tables = self.coordinator.storage.timetables
        settings = RamadanSettings.from_options(self.entry.options)
        key = (tables, settings, self.coordinator.zone)
        if (
            key != self._next_key
            or self._computed_at is None
            or now < self._computed_at
            or (
                self._next is not None
                and self._next.end.astimezone(timezone.utc) <= now
            )
        ):
            self._next = _next_event(
                self.entry.unique_id, tables, settings, self.coordinator.zone, now
            )
            self._next_key = key
            self._computed_at = now
        return self._next

    async def async_get_events(self, hass, start_date, end_date):
        return await hass.async_add_executor_job(
            calendar_events,
            self.entry.unique_id,
            self.coordinator.storage.timetables,
            RamadanSettings.from_options(self.entry.options),
            self.coordinator.zone,
            start_date,
            end_date,
        )
