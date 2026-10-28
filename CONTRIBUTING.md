# Contributing

Use Python 3.14.2+ and `uv sync --frozen --group dev`. Run `uv run --frozen pytest`,
`uv run --frozen ruff check .` and `uv run --frozen ruff format --check .` before
opening a focused pull request. The locked Python and Node unit suites must not
require external network access or a separate live HA installation after dependencies
are installed. Update the lockfile intentionally with dependency changes.
Run the full suite on Linux/POSIX: the isolated PDF worker uses process resource
limits that native Windows does not provide.

The locked `pytest-homeassistant-custom-component` package supplies Home Assistant
test fixtures. These tests and the HACS validation action do not establish an
authenticated HACS installation; that remains a separate live acceptance check.

The complete test-file inventory, ownership rules, fixtures and per-area commands are in [the testing guide](docs/testing.md). Keep new Python tests in the matching `tests/<area>/` folder, share reusable fixtures through `tests/conftest.py`, and do not use hard-coded file-relative paths that break when tests move.

Use Node.js 24 for frontend checks. Run `npm test` and `npm run test:browser`; there
are no npm dependencies and no install step. The browser harness requires Chromium
or Chrome. Set `CHROME_BIN` to its executable if it is not found on a standard path.
Set `REQUIRE_BROWSER_TESTS=1` to fail when no browser is available, as CI does; without
that setting the browser test is skipped when no executable is found. The harness
uses HA element stand-ins and does not replace a live HA/frontend installation check.

Validate also runs full pinned Python compatibility suites on HA 2026.10.0
and 2026.10.3, plus one real Docker-based live acceptance on HA 2026.10.3.
The live job needs network access for official images and HA-managed dependencies,
and real Chromium/Chrome for the frontend. The reusable workflow supports manual
runs and weekly checks. To run the live acceptance locally:

```sh
node scripts/live_smoke.mjs --ha-version 2026.10.3 --require-fresh-dependency --output-dir /tmp/salah-live-results
```

Strict dependency proof checks absence in the base image and the manifest-pinned
metadata/import after setup. Do not combine it with `--preload-pypdf`. If the test
network uses a private proxy CA, use `--ca-bundle` with a trusted combined bundle;
keep TLS verification enabled. See [runner details](docs/live-smoke.md).
The runner uses synthetic data and removes its private configuration/containers.
It does not establish authenticated HACS installation or full-backup acceptance.

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
