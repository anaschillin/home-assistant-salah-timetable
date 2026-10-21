# Contributing

Use Python 3.14.2+ and `uv sync --frozen --group dev`. Run `uv run --frozen pytest`,
`uv run --frozen ruff check .` and `uv run --frozen ruff format --check .` before
opening a focused pull request. Tests must not require network access or a live HA
installation. Update the lockfile intentionally with dependency changes.

Keep data parsing and event calculation separate from HA lifecycle code. Preserve
original source values and missing data; never invent a prayer time to make an import
pass. Add sanitized, redistributable fixtures before claiming a PDF layout is
supported. Do not commit real Home Assistant storage, personal information or tokens.

See `docs/milestones.md` for scoped follow-up work. Bugs should include HA/integration
versions, timezone, expected behavior and redacted logs. Report security issues using
GitHub's private vulnerability reporting when available; do not post exploit details
or credentials publicly.
