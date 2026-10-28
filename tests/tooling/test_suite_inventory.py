"""Keep the documented test inventory aligned with files on disk.

This is intentionally stdlib-only: a test file moved or added without updating the
inventory/area guide should fail the regular pytest CI job.
"""

import re
from pathlib import Path

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
    section = _section(content, "## Python test modules", "## JavaScript and browser tests")
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
    actual = sorted(
        path.relative_to(TEST_ROOT).as_posix()
        for path in TEST_ROOT.rglob("test_*.py")
    )
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
    actual = sorted(
        path.name for path in TEST_ROOT.rglob("*.test.mjs")
    )
    assert len(documented) == len(set(documented)), "Duplicate Node inventory entries"
    assert sorted(documented) == actual
    assert all(
        path.parent == TEST_ROOT / "frontend"
        for path in TEST_ROOT.rglob("*.test.mjs")
    )
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
