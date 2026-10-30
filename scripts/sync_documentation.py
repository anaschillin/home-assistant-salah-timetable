"""Synchronise rendered documentation values, shared excerpts and guide links.

GitHub Markdown has no cross-file variables. Inline docs markers contain real,
rendered text; this tool keeps those values synchronized with project metadata.
Run with --write after version or guide changes, or --check in CI.
"""

import argparse
import json
import posixpath
import re
import shlex
from pathlib import Path

if __package__:
    from .versions import ROOT, load_versions
else:
    from versions import ROOT, load_versions

# Single source for retired guide routes. The optional suffix is the landing section.
GUIDE_ROUTES = {
    "docs/calendar.md": "docs/automations.md#prayer-calendar",
    "docs/pdf_layouts.md": "docs/import_review.md#supported-pdf-layouts",
    "docs/ramadan_validation.md": "docs/import_review.md#ramadan-timetable-validation",
    "docs/mosque-background-credits.md": "docs/asset-provenance.json",
    "docs/mosque-backgrounds.md": "docs/dashboard.md#mosque-photograph-implementation-and-maintenance",
    "docs/support.md": "docs/getting-started.md#support-and-compatibility-policy",
    "docs/module-inventory.md": "docs/architecture.md#production-module-inventory",
    "docs/compatibility.md": "docs/testing.md#compatibility-test-environments",
    "docs/live-smoke.md": "docs/testing.md#disposable-home-assistant-live-testing",
    "docs/visual-regression.md": "docs/testing.md#frontend-visual-regression",
    "docs/validation.md": "docs/releasing.md#validation-and-acceptance-scope",
    "docs/backup-restore-acceptance.md": "docs/releasing.md#optional-full-backup-and-restore-acceptance",
    "docs/islamic-history-display-defaults.md": "docs/dashboard.md#hijri-month-information-and-future-history-options",
    "docs/islamic-history-source-audit.md": "research/islamic-history/islamic-history-source-audit.md",
    "docs/islamic-history-dorar-coverage-audit.md": "research/islamic-history/islamic-history-dorar-coverage-audit.md",
}
for _name in (
    "islamic-history-additional-eras.json",
    "islamic-history-candidates.json",
    "islamic-history-day-coverage.json",
    "islamic-history-months-draft.json",
    "islamic-history-prophetic-era-subset.json",
):
    GUIDE_ROUTES["docs/" + _name] = "research/islamic-history/" + _name

LINK = re.compile(r"(?<!!)\]\((?P<target>[^)\s]+)(?P<suffix>\s+\"[^\"]*\")?\)")
MARKER = re.compile(
    r"<!-- docs:(?P<key>[a-z_]+) -->(?P<value>.*?)<!-- /docs:(?P=key) -->"
)

EXCERPT = re.compile(
    r"<!-- docs:excerpt (?P<name>[a-z][a-z0-9-]*) -->\n"
    r"(?P<value>.*?)\n<!-- /docs:excerpt (?P=name) -->",
    re.DOTALL,
)
EXCERPT_OPEN = re.compile(r"<!-- docs:excerpt [a-z][a-z0-9-]* -->")


def metadata(root: Path) -> dict[str, str]:
    """Read documentation and CI values from the authoritative version file."""
    return load_versions(root)


def shell_assignments(values: dict[str, str]) -> str:
    """Emit Bash-compatible assignments from the same metadata as the docs."""
    names = {
        "INTEGRATION_VERSION": "version",
        "PYTHON_MIN_VERSION": "python_min",
        "PYTHON_SERIES": "python_minor",
        "NODE_MAJOR_VERSION": "node_major",
        "UV_VERSION": "uv",
        "PYPDF_VERSION": "pypdf",
        "HA_MIN_VERSION": "homeassistant_min",
        "HA_TESTED_VERSION": "homeassistant_tested",
        "PLUGIN_MIN_VERSION": "test_plugin_min",
        "PLUGIN_TESTED_VERSION": "test_plugin_tested",
    }
    return "\n".join(
        f"{variable}={shlex.quote(values[key])}" for variable, key in names.items()
    )


def compatibility_matrix(values: dict[str, str]) -> str:
    """Build the pinned compatibility matrix directly from the lock projects."""
    lanes = (
        ("minimum", "homeassistant_min", "test_plugin_min"),
        ("supported-current", "homeassistant_tested", "test_plugin_tested"),
    )
    return json.dumps(
        {
            "include": [
                {
                    "lane": lane,
                    "ha-version": values[ha],
                    "plugin-version": values[plugin],
                }
                for lane, ha, plugin in lanes
            ]
        },
        separators=(",", ":"),
    )


def rewrite_links(source_path: Path, text: str) -> str:
    """Change links to removed documents into relative links to canonical guides."""
    current = source_path.as_posix()

    def replace(m: re.Match[str]) -> str:
        target = m.group("target")
        if target.startswith(("https:", "http:", "mailto:", "#", "data:", "/", "//")):
            return m.group(0)
        bare, sep, fragment = target.partition("#")
        normalized = posixpath.normpath(
            posixpath.join(posixpath.dirname(current), bare)
        )
        route = GUIDE_ROUTES.get(normalized)
        if route is None:
            return m.group(0)
        destination, _, default_fragment = route.partition("#")
        relative = posixpath.relpath(destination, posixpath.dirname(current) or ".")
        anchor = fragment if sep else default_fragment
        return (
            "]("
            + relative
            + ("#" + anchor if anchor else "")
            + (m.group("suffix") or "")
            + ")"
        )

    return LINK.sub(replace, text)


