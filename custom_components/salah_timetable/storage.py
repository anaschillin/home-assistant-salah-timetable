"""Versioned per-entry persistence, using Home Assistant's atomic Store."""

from asyncio import Lock
from datetime import date
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util.json import load_json

from .const import DOMAIN, STORAGE_VERSION
from .model import DailyPrayers, PrayerField, Timetable


class TimetableStorage:
    """Persist validated sources before replacing the in-memory snapshot."""

    def __init__(self, hass: HomeAssistant, entry_id: str, zone: ZoneInfo) -> None:
        self._hass = hass
        self._lock = Lock()
        self._store = Store(
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}.{entry_id}",
            private=True,
            atomic_writes=True,
            serialize_in_event_loop=False,
        )
        self._zone = zone
        self.timetables: tuple[Timetable, ...] = ()

    def _validate(self, tables: tuple[Timetable, ...]) -> None:
        if len({table.timetable_id for table in tables}) != len(tables):
            raise ValueError("Duplicate timetable ID")
        annual_dates: set[date] = set()
        for table in tables:
            for row in table.days:
                for field in PrayerField:
                    row.timestamps(field, self._zone)
                if table.kind == "annual":
                    if row.day in annual_dates:
                        raise ValueError("Overlapping annual timetables")
                    annual_dates.add(row.day)

    async def async_load(self) -> None:
        data = await self._store.async_load()
        if data is None:
            return
        tables = tuple(Timetable.from_dict(item) for item in data["timetables"])
        self._validate(tables)
        self.timetables = tables

    async def async_replace(self, tables: tuple[Timetable, ...]) -> None:
        """Internal validated persistence API; imports are not exposed yet."""
        async with self._lock:
            tables = tuple(tables)
            await self._hass.async_add_executor_job(self._validate, tables)
            payload = await self._hass.async_add_executor_job(
                lambda: {"timetables": [table.as_dict() for table in tables]}
            )
            await self._store.async_save(payload)
            # Store logs WriteError instead of propagating it. Verify disk,
            # bypassing Store's cache before promoting a replacement.
            written = await self._hass.async_add_executor_job(
                load_json, self._store.path
            )
            if written.get("data") != payload:
                raise OSError("Timetable persistence could not be confirmed")
            self.timetables = tables

    def for_date(self, day: date) -> DailyPrayers | None:
        """Use exact annual dates only; Ramadan activation is not implemented."""
        return next(
            (
                row
                for table in self.timetables
                if table.kind == "annual"
                for row in table.days
                if row.day == day
            ),
            None,
        )

    async def async_remove(self) -> None:
        await self._store.async_remove()
