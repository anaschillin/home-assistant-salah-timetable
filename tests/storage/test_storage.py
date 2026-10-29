from datetime import date, time
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest

from custom_components.salah_timetable.domain.model import (
    DailyPrayers,
    PrayerField,
    Timetable,
)
from custom_components.salah_timetable.persistence.storage import TimetableStorage


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


@pytest.mark.parametrize(
    "invalid_id",
    ["", "f" * 31, "g" * 32, "A" * 32, True, None, 123],
)
def test_staged_import_identity_rejects_invalid_persisted_ids(invalid_id):
    from custom_components.salah_timetable.parsers.csv_parser import CsvParser
    from custom_components.salah_timetable.persistence.storage import StagedImport

    candidate = CsvParser().parse(
        b"Date,Fajr Begin\n2026-10-21,05:45\n",
        timetable_id="annual-2026",
        kind="annual",
        year=2026,
        date_column="Date",
        columns={"Fajr Begin": "fajr_begin"},
    )
    with pytest.raises(ValueError, match="staged import identity"):
        StagedImport.from_dict(
            {"stage_id": invalid_id, "candidate": candidate.as_dict()}
        )


def test_staged_import_identity_round_trips_valid_provenance():
    from custom_components.salah_timetable.parsers.csv_parser import CsvParser
    from custom_components.salah_timetable.persistence.storage import StagedImport

    candidate = CsvParser().parse(
        b"Date,Fajr Begin\n2026-10-21,05:45\n",
        timetable_id="annual-2026",
        kind="annual",
        year=2026,
        date_column="Date",
        columns={"Fajr Begin": "fajr_begin"},
    )
    staged = StagedImport("a" * 32, candidate)
    assert StagedImport.from_dict(staged.as_dict()) == staged


def test_snapshot_validation_rejects_inconsistent_source_metadata(hass, entry):
    """A corrupted record cannot silently become an approved mosque timetable."""
    from dataclasses import replace

    from custom_components.salah_timetable.parsers.csv_parser import CsvParser
    from custom_components.salah_timetable.sources.source_model import RemoteSource

    store = TimetableStorage(hass, entry.entry_id, ZoneInfo("UTC"))
    candidate = CsvParser().parse(
        b"Date,Fajr Begin\n2026-10-21,05:45\n",
        timetable_id="annual-2026",
        kind="annual",
        year=2026,
        date_column="Date",
        columns={"Fajr Begin": "fajr_begin"},
    )
    source = RemoteSource(
        "annual-2026",
        "https://example.org/timetable.csv",
        "csv",
        "annual",
        2026,
        "Date",
        {"Fajr Begin": "fajr_begin"},
        parser_id="csv_v1",
    )
    invalid = (
        (
            replace(store._snapshot, approved_sources={"annual-2026": candidate}),
            "Approved provenance",
        ),
        (
            replace(
                store._snapshot, remote_checks={"annual-2026": {"status": "configured"}}
            ),
            "Source checks",
        ),
        (
            replace(store._snapshot, remote_sources={"mismatched": source}),
            "Remote source identity",
        ),
    )
    for snapshot, message in invalid:
        with pytest.raises(ValueError, match=message):
            store._validate_snapshot(snapshot)
    assert store.timetables == ()
    assert store.approved_sources == {}


@pytest.mark.parametrize(
    ("field", "invalid", "message"),
    [
        ("timetables", {}, "must be a list"),
        ("approved_sources", [], "Invalid import storage"),
        ("staged", [], "Invalid import storage"),
        ("remote_sources", [], "Invalid remote source"),
        ("remote_checks", [], "Invalid remote source"),
    ],
)
def test_decoding_untrusted_storage_rejects_malformed_collections(
    hass, entry, field, invalid, message
):
    store = TimetableStorage(hass, entry.entry_id, ZoneInfo("UTC"))
    serialized = store._snapshot.as_dict()
    serialized[field] = invalid
    with pytest.raises(ValueError, match=message):
        store._decode(serialized)


async def test_duplicate_timetable_identity_is_rejected_before_persistence(
    hass, entry, timetable
):
    store = TimetableStorage(hass, entry.entry_id, ZoneInfo("UTC"))
    with pytest.raises(ValueError, match="Duplicate timetable ID"):
        await store.async_replace((timetable, timetable))
    assert store.timetables == ()
