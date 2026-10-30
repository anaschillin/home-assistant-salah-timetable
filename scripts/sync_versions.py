"""Generate required metadata, frontend cache keys, CI pins and docs from versions.toml."""

import argparse
import json
import re
from pathlib import Path

if __package__:
    from .versions import ROOT, load_versions
else:
    from versions import ROOT, load_versions


def _replace(source: str, pattern: str, replacement: str, name: str) -> str:
    result, count = re.subn(pattern, replacement, source, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"Expected one {name} version field, found {count}")
    return result


def synchronise(root: Path = ROOT, write: bool = False) -> list[str]:
    """Check all generated copies; write only after every input validates."""
    values = load_versions(root)
    outputs: dict[Path, str] = {}

    def read(name: str) -> str:
        return (root / name).read_text(encoding="utf-8")

    def json_output(name: str, **updates) -> None:
        data = json.loads(read(name))
        data.update(updates)
        outputs[Path(name)] = json.dumps(data, indent=2) + "\n"

    manifest = "custom_components/salah_timetable/manifest.json"
    requirements = json.loads(read(manifest))["requirements"]
    if sum(item.startswith("pypdf==") for item in requirements) != 1:
        raise ValueError("Expected one manifest pypdf requirement")
    json_output(
        manifest,
        version=values["version"],
        requirements=[
            f"pypdf=={values['pypdf']}" if item.startswith("pypdf==") else item
            for item in requirements
        ],
    )
    json_output("hacs.json", homeassistant=values["homeassistant_min"])
    for lane in (None, "minimum", "supported-current"):
        name = (
            "pyproject.toml" if lane is None else f"compatibility/{lane}/pyproject.toml"
        )
        source = read(name)
        if lane is None:
            source = _replace(
                source, r'^version = "[^"]+"$', f'version = "{values["version"]}"', name
            )
            requirement = f">={values['python_min']}"
        else:
            requirement = f">={values['python_min']},<{values['python_next_minor']}"
        source = _replace(
            source,
            r'^requires-python = "[^"]+"$',
            f'requires-python = "{requirement}"',
            name,
        )
        suffix = "min" if lane == "minimum" else "tested"
        for package, version in (
            ("pypdf", values["pypdf"]),
            ("pytest-homeassistant-custom-component", values[f"test_plugin_{suffix}"]),
        ):
            source = _replace(
                source,
                rf'"{package}==[^\"]+"',
                f'"{package}=={version}"',
                name + " " + package,
            )
        if lane is None:
            source = _replace(
                source, r'"ruff==[^\"]+"', f'"ruff=={values["ruff"]}"', name + " ruff"
            )
            source = _replace(
                source,
                r'^target-version = "[^"]+"$',
                f'target-version = "{values["python_target"]}"',
                name + " Ruff target",
            )
        else:
            source = _replace(
                source,
                r'"homeassistant==[^\"]+"',
                f'"homeassistant=={values[f"homeassistant_{suffix}"]}"',
                name + " HA",
            )
        outputs[Path(name)] = source

    frontend = "custom_components/salah_timetable/frontend.py"
    outputs[Path(frontend)] = _replace(
        read(frontend),
        r'^CARD_VERSION = "[^"]+"$',
        f'CARD_VERSION = "{values["version"]}"',
        frontend,
    )
    # Discover consumers so a new local helper cannot miss version synchronization.
    for path in sorted(
        (root / "custom_components/salah_timetable/frontend").glob("*.js")
    ):
        source = path.read_text(encoding="utf-8")

        def version_import(found: re.Match[str]) -> str:
            # Keep unrelated query options while giving every local module a
            # cache key, including imports newly added without one.
            options = [
                item
                for item in (found[2] or "").split("&")
                if item and not item.startswith("v=")
            ]
            query = "&".join(["v=" + values["version"], *options])
            return found[1] + "?" + query + found[3]

        source = re.sub(
            r'((?:from\s*|import\s*)["\']\./[^"\']+\.js)(?:\?([^"\']*))?(["\'])',
            version_import,
            source,
        )
        outputs[path.relative_to(root)] = source

    hook = ".pre-commit-config.yaml"
    outputs[Path(hook)] = _replace(
        read(hook),
        r"(repo: https://github\.com/astral-sh/ruff-pre-commit\n[ \t]+rev: )v[^\n]+",
        rf"\g<1>v{values['ruff']}",
        hook,
    )
    for path in sorted((root / ".github/workflows").glob("*.yml")):
        source = path.read_text(encoding="utf-8")
        for setting, key in (
            ("python-version", "python_minor"),
            ("node-version", "node_major"),
        ):
            source = re.sub(
                rf"({setting}: )['\"][^'\"]+['\"]",
                lambda found: found[1] + f"'{values[key]}'",
                source,
            )
        source = re.sub(
            r"(uses: astral-sh/setup-uv@[^\n]+\n\s+with:\n\s+version: )['\"][^'\"]+['\"]",
            lambda found: found[1] + f"'{values['uv']}'",
            source,
        )
        source = re.sub(
            r"--python python\d+\.\d+",
            "--python python" + values["python_minor"],
            source,
        )
        outputs[path.relative_to(root)] = source

    if __package__:
        from .sync_documentation import synchronise as sync_docs
    else:
        from sync_documentation import synchronise as sync_docs

    # Validate documentation before writing any generated metadata.
    doc_changes = sync_docs(root)
    changed = [
        path.as_posix()
        for path, content in outputs.items()
        if (root / path).read_text(encoding="utf-8") != content
    ]
    if write:
        for name in changed:
            (root / name).write_text(outputs[Path(name)], encoding="utf-8")
        sync_docs(root, write=True)
    return sorted(changed + doc_changes)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--write", action="store_true", help="Update all generated version copies"
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="Fail on stale generated versions (default)",
    )
    args = parser.parse_args()
    try:
        changed = synchronise(write=args.write)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Version synchronization failed: {error}\n")
    if changed:
        print(
            ("Updated" if args.write else "Out-of-sync")
            + " versions: "
            + ", ".join(changed)
        )
    if changed and not args.write:
        print("Run: python scripts/sync_versions.py --write")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
