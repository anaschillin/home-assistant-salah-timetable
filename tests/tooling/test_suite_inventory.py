"""Keep the documented test inventory aligned with files on disk.

This is intentionally stdlib-only: a test file moved or added without updating the
inventory/area guide should fail the regular pytest CI job.
"""

import json
import re
import shutil
import tomllib
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
    from scripts.versions import load_versions

    values = load_versions(REPO_ROOT)
    central = (REPO_ROOT / "versions.toml").read_text(encoding="utf-8")
    central = central.replace(f'version = "{values["version"]}"', 'version = "9.8.7"')
    (tmp_path / "versions.toml").write_text(central, encoding="utf-8")
    manifest = tmp_path / "custom_components" / "salah_timetable" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('{"version":"0.0.0","requirements":["pypdf==0.0.0"]}')
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nrequires-python = ">=3.14.2"\n'
    )
    for lane, ha, plugin in (
        ("minimum", "1900.1.0", "0.0.0"),
        ("supported-current", "1900.2.0", "0.0.1"),
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
    # A normal WSL checkout may use .venv-wsl rather than uv's default .venv.
    # Installed packages refer to upstream files that are absent from wheels.
    for ignored in (
        ".venv",
        ".venv-wsl/lib/site-packages",
        "venv-local/lib/site-packages",
        "compatibility/minimum/.venv/lib/site-packages",
        "node_modules/package",
        "dist/package",
    ):
        package_readme = tmp_path / ignored / "README.md"
        package_readme.parent.mkdir(parents=True, exist_ok=True)
        package_readme.write_text("[upstream tests](missing-fixtures/)\n")
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


def test_central_versions_update_all_consumers_without_check_mutation(tmp_path):
    """One config change reaches metadata, browser caches, CI and linked docs."""
    from scripts.build_release import check_versions
    from scripts.sync_versions import synchronise as synchronise_versions
    from scripts.versions import load_versions

    root = tmp_path / "source"
    shutil.copytree(
        REPO_ROOT,
        root,
        ignore=shutil.ignore_patterns(
            ".git",
            ".venv*",
            "venv-*",
            "node_modules",
            "__pycache__",
            ".pytest_cache",
            ".ruff_cache",
            ".coverage*",
            "dist",
        ),
    )
    original = load_versions(root)
    config = root / "versions.toml"
    central = config.read_text(encoding="utf-8")
    replacements = (
        ("version", original["version"], "9.8.7"),
        ("python_min", original["python_min"], "3.15.1"),
        ("node_major", original["node_major"], "26"),
        ("uv", original["uv"], "0.14.0"),
        ("ruff", original["ruff"], "0.18.0"),
        ("pypdf", original["pypdf"], "6.22.0"),
        ("homeassistant", original["homeassistant_min"], "2026.10.1"),
        ("homeassistant", original["homeassistant_tested"], "2026.11.0"),
        ("test_plugin", original["test_plugin_min"], "0.13.372"),
        ("test_plugin", original["test_plugin_tested"], "0.14.0"),
    )
    for key, old, new in replacements:
        setting = f'{key} = "{old}"'
        assert central.count(setting) == 1
        central = central.replace(setting, f'{key} = "{new}"')
    config.write_text(central, encoding="utf-8")
    frontend = root / "custom_components/salah_timetable/frontend"
    extra_consumer = frontend / "extra-consumer.js"
    extra_consumer.write_text(
        'import "./card-utils.js?v=0.0.0";\n'
        'import { future } from "./future-helper.js";\n'
    )
    (frontend / "future-helper.js").write_text("export const future = 1;\n")
    existing_consumer = frontend / "salah-timetable-card.js"
    existing_consumer.write_text(
        existing_consumer.read_text().replace(
            f"card-styles.js?v={original['version']}", "card-styles.js"
        )
    )
    manifest_path = root / "custom_components/salah_timetable/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["requirements"].append("unrelated-helper==1.2.3")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    def snapshot():
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file()
        }

    before_check = snapshot()
    changed = synchronise_versions(root)
    assert snapshot() == before_check
    assert set(changed) >= {
        "pyproject.toml",
        "hacs.json",
        ".pre-commit-config.yaml",
        ".github/workflows/validate.yml",
        ".github/workflows/unit-compatibility.yml",
        "compatibility/minimum/pyproject.toml",
        "compatibility/supported-current/pyproject.toml",
        "custom_components/salah_timetable/manifest.json",
        "custom_components/salah_timetable/frontend.py",
        "custom_components/salah_timetable/frontend/extra-consumer.js",
        "README.md",
        "docs/testing.md",
    }
    assert synchronise_versions(root, write=True) == changed
    assert synchronise_versions(root) == []
    assert config.read_text(encoding="utf-8") == central
    assert check_versions(root) == "9.8.7"
    manifest = json.loads(
        (root / "custom_components/salah_timetable/manifest.json").read_text()
    )
    assert manifest["version"] == "9.8.7"
    assert manifest["requirements"] == ["pypdf==6.22.0", "unrelated-helper==1.2.3"]
    assert json.loads((root / "hacs.json").read_text())["homeassistant"] == "2026.10.1"
    project = tomllib.loads((root / "pyproject.toml").read_text())
    assert project["project"]["version"] == "9.8.7"
    assert project["project"]["requires-python"] == ">=3.15.1"
    assert project["tool"]["ruff"]["target-version"] == "py315"
    assert {
        "pypdf==6.22.0",
        "ruff==0.18.0",
        "pytest-homeassistant-custom-component==0.14.0",
    } <= set(project["dependency-groups"]["dev"])
    for lane, ha, plugin in (
        ("minimum", "2026.10.1", "0.13.372"),
        ("supported-current", "2026.11.0", "0.14.0"),
    ):
        metadata = tomllib.loads(
            (root / "compatibility" / lane / "pyproject.toml").read_text()
        )["project"]
        assert metadata["requires-python"] == ">=3.15.1,<3.16"
        assert {
            f"homeassistant=={ha}",
            f"pytest-homeassistant-custom-component=={plugin}",
            "pypdf==6.22.0",
        } <= set(metadata["dependencies"])
    assert "rev: v0.18.0" in (root / ".pre-commit-config.yaml").read_text()
    validate = (root / ".github/workflows/validate.yml").read_text()
    assert "python-version: '3.15'" in validate
    assert "node-version: '26'" in validate
    assert "version: '0.14.0'" in validate
    compatibility = (root / ".github/workflows/unit-compatibility.yml").read_text()
    assert "--python python3.15" in compatibility
    assert 'import "./card-utils.js?v=9.8.7";' in extra_consumer.read_text()
    assert 'from "./future-helper.js?v=9.8.7"' in extra_consumer.read_text()
    assert "card-styles.js?v=9.8.7" in existing_consumer.read_text()
    readme = (root / "README.md").read_text()
    assert "<!-- docs:version -->9.8.7<!-- /docs:version -->" in readme
    assert "<!-- docs:python_min -->3.15.1<!-- /docs:python_min -->" in readme
    guide = (root / "docs/testing.md").read_text()
    assert "<!-- docs:pypdf -->6.22.0<!-- /docs:pypdf -->" in guide
    assert "<!-- docs:homeassistant_tested -->2026.11.0" in guide


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
    matrix = json.loads(compatibility_matrix(values))
    assert len(matrix["include"]) == 2
    for lane in matrix["include"]:
        assert (lane["ha-version"], lane["plugin-version"]) == expected[lane["lane"]]
    assignments = shell_assignments(values)
    assert f"HA_TESTED_VERSION={values['homeassistant_tested']}" in assignments
    assert f"INTEGRATION_VERSION={values['version']}" in assignments


