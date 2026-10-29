from datetime import date, time
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest

from custom_components.salah_timetable.model import DailyPrayers, PrayerField, Timetable
from custom_components.salah_timetable.storage import TimetableStorage


async def test_round_trip(hass, entry, timetable):
    store = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    await store.async_load()
    assert store.timetables == ()
    await store.async_replace((timetable,))
    reloaded = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    await reloaded.async_load()
    assert reloaded.timetables == (timetable,)
    assert reloaded.for_date(date(2026, 10, 21)) == timetable.days[0]
    assert reloaded.for_date(date(2026, 10, 23)) is None
    await reloaded.async_remove()
    empty = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    await empty.async_load()
    assert empty.timetables == ()


async def test_failed_save_retains_last_good(hass, entry, timetable):
    store = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    await store.async_replace((timetable,))
    with (
        patch.object(
            store._store, "async_save", AsyncMock(side_effect=OSError("disk full"))
        ),
        pytest.raises(OSError),
    ):
        await store.async_replace(())
    assert store.timetables == (timetable,)
    fresh = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    await fresh.async_load()
    assert fresh.timetables == (timetable,)


async def test_overlap_rejected(hass, entry, timetable):
    store = TimetableStorage(hass, entry.entry_id, ZoneInfo("UTC"))
    with pytest.raises(ValueError, match="Overlapping"):
        await store.async_replace(
            (timetable, Timetable("second", "annual", timetable.days))
        )
    assert store.timetables == ()


async def test_multi_year_and_ramadan_not_implicitly_applied(hass, entry):
    store = TimetableStorage(hass, entry.entry_id, ZoneInfo("UTC"))

    def row(day, hour):
        return DailyPrayers(day, {PrayerField.FAJR_BEGIN: (time(hour),)}, {})

    annual = Timetable(
        "annual", "annual", (row(date(2026, 12, 31), 5), row(date(2027, 1, 1), 6))
    )
    ramadan = Timetable("ramadan", "ramadan", (row(date(2027, 1, 1), 4),))
    await store.async_replace((annual, ramadan))
    assert store.for_date(date(2027, 1, 1)).times[PrayerField.FAJR_BEGIN] == (time(6),)


async def test_invalid_storage_does_not_replace_memory(hass, entry, timetable):
    store = TimetableStorage(hass, entry.entry_id, ZoneInfo("UTC"))
    await store.async_replace((timetable,))
    with (
        patch.object(
            store._store,
            "async_load",
            AsyncMock(return_value={"timetables": [{"id": "broken"}]}),
        ),
        pytest.raises(KeyError),
    ):
        await store.async_load()
    assert store.timetables == (timetable,)


async def test_logged_write_error_does_not_promote(hass, entry, timetable):
    from homeassistant.util.file import WriteError

    store = TimetableStorage(hass, entry.entry_id, ZoneInfo("UTC"))
    await store.async_replace((timetable,))
    with (
        patch.object(
            store._store, "_write_prepared_data", side_effect=WriteError("disk full")
        ),
        pytest.raises(OSError, match="persistence"),
    ):
        await store.async_replace(())
    assert store.timetables == (timetable,)
    fresh = TimetableStorage(hass, entry.entry_id, ZoneInfo("UTC"))
    await fresh.async_load()
    assert fresh.timetables == (timetable,)
