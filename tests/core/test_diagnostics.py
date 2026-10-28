"""Diagnostics use an allowlist instead of recursively redacting private imports."""

import json
from dataclasses import replace
from datetime import date, time
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from custom_components.salah_timetable.parsers.csv_parser import CsvParser
from custom_components.salah_timetable.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.salah_timetable.domain.model import DailyPrayers, PrayerField, Timetable
from custom_components.salah_timetable.sources.source_model import RemoteSource
from custom_components.salah_timetable.persistence.storage import TimetableStorage


async def test_diagnostics_exclude_identity_urls_validators_and_source(hass, entry):
    private = "SENSITIVE_IMPORTED_VALUE"
    url = "https://example.com/private.csv?token=SECRET_TOKEN"
    source = RemoteSource(
        "annual-2026",
        url,
        "csv",
        "annual",
        2026,
        "Date",
        {"Fajr Begin": "fajr_begin"},
        parser_id="csv_v1",
    )
    content = f"Date,Fajr Begin,Private\n2026-10-21,05:45,{private}\n".encode()
    candidate = replace(
        CsvParser().parse(
            content,
            timetable_id=source.source_id,
            kind="annual",
            year=2026,
            date_column="Date",
            columns=dict(source.columns),
        ),
        source_url=url,
        etag='"PRIVATE_VALIDATOR"',
    )
    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("UTC"))
    await storage.async_stage(candidate, remote_source=source)
    entry.runtime_data = SimpleNamespace(storage=storage)
    result = await async_get_config_entry_diagnostics(hass, entry)
    output = json.dumps(result)
    for secret in (
        entry.entry_id,
        entry.title,
        entry.unique_id,
        url,
        "example.com",
        "SECRET_TOKEN",
        private,
        "PRIVATE_VALIDATOR",
        "05:45",
    ):
        assert secret not in output
    assert result["pending_review"] is True
    assert result["remote_sources"][0]["source"] == "source_1"
    assert result["remote_sources"][0]["format"] == "csv"
    assert result["approved_rows"] == 0


async def test_unloaded_diagnostics_have_no_raw_config(hass, entry):
    result = await async_get_config_entry_diagnostics(hass, entry)
    assert result["loaded"] is False
    assert "data" not in result
    assert "options" not in result


async def test_loaded_diagnostics_explain_missing_rows_without_values(
    hass, entry, freezer
):
    freezer.move_to("2026-10-23T12:00:00+00:00")
    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    await storage.async_replace(
        (
            Timetable(
                "annual-private-source",
                "annual",
                (
                    DailyPrayers(
                        date(2026, 10, 24),
                        {PrayerField.FAJR_BEGIN: (time(6, 13),)},
                        {"private": "PRIVATE_IMPORTED_CELL"},
                    ),
                ),
            ),
        )
    )
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await async_get_config_entry_diagnostics(hass, entry)
    assert result["loaded"] is True
    assert result["entry_state"] == "loaded"
    assert result["last_update_success"] is True
    snapshot = result["last_snapshot"]
    assert snapshot["day_row_available"] is False
    assert snapshot["next_day_row_available"] is True
    assert snapshot["effective_fields"] == 0
    assert snapshot["ramadan_active"] is False
    assert snapshot["jamaat_context"] == "unavailable"
    assert snapshot["events_available"] == {
        "next_salah": True,
        "next_jamaat": False,
        "previous_jamaat": False,
        "next_sehri": False,
        "next_iftar": False,
    }
    serialized = json.dumps(result)
    for private in (
        entry.entry_id,
        entry.title,
        entry.unique_id,
        "annual-private-source",
        "PRIVATE_IMPORTED_CELL",
        "2026-10-24",
        "06:13",
        "Europe/London",
    ):
        assert private not in serialized


async def test_unloaded_entry_with_old_runtime_is_not_reported_as_loaded(hass, entry):
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_unload(entry.entry_id)
    result = await async_get_config_entry_diagnostics(hass, entry)
    assert result["loaded"] is False
    assert result["entry_state"] == "not_loaded"
    assert "last_snapshot" not in result