def test_excerpt_rendering_preserves_links_for_each_consumer(tmp_path):
    """One source renders working relative links in root and nested guides."""
    from scripts.sync_documentation import render_excerpts

    excerpt = tmp_path / "docs/_excerpts/support-summary.md"
    excerpt.parent.mkdir(parents=True)
    excerpt.write_text(
        "See [testing](../testing.md#compatibility-test-environments). "
        "HA <!-- docs:homeassistant_min -->old<!-- /docs:homeassistant_min -->.\n",
        encoding="utf-8",
    )
    marker = (
        "<!-- docs:excerpt support-summary -->\n"
        "stale content\n"
        "<!-- /docs:excerpt support-summary -->"
    )
    values = {"homeassistant_min": "2026.10.0"}
    root_rendered = render_excerpts(tmp_path, Path("README.md"), marker, values)
    nested_rendered = render_excerpts(
        tmp_path, Path("docs/getting-started.md"), marker, values
    )
    assert "[testing](docs/testing.md#compatibility-test-environments)" in root_rendered
    assert "[testing](testing.md#compatibility-test-environments)" in nested_rendered
    assert "docs:homeassistant_min -->2026.10.0" in nested_rendered
    assert "stale content" not in nested_rendered
    assert (
        render_excerpts(
            tmp_path, Path("docs/getting-started.md"), nested_rendered, values
        )
        == nested_rendered
    )


def test_excerpt_rendering_rejects_missing_or_unbalanced_sources(tmp_path):
    """Broken include names must fail the documentation CI check."""
    from scripts.sync_documentation import render_excerpts

    opening = "<!-- docs:excerpt unknown -->"
    with pytest.raises(ValueError, match="Unbalanced"):
        render_excerpts(tmp_path, Path("README.md"), opening, {})
    complete = opening + "\nold\n<!-- /docs:excerpt unknown -->"
    with pytest.raises(ValueError, match="Missing documentation excerpt"):
        render_excerpts(tmp_path, Path("README.md"), complete, {})
