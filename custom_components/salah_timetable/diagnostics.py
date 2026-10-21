"""Aggregate diagnostics without mosque identity, URLs or imported content."""

from homeassistant.core import HomeAssistant

from .const import STORAGE_VERSION


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry) -> dict:
    """Only include an allowlisted summary; raw config is never serialized."""
    runtime = getattr(entry, "runtime_data", None)
    if runtime is None:
        return {"storage_version": STORAGE_VERSION, "loaded": False}
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
    return {
        "storage_version": STORAGE_VERSION,
        "loaded": True,
        "approved_timetables": len(storage.timetables),
        "approved_rows": sum(len(table.days) for table in storage.timetables),
        "approved_sources": len(storage.approved_sources),
        "pending_review": storage.staged is not None,
        "remote_sources": sources,
    }