def check_local_links(root: Path, source_path: Path, source: str) -> None:
    """Reject broken relative Markdown paths after redirects are applied."""
    current = source_path.as_posix()
    for match in LINK.finditer(source):
        target = match.group("target")
        if target.startswith(("https:", "http:", "mailto:", "#", "data:", "/", "//")):
            continue
        bare = target.partition("#")[0].partition("?")[0]
        candidate = posixpath.normpath(posixpath.join(posixpath.dirname(current), bare))
        if not (root / candidate).exists():
            raise ValueError(f"Missing link destination in {current}: {target}")


def render_excerpts(
    root: Path, destination: Path, text: str, values: dict[str, str]
) -> str:
    """Expand canonical snippets into GitHub-renderable, relative-link-safe Markdown."""
    matches = list(EXCERPT.finditer(text))
    if len(matches) != len(EXCERPT_OPEN.findall(text)):
        raise ValueError(f"Unbalanced documentation excerpt in {destination}")

    def replace_excerpt(match: re.Match[str]) -> str:
        name = match.group("name")
        source = Path("docs/_excerpts") / f"{name}.md"
        absolute = root / source
        if not absolute.is_file():
            raise ValueError(f"Missing documentation excerpt {name} in {destination}")
        content = absolute.read_text(encoding="utf-8").strip()
        if EXCERPT_OPEN.search(content):
            raise ValueError(f"Nested documentation excerpt in {source}")
        content = rewrite_links(source, content)

        def replace_marker(found: re.Match[str]) -> str:
            key = found.group("key")
            if key not in values:
                raise ValueError(f"Unknown docs variable {key} in {source}")
            return f"<!-- docs:{key} -->{values[key]}<!-- /docs:{key} -->"

        content = MARKER.sub(replace_marker, content)

        def rewrite_relative_link(found: re.Match[str]) -> str:
            url = found.group("target")
            if url.startswith(("https:", "http:", "mailto:", "#", "data:", "/", "//")):
                return found.group(0)
            path, separator, fragment = url.partition("#")
            canonical = posixpath.normpath(
                posixpath.join(source.parent.as_posix(), path)
            )
            relative = posixpath.relpath(
                canonical, destination.parent.as_posix() or "."
            )
            return (
                "]("
                + relative
                + ("#" + fragment if separator else "")
                + (found.group("suffix") or "")
                + ")"
            )

        content = LINK.sub(rewrite_relative_link, content)
        return f"<!-- docs:excerpt {name} -->\n{content}\n<!-- /docs:excerpt {name} -->"

    return EXCERPT.sub(replace_excerpt, text)


def synchronise(root: Path = ROOT, write: bool = False) -> list[str]:
    """Return changed file names; write them only when explicitly requested."""
    values = metadata(root)
    differences = []
    # Prune before descending: local venvs can contain thousands of unrelated
    # Markdown files and links to test fixtures absent from installed wheels.
    paths = []
    for directory, directories, filenames in root.walk():
        directories[:] = [
            name
            for name in directories
            if name not in {".git", "node_modules", "dist", "venv"}
            and not name.startswith((".venv", "venv-"))
        ]
        paths.extend(directory / name for name in filenames if name.endswith(".md"))
    for path in sorted(paths):
        relative = path.relative_to(root)
        original = path.read_text(encoding="utf-8")
        expected = rewrite_links(relative, original)

        def replace_marker(m: re.Match[str]) -> str:
            key = m.group("key")
            if key not in values:
                raise ValueError(f"Unknown docs variable {key} in {relative}")
            return f"<!-- docs:{key} -->{values[key]}<!-- /docs:{key} -->"

        expected = MARKER.sub(replace_marker, expected)
        expected = render_excerpts(root, relative, expected, values)
        check_local_links(root, relative, expected)
        if expected != original:
            differences.append(relative.as_posix())
            if write:
                path.write_text(expected, encoding="utf-8")
    return differences


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write", action="store_true", help="Update generated values and links"
    )
    parser.add_argument(
        "--check", action="store_true", help="Check tracked documentation"
    )
    parser.add_argument(
        "--shell",
        action="store_true",
        help="Print current metadata as Bash assignments",
    )
    parser.add_argument(
        "--matrix", action="store_true", help="Print the pinned HA matrix as JSON"
    )
    args = parser.parse_args()
    if args.shell or args.matrix:
        if args.write or args.check or (args.shell and args.matrix):
            parser.error("--shell/--matrix cannot be combined with other modes")
        values = metadata(ROOT)
        print(shell_assignments(values) if args.shell else compatibility_matrix(values))
        return 0
    changed = synchronise(write=args.write)
    if changed:
        status = "Updated" if args.write else "Documentation needs syncing"
        print(status + ": " + ", ".join(changed))
    if changed and not args.write:
        print("Run: python scripts/sync_documentation.py --write")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
