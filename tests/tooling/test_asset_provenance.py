"""Audit asset inventory integrity separately from human licence clearance."""

import hashlib
import json
from pathlib import Path

import pytest

from scripts import check_asset_provenance as provenance


def _inventory(root: Path, assets: list[dict]) -> None:
    (root / "docs/asset-provenance.json").write_text(
        json.dumps({"schema_version": 1, "assets": assets}), encoding="utf-8"
    )


@pytest.fixture
def sample_repo(tmp_path, monkeypatch):
    """Minimal rights-cleared fixture with real file and evidence bytes."""
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/evidence.md").write_text("Independently generated.")
    (tmp_path / "assets").mkdir()
    content = b"original test asset"
    (tmp_path / "assets/sample.png").write_bytes(content)
    monkeypatch.setattr(provenance, "ASSET_DIRS", (Path("assets"),))
    item = {
        "path": "assets/sample.png",
        "rights": "original_mit",
        "owner": "Repository maintainers",
        "basis": "Independently generated fixture",
        "evidence": "docs/evidence.md",
        "sha256": hashlib.sha256(content).hexdigest(),
    }
    _inventory(tmp_path, [item])
    return tmp_path, item


def test_repository_asset_inventory_is_complete():
    unresolved = provenance.audit(provenance.ROOT)
    assert "tests/fixtures/pdf/mosque_a_monthly_2022.pdf" not in unresolved
    assert "tests/fixtures/pdf/mosque_b_2026.pdf" not in unresolved
    assert "custom_components/salah_timetable/brand/icon.png" in unresolved
    assert len(unresolved) == 5
    data = json.loads((provenance.ROOT / provenance.INVENTORY).read_text())
    paths = {asset["path"] for asset in data["assets"]}
    assert len(paths) == 37
    assert "tests/fixtures/csv/annual.csv" in paths
    assert "tests/fixtures/storage/v2_approved_pending.json" in paths
    assert all(asset.get("sha256") for asset in data["assets"])
    with pytest.raises(ValueError, match="Redistribution unresolved"):
        provenance.audit(provenance.ROOT, require_cleared=True)


def test_original_evidence_and_checksum_allow_strict_audit(sample_repo):
    root, _ = sample_repo
    assert provenance.audit(root) == []
    assert provenance.audit(root, require_cleared=True) == []


def test_unlisted_asset_blocks_inventory_validation(sample_repo):
    root, _ = sample_repo
    (root / "assets/unlisted.csv").write_text("fictional,values")
    with pytest.raises(ValueError, match="Inventory drift"):
        provenance.audit(root)


@pytest.mark.parametrize(
    ("extension", "content"),
    [
        (".csv", "Date,Example\\n2026-01-01,05:00\\n"),
        (".json", '{"synthetic": true}'),
        (".woff2", "dummy font bytes"),
    ],
)
def test_other_fixture_or_runtime_asset_types_are_not_ignored(
    sample_repo, extension, content
):
    root, _ = sample_repo
    (root / f"assets/extra{extension}").write_text(content)
    with pytest.raises(ValueError, match="Inventory drift"):
        provenance.audit(root)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"rights": "permission_documented", "evidence": None}, "lacks documented evidence"),
        ({"rights": "permission_documented", "evidence": "https://"}, "rights evidence"),
        ({"rights": "permission_documented", "evidence": "docs/missing.txt"}, "rights evidence"),
        ({"evidence": "docs/missing.txt"}, "rights evidence"),
        ({"evidence": "../docs/evidence.md"}, "rights evidence"),
        ({"owner": "   "}, "rights/owner/basis"),
        ({"basis": ""}, "rights/owner/basis"),
        ({"rights": "unknown"}, "rights/owner/basis"),
        ({"sha256": None}, "checksum"),
        ({"sha256": "0" * 64}, "checksum"),
        ({"path": "../assets/sample.png"}, "inventory path"),
        ({"path": "assets/../assets/sample.png"}, "inventory path"),
    ],
)
def test_invalid_inventory_claims_are_rejected(sample_repo, change, message):
    root, item = sample_repo
    _inventory(root, [{**item, **change}])
    with pytest.raises(ValueError, match=message):
        provenance.audit(root)


def test_original_evidence_file_must_exist(sample_repo):
    root, _ = sample_repo
    (root / "docs/evidence.md").unlink()
    with pytest.raises(ValueError, match="rights evidence"):
        provenance.audit(root)


def test_changing_asset_bytes_is_not_silently_accepted(sample_repo):
    root, _ = sample_repo
    (root / "assets/sample.png").write_bytes(b"different content")
    with pytest.raises(ValueError, match="checksum"):
        provenance.audit(root)


def test_permission_documented_url_needs_review_but_can_be_recorded(sample_repo):
    root, item = sample_repo
    _inventory(
        root,
        [
            {
                **item,
                "rights": "permission_documented",
                "evidence": "https://unsplash.com/photos/example",
            }
        ],
    )
    assert provenance.audit(root, require_cleared=True) == []


def test_symlinked_assets_are_rejected(sample_repo, tmp_path):
    root, _ = sample_repo
    external = tmp_path / "other.png"
    external.write_bytes(b"private")
    (root / "assets/hidden.png").symlink_to(external)
    with pytest.raises(ValueError, match="Symlink"):
        provenance.audit(root)


def test_missing_asset_directory_fails_closed(sample_repo):
    root, _ = sample_repo
    (root / "assets/sample.png").unlink()
    (root / "assets").rmdir()
    with pytest.raises(ValueError, match="asset directory"):
        provenance.audit(root)
