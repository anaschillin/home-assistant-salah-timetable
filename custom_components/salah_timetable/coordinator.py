"""Refresh date selection without writing countdowns into HA states."""

import logging
from datetime import timedelta
from zoneinfo import ZoneInfo

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .model import DailyPrayers
from .storage import TimetableStorage


class SalahCoordinator(DataUpdateCoordinator[DailyPrayers | None]):
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

    async def _async_update_data(self) -> DailyPrayers | None:
        return self.storage.for_date(dt_util.utcnow().astimezone(self.zone).date())
