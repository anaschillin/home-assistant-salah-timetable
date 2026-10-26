"""Coverage checks for Home Assistant compatibility file selection."""

from pathlib import Path

import pytest

from scripts.select_compatibility_tests import CORE_GROUPS, partition_test_files


def write_test_modules(directory: Path, count: int = 19) -> list[Path]:
    directory.mkdir()
    paths = [directory / f"test_module_{index:02}.py" for index in range(count)] + [
        directory / "test_source_flow.py"
    ]
    for path in paths:
        path.write_text("# fixture module\n", encoding="utf-8")
    return sorted(paths)


def test_partitions_cover_all_modules_once_and_isolate_source_flow(tmp_path):
    tests_dir = tmp_path / "tests"
    expected = write_test_modules(tests_dir)
    groups = partition_test_files(tests_dir)

    assert groups["all"] == expected
    assert groups["source-flow"] == [tests_dir / "test_source_flow.py"]
    assert len(groups) == CORE_GROUPS + 2

    minimum_modules = [
        module
        for name, modules in groups.items()
        if name != "all"
        for module in modules
    ]
    assert sorted(minimum_modules) == expected
    assert all(groups[f"core-{index}"] for index in range(CORE_GROUPS))
    assert all(
        tests_dir / "test_source_flow.py" not in groups[f"core-{index}"]
        for index in range(CORE_GROUPS)
    )

    # The same input tree always yields the same group boundaries.
    assert partition_test_files(tests_dir) == groups


def test_missing_source_flow_fails_closed(tmp_path):
    tests_dir = tmp_path / "tests"
    write_test_modules(tests_dir)
    (tests_dir / "test_source_flow.py").unlink()
    with pytest.raises(ValueError, match="Required test module is missing"):
        partition_test_files(tests_dir)


def test_too_few_modules_fails_closed(tmp_path):
    tests_dir = tmp_path / "tests"
    write_test_modules(tests_dir, count=CORE_GROUPS - 1)
    with pytest.raises(ValueError, match="Not enough test modules"):
        partition_test_files(tests_dir)
