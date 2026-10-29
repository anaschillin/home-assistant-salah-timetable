"""Check that the Markdown-only CI optimisation never hides code edits."""

import subprocess

import pytest

from scripts.ci_changed_files import changed_paths, is_markdown_only


@pytest.mark.parametrize(
    ("paths", "expected"),
    [
        ([], False),
        (["README.md"], True),
        (["docs/_excerpts/install.md", "research/example.md"], True),
        (["tests/tooling/README.md"], True),
        (["README.md", "custom_components/salah_timetable/__init__.py"], False),
        (["docs/asset-provenance.json"], False),
        ([".github/workflows/validate.yml"], False),
        (["scripts/ci_changed_files.py"], False),
    ],
)
def test_markdown_only_classification(paths, expected):
    assert is_markdown_only(paths) is expected


def test_code_to_markdown_rename_is_not_docs_only(tmp_path):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True).strip()

    git("init", "-q")
    git("config", "user.email", "tests@example.invalid")
    git("config", "user.name", "CI Tests")
    (tmp_path / "module.py").write_text("print('hello')\n")
    git("add", "module.py")
    git("commit", "-qm", "code")
    base = git("rev-parse", "HEAD")
    git("mv", "module.py", "guide.md")
    git("commit", "-qam", "rename")
    paths = changed_paths(base, git("rev-parse", "HEAD"), cwd=tmp_path)
    assert paths == ["guide.md", "module.py"]
    assert not is_markdown_only(paths)
