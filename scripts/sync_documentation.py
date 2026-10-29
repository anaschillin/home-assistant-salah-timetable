"""Synchronise rendered documentation values and moved guide links.

GitHub Markdown has no cross-file variables. Inline docs markers contain real,
rendered text; this tool keeps those values synchronized with project metadata.
Run with --write after version or guide changes, or --check in CI.
"""

import argparse
import json
import posixpath
import re
import shlex
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

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


def metadata(root: Path) -> dict[str, str]:
    manifest = json.loads(
        (root / "custom_components/salah_timetable/manifest.json").read_text(
            encoding="utf-8"
        )
    )
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    values = {"version": manifest["version"]}
    values["python_min"] = re.search(
        r">=\s*(\d+\.\d+(?:\.\d+)?)", project["project"]["requires-python"]
    ).group(1)
    requirement = next(
        dep for dep in manifest["requirements"] if dep.startswith("pypdf==")
    )
    values["pypdf"] = requirement.split("==", 1)[1]
    for key, location in (
        ("homeassistant_min", "minimum"),
        ("homeassistant_tested", "supported-current"),
    ):
        setting = tomllib.loads(
            (root / "compatibility" / location / "pyproject.toml").read_text(
                encoding="utf-8"
            )
        )
        requirement = next(
            d
            for d in setting["project"]["dependencies"]
            if d.startswith("homeassistant==")
        )
        values[key] = requirement.split("==", 1)[1]
        plugin = next(
            d
            for d in setting["project"]["dependencies"]
            if d.startswith("pytest-homeassistant-custom-component==")
        )
        values["test_plugin_min" if location == "minimum" else "test_plugin_tested"] = (
            plugin.split("==", 1)[1]
        )
    return values


def shell_assignments(values: dict[str, str]) -> str:
    """Emit Bash-compatible assignments from the same metadata as the docs."""
    names = {
        "INTEGRATION_VERSION": "version",
        "PYTHON_MIN_VERSION": "python_min",
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


def synchronise(root: Path = ROOT, write: bool = False) -> list[str]:
    """Return changed file names; write them only when explicitly requested."""
    values = metadata(root)
    differences = []
    for path in sorted(root.rglob("*.md")):
        if set(path.relative_to(root).parts) & {
            ".venv",
            ".git",
            "node_modules",
            "dist",
        }:
            continue
        relative = path.relative_to(root)
        original = path.read_text(encoding="utf-8")
        expected = rewrite_links(relative, original)

        def replace_marker(m: re.Match[str]) -> str:
            key = m.group("key")
            if key not in values:
                raise ValueError(f"Unknown docs variable {key} in {relative}")
            return f"<!-- docs:{key} -->{values[key]}<!-- /docs:{key} -->"

        expected = MARKER.sub(replace_marker, expected)
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
