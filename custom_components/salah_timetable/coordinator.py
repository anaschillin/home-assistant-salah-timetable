"""Select effective daily data and absolute events at scheduled boundaries."""

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .coverage import CoverageSnapshot, calculate_coverage
from .events import EventSnapshot, calculate_events
from .model import Timetable
from .ramadan import EffectiveTimetable, RamadanSettings, resolve_day
from .storage import TimetableStorage


@dataclass(frozen=True)
class SalahData:
    day: date
    effective: EffectiveTimetable
    events: EventSnapshot
    days: tuple[EffectiveTimetable, ...]
    coverage: CoverageSnapshot
    approved_tables: tuple[Timetable, ...] = ()


class SalahCoordinator(DataUpdateCoordinator[SalahData]):
    def __init__(
        self, hass: HomeAssistant, entry, storage: TimetableStorage, zone: ZoneInfo
    ) -> None:
        super().__init__(
            hass,
            logging.getLogger(__name__),
            config_entry=entry,
            name="Salah Timetable",
            update_interval=timedelta(minutes=1),
            always_update=False,
        )
        self.storage = storage
        self.zone = zone
        self._boundary_unsub = None
        self._coverage_key = None
        self._coverage = None

    async def _async_update_data(self) -> SalahData:
        now = dt_util.utcnow()
        day = now.astimezone(self.zone).date()
        settings = RamadanSettings.from_options(self.config_entry.options)
        tables = self.storage.timetables
        coverage_key = (day, tables, settings)
        if coverage_key != self._coverage_key:
            self._coverage = await self.hass.async_add_executor_job(
                calculate_coverage, day, tables, settings
            )
            self._coverage_key = coverage_key
        resolved = {
            day + timedelta(days=offset): resolve_day(
                day + timedelta(days=offset), tables, settings
            )
            for offset in (-1, 0, 1)
        }
        events = calculate_events(
            now,
            self.zone,
            lambda key: resolved.get(key).row if key in resolved else None,
            ramadan_lookup=lambda key: (
                resolved[key].row
                if key in resolved and resolved[key].ramadan_active
                else None
            ),
        )
        data = SalahData(
            day, resolved[day], events, tuple(resolved.values()), self._coverage, tables
        )
        boundaries = [
            datetime.combine(day + timedelta(days=1), time.min, self.zone).astimezone(
                timezone.utc
            )
        ]
        boundaries.extend(
            event.timestamp.astimezone(timezone.utc)
            for event in (
                events.next_salah,
                events.next_jamaat,
                events.next_sehri,
                events.next_iftar,
            )
            if event is not None
        )
        if self._boundary_unsub is not None:
            self._boundary_unsub()
        self._boundary_unsub = async_track_point_in_utc_time(
            self.hass, self._async_boundary, min(boundaries)
        )
        return data

    async def _async_boundary(self, _now) -> None:
        self._boundary_unsub = None
        await self.async_refresh()

    async def async_shutdown(self) -> None:
        if self._boundary_unsub is not None:
            self._boundary_unsub()
            self._boundary_unsub = None
        await super().async_shutdown()
