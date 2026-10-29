"""Report branch coverage while preserving the existing 94.5% *line* gate.

pytest-cov's --cov-fail-under with --cov-branch measures a combined percentage,
so it cannot enforce the original line threshold directly. Keep line coverage
blocking and report the measured branch percentage separately.
"""

import argparse
import json
from pathlib import Path

MIN_LINE_PERCENT = 94.5


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument(
        "--badge-output",
        type=Path,
        help="Write a Shields.io endpoint for measured line coverage",
    )
    args = parser.parse_args()
    totals = json.loads(args.report.read_text(encoding="utf-8"))["totals"]
    statements = totals["num_statements"]
    covered_lines = totals["covered_lines"]
    branches = totals.get("num_branches", 0)
    covered_branches = totals.get("covered_branches", 0)
    if not statements or not branches:
        raise SystemExit("Branch coverage data is missing; pass --cov-branch")
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
    if line_percent + 1e-9 < MIN_LINE_PERCENT:
        print("Line coverage below the existing release gate")
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
