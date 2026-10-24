# Opt-in live Home Assistant acceptance runner

The runner is manual-only; it is not a required hosted CI job. It creates a
disposable official HA container and synthetic timetable, runs authenticated APIs
and the real frontend, and removes its container and private configuration afterward.
No user configuration or credentials are checked into the repository.

Requirements: Docker, Node.js 24 and Chromium/Chrome. Example:

```sh
node scripts/live_smoke.mjs --ha-version 2026.10.0 --output-dir /tmp/salah-live-results
```

The optional `--preload-pypdf` supplies the exact manifest-pinned pure-Python
package and metadata from the repository's development venv. It is an explicit
workaround for the test environment's proxy CA, not proof that fresh dependency
installation works. TLS verification remains enabled.

## Observed acceptance — 24 October 2026

The local 0.6.1 candidate passed 19 checks against HA 2026.10.0, with explicit
locked-dependency preloading. Approved and pending imports, Ramadan options,
entity IDs and resource registration survived restart. The actual card picker,
keyboard title/focus, themes and phone/tablet viewports passed. Every display
control was exercised; saved settings survived page reload, changed the rendered
card, and preserved prayer data and Ramadan activation. See
[validation](../docs/validation.md#peer-review-follow-up--candidate-061).

## Readiness and reporting

Wait for HA `RUNNING` before configuration and shutdown. After restart, wait for
`RUNNING` and the specific mosque entry before checking timetable values. Terminal
setup/migration errors fail separately. Polling retries refused/reset connections,
transport timeouts and HTTP 502/503/504; authentication failures, incompatible APIs,
invalid JSON and assertions fail immediately. A fixed loopback host port preserves
the origin across restart. Browser startup uses bounded debugger discovery.

Reports contain acceptance flags and version/image identity, never tokens, private
configuration or imported values. Restart Fajr diagnostics expose only presence,
availability and match flags. Screenshots contain synthetic data. The ten-minute
run deadline and scoped cleanup remain mandatory. Docker creates/copies can take
several minutes in this environment.

The current runner supersedes an earlier unsuccessful attempt. Its restart timeout
was unresolved then; it is not proof of a storage bug.
Authenticated HACS installation, physical-device checks and fresh dependency
installation remain outside this manual-install result.
