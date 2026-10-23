"""Aggregate diagnostics without mosque identity, URLs or imported content."""

from datetime import timedelta

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from .const import STORAGE_VERSION


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry) -> dict:
    """Only include an allowlisted summary; raw config is never serialized."""
    runtime = getattr(entry, "runtime_data", None)
    summary = {
        "storage_version": STORAGE_VERSION,
        "loaded": runtime is not None and entry.state is ConfigEntryState.LOADED,
        "entry_state": entry.state.value,
    }
    if runtime is None:
        return summary
    storage = runtime.storage
    checks = storage.remote_checks
    sources = []
    for number, source in enumerate(storage.remote_sources.values(), start=1):
        check = checks.get(source.source_id, {})
        sources.append(
            {
                "source": f"source_{number}",
                "kind": source.kind,
                "year": source.year,
                "format": source.media_type,
                "status": check.get("status", "configured"),
                "last_checked": check.get("last_checked"),
                "last_success": check.get("last_success"),
                "error_code": check.get("error_code"),
            }
        )
    summary.update(
        {
            "approved_timetables": len(storage.timetables),
            "approved_rows": sum(len(table.days) for table in storage.timetables),
            "approved_sources": len(storage.approved_sources),
            "pending_review": storage.staged is not None,
            "remote_sources": sources,
        }
    )
    snapshot = getattr(runtime, "data", None)
    if summary["loaded"] and snapshot is not None:
        summary["last_update_success"] = runtime.last_update_success
        summary["last_snapshot"] = {
            "day_row_available": snapshot.effective.row is not None,
            "next_day_row_available": any(
                effective.row is not None
                and effective.row.day == snapshot.day + timedelta(days=1)
                for effective in snapshot.days
            ),
            "effective_fields": len(snapshot.effective.row.times)
            if snapshot.effective.row
            else 0,
            "ramadan_active": snapshot.effective.ramadan_active,
            "jamaat_context": snapshot.events.context_mode,
            "events_available": {
                key: getattr(snapshot.events, key) is not None
                for key in (
                    "next_salah",
                    "next_jamaat",
                    "previous_jamaat",
                    "next_sehri",
                    "next_iftar",
                )
            },
        }
    return summary
