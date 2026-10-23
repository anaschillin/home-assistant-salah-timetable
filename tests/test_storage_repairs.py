"""Invalid structured storage raises actionable Repairs without overwriting data."""

import json
from pathlib import Path

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import issue_registry as ir

from custom_components.salah_timetable.const import DOMAIN, STORAGE_VERSION


def empty_payload():
    return {
        "timetables": [],
        "approved_sources": {},
        "staged": None,
        "remote_sources": {},
        "remote_checks": {},
    }


async def write_payload(hass, entry, data):
    path = Path(hass.config.path(".storage", f"{DOMAIN}.{entry.entry_id}"))
    content = json.dumps(
        {
            "version": STORAGE_VERSION,
            "minor_version": 1,
            "key": f"{DOMAIN}.{entry.entry_id}",
            "data": data,
        },
        indent=2,
    ).encode()

    def write():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    await hass.async_add_executor_job(write)
    return path, content


def issue(hass, entry):
    return ir.async_get(hass).async_get_issue(
        DOMAIN, f"invalid_storage_{entry.entry_id}"
    )


@pytest.mark.parametrize("invalid_rows", [None, [{}], ["SENSITIVE_IMPORT"]])
async def test_invalid_store_creates_safe_persistent_repair_and_preserves_file(
    hass, entry, invalid_rows
):
    payload = empty_payload()
    payload["timetables"] = invalid_rows
    payload["private_source"] = "https://private.example/timetable?token=SECRET"
    path, original = await write_payload(hass, entry, payload)
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.SETUP_ERROR
    repair = issue(hass, entry)
    assert repair is not None
    assert repair.is_persistent is True
    assert repair.is_fixable is False
    assert repair.severity == ir.IssueSeverity.ERROR
    assert repair.translation_key == "invalid_storage"
    assert repair.translation_placeholders == {"mosque": entry.title}
    assert repair.data is None
    assert repair.learn_more_url is None
    serialized = json.dumps(repair.to_json())
    for private in ("SENSITIVE_IMPORT", "private.example", "SECRET"):
        assert private not in serialized
    assert await hass.async_add_executor_job(path.read_bytes) == original


async def test_storage_repair_clears_after_successful_recovery(hass, entry):
    await write_payload(hass, entry, {"timetables": [{}]})
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert issue(hass, entry) is not None
    await write_payload(hass, entry, empty_payload())
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.LOADED
    assert issue(hass, entry) is None


async def test_storage_repair_clears_when_failed_mosque_is_removed(hass, entry):
    path, _ = await write_payload(hass, entry, {"timetables": [{}]})
    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert issue(hass, entry) is not None
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert issue(hass, entry) is None
    assert not await hass.async_add_executor_job(path.exists)
