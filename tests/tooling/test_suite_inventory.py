"""Keep the documented test inventory aligned with files on disk.

This is intentionally stdlib-only: a test file moved or added without updating the
inventory/area guide should fail the regular pytest CI job.
"""

import re
from pathlib import Path

import pytest

from scripts.sync_documentation import (
    compatibility_matrix,
    metadata,
    shell_assignments,
    synchronise,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_ROOT = REPO_ROOT / "tests"
GUIDE = REPO_ROOT / "docs" / "testing.md"
AREAS = frozenset(
    {
        "automations",
        "calendar",
        "core",
        "frontend",
        "imports",
        "parsers",
        "ramadan",
        "sources",
        "storage",
        "tooling",
    }
)


def _section(content: str, start: str, end: str) -> str:
    """Return one section from the documented test inventory."""
    assert start in content, f"Missing inventory heading: {start}"
    after_start = content.split(start, 1)[1]
    assert end in after_start, f"Missing next inventory heading: {end}"
    return after_start.split(end, 1)[0]


def _python_inventory(content: str) -> list[str]:
    section = _section(
        content, "## Python test modules", "## JavaScript and browser tests"
    )
    result = []
    area = None
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 3:
            continue
        heading, filename = cells[:2]
        if heading.startswith("**") and heading.endswith("**"):
            area = heading.strip("*")
        if re.fullmatch(r"`test_[a-zA-Z0-9_]+\.py`", filename):
            assert area in AREAS, f"Unknown category for {filename}: {area}"
            result.append(f"{area}/{filename.strip('`')}")
    return result


def test_all_python_test_modules_are_documented_once():
    content = GUIDE.read_text(encoding="utf-8")
    documented = _python_inventory(content)
    paths = TEST_ROOT.rglob("test_*.py")
    actual = sorted(path.relative_to(TEST_ROOT).as_posix() for path in paths)
    assert len(documented) == len(set(documented)), "Duplicate Python inventory entries"
    assert sorted(documented) == actual
    heading = re.search(r"## Python test modules \((\d+)\)", content)
    assert heading is not None
    assert int(heading.group(1)) == len(actual)


def test_all_node_unit_test_modules_are_documented_once():
    content = GUIDE.read_text(encoding="utf-8")
    section = _section(
        content,
        "## JavaScript and browser tests",
        "## Fixtures, helpers and test data",
    )
    documented = re.findall(r"(?m)^\|\s*`([^\`]+\.test\.mjs)`\s*\|", section)
    node_paths = list(TEST_ROOT.rglob("*.test.mjs"))
    actual = sorted(path.name for path in node_paths)
    assert len(documented) == len(set(documented)), "Duplicate Node inventory entries"
    assert sorted(documented) == actual
    assert all(path.parent == TEST_ROOT / "frontend" for path in node_paths)
    count = re.search(r"The following (\d+) Node unit modules", section)
    assert count is not None
    assert int(count.group(1)) == len(actual)


def test_every_test_area_has_a_maintenance_guide():
    modules = list(TEST_ROOT.rglob("test_*.py"))
    assert modules
    categories = {path.relative_to(TEST_ROOT).parts[0] for path in modules}
    assert categories == AREAS
    assert (TEST_ROOT / "conftest.py").is_file()
    for area in sorted(AREAS):
        guide = TEST_ROOT / area / "README.md"
        assert guide.is_file(), f"No maintenance guide for {area}"
        assert "../../docs/testing.md" in guide.read_text(encoding="utf-8")


def test_documentation_sync_updates_metadata_and_renamed_links(tmp_path):
    """Documentation is rendered from project metadata and canonical link routes."""
    manifest = tmp_path / "custom_components" / "salah_timetable" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"version":"9.8.7","requirements":["pypdf==6.21.2"]}')
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nrequires-python = ">=3.14.2"\n'
    )
    for lane, ha, plugin in (
        ("minimum", "2026.10.0", "0.13.371"),
        ("supported-current", "2026.10.3", "0.13.374"),
    ):
        path = tmp_path / "compatibility" / lane / "pyproject.toml"
        path.parent.mkdir(parents=True)
        path.write_text(
            "[project]\ndependencies = ["
            f'"homeassistant=={ha}", '
            f'"pytest-homeassistant-custom-component=={plugin}"]\n'
        )
    guide = tmp_path / "docs" / "automations.md"
    guide.parent.mkdir()
    guide.write_text("# Automations\n\n## Prayer calendar\n")
    index = tmp_path / "README.md"
    index.write_text(
        "See [calendar](docs/calendar.md). Version "
        "<!-- docs:version -->0.0.1<!-- /docs:version -->, "
        "plugin <!-- docs:test_plugin_min -->0.0.0<!-- /docs:test_plugin_min -->."
    )
    assert synchronise(tmp_path) == ["README.md"]
    assert synchronise(tmp_path, write=True) == ["README.md"]
    written = index.read_text()
    assert "docs/automations.md#prayer-calendar" in written
    assert "<!-- docs:version -->9.8.7<!-- /docs:version -->" in written
    assert (
        "<!-- docs:test_plugin_min -->0.13.371<!-- /docs:test_plugin_min -->" in written
    )
    assert synchronise(tmp_path) == []


def test_documentation_sync_rejects_missing_relative_destinations(tmp_path):
    """A local Markdown link must not become a silent 404."""
    from scripts.sync_documentation import check_local_links

    (tmp_path / "README.md").write_text("# Documentation")
    with pytest.raises(ValueError, match="Missing link destination"):
        check_local_links(
            tmp_path, Path("README.md"), "[missing](docs/no-such-guide.md)"
        )


def test_version_exports_match_pinned_metadata():
    """Executable examples and CI use one authority for their version values."""
    values = metadata(REPO_ROOT)
    expected = {
        "minimum": (values["homeassistant_min"], values["test_plugin_min"]),
        "supported-current": (
            values["homeassistant_tested"],
            values["test_plugin_tested"],
        ),
    }
    import json

    matrix = json.loads(compatibility_matrix(values))
    assert len(matrix["include"]) == 2
    for lane in matrix["include"]:
        assert (lane["ha-version"], lane["plugin-version"]) == expected[lane["lane"]]
    assignments = shell_assignments(values)
    assert f"HA_TESTED_VERSION={values['homeassistant_tested']}" in assignments
    assert f"INTEGRATION_VERSION={values['version']}" in assignments
