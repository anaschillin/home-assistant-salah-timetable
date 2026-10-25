"""A restored HA archive must preserve identities and approval boundaries."""

import json
from copy import deepcopy

import pytest

from scripts.verify_backup_restore import compare


def make_disposable(config, *, changed=False):
    storage = config / ".storage"
    storage.mkdir(parents=True)
    entry_id = "01EXAMPLEONLY"
    files = {
        "core.config_entries": {
            "entries": [
                {
                    "entry_id": entry_id,
                    "domain": "salah_timetable",
                    "unique_id": "test_mosque",
                    "title": "Synthetic Mosque",
                    "options": {"ramadan_mode": "on"},
                }
            ]
        },
        "core.entity_registry": {
            "entities": [
                {
                    "entity_id": "sensor.synthetic_mosque_fajr",
                    "unique_id": "test_fajr",
                    "config_entry_id": entry_id,
                    "platform": "salah_timetable",
                }
            ]
        },
        "core.device_registry": {
            "devices": [{"id": "synthetic_device", "config_entries": [entry_id]}]
        },
        "lovelace_resources": {
            "items": [{"url": "/salah_timetable/salah-timetable-card.js?v=0.7.0"}]
        },
        f"salah_timetable.{entry_id}": {
            "timetables": [{"timetable_id": "annual-2026"}],
            "approved_sources": {"annual-2026": {"sha256": "a" * 64}},
            "staged": {"stage_id": "b" * 32, "candidate": {"sha256": "b" * 64}},
            "remote_sources": {"annual-2026": {"type": "csv"}},
            "remote_checks": {"annual-2026": {"status": "pending"}},
        },
    }
    if changed:
        files[f"salah_timetable.{entry_id}"]["staged"] = None
    for name, data in files.items():
        (storage / name).write_text(json.dumps({"version": 1, "data": deepcopy(data)}))


def test_restored_backup_preserves_entry_ids_provenance_and_pending(tmp_path):
    original = tmp_path / "original"
    restored = tmp_path / "restored"
    make_disposable(original)
    make_disposable(restored)
    assert compare(original, restored) == {
        "mosques": 1,
        "entities": 1,
        "devices": 1,
        "cards": 1,
        "approved_sources": 1,
        "pending_proposals": 1,
    }


def test_restore_must_not_promote_or_discard_pending_content(tmp_path):
    original = tmp_path / "original"
    restored = tmp_path / "restored"
    make_disposable(original)
    make_disposable(restored, changed=True)
    with pytest.raises(ValueError, match="changed stores"):
        compare(original, restored)


def test_restore_requires_real_approval_and_pending_fixture(tmp_path):
    original = tmp_path / "original"
    restored = tmp_path / "restored"
    make_disposable(original, changed=True)
    make_disposable(restored, changed=True)
    with pytest.raises(ValueError, match="lacks a pending proposal"):
        compare(original, restored)
