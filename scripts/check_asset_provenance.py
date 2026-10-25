"""Audit tracked binary/table fixture provenance and guard public releases.

No command can infer publisher copyright permission; human-attested evidence is
required to clear a pending asset. Normal CI checks inventory integrity only.
"""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = Path("docs/asset-provenance.json")
ASSET_DIRS = (
    Path("tests/fixtures/pdf"),
    Path("docs/images"),
    Path("custom_components/salah_timetable/brand"),
)
ASSET_TYPES = {".pdf", ".csv", ".png", ".jpg", ".jpeg", ".svg", ".webp"}
CLEARED = {"original_mit", "permission_documented"}
KNOWN = CLEARED | {"permission_pending", "review_pending"}


def audit(root: Path, *, require_cleared: bool = False) -> list[str]:
    """Reject omissions and unsupported rights assertions, without guessing licences."""
    data = json.loads((root / INVENTORY).read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("assets"), list):
        raise ValueError("Invalid asset inventory version or structure")
    entries = data["assets"]
    if any(not isinstance(item, dict) for item in entries):
        raise ValueError("Invalid inventory entry")
    declared = [item.get("path") for item in entries]
    if len(declared) != len(set(declared)) or not all(
        isinstance(name, str) for name in declared
    ):
        raise ValueError("Duplicate or invalid inventory path")
    actual = {
        file.relative_to(root).as_posix()
        for directory in ASSET_DIRS
        for file in (root / directory).rglob("*")
        if file.is_file() and file.suffix.lower() in ASSET_TYPES
    }
    if set(declared) != actual:
        missing = sorted(actual - set(declared))
        orphaned = sorted(set(declared) - actual)
        raise ValueError(f"Inventory drift: unlisted={missing}, absent={orphaned}")
    unresolved = []
    for item in entries:
        name = item["path"]
        path = root / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"Invalid asset file: {name}")
        if item.get("rights") not in KNOWN or not item.get("owner") or not item.get("basis"):
            raise ValueError(f"Missing asset rights/owner/basis: {name}")
        evidence = item.get("evidence")
        if item["rights"] in CLEARED:
            if not isinstance(evidence, str) or not evidence.strip():
                raise ValueError(f"Cleared asset lacks documented evidence: {name}")
            if item["rights"] == "permission_documented" and not evidence.startswith(
                ("https://", "docs/")
            ):
                raise ValueError(f"Permission evidence must be reviewable: {name}")
        else:
            unresolved.append(name)
        if "sha256" in item:
            expected = item["sha256"]
            if (
                not isinstance(expected, str)
                or len(expected) != 64
                or hashlib.sha256(path.read_bytes()).hexdigest() != expected
            ):
                raise ValueError(f"Asset checksum mismatch: {name}")
    if require_cleared and unresolved:
        raise ValueError(
            "Redistribution unresolved for: " + ", ".join(sorted(unresolved))
        )
    return sorted(unresolved)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--require-cleared",
        action="store_true",
        help="Block release until all repository-distributed assets have evidence",
    )
    args = parser.parse_args()
    try:
        unresolved = audit(args.root, require_cleared=args.require_cleared)
    except (OSError, ValueError, KeyError, TypeError) as err:
        parser.exit(1, f"Asset provenance failed: {err}\n")
    print(f"Asset inventory valid; {len(unresolved)} items need rights review")
    if unresolved:
        for name in unresolved:
            print(f"  PENDING: {name}")


if __name__ == "__main__":
    main()
