"""Exercise the CI gates and measured README badge through the coverage CLI."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[2] / "scripts/check_coverage.py"
PACKAGE = Path("custom_components/salah_timetable")


def summary(statements=990, lines=990, branches=1000, covered_branches=1000):
    return {
        "num_statements": statements,
        "covered_lines": lines,
        "num_branches": branches,
        "covered_branches": covered_branches,
        # Rounded display values must never control a gate.
        "percent_covered": 100,
        "percent_covered_display": "100",
    }


@pytest.fixture
def coverage_report(tmp_path):
    files = {
        str(PACKAGE / "config_flow.py"): {"summary": summary(10, 10, 2, 2)},
        str(PACKAGE / "runtime.py"): {"summary": summary()},
        str(PACKAGE / "domain/__init__.py"): {"summary": summary(0, 0, 0, 0)},
    }
    for name in files:
        source = tmp_path / name
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text('"""Synthetic integration module."""\n', encoding="utf-8")
    return {"meta": {"branch_coverage": True}, "files": files}


def run_check(tmp_path, report):
    report_path = tmp_path / "report.json"
    badge = tmp_path / "coverage.json"
    if "totals" not in report:
        report["totals"] = {
            key: sum(file["summary"][key] for file in report["files"].values())
            for key in (
                "num_statements",
                "covered_lines",
                "num_branches",
                "covered_branches",
            )
        }
    report_path.write_text(json.dumps(report), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(report_path), "--badge-output", str(badge)],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    return result, badge


@pytest.mark.parametrize(
    ("covered", "expected_color"),
    [(987, "brightgreen"), (946, "yellow")],
)
def test_coverage_badge_reflects_measured_line_percent(
    tmp_path, coverage_report, covered, expected_color
):
    coverage_report["files"][str(PACKAGE / "runtime.py")]["summary"][
        "covered_lines"
    ] = covered - 10
    result, badge = run_check(tmp_path, coverage_report)
    assert result.returncode == 0, result.stderr
    assert json.loads(badge.read_text(encoding="utf-8")) == {
        "schemaVersion": 1,
        "label": "coverage",
        "message": f"{covered / 10:.2f}%",
        "color": expected_color,
    }


@pytest.mark.parametrize(("lines", "expected"), [(935, 0), (934, 1)])
def test_aggregate_line_gate_preserves_exact_threshold(
    tmp_path, coverage_report, lines, expected
):
    # Full branch coverage keeps the module above 95% while exercising 94.5%
    # aggregate line coverage independently of the combined coverage gate.
    coverage_report["files"][str(PACKAGE / "runtime.py")]["summary"][
        "covered_lines"
    ] = lines
    result, badge = run_check(tmp_path, coverage_report)
    assert result.returncode == expected, result.stdout + result.stderr
    assert badge.exists() == (expected == 0)


@pytest.mark.parametrize(
    ("lines", "branches", "expected"),
    [(95, 95, 1), (96, 94, 1), (96, 95, 0)],
)
def test_module_gate_requires_strictly_more_than_95_percent(
    tmp_path, coverage_report, lines, branches, expected
):
    coverage_report["files"][str(PACKAGE / "runtime.py")]["summary"] = summary(
        100, lines, 100, branches
    )
    result, badge = run_check(tmp_path, coverage_report)
    assert result.returncode == expected, result.stdout + result.stderr
    assert badge.exists() == (expected == 0)


def test_low_module_cannot_hide_behind_high_aggregate(tmp_path, coverage_report):
    new_source = PACKAGE / "new_module.py"
    (tmp_path / new_source).write_text("value = 1\n", encoding="utf-8")
    coverage_report["files"][str(new_source)] = {"summary": summary(20, 18, 0, 0)}
    result, badge = run_check(tmp_path, coverage_report)
    assert result.returncode == 1
    assert not badge.exists()
    assert "new_module.py: combined coverage 18/20" in result.stdout


def test_module_percentage_is_not_rounded_up(tmp_path, coverage_report):
    coverage_report["files"][str(PACKAGE / "runtime.py")]["summary"] = summary(
        100000, 100000, 100000, 89999
    )
    result, badge = run_check(tmp_path, coverage_report)
    assert result.returncode == 1
    assert "95.0000%" not in result.stdout
    assert "94.9995%" in result.stdout
    assert not badge.exists()


@pytest.mark.parametrize("uncovered", ["line", "branch"])
@pytest.mark.parametrize(
    "flow", ["config_flow.py", "imports/import_flow.py", "sources/source_flow.py"]
)
def test_config_and_options_flows_require_full_line_and_branch_coverage(
    tmp_path, coverage_report, uncovered, flow
):
    source = tmp_path / PACKAGE / flow
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("value = 1\n", encoding="utf-8")
    coverage_report["files"][str(PACKAGE / flow)] = {
        "summary": summary(
            100,
            99 if uncovered == "line" else 100,
            100,
            99 if uncovered == "branch" else 100,
        )
    }
    result, badge = run_check(tmp_path, coverage_report)
    assert result.returncode == 1
    assert (
        "config and options flows require 100% line and branch coverage"
        in result.stdout
    )
    assert not badge.exists()


@pytest.mark.parametrize("missing", ["runtime.py", "domain/__init__.py"])
def test_source_inventory_rejects_omitted_modules(tmp_path, coverage_report, missing):
    del coverage_report["files"][str(PACKAGE / missing)]
    result, badge = run_check(tmp_path, coverage_report)
    assert result.returncode == 1
    assert f"{missing}: missing from coverage report" in result.stdout
    assert not badge.exists()


def test_zero_statement_initializer_cannot_hide_executable_code(
    tmp_path, coverage_report
):
    (tmp_path / PACKAGE / "domain/__init__.py").write_text(
        "value = 1\n", encoding="utf-8"
    )
    result, badge = run_check(tmp_path, coverage_report)
    assert result.returncode == 1
    assert "domain/__init__.py: no measured statements" in result.stdout
    assert not badge.exists()


def test_zero_statement_regular_module_is_not_an_empty_initializer(
    tmp_path, coverage_report
):
    coverage_report["files"][str(PACKAGE / "runtime.py")]["summary"] = summary(
        0, 0, 0, 0
    )
    result, badge = run_check(tmp_path, coverage_report)
    assert result.returncode == 1
    assert "runtime.py: no measured statements" in result.stdout
    assert not badge.exists()


@pytest.mark.parametrize("invalid", ["meta", "totals", "module", "count"])
def test_missing_branch_data_and_invalid_counts_fail_closed(
    tmp_path, coverage_report, invalid
):
    runtime = coverage_report["files"][str(PACKAGE / "runtime.py")]["summary"]
    if invalid == "meta":
        coverage_report["meta"]["branch_coverage"] = False
    elif invalid == "totals":
        coverage_report["totals"] = {"num_statements": 1000, "covered_lines": 1000}
    elif invalid == "module":
        del runtime["num_branches"]
        coverage_report["totals"] = summary()
    else:
        runtime["covered_branches"] = 1001
    result, badge = run_check(tmp_path, coverage_report)
    assert result.returncode == 1
    assert "Invalid coverage report:" in result.stdout
    assert not badge.exists()


def test_source_inventory_accepts_absolute_report_paths(tmp_path, coverage_report):
    coverage_report["files"] = {
        str(tmp_path / path): data for path, data in coverage_report["files"].items()
    }
    result, badge = run_check(tmp_path, coverage_report)
    assert result.returncode == 0, result.stdout + result.stderr
    assert badge.exists()


def test_missing_source_tree_fails_closed(tmp_path, coverage_report):
    for source in (tmp_path / PACKAGE).rglob("*.py"):
        source.unlink()
    result, badge = run_check(tmp_path, coverage_report)
    assert result.returncode == 1
    assert "No integration modules found" in result.stdout
    assert not badge.exists()
