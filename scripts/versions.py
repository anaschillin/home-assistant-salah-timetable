"""Read the repository's authoritative maintained versions without dependencies."""

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_versions(root: Path = ROOT) -> dict[str, str]:
    """Return validated values shared by generators, CI, docs and packaging."""
    config = tomllib.loads((root / "versions.toml").read_text(encoding="utf-8"))
    try:
        project = config["project"]
        dependencies = config["dependencies"]
        minimum = config["compatibility"]["minimum"]
        current = config["compatibility"]["supported_current"]
        values = {
            "version": project["version"],
            "python_min": project["python_min"],
            "node_major": project["node_major"],
            "pypdf": dependencies["pypdf"],
            "ruff": dependencies["ruff"],
            "uv": dependencies["uv"],
            "homeassistant_min": minimum["homeassistant"],
            "test_plugin_min": minimum["test_plugin"],
            "homeassistant_tested": current["homeassistant"],
            "test_plugin_tested": current["test_plugin"],
        }
    except (KeyError, TypeError) as error:
        raise ValueError(
            f"Missing version setting in versions.toml: {error}"
        ) from error
    for key, value in values.items():
        pattern = (
            r"[1-9][0-9]*"
            if key == "node_major"
            else r"\d+\.\d+\.\d+(?:[a-zA-Z0-9.+-]*)"
        )
        if not isinstance(value, str) or not re.fullmatch(pattern, value):
            raise ValueError(f"Invalid {key} in versions.toml: {value!r}")
    python = values["python_min"].split(".")
    if not all(part.isdigit() for part in python):
        raise ValueError("python_min must be a stable major.minor.patch version")
    values["python_minor"] = ".".join(python[:2])
    values["python_target"] = "py" + "".join(python[:2])
    values["python_next_minor"] = f"{python[0]}.{int(python[1]) + 1}"
    return values
