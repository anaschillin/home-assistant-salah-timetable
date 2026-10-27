"""Build a reproducible manual-install archive without importing Home Assistant."""

import argparse
import ast
import hashlib
import json
import re
import tempfile
import tomllib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = Path("custom_components/salah_timetable")
REQUIRED_FILES = {
    "__init__.py",
    "manifest.json",
    "config_flow.py",
    "strings.json",
    "translations/en.json",
    "frontend.py",
    "frontend/salah-timetable-card.js",
    "frontend/card-styles.js",
    "frontend/card-utils.js",
    "frontend/card-i18n.js",
}
ASSET_SUFFIXES = {
    "frontend": {".js", ".css", ".svg", ".woff2"},
    "translations": {".json"},
    "brand": {".png", ".svg"},
}


def check_versions(root: Path) -> str:
    """Keep integration metadata and every bundled module cache version in sync."""
    source = root / INTEGRATION
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    version = manifest.get("version")
    if (
        manifest.get("domain") != "salah_timetable"
        or not isinstance(version, str)
        or not re.fullmatch(r"[0-9][0-9A-Za-z.+-]*", version)
    ):
        raise ValueError(
            "The manifest must declare salah_timetable and a valid version"
        )
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    if project["project"]["version"] != version:
        raise ValueError("pyproject.toml and manifest.json versions differ")
    frontend = ast.parse((source / "frontend.py").read_text(encoding="utf-8"))
    card_versions = [
        node.value.value
        for node in frontend.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "CARD_VERSION"
            for target in node.targets
        )
        and isinstance(node.value, ast.Constant)
    ]
    if card_versions != [version]:
        raise ValueError("frontend.py CARD_VERSION must equal the manifest version")
    card = (source / "frontend/salah-timetable-card.js").read_text(encoding="utf-8")
    imports = re.findall(r'from\s*["\']\./card-utils\.js\?v=([^"\']+)["\']', card)
    if imports != [version]:
        raise ValueError(
            "The card-utils.js import cache version must match the manifest"
        )
    style_imports = re.findall(
        r'from\s*["\']\./card-styles\.js\?v=([^"\']+)["\']', card
    )
    if style_imports != [version]:
        raise ValueError(
            "The card-styles.js import cache version must match the manifest"
        )
    for name in ("salah-timetable-card.js", "card-utils.js"):
        consumer = source / "frontend" / name
        if not consumer.is_file():
            continue  # release_files reports missing runtime assets separately.
        versions = re.findall(
            r"from\s*[\"']\./card-i18n\.js\?v=([^\"']+)[\"']",
            consumer.read_text(encoding="utf-8"),
        )
        if versions != [version]:
            raise ValueError(
                f"The card-i18n.js import cache version in {name} must match the manifest"
            )
    return version


def release_files(root: Path) -> list[tuple[str, Path]]:
    """Allow only runtime source/assets and the distribution's license."""
    source = root / INTEGRATION
    if not source.is_dir() or source.is_symlink():
        raise ValueError("The integration source must be a regular directory")
    files = []
    found = set()
    for path in source.rglob("*"):
        if path.is_symlink():
            raise ValueError("Release sources must not contain symlinks")
        relative = path.relative_to(source)
        if not path.is_file() or any(
            part.startswith(".")
            or part in {"__pycache__", "tests", "test", "fixtures", "node_modules"}
            for part in relative.parts
        ):
            continue
        if len(relative.parts) == 1:
            include = path.suffix == ".py" or relative.name in {
                "manifest.json",
                "strings.json",
            }
        else:
            include = path.suffix in ASSET_SUFFIXES.get(relative.parts[0], set())
        if include:
            found.add(relative.as_posix())
            files.append(((INTEGRATION / relative).as_posix(), path))
    if missing := REQUIRED_FILES - found:
        raise ValueError(f"Missing release files: {', '.join(sorted(missing))}")
    license_file = root / "LICENSE"
    if not license_file.is_file() or license_file.is_symlink():
        raise ValueError("A regular LICENSE file is required")
    files.append(("LICENSE", license_file))
    return sorted(files)


def build_release(root: Path, output_dir: Path) -> Path:
    """Normalize archive order, timestamps and modes across clean checkouts."""
    version = check_versions(root)
    files = release_files(root)
    output_dir.mkdir(parents=True, exist_ok=True)
    archive = output_dir / f"salah_timetable-{version}.zip"
    with tempfile.NamedTemporaryFile(dir=output_dir, delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with ZipFile(temporary_path, "w", ZIP_DEFLATED, compresslevel=9) as bundle:
            for name, path in files:
                info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = ZIP_DEFLATED
                bundle.writestr(info, path.read_bytes(), compresslevel=9)
        temporary_path.replace(archive)
    finally:
        temporary_path.unlink(missing_ok=True)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".zip.sha256").write_text(
        f"{digest}  {archive.name}\n", encoding="ascii"
    )
    return archive


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "dist")
    parser.add_argument(
        "--check", action="store_true", help="Validate without building"
    )
    args = parser.parse_args()
    try:
        if args.check:
            version = check_versions(args.root)
            files = release_files(args.root)
            print(f"Release {version}: {len(files)} validated files")
        else:
            archive = build_release(args.root, args.output_dir)
            print(archive)
            print(
                archive.with_suffix(".zip.sha256").read_text(encoding="ascii").strip()
            )
    except (OSError, ValueError, KeyError, SyntaxError) as err:
        parser.exit(1, f"Release build failed: {err}\n")


if __name__ == "__main__":
    main()
