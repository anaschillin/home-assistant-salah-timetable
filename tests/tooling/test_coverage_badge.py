"""Verify README badge data comes from measured pytest coverage, never constants."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[2] / "scripts/check_coverage.py"


@pytest.mark.parametrize(
    ("covered", "expected_color"),
    [(987, "brightgreen"), (946, "yellow")],
)
def test_coverage_badge_reflects_measured_line_percent(
    tmp_path, covered, expected_color
):
    report = tmp_path / "report.json"
    badge = tmp_path / "coverage.json"
    report.write_text(
        json.dumps(
            {
                "totals": {
                    "num_statements": 1000,
                    "covered_lines": covered,
                    "num_branches": 200,
                    "covered_branches": 190,
                }
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(report), "--badge-output", str(badge)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(badge.read_text(encoding="utf-8")) == {
        "schemaVersion": 1,
        "label": "coverage",
        "message": f"{covered / 10:.2f}%",
        "color": expected_color,
    }


def test_failed_coverage_gate_does_not_publish_a_badge(tmp_path):
    report = tmp_path / "report.json"
    badge = tmp_path / "coverage.json"
    report.write_text(
        json.dumps(
            {
                "totals": {
                    "num_statements": 100,
                    "covered_lines": 90,
                    "num_branches": 20,
                    "covered_branches": 15,
                }
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(report), "--badge-output", str(badge)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert not badge.exists()
