"""Keep bundled frontend cache keys aligned with the integration manifest version."""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "salah_timetable"
MANIFEST = COMPONENT / "manifest.json"
TARGETS = (
    (
        COMPONENT / "frontend.py",
        re.compile(r'(?m)^(CARD_VERSION = ")[^"]+(")$'),
        r"\g<1>{version}\g<2>",
    ),
    (
        COMPONENT / "frontend" / "salah-timetable-card.js",
        re.compile(r'(?<=\?v=)\d+\.\d+\.\d+'),
        "{version}",
    ),
    (
        COMPONENT / "frontend" / "card-utils.js",
        re.compile(r'(?<=\?v=)\d+\.\d+\.\d+'),
        "{version}",
    ),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write",
        action="store_true",
        help="Synchronise cache keys instead of checking",
    )
    args = parser.parse_args()
    version = json.loads(MANIFEST.read_text(encoding="utf-8"))["version"]
    mismatches = []
    for path, pattern, replacement in TARGETS:
        source = path.read_text(encoding="utf-8")
        expected, count = pattern.subn(replacement.format(version=version), source)
        if count == 0:
            raise SystemExit(
                f"Expected frontend version marker missing: {path.relative_to(ROOT)}"
            )
        if source != expected:
            mismatches.append(str(path.relative_to(ROOT)))
            if args.write:
                path.write_text(expected, encoding="utf-8")
    if mismatches:
        print(
            ("Updated" if args.write else "Out-of-sync")
            + " frontend versions: "
            + ", ".join(mismatches)
        )
    if mismatches and not args.write:
        print("Run: python scripts/sync_frontend_version.py --write")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
