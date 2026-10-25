"""Restore a real Home Assistant archive only into a disposable Docker config.

Never point this tool at a production configuration. The original and archive
are read-only; temporary restored data is automatically removed on exit.
"""

import argparse
import json
import os
import re
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

IMAGE = "ghcr.io/home-assistant/home-assistant:{}"


def run(*args: str) -> str:
    """Run Docker without a shell or secrets in command-line arguments."""
    result = subprocess.run(
        ("docker", *args),
        check=True,
        capture_output=True,
        text=True,
        timeout=240,
    )
    return result.stdout.strip()


@contextmanager
def restored_directory(image: str):
    """Remove root-owned files with Docker before Python removes the test root."""
    with tempfile.TemporaryDirectory(prefix="salah-disposable-restore-") as temp:
        try:
            yield Path(temp)
        finally:
            run(
                "run",
                "--rm",
                "--entrypoint",
                "python",
                "--mount",
                f"type=bind,src={temp},dst=/cleanup",
                image,
                "-c",
                "from pathlib import Path; import shutil; "
                "p=Path('/cleanup'); "
                "[(shutil.rmtree(c) if c.is_dir() and not c.is_symlink() "
                "else c.unlink()) for c in p.iterdir()]",
            )


def compare_with_container(image: str, original: Path, config: Path) -> dict:
    """Compare both read-only snapshots as root without exporting source secrets."""
    project = Path(__file__).resolve().parents[1]
    output = run(
        "run",
        "--rm",
        "--entrypoint",
        "python",
        "--mount",
        f"type=bind,src={original},dst=/before,readonly",
        "--mount",
        f"type=bind,src={config},dst=/after,readonly",
        "--mount",
        f"type=bind,src={project / 'scripts'},dst=/audit,readonly",
        image,
        "-c",
        "import importlib.util,json; "
        "spec=importlib.util.spec_from_file_location('audit','/audit/verify_backup_restore.py'); "
        "m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); "
        "from pathlib import Path; "
        "print(json.dumps(m.compare(Path('/before'),Path('/after'))))",
    )
    return json.loads(output)


def restore(backup: Path, original: Path, version: str, *, serve: bool) -> dict:
    """Use Home Assistant's *own* backup_restore module in a fresh container."""
    if not re.fullmatch(r"20[0-9]{2}\.[0-9]{1,2}\.[0-9]{1,2}", version):
        raise ValueError("Pin an exact Home Assistant Core version")
    backup = backup.resolve(strict=True)
    original = original.resolve(strict=True)
    if not backup.is_file() or not original.is_dir() or backup.suffix != ".tar":
        raise ValueError("Expected a real backup .tar and disposable HA config")
    image = IMAGE.format(version)
    # Never copy an archive or original config into the repository or CI artifact.
    with restored_directory(image) as path:
        config = path / "config"
        config.mkdir(mode=0o700)
        password = os.environ.get("SALAH_TEST_BACKUP_PASSWORD") or None
        instruction = {
            "path": "/restore/input.tar",
            "password": password,
            "remove_after_restore": False,
            "restore_database": True,
            "restore_homeassistant": True,
        }
        (config / ".HA_RESTORE").write_text(json.dumps(instruction))
        # The image's official restore implementation performs archive validation,
        # safe extraction and correct .storage restoration, including hidden files.
        run(
            "run",
            "--rm",
            "--entrypoint",
            "python",
            "--mount",
            f"type=bind,src={config},dst=/config",
            "--mount",
            f"type=bind,src={backup},dst=/restore/input.tar,readonly",
            image,
            "-I",
            "-c",
            "from homeassistant.backup_restore import restore_backup; "
            "assert restore_backup('/config')",
        )
        result = json.loads((config / ".HA_RESTORE_RESULT").read_text())
        if result.get("success") is not True:
            raise ValueError("Home Assistant reported a restore failure")
        counts = compare_with_container(image, original, config)
        if not serve:
            return counts
        name = f"salah-restored-{uuid4().hex[:10]}"
        try:
            run(
                "create",
                "--name",
                name,
                "--publish",
                "127.0.0.1::8123",
                "--mount",
                f"type=bind,src={config},dst=/config",
                image,
            )
            run("start", name)
            port = run("port", name, "8123/tcp")
            print(f"Disposable restored Home Assistant: http://{port}")
            print("Inspect with the test credentials from the original disposable")
            print("instance. Press Enter to stop and delete this test instance.")
            input()
        finally:
            subprocess.run(
                ("docker", "rm", "--force", name),
                check=False,
                capture_output=True,
                timeout=60,
            )
        return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--ha-version", required=True)
    parser.add_argument(
        "--confirm-disposable",
        action="store_true",
        help="Explicitly confirm the source is a disposable test instance",
    )
    parser.add_argument(
        "--serve", action="store_true", help="Boot a second disposable HA instance"
    )
    args = parser.parse_args()
    if not args.confirm_disposable:
        parser.error("Refusing restore without --confirm-disposable")
    try:
        result = restore(args.backup, args.original, args.ha_version, serve=args.serve)
    except (ValueError, OSError, subprocess.SubprocessError) as err:
        parser.exit(1, f"Disposable restore failed: {err}\n")
    print("Verified restored config safely:", json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
