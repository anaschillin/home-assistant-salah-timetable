"""Diagnostics use an allowlist instead of recursively redacting private imports."""

import json
from dataclasses import replace
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from custom_components.salah_timetable.csv_parser import CsvParser
from custom_components.salah_timetable.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.salah_timetable.source_model import RemoteSource
from custom_components.salah_timetable.storage import TimetableStorage


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
