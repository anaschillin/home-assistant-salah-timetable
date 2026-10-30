"""Approved month, source and CSV reads; no pending proposal exposure."""

import csv
import io
from datetime import date, time
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from homeassistant.exceptions import Unauthorized
from homeassistant.helpers import entity_registry as er

from custom_components.salah_timetable import data_api
from custom_components.salah_timetable.const import DOMAIN
from custom_components.salah_timetable.domain.model import (
    DailyPrayers,
    PrayerField,
    Timetable,
)
from custom_components.salah_timetable.domain.month_data import (
    approved_month,
    approved_source_details,
    approved_year_csv,
    effective_range,
)
from custom_components.salah_timetable.domain.ramadan import RamadanSettings
from custom_components.salah_timetable.persistence.storage import TimetableStorage


def table(day, times, source_id="annual", kind="annual"):
    return Timetable(source_id, kind, (DailyPrayers(day, times, {}),))


def test_month_rows_distinguish_missing_days_and_multi_jumuah():
    d = date(2026, 10, 23)
    approved = (
        table(
            d,
            {
                PrayerField.FAJR_BEGIN: (time(5, 30),),
                PrayerField.JUMUAH: (time(13), time(14)),
            },
        ),
    )
    source = approved[0].as_dict()
    rows = approved_month(approved, RamadanSettings(), 2026, 10)
    assert len(rows) == 31
    friday = rows[22]
    assert friday["date"] == "2026-10-23"
    assert friday["published"]
    assert friday["times"]["jumuah"] == ["13:00", "14:00"]
    assert rows[21]["published"] is False
    assert rows[21]["times"] == {}
    assert approved[0].as_dict() == source


def test_year_csv_preserves_missing_fields_and_local_timezone():
    d = date(2026, 10, 23)
    data = approved_year_csv(
        (table(d, {PrayerField.JUMUAH: (time(13), time(14))}),),
        RamadanSettings(),
        2026,
        "Europe/London",
    )
    parsed = list(csv.DictReader(io.StringIO(data)))
    assert len(parsed) == 365
    assert parsed[295]["date"] == "2026-10-23"
    assert parsed[295]["jumuah"] == "13:00; 14:00"
    assert parsed[295]["time_zone"] == "Europe/London"
    assert parsed[0]["fajr_begin"] == ""
    assert "http" not in data


def test_effective_rows_respect_confirmed_ramadan_and_no_guessing():
    d = date(2026, 10, 23)
    annual = table(d, {PrayerField.FAJR_BEGIN: (time(5),)})
    ramadan = table(d, {PrayerField.IFTAR: (time(17),)}, "ramadan", "ramadan")
    inactive = approved_month((annual, ramadan), RamadanSettings(), 2026, 10)
    assert "iftar" not in inactive[22]["times"]
    active = approved_month((annual, ramadan), RamadanSettings(mode="on"), 2026, 10)
    assert active[22]["ramadan_active"]
    assert active[22]["times"]["iftar"] == ["17:00"]


@pytest.mark.parametrize(
    ("year", "month"),
    [(0, 1), (10000, 1), (2026, 0), (2026, 13), ("2026", 10)],
)
def test_month_rejects_invalid_year_month(year, month):
    with pytest.raises(ValueError, match="Gregorian month"):
        approved_month((), RamadanSettings(), year, month)


def test_query_rejects_invalid_date_types_and_excessive_ranges():
    with pytest.raises(ValueError, match="Gregorian dates"):
        effective_range((), RamadanSettings(), "2026-10-01", date(2026, 10, 2))
    with pytest.raises(ValueError, match="366 dates"):
        effective_range((), RamadanSettings(), date(2026, 1, 1), date(2027, 1, 2))
    with pytest.raises(ValueError, match="366 dates"):
        effective_range((), RamadanSettings(), date(2026, 10, 2), date(2026, 10, 1))
    with pytest.raises(ValueError, match="Gregorian year"):
        approved_year_csv((), RamadanSettings(), 0, "UTC")


def test_calendar_month_leap_day_and_year_boundary():
    assert len(approved_month((), RamadanSettings(), 2024, 2)) == 29
    assert len(approved_month((), RamadanSettings(), 2026, 2)) == 28
    assert len(approved_month((), RamadanSettings(), 2026, 12)) == 31


