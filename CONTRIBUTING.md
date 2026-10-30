# Contributing

Use Python <!-- docs:python_min -->3.14.2<!-- /docs:python_min -->+, Node.js <!-- docs:node_major -->24<!-- /docs:node_major -->, uv <!-- docs:uv -->0.13.6<!-- /docs:uv --> and the locked project environment. Run these standard checks before opening a focused pull request:

<!-- docs:excerpt development-checks -->
```sh
uv sync --frozen --group dev
uv run --frozen pytest
uv run --frozen ruff check .
uv run --frozen ruff format --check .
npm test
REQUIRE_BROWSER_TESTS=1 npm run test:browser
```
<!-- /docs:excerpt development-checks -->

The locked Python and Node unit suites must not
require external network access or a separate live HA installation after dependencies
are installed. Update the lockfile intentionally with dependency changes.
Run the full suite on Linux/POSIX or WSL: the isolated PDF worker uses process resource
limits that native Windows does not provide. Use a Linux-filesystem virtual environment
when testing a Windows checkout through WSL; set `UV_PROJECT_ENVIRONMENT` to its absolute
path for `uv sync` and `uv run` to avoid slow imports from a mounted Windows drive.
Always run `uv sync --frozen --group dev` after pulling dependency updates; an existing
virtual environment may still contain older packages even when the checkout is current.

The locked `pytest-homeassistant-custom-component` package supplies Home Assistant
test fixtures. The complete test-file inventory, ownership rules, fixtures and per-area commands are in [the testing guide](docs/testing.md). Keep new Python tests in the matching `tests/<area>/` folder, share reusable fixtures through `tests/conftest.py`, and do not use hard-coded file-relative paths that break when tests move.

The frontend tests have no npm dependencies and no install step. The browser harness requires Chromium
or Chrome. Set `CHROME_BIN` to its executable if it is not found on a standard path.
Set `REQUIRE_BROWSER_TESTS=1` to fail when no browser is available, as CI does; without
that setting the browser test is skipped when no executable is found. The harness
uses HA element stand-ins and does not replace a live HA/frontend installation check.

Validate also runs full pinned Python compatibility suites on HA <!-- docs:homeassistant_min -->2026.10.0<!-- /docs:homeassistant_min -->
and <!-- docs:homeassistant_tested -->2026.10.4<!-- /docs:homeassistant_tested -->, plus one real Docker-based live acceptance on HA <!-- docs:homeassistant_tested -->2026.10.4<!-- /docs:homeassistant_tested -->.
The live job needs network access for official images and HA-managed dependencies,
and real Chromium/Chrome for the frontend. The reusable workflow supports manual
runs and weekly checks. To run the live acceptance locally:

```sh
source <(python3 scripts/sync_documentation.py --shell)
node scripts/live_smoke.mjs --ha-version "$HA_TESTED_VERSION" --require-fresh-dependency --output-dir /tmp/salah-live-results
```

