"""Check tracked asset integrity and recorded redistribution provenance.

An inventory check cannot establish a copyright or trademark licence. A
maintainer must separately review the cited source/permission evidence.
Normal CI checks inventory integrity; --require-cleared also blocks assets
whose redistribution status has not been reviewed and cleared.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = Path("docs/asset-provenance.json")
ASSET_DIRS = (
    Path("tests/fixtures"),
    Path("docs/images"),
    Path("custom_components/salah_timetable/brand"),
    Path("custom_components/salah_timetable/frontend"),
)
ASSET_TYPES = {
    ".pdf",
    ".csv",
    ".json",
    ".png",
    ".jpg",
    ".jpeg",
    ".svg",
    ".webp",
    ".avif",
    ".gif",
    ".ico",
    ".woff2",
    ".ttf",
    ".otf",
}
CLEARED = {"original_mit", "permission_documented"}
KNOWN = CLEARED | {"permission_pending", "review_pending"}


def _relative_path(name: str, *, label: str) -> Path:
    """Accept only canonical repository-relative POSIX paths."""
    if not isinstance(name, str):
        raise ValueError(f"Invalid {label}: expected a path string")
    candidate = PurePosixPath(name)
    if (
        not name
        or candidate.is_absolute()
        or candidate.as_posix() != name
        or ".." in candidate.parts
        or "\\" in name
    ):
        raise ValueError(f"Unsafe or noncanonical {label}: {name}")
    return Path(*candidate.parts)


def _evidence_valid(root: Path, evidence: str, *, rights: str) -> bool:
    """Validate evidence references without claiming to verify URL contents."""
    if not isinstance(evidence, str) or not evidence.strip():
        return False
    if evidence.startswith("https://"):
        parsed = urlsplit(evidence)
        return bool(
            parsed.hostname
            and not parsed.username
            and not parsed.password
            and not any(char.isspace() for char in evidence)
        )
    if rights == "permission_documented" and not evidence.startswith("docs/"):
        return False
    try:
        local = _relative_path(evidence, label="evidence path")
    except ValueError:
        return False
    target = root / local
    return target.is_file() and not target.is_symlink()


def _listed_assets(root: Path) -> set[str]:
    """Inventory all tracked asset types in the owned fixture/media areas."""
    actual = set()
    for directory in ASSET_DIRS:
        target = root / directory
        if not target.is_dir() or target.is_symlink():
            raise ValueError(f"Missing or unsafe asset directory: {directory}")
        for file in target.rglob("*"):
            if file.is_symlink():
                raise ValueError(f"Symlink in asset directory: {file.relative_to(root)}")
            if file.is_file() and file.suffix.lower() in ASSET_TYPES:
                actual.add(file.relative_to(root).as_posix())
    return actual


def audit(root: Path, *, require_cleared: bool = False) -> list[str]:
    """Check inventory and checksums, optionally blocking unresolved rights."""
    data = json.loads((root / INVENTORY).read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("assets"), list):
        raise ValueError("Invalid asset inventory version or structure")
    entries = data["assets"]
    if any(not isinstance(item, dict) for item in entries):
        raise ValueError("Invalid inventory entry")

    declared = [item.get("path") for item in entries]
    for name in declared:
        _relative_path(name, label="inventory path")
    if len(declared) != len(set(declared)):
        raise ValueError("Duplicate inventory path")
    actual = _listed_assets(root)
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
        rights = item.get("rights")
        if (
            not isinstance(rights, str)
            or rights not in KNOWN
            or not isinstance(item.get("owner"), str)
            or not item["owner"].strip()
            or not isinstance(item.get("basis"), str)
            or not item["basis"].strip()
        ):
            raise ValueError(f"Missing asset rights/owner/basis: {name}")
        if rights in CLEARED:
            evidence = item.get("evidence")
            if not isinstance(evidence, str) or not evidence.strip():
                raise ValueError(f"Cleared asset lacks documented evidence: {name}")
            if not _evidence_valid(root, evidence, rights=rights):
                raise ValueError(f"Invalid or missing asset rights evidence: {name}")
        else:
            unresolved.append(name)

        expected = item.get("sha256")
        if (
            not isinstance(expected, str)
            or re.fullmatch(r"[a-f0-9]{64}", expected) is None
            or hashlib.sha256(path.read_bytes()).hexdigest() != expected
        ):
            raise ValueError(f"Missing or mismatched asset checksum: {name}")

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
        help="Block release until all inventoried assets have reviewed rights evidence",
    )
    args = parser.parse_args()
    try:
        unresolved = audit(args.root, require_cleared=args.require_cleared)
    except (OSError, ValueError, KeyError, TypeError) as err:
        parser.exit(1, f"Asset provenance failed: {err}\n")
    print(
        f"Asset inventory integrity valid; {len(unresolved)} assets need rights review "
        "(not a licence certification)"
    )
    for name in unresolved:
        print(f"  PENDING: {name}")


if __name__ == "__main__":
    main()
