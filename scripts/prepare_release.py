"""Prepare reviewable release assets for a previously validated source tag."""

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

from .build_release import PROJECT_ROOT, build_release, check_versions


@dataclass(frozen=True)
class PreparedRelease:
    """Names and digest used by the draft-only publication job."""

    tag: str
    version: str
    archive: Path
    checksum: Path
    notes: Path


def release_notes(root: Path, version: str) -> str:
    """Read only the requested changelog section, excluding older versions."""
    content = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    lines = content.splitlines()
    heading = re.compile(rf"## {re.escape(version)}(?:\s+—[^\n]*)?\s*")
    start = next(
        (index + 1 for index, line in enumerate(lines) if heading.fullmatch(line)),
        None,
    )
    if start is None:
        raise ValueError("The requested version has no changelog section")
    end = next(
        (index for index in range(start, len(lines)) if lines[index].startswith("## ")),
        len(lines),
    )
    notes = "\n".join(lines[start:end]).strip()
    if not notes:
        raise ValueError("The requested changelog section is empty")
    return f"# Salah Timetable {version}\n\n{notes}\n"


def prepare_release(root: Path, tag: str, output_dir: Path) -> PreparedRelease:
    """Validate metadata and notes before building any output files."""
    version = check_versions(root)
    if tag != f"v{version}":
        raise ValueError("The existing tag must be v followed by the manifest version")
    notes = release_notes(root, version)
    archive = build_release(root, output_dir)
    checksum = archive.with_suffix(".zip.sha256")
    notes_file = output_dir / "release-notes.md"
    notes_file.write_text(notes, encoding="utf-8")
    return PreparedRelease(tag, version, archive, checksum, notes_file)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "dist")
    args = parser.parse_args()
    try:
        prepared = prepare_release(args.root, args.tag, args.output_dir)
    except (OSError, ValueError, KeyError, SyntaxError) as err:
        parser.exit(1, f"Release preparation failed: {err}\n")
    print(
        json.dumps(
            {
                "tag": prepared.tag,
                "version": prepared.version,
                "archive": prepared.archive.name,
                "checksum": prepared.checksum.name,
                "notes": prepared.notes.name,
            }
        )
    )


if __name__ == "__main__":
    main()