Strict dependency proof checks absence in the base image and the manifest-pinned
metadata/import after setup. Do not combine it with `--preload-pypdf`. If the test
network uses a private proxy CA, use `--ca-bundle` with a trusted combined bundle;
keep TLS verification enabled. See [runner details](docs/testing.md#disposable-home-assistant-live-testing).
The runner uses synthetic data and removes its private configuration/containers.

Run `uv run --frozen python scripts/build_release.py --check` to check runtime
assets and synchronized integration/frontend cache versions. See
[release preparation](docs/releasing.md) for archive builds and manual acceptance.

<!-- docs:excerpt validation-boundaries -->
HACS repository validation does not prove installation through the authenticated HACS UI. Chromium tests use Home Assistant element stand-ins, and disposable Home Assistant Container checks do not establish physical-device behaviour or full Home Assistant OS/Supervisor restoration. Assess the **exact candidate version** through the manual [release acceptance checklist](docs/releasing.md#manual-hacs-and-home-assistant-acceptance).
<!-- /docs:excerpt validation-boundaries -->

Keep data parsing and event calculation separate from HA lifecycle code. Preserve
original source values and missing data; never invent a prayer time to make an import
pass. Add sanitized, redistributable fixtures before claiming a PDF layout is
supported. Do not commit real Home Assistant storage, personal information or tokens.

See `docs/roadmap.md` for scoped follow-up work. Bugs should include HA/integration
versions, timezone, expected behavior and redacted logs. Report security issues using
GitHub's private vulnerability reporting when available; do not post exploit details
or credentials publicly.

## Documentation numbering and structure

Use these Markdown conventions throughout the README, `docs/`, `examples/` and test guides:

- Use one unnumbered `#` title per document, then unnumbered `##` sections and `###` subsections. Do not manually prefix headings with section or milestone numbers.
- Use ordered Markdown lists (`1.`, `2.`, `3.`) only when order matters, such as installation, verification or recovery procedures. Start each independent procedure at `1.` and keep numbering sequential.
- Use `-` bullet lists for non-sequential features, rules, alternatives, test cases and future plans. Do not number an unordered list merely for presentation.
- Preserve meaningful identifiers: semantic versions in `CHANGELOG.md`, Home Assistant versions, dates, parser IDs and technical constants are **not** document numbering.
- Keep [the roadmap](docs/roadmap.md) free of completed milestone IDs, and do not add old PR numbers or dated acceptance diaries to active documentation. Git history and Actions retain that evidence.
- Use descriptive headings so internal Markdown anchors remain stable; verify links when moving or renaming sections.

## Keeping documentation variables current

[`versions.toml`](versions.toml) is the single source for the integration release,
minimum Python version, Node.js major version, uv, pypdf, Ruff and the minimum/current
Home Assistant and test-plugin pairs. To change a supported version, edit that file
and run one command from the repository root:

```sh
python scripts/sync_versions.py --write
```

The synchronizer mirrors those values into the metadata required by Home Assistant,
HACS, Python tooling, frontend cache/import URLs, CI and the rendered documentation.
These copies remain checked in so each consumer can read its required format; do
not maintain their version fields manually. The synchronizer uses the Python
standard library and does not install packages or resolve dependencies.

Lockfiles remain uv-generated dependency resolutions. After changing the release
version or root dependency pins, regenerate the root lock with `uv lock`. If a
compatibility lane's dependency pins changed, regenerate its lock with
`uv lock --project compatibility/minimum` or
`uv lock --project compatibility/supported-current`, as applicable. A shared pypdf
pin change affects all three locks. Commit `versions.toml`, its generated copies
and affected locks together, then install and test with `uv sync --frozen --group dev`.

Dependabot may propose changes directly to generated project metadata and locks.
Move reviewed direct dependency updates into `versions.toml`, synchronize, then
regenerate the affected locks. Preserve Home Assistant's exact dependency and
test-plugin constraints; see the [upstream advisory policy](SECURITY.md#dependency-advisories).

Before opening a pull request, check for drift:

```sh
python scripts/sync_versions.py --check
```

CI runs the same check and rejects generated values that disagree with
`versions.toml`. Keep historical version headings and release notes in `CHANGELOG.md`
as written; they record past releases and are not generated current-version fields.

GitHub Markdown does not support native cross-file includes. Canonical excerpts in
`docs/_excerpts/` are materialised inside `docs:excerpt NAME` blocks so GitHub renders
complete prose and commands. Edit the excerpt source, never its generated copies.
Visible values inside `<!-- docs:... -->` markers also come from `versions.toml`.
Run the same `--write` command after changing excerpts or guide links. The
documentation helper retains canonical guide redirects and shell/matrix exports:

```bash
source <(python3 scripts/sync_documentation.py --shell)
echo "$INTEGRATION_VERSION $HA_MIN_VERSION $HA_TESTED_VERSION"
```

The compatibility CI matrix, live-smoke workflow and executable examples read these
central values instead of maintaining separate version literals.
