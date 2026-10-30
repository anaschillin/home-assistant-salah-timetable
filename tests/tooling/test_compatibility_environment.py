"""Compatibility lanes must fail before tests can run against the wrong HA."""

import sys
from pathlib import Path

import pytest

from scripts import check_compatibility_environment as checker


@pytest.fixture
def matching_environment(monkeypatch):
    """Keep these guard tests independent of the lane running the test suite."""
    from homeassistant import const

    monkeypatch.setattr(const, "__version__", "2026.10.0")
    versions = {
        "homeassistant": "2026.10.0",
        "pytest-homeassistant-custom-component": "0.13.371",
    }
    monkeypatch.setattr(checker, "version", versions.__getitem__)
    return versions


def verify():
    return checker.verify_environment(
        ha_version="2026.10.0",
        plugin_version="0.13.371",
        environment=Path(sys.prefix),
    )


def test_matching_lane_reports_both_distribution_and_imported_versions(
    matching_environment,
):
    evidence = verify()
    assert evidence["homeassistant_distribution"] == "2026.10.0"
    assert evidence["homeassistant_imported"] == "2026.10.0"
    assert evidence["pytest_homeassistant_custom_component"] == "0.13.371"
    assert evidence["environment"] == str(Path(sys.prefix).resolve())
    assert evidence["executable"] == sys.executable
    assert evidence["python"] == ".".join(map(str, sys.version_info[:3]))


@pytest.mark.parametrize("mismatch", ["distribution", "import", "plugin"])
def test_a_lane_rejects_a_different_ha_or_plugin(
    matching_environment, monkeypatch, mismatch
):
    if mismatch == "distribution":
        matching_environment["homeassistant"] = "2026.10.3"
    elif mismatch == "import":
        from homeassistant import const

        monkeypatch.setattr(const, "__version__", "2026.10.3")
    else:
        matching_environment["pytest-homeassistant-custom-component"] = "0.13.374"
    with pytest.raises(ValueError, match="Expected"):
        verify()


def test_a_lane_rejects_the_root_or_another_environment(matching_environment, tmp_path):
    with pytest.raises(ValueError, match="Expected isolated environment"):
        checker.verify_environment(
            ha_version="2026.10.0",
            plugin_version="0.13.371",
            environment=tmp_path / "separate-compatibility-environment",
        )


@pytest.mark.parametrize("python_version", [(3, 14, 1), (3, 13, 9), (3, 15, 0)])
def test_a_lane_rejects_an_unsupported_interpreter(
    matching_environment, monkeypatch, python_version
):
    with monkeypatch.context() as patch:
        patch.setattr(sys, "version_info", python_version)
        with pytest.raises(ValueError, match="Expected Python"):
            verify()


@pytest.mark.parametrize(
    ("python_version", "accepted"),
    [((3, 13, 7), False), ((3, 13, 8), True), ((3, 14, 0), False)],
    ids=["below-configured-minimum", "configured-series", "different-series"],
)
def test_interpreter_guard_follows_central_python_policy(
    matching_environment, monkeypatch, python_version, accepted
):
    """Changing central Python policy changes both minimum and series checks."""
    monkeypatch.setattr(
        checker,
        "load_versions",
        lambda: {"python_min": "3.13.8", "python_minor": "3.13"},
    )
    with monkeypatch.context() as patch:
        patch.setattr(sys, "version_info", python_version)
        if accepted:
            assert verify()["python"] == "3.13.8"
        else:
            with pytest.raises(
                ValueError, match=r"Expected Python 3\.13\.8 or later in 3\.13"
            ):
                verify()
