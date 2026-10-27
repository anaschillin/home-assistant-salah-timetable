"""Use HA's real registries, storage and config flow machinery."""

from datetime import date, time
from zoneinfo import ZoneInfo

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.salah_timetable.const import DOMAIN
from custom_components.salah_timetable.model import DailyPrayers, PrayerField, Timetable
from custom_components.salah_timetable.storage import TimetableStorage


def pytest_make_parametrize_id(
    config: pytest.Config, val: object, argname: str
) -> str | None:
    """Avoid printing multi-megabyte binary/CSV payloads as verbose test IDs."""
    if isinstance(val, (bytes, str)) and len(val) > 120:
        return f"{argname}-{type(val).__name__}-{len(val)}"
    return None


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def entry(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Example Mosque",
        unique_id="example",
        data={
            "name": "Example Mosque",
            "mosque_id": "example",
            "time_zone": "Europe/London",
        },
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def timetable():
    return Timetable(
        "annual-2026",
        "annual",
        (
            DailyPrayers(
                date(2026, 10, 21),
                {
                    PrayerField.FAJR_BEGIN: (time(5, 45),),
                    PrayerField.FAJR_JAMAAT: (time(6, 15),),
                    PrayerField.JUMUAH: (time(13), time(14)),
                },
                {"Fajr Start": "05:45", "Fajr Jamaat": "06:15"},
            ),
            DailyPrayers(
                date(2026, 10, 22),
                {PrayerField.FAJR_BEGIN: (time(5, 47),)},
                {"Fajr Start": "05:47"},
            ),
        ),
    )


@pytest.fixture
async def populated(hass, entry, timetable):
    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    await storage.async_replace((timetable,))
    return entry


@pytest.fixture
def hass_storage():
    """Exercise real HA atomic disk storage instead of the default memory mock."""
    return {}


@pytest.fixture
def hass_config_dir(hass_tmp_config_dir):
    return hass_tmp_config_dir
