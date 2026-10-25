"""Compare Home Assistant's full restored configuration without printing private data.

Run only against disposable installations; this module never modifies files.
"""

import argparse
import json
from pathlib import Path
from typing import Any

DOMAIN = "salah_timetable"


def _data(config: Path, name: str) -> dict[str, Any]:
    """Read a Home Assistant .storage file's versioned data envelope."""
    path = config / ".storage" / name
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("data"), dict):
        raise ValueError(f"Invalid Home Assistant storage structure: {name}")
    return value["data"]


def snapshot(config: Path) -> dict[str, Any]:
    """Collect only structures requiring equivalence; never emit their content."""
    entries = {
        item["entry_id"]: item
        for item in _data(config, "core.config_entries")["entries"]
        if item.get("domain") == DOMAIN
    }
    if not entries:
        raise ValueError("No Salah Timetable config entries in test configuration")
    result: dict[str, Any] = {
        "entries": entries,
        "stores": {},
        "entities": {},
        "devices": {},
        "card_resources": [],
    }
    for entry_id in entries:
        store = _data(config, f"{DOMAIN}.{entry_id}")
        if (
            not isinstance(store.get("timetables"), list)
            or not isinstance(store.get("approved_sources"), dict)
            or "staged" not in store
        ):
            raise ValueError("Invalid timetable store or missing stage")
        result["stores"][entry_id] = store

    entry_ids = set(entries)
    registry = _data(config, "core.entity_registry")
    for item in registry["entities"]:
        if item.get("config_entry_id") in entry_ids or (
            item.get("platform") == DOMAIN
            and item.get("config_entry_id") in entry_ids
        ):
            key = item["entity_id"]
            if key in result["entities"]:
                raise ValueError("Duplicate entity in registry")
            result["entities"][key] = {
                "unique_id": item["unique_id"],
                "config_entry_id": item.get("config_entry_id"),
                "platform": item.get("platform"),
            }
    devices = _data(config, "core.device_registry")["devices"]
    for item in devices:
        if set(item.get("config_entries", [])) & entry_ids:
            result["devices"][item["id"]] = sorted(item["config_entries"])

    resource_file = config / ".storage" / "lovelace_resources"
    if resource_file.exists():
        resources = _data(config, "lovelace_resources").get("items", [])
        result["card_resources"] = sorted(
            item.get("url", "")
            for item in resources
            if "/salah_timetable/" in item.get("url", "")
        )
    if len(result["card_resources"]) != len(set(result["card_resources"])):
        raise ValueError("Duplicated Salah Timetable card resources")
    return result


def compare(
    original: Path,
    restored: Path,
    *,
    require_approved: bool = True,
    require_pending: bool = True,
) -> dict[str, int]:
    """Require identity and source metadata to survive without promotion."""
    before = snapshot(original)
    after = snapshot(restored)
    if require_approved and not any(
        store["approved_sources"] for store in before["stores"].values()
    ):
        raise ValueError("Test setup lacks an approved source")
    if require_pending and not any(
        store["staged"] is not None for store in before["stores"].values()
    ):
        raise ValueError("Test setup lacks a pending proposal")
    for key in ("entries", "stores", "entities", "devices", "card_resources"):
        if before[key] != after[key]:
            raise ValueError(f"Backup restore changed {key}")
    return {
        "mosques": len(after["entries"]),
        "entities": len(after["entities"]),
        "devices": len(after["devices"]),
        "cards": len(after["card_resources"]),
        "approved_sources": sum(
            len(store["approved_sources"]) for store in after["stores"].values()
        ),
        "pending_proposals": sum(
            store["staged"] is not None for store in after["stores"].values()
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", required=True, type=Path)
    parser.add_argument("--restored", required=True, type=Path)
    args = parser.parse_args()
    try:
        counts = compare(args.original, args.restored)
    except (OSError, ValueError, KeyError, TypeError) as err:
        parser.exit(1, f"Restore validation failed: {err}\n")
    print("Backup restore matched approved, pending, config and registry state")
    print("Safe counts:", json.dumps(counts, sort_keys=True))


if __name__ == "__main__":
    main()
