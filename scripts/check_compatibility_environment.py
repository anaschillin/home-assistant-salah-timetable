"""Fail before compatibility tests if their selected runtime was not installed."""

import argparse
import json
import sys
from importlib.metadata import version
from pathlib import Path

if __package__:
    from .versions import load_versions
else:
    from versions import load_versions


def verify_environment(
    *,
    ha_version: str,
    plugin_version: str,
    environment: Path,
) -> dict[str, str]:
    """Check distribution metadata, imported HA code and the interpreter prefix."""
    from homeassistant.const import __version__ as imported_ha_version

    pins = load_versions()
    python_min = tuple(map(int, pins["python_min"].split(".")))
    python_minor = tuple(map(int, pins["python_minor"].split(".")))
    if sys.version_info[:3] < python_min or sys.version_info[:2] != python_minor:
        raise ValueError(
            f"Expected Python {pins['python_min']} or later in "
            f"{pins['python_minor']}, got {sys.version}"
        )
    actual_environment = Path(sys.prefix).resolve()
    if actual_environment != environment.resolve():
        raise ValueError(
            f"Expected isolated environment {environment.resolve()}, "
            f"got {actual_environment}"
        )
    installed_ha_version = version("homeassistant")
    if installed_ha_version != ha_version or imported_ha_version != ha_version:
        raise ValueError(
            f"Expected HA {ha_version}; distribution={installed_ha_version}, "
            f"imported={imported_ha_version}"
        )
    installed_plugin_version = version("pytest-homeassistant-custom-component")
    if installed_plugin_version != plugin_version:
        raise ValueError(
            f"Expected pytest-homeassistant-custom-component {plugin_version}, "
            f"got {installed_plugin_version}"
        )
    return {
        "homeassistant_distribution": installed_ha_version,
        "homeassistant_imported": imported_ha_version,
        "pytest_homeassistant_custom_component": installed_plugin_version,
        "python": ".".join(map(str, sys.version_info[:3])),
        "environment": str(actual_environment),
        "executable": sys.executable,
    }


def main() -> None:
    """Print evidence and optionally save it for the workflow artifact."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ha-version", required=True)
    parser.add_argument("--plugin-version", required=True)
    parser.add_argument("--environment", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    options = parser.parse_args()
    evidence = verify_environment(
        ha_version=options.ha_version,
        plugin_version=options.plugin_version,
        environment=options.environment,
    )
    rendered = json.dumps(evidence, indent=2) + "\n"
    if options.output:
        options.output.parent.mkdir(parents=True, exist_ok=True)
        options.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
