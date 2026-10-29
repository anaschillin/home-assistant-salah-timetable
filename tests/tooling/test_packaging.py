"""Distribution checks guard missing assets, stale browser caches and private files."""

import hashlib
import os
import shutil
from zipfile import ZipFile

import pytest

from scripts.build_release import (
    INTEGRATION,
    PROJECT_ROOT,
    build_release,
    check_versions,
    release_files,
)


@pytest.fixture
def release_source(tmp_path):
    root = tmp_path / "source"
    shutil.copytree(
        PROJECT_ROOT / INTEGRATION,
        root / INTEGRATION,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    for name in ("LICENSE", "pyproject.toml"):
        shutil.copyfile(PROJECT_ROOT / name, root / name)
    return root


def test_archive_is_complete_and_excludes_nonruntime_data(release_source, tmp_path):
    source = release_source / INTEGRATION
    for name in (
        "__pycache__/storage.cpython-314.pyc",
        "original-timetable.pdf",
        "original-timetable.csv",
        "private.json",
        ".storage/private.json",
        "tests/fixture.csv",
        "frontend/.cache/private.js",
        "frontend/tests/private.js",
        "frontend/node_modules/private.js",
    ):
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"must never be distributed")
    archive = build_release(release_source, tmp_path / "dist")
    with ZipFile(archive) as bundle:
        names = bundle.namelist()
        assert names == sorted(names)
        for relative in (
            "__init__.py",
            "manifest.json",
            "icons.json",
            "translations/en.json",
            "frontend/salah-timetable-card.js",
            "frontend/card-styles.js",
            "frontend/card-utils.js",
            "frontend/card-i18n.js",
            "brand/icon.png",
        ):
            assert (INTEGRATION / relative).as_posix() in names
        assert "LICENSE" in names
        assert bundle.testzip() is None
        assert not any(
            word in name
            for name in names
            for word in ("private", "tests", ".pyc", ".pdf", ".csv")
        )
        for info in bundle.infolist():
            assert info.date_time == (1980, 1, 1, 0, 0, 0)
            assert info.external_attr >> 16 == 0o100644
    checksum = archive.with_suffix(".zip.sha256").read_text().strip()
    assert (
        checksum
        == f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}"
    )


def test_archive_does_not_depend_on_source_mtime_or_permissions(
    release_source, tmp_path
):
    first = build_release(release_source, tmp_path / "first").read_bytes()
    for _, path in release_files(release_source):
        os.utime(path, (1_700_000_000, 1_700_000_000))
        path.chmod(0o600)
    second = build_release(release_source, tmp_path / "second").read_bytes()
    assert first == second


@pytest.mark.parametrize(
    ("name", "old", "new", "error"),
    [
        ("pyproject.toml", 'version = "{version}"', 'version = "999.0.0"', "pyproject"),
        (
            "custom_components/salah_timetable/frontend.py",
            'CARD_VERSION = "{version}"',
            'CARD_VERSION = "999.0.0"',
            "CARD_VERSION",
        ),
        (
            "custom_components/salah_timetable/frontend/salah-timetable-card.js",
            "card-utils.js?v={version}",
            "card-utils.js?v=999.0.0",
            "cache version",
        ),
        (
            "custom_components/salah_timetable/frontend/salah-timetable-card.js",
            "card-styles.js?v={version}",
            "card-styles.js?v=999.0.0",
            "cache version",
        ),
        (
            "custom_components/salah_timetable/frontend/salah-timetable-card.js",
            "card-i18n.js?v={version}",
            "card-i18n.js?v=999.0.0",
            "cache version",
        ),
        (
            "custom_components/salah_timetable/frontend/card-utils.js",
            "card-i18n.js?v={version}",
            "card-i18n.js?v=999.0.0",
            "cache version",
        ),
    ],
)
def test_mismatched_versions_are_rejected(release_source, name, old, new, error):
    path = release_source / name
    old = old.format(version=check_versions(release_source))
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new))
    with pytest.raises(ValueError, match=error):
        check_versions(release_source)


@pytest.mark.parametrize("name", ["card-utils.js", "card-i18n.js", "card-styles.js"])
def test_missing_frontend_asset_is_rejected_before_output(
    release_source, tmp_path, name
):
    (release_source / INTEGRATION / "frontend" / name).unlink()
    output = tmp_path / "dist"
    with pytest.raises(ValueError, match="Missing release files"):
        build_release(release_source, output)
    assert not output.exists()


def test_symlinks_cannot_include_files_outside_source(release_source, tmp_path):
    private = tmp_path / "private.py"
    private.write_text("PRIVATE = 'secret'")
    (release_source / INTEGRATION / "private.py").symlink_to(private)
    with pytest.raises(ValueError, match="symlinks"):
        release_files(release_source)


def test_production_modules_have_single_canonical_location():
    """Only Home Assistant entrypoints and the PDF subprocess stay at root."""
    package = PROJECT_ROOT / INTEGRATION
    root_modules = {
        "__init__.py",
        "calendar.py",
        "config_flow.py",
        "const.py",
        "diagnostics.py",
        "frontend.py",
        "pdf_worker.py",
        "sensor.py",
    }
    assert {path.name for path in package.glob("*.py")} == root_modules

    grouped = {
        "domain": {
            "model.py",
            "ramadan.py",
            "ramadan_validation.py",
            "coverage.py",
            "events.py",
            "presentation.py",
        },
        "parsers": {
            "import_model.py",
            "csv_parser.py",
            "pdf_parser.py",
            "mosque_a_layout.py",
            "mosque_a_monthly_layout.py",
            "mosque_b_annual_layout.py",
            "mosque_b_ramadan_layout.py",
        },
        "imports": {
            "import_flow.py",
            "import_comparison.py",
        },
        "sources": {
            "download.py",
            "source_model.py",
            "source_flow.py",
            "source_updates.py",
        },
        "persistence": {
            "storage.py",
        },
        "runtime": {
            "coordinator.py",
        },
    }
    for folder, modules in grouped.items():
        actual = {path.name for path in (package / folder).glob("*.py")}
        assert actual == modules | {"__init__.py"}, folder
        assert not (root_modules & modules), folder
