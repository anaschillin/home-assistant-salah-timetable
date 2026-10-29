"""Release preparation selects reviewed notes and rejects metadata mismatch."""

import json
import shutil
from pathlib import Path
from zipfile import ZipFile

import pytest

from scripts.build_release import INTEGRATION, PROJECT_ROOT
from scripts.prepare_release import prepare_release, release_notes


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "source"
    shutil.copytree(
        PROJECT_ROOT / INTEGRATION,
        root / INTEGRATION,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    for name in ("LICENSE", "pyproject.toml", "CHANGELOG.md"):
        shutil.copyfile(PROJECT_ROOT / name, root / name)
    return root


def version(root: Path) -> str:
    return json.loads((root / INTEGRATION / "manifest.json").read_text())["version"]


def test_prepared_assets_have_current_notes_and_complete_archive(source, tmp_path):
    current = version(source)
    (source / "CHANGELOG.md").write_text(
        f"# Changelog\n\n## {current} — unreleased\n\n"
        "- Correct the current display.\n\n## 0.0.1\n\n- Old change.\n"
    )
    prepared = prepare_release(source, f"v{current}", tmp_path / "output")
    assert prepared.version == current
    assert prepared.archive.name == f"salah_timetable-{current}.zip"
    assert prepared.checksum.is_file()
    assert "Correct the current display." in prepared.notes.read_text()
    assert "Old change." not in prepared.notes.read_text()
    assert "unreleased" not in prepared.notes.read_text()
    with ZipFile(prepared.archive) as bundle:
        assert (
            INTEGRATION / "frontend/salah-timetable-card.js"
        ).as_posix() in bundle.namelist()
        assert "release-notes.md" not in bundle.namelist()


@pytest.mark.parametrize(
    "tag", ["v999.0.0", "main", "../outside", "v0.5.1; echo wrong"]
)
def test_wrong_tags_create_no_output(source, tmp_path, tag):
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="manifest version"):
        prepare_release(source, tag, output)
    assert not output.exists()


@pytest.mark.parametrize("notes", ["# Changelog\n\n## 0.0.1\n\n- Old.\n", "empty"])
def test_missing_or_empty_notes_create_no_output(source, tmp_path, notes):
    current = version(source)
    if notes == "empty":
        notes = f"# Changelog\n\n## {current}\n\n## 0.0.1\n\n- Old.\n"
    (source / "CHANGELOG.md").write_text(notes)
    output = tmp_path / "output"
    with pytest.raises(ValueError, match="changelog section"):
        prepare_release(source, f"v{current}", output)
    assert not output.exists()


def test_repository_changelog_current_version_has_release_notes():
    """Catch version headings annotated with dates/status in the real changelog."""
    current = version(PROJECT_ROOT)
    notes = release_notes(PROJECT_ROOT, current)
    assert notes.startswith(f"# Salah Timetable {current}\n")
    assert len(notes.splitlines()) > 2
