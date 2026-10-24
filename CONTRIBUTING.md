# Contributing

Use Python 3.14.2+ and `uv sync --frozen --group dev`. Run `uv run --frozen pytest`,
`uv run --frozen ruff check .` and `uv run --frozen ruff format --check .` before
opening a focused pull request. Tests must not require network access or a live HA
installation. Update the lockfile intentionally with dependency changes.
Run the full suite on Linux/POSIX: the isolated PDF worker uses process resource
limits that native Windows does not provide.

The locked `pytest-homeassistant-custom-component` package supplies Home Assistant
test fixtures. These tests and the HACS validation action do not establish an
authenticated HACS installation; that remains a separate live acceptance check.

Use Node.js 24 for frontend checks. Run `npm test` and `npm run test:browser`; there
are no npm dependencies and no install step. The browser harness requires Chromium
or Chrome. Set `CHROME_BIN` to its executable if it is not found on a standard path.
Set `REQUIRE_BROWSER_TESTS=1` to fail when no browser is available, as CI does; without
that setting the browser test is skipped when no executable is found. The harness
uses HA element stand-ins and does not replace a live HA/frontend installation check.

Run `uv run --frozen python scripts/build_release.py --check` to check runtime
assets and synchronized integration/frontend cache versions. See
[release preparation](docs/releasing.md) for archive builds and manual acceptance.

Keep data parsing and event calculation separate from HA lifecycle code. Preserve
original source values and missing data; never invent a prayer time to make an import
pass. Add sanitized, redistributable fixtures before claiming a PDF layout is
supported. Do not commit real Home Assistant storage, personal information or tokens.

See `docs/milestones.md` for scoped follow-up work. Bugs should include HA/integration
versions, timezone, expected behavior and redacted logs. Report security issues using
GitHub's private vulnerability reporting when available; do not post exploit details
or credentials publicly.
