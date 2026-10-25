"""Asset inventory must be complete and cannot self-certify unknown rights."""

import json
from pathlib import Path

import pytest

from scripts import check_asset_provenance as provenance


def test_repository_asset_inventory_is_complete():
    unresolved = provenance.audit(provenance.ROOT)
    assert "tests/fixtures/pdf/nms ramadhan.pdf" in unresolved
    assert "tests/fixtures/pdf/zak.pdf" in unresolved
    assert "custom_components/salah_timetable/brand/icon.png" in unresolved
    with pytest.raises(ValueError, match="Redistribution unresolved"):
        provenance.audit(provenance.ROOT, require_cleared=True)


def test_unlisted_asset_blocks_inventory_validation(tmp_path, monkeypatch):
    root = tmp_path
    (root / "docs").mkdir()
    asset_dir = root / "assets"
    asset_dir.mkdir()
    (asset_dir / "sample.png").write_bytes(b"synthetic test image")
    (root / "docs/asset-provenance.json").write_text(
        json.dumps({"schema_version": 1, "assets": []})
    )
    monkeypatch.setattr(provenance, "ASSET_DIRS", (Path("assets"),))
    with pytest.raises(ValueError, match="Inventory drift"):
        provenance.audit(root)


def test_permission_cannot_be_declared_without_evidence(tmp_path, monkeypatch):
    root = tmp_path
    (root / "docs").mkdir()
    asset_dir = root / "assets"
    asset_dir.mkdir()
    (asset_dir / "sample.png").write_bytes(b"synthetic test image")
    (root / "docs/asset-provenance.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "assets": [
                    {
                        "path": "assets/sample.png",
                        "rights": "permission_documented",
                        "owner": "Example",
                        "basis": "Claimed permission",
                        "evidence": None,
                    }
                ],
            }
        )
    )
    monkeypatch.setattr(provenance, "ASSET_DIRS", (Path("assets"),))
    with pytest.raises(ValueError, match="lacks documented evidence"):
        provenance.audit(root)