async def test_approved_source_details_never_return_url_or_pending_content(hass, entry):
    storage = TimetableStorage(hass, entry.entry_id, ZoneInfo("Europe/London"))
    source = table(date(2026, 10, 23), {PrayerField.FAJR_BEGIN: (time(5),)})
    await storage.async_replace((source,))
    result = approved_source_details(storage)
    assert result[0]["rows"] == 1
    assert result[0]["format"] is None
    assert result[0]["check_status"] == "not_configured"
    assert "url" not in result[0]
    assert "source_text" not in result[0]


async def test_authenticated_month_export_and_redacted_sources(
    hass, populated, hass_ws_client, monkeypatch
):
    # The WS client fixture issues its auth token before this test runs.
    # Do not move the clock afterwards: that invalidates the token.
    assert await hass.config_entries.async_setup(populated.entry_id)
    await hass.async_block_till_done()
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, "example_dashboard"
    )
    assert entity_id is not None
    client = await hass_ws_client(hass)
    await client.send_json_auto_id(
        {
            "type": "salah_timetable/month",
            "entity_id": entity_id,
            "year": 2026,
            "month": 10,
        }
    )
    msg = await client.receive_json()
    assert msg["success"], msg
    assert len(msg["result"]["rows"]) == 31
    await client.send_json_auto_id(
        {"type": "salah_timetable/year_csv", "entity_id": entity_id, "year": 2026}
    )
    msg = await client.receive_json()
    assert msg["success"], msg
    assert "2026-10-21" in msg["result"]["csv"]
    await client.send_json_auto_id(
        {"type": "salah_timetable/sources", "entity_id": entity_id}
    )
    msg = await client.receive_json()
    assert msg["success"], msg
    assert msg["result"]["sources"]
    assert "url" not in str(msg["result"]["sources"])
    await client.send_json_auto_id(
        {
            "type": "salah_timetable/month",
            "entity_id": "sensor.not_a_mosque",
            "year": 2026,
            "month": 10,
        }
    )
    msg = await client.receive_json()
    assert not msg["success"]
    assert msg["error"]["code"] == "not_found"

    # All three commands must reject a nonexistent mosque independently.
    for command in ("salah_timetable/year_csv", "salah_timetable/sources"):
        request = {"type": command, "entity_id": "sensor.not_a_mosque"}
        if command.endswith("year_csv"):
            request["year"] = 2026
        await client.send_json_auto_id(request)
        response = await client.receive_json()
        assert not response["success"]
        assert response["error"]["code"] == "not_found"

    # Conflicting approved sources fail closed; no guessed data or CSV is sent.
    def unresolved(*args):
        raise ValueError("Ambiguous approved sources")

    with monkeypatch.context() as patch:
        patch.setattr(data_api, "approved_month", unresolved)
        await client.send_json_auto_id(
            {
                "type": "salah_timetable/month",
                "entity_id": entity_id,
                "year": 2026,
                "month": 10,
            }
        )
        response = await client.receive_json()
        assert response["success"] is False
        assert response["error"]["code"] == "unresolved_timetable"

    with monkeypatch.context() as patch:
        patch.setattr(data_api, "approved_year_csv", unresolved)
        await client.send_json_auto_id(
            {
                "type": "salah_timetable/year_csv",
                "entity_id": entity_id,
                "year": 2026,
            }
        )
        response = await client.receive_json()
        assert response["success"] is False
        assert response["error"]["code"] == "unresolved_timetable"

    # A non-admin cannot read another mosque's private timetable fields.
    unauthorized = SimpleNamespace(
        is_admin=False,
        permissions=SimpleNamespace(check_entity=lambda *_args: False),
    )
    with pytest.raises(Unauthorized):
        data_api._entry_for_dashboard(
            hass, SimpleNamespace(user=unauthorized), entity_id
        )
    with pytest.raises(Unauthorized):
        data_api._entry_for_dashboard(hass, SimpleNamespace(user=None), entity_id)

    permitted = SimpleNamespace(
        is_admin=False,
        permissions=SimpleNamespace(check_entity=lambda *_args: True),
    )
    assert (
        data_api._entry_for_dashboard(hass, SimpleNamespace(user=permitted), entity_id)
        is populated
    )
    data_api.register_websocket_commands(hass)
