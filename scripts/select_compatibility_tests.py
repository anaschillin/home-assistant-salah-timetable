"""Deterministic file selection for separately pinned Home Assistant CI lanes.

All test_*.py modules run in every HA version. The minimum lane isolates the
HTTP-upload-heavy source flow module in its own process; other modules are split
evenly into four disjoint groups. New modules are discovered automatically.
"""

import argparse
from pathlib import Path

CORE_GROUPS = 4
SOURCE_FLOW_MODULE = "test_source_flow.py"


def partition_test_files(test_dir: Path) -> dict[str, list[Path]]:
    """Return the full suite and an exhaustive, non-overlapping minimum partition."""
    modules = sorted(path for path in test_dir.glob("test_*.py") if path.is_file())
    source_flow = test_dir / SOURCE_FLOW_MODULE
    if source_flow not in modules:
        raise ValueError(f"Required test module is missing: {source_flow}")

    other_modules = [path for path in modules if path != source_flow]
    if len(other_modules) < CORE_GROUPS:
        raise ValueError("Not enough test modules for the configured compatibility groups")

    groups = {f"core-{index}": [] for index in range(CORE_GROUPS)}
    for index, path in enumerate(other_modules):
        groups[f"core-{index % CORE_GROUPS}"].append(path)
    groups["source-flow"] = [source_flow]

    assigned = [path for group in groups.values() for path in group]
    if sorted(assigned) != modules:
        raise ValueError("Test partition omits or duplicates test modules")
    return {"all": modules, **groups}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("group", choices=("all", "source-flow", *(f"core-{i}" for i in range(CORE_GROUPS))))
    parser.add_argument("--tests-dir", type=Path, default=Path("tests"))
    args = parser.parse_args()

    try:
        groups = partition_test_files(args.tests_dir)
    except ValueError as err:
        parser.error(str(err))
    for module in groups[args.group]:
        print(module.as_posix())


if __name__ == "__main__":
    main()
