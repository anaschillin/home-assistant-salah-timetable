"""Classify PR changes conservatively so required CI checks remain present."""

import argparse
import subprocess
import sys
from pathlib import Path


def changed_paths(base: str, head: str, *, cwd: Path | None = None) -> list[str]:
    """Include original paths of renames/deletions in a merge-base diff."""
    result = subprocess.run(
        ["git", "diff", "--no-renames", "--name-only", "-z", f"{base}...{head}"],
        check=True,
        capture_output=True,
        cwd=cwd,
    )
    return [path.decode("utf-8") for path in result.stdout.split(b"\0") if path]


def is_markdown_only(paths: list[str]) -> bool:
    """Unknown, empty, and non-Markdown changes must run full validation."""
    return bool(paths) and all(path.endswith(".md") for path in paths)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    paths = changed_paths(args.base, args.head)
    docs_only = is_markdown_only(paths)
    print(f"docs_only={str(docs_only).lower()}")
    print(
        f"CI: {len(paths)} changed paths; Markdown-only: {docs_only}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
