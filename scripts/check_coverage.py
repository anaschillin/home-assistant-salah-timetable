"""Enforce the integration's line and rule-specific branch coverage gates.

pytest-cov's --cov-fail-under with --cov-branch measures a combined percentage,
so use raw counts to preserve the 94.5% aggregate line threshold, require greater
than 95% combined statement/branch coverage per module, and require full config
and options flow coverage. Run from the repository root with a coverage.py JSON report.
"""

import argparse
import ast
import json
from pathlib import Path

MIN_LINE_TENTHS = 945
MIN_LINE_PERCENT = MIN_LINE_TENTHS / 10
MIN_MODULE_PERCENT = 95
INTEGRATION_ROOT = Path("custom_components/salah_timetable")
FLOW_MODULES = frozenset(
    Path(name)
    for name in ("config_flow.py", "imports/import_flow.py", "sources/source_flow.py")
)


def coverage_counts(summary: dict, label: str) -> tuple[int, int, int, int]:
    """Reject missing branch measurements and impossible coverage counts."""
    if not isinstance(summary, dict):
        raise ValueError(f"{label}: missing coverage summary")
    keys = ("num_statements", "covered_lines", "num_branches", "covered_branches")
    counts = tuple(summary.get(key) for key in keys)
    if any(type(count) is not int or count < 0 for count in counts):
        raise ValueError(f"{label}: missing or invalid coverage counts")
    statements, lines, branches, covered_branches = counts
    if (
        lines > statements
        or covered_branches > branches
        or (not statements and branches)
    ):
        raise ValueError(f"{label}: covered counts exceed measured counts")
    return statements, lines, branches, covered_branches


def empty_initializer(path: Path) -> bool:
    """Only genuinely empty package initializers have no measurable statements."""
    return path.name == "__init__.py" and all(
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str)
        for statement in ast.parse(path.read_text(encoding="utf-8")).body
    )


def check_modules(report: dict) -> bool:
    """Check the source inventory so omitted/new modules cannot evade the gate."""
    sources = sorted(INTEGRATION_ROOT.rglob("*.py"))
    if not sources:
        raise ValueError(f"No integration modules found under {INTEGRATION_ROOT}")
    files = report.get("files", {})
    if not isinstance(files, dict):
        raise ValueError("Per-module coverage data is missing")
    summaries = {Path(name).resolve(): data["summary"] for name, data in files.items()}
    passed = True
    for source in sources:
        summary = summaries.get(source.resolve())
        if summary is None:
            print(f"{source}: missing from coverage report")
            passed = False
            continue
        statements, lines, branches, covered_branches = coverage_counts(
            summary, str(source)
        )
        total = statements + branches
        covered = lines + covered_branches
        if total == 0:
            if empty_initializer(source):
                print(f"{source}: empty package initializer (no executable statements)")
            else:
                print(f"{source}: no measured statements")
                passed = False
            continue
        percent = 100 * covered / total
        # Compare integer counts: even a result rounded to 95.00% must be >95%.
        if covered * 100 <= MIN_MODULE_PERCENT * total:
            print(
                f"{source}: combined coverage {covered}/{total} ({percent:.4f}%), "
                f"must be >{MIN_MODULE_PERCENT}%"
            )
            passed = False
        if source.relative_to(INTEGRATION_ROOT) in FLOW_MODULES and (
            lines != statements or covered_branches != branches
        ):
            print(
                f"{source}: config and options flows require 100% line and branch coverage "
                f"({lines}/{statements} lines, {covered_branches}/{branches} branches)"
            )
            passed = False
    if passed:
        print(
            f"Module coverage: all {len(sources)} modules pass >{MIN_MODULE_PERCENT}% "
            "combined coverage (empty initializers have no statements); "
            "config and options flows have 100% line and branch coverage"
        )
    return passed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument(
        "--badge-output",
        type=Path,
        help="Write a Shields.io endpoint for measured line coverage",
    )
    args = parser.parse_args()
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
        if (
            not isinstance(report, dict)
            or report.get("meta", {}).get("branch_coverage") is not True
        ):
            raise ValueError("Branch coverage data is missing; pass --cov-branch")
        statements, covered_lines, branches, covered_branches = coverage_counts(
            report["totals"], "Totals"
        )
        if not statements or not branches:
            raise ValueError("Branch coverage data is missing; pass --cov-branch")
        modules_passed = check_modules(report)
    except (KeyError, TypeError, ValueError) as error:
        print(f"Invalid coverage report: {error}")
        return 1
    line_percent = 100 * covered_lines / statements
    branch_percent = 100 * covered_branches / branches
    print(
        f"Line coverage: {covered_lines}/{statements} "
        f"({line_percent:.2f}%, minimum {MIN_LINE_PERCENT}%)"
    )
    print(
        f"Branch coverage (diagnostic): {covered_branches}/{branches} "
        f"({branch_percent:.2f}%)"
    )
    if covered_lines * 1000 < MIN_LINE_TENTHS * statements:
        print("Line coverage below the existing release gate")
        return 1
    if not modules_passed:
        return 1
    if args.badge_output is not None:
        badge = {
            "schemaVersion": 1,
            "label": "coverage",
            "message": f"{line_percent:.2f}%",
            "color": "brightgreen" if line_percent > 95 else "yellow",
        }
        args.badge_output.write_text(
            json.dumps(badge, indent=2) + "\n", encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
