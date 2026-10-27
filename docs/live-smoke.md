# Disposable Home Assistant live acceptance runner

The runner is used by the required **supported-current HA 2026.10.3** live job
in Validate and can also run manually. The reusable live workflow runs weekly as a
compatibility check. It creates a
disposable official HA container and synthetic timetable, runs authenticated APIs
and the real frontend, and removes its container and private configuration afterward.
No user configuration or credentials are checked into the repository.

Requirements: Docker, Node.js 24 and Chromium/Chrome. Example:

```sh
node scripts/live_smoke.mjs --ha-version 2026.10.3 --output-dir /tmp/salah-live-results
```

The optional `--preload-pypdf` supplies the exact manifest-pinned pure-Python
package and metadata from the repository's development venv. It is an explicit
workaround for the test environment's proxy CA, not proof that fresh dependency
installation works. TLS verification remains enabled.
The default omits this preload and lets HA resolve the manifest requirement.
`--require-fresh-dependency` verifies that both pypdf metadata and import are absent
in the base image and match the manifest pin after the mosque has loaded. It fails
rather than treating a pre-existing/preloaded package as fresh-install evidence.
CI uses this flag. Reports record before/after versions and
`dependency.fresh_install_verified`.

When a test environment uses a private outbound proxy CA, pass
`--ca-bundle /path/to/combined-ca-bundle.pem`. The bundle is mounted read-only and
selected with `SSL_CERT_FILE`/`PIP_CERT`; normal TLS verification stays enabled.
This opt-in trust setup is separate from preloading and supplies no package files.

## Observed acceptance — 24 October 2026

An earlier local 0.6.1 candidate passed 19 checks against HA 2026.10.0, with explicit
locked-dependency preloading. Approved and pending imports, Ramadan options,
entity IDs and resource registration survived restart. The actual card picker,
keyboard title/focus, themes and phone/tablet viewports passed. Every display
control was exercised; saved settings survived page reload, changed the rendered
card, and preserved prayer data and Ramadan activation. See
[validation](validation.md#peer-review-follow-up--candidate-061).
The subsequent hosted live run
[40131759984](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40131759984)
passed HA 2026.10.0 and 2026.10.3, including per-toggle visible preview checks, on
source tree `27aa4b9348bed4160550106c37919fe86f9c3bb3` (the same tree as main
`c9b42f3`). It did not preload pypdf, but did not yet record before/after package
provenance. The local 0.6.2 candidate then passed 20 checks on HA 2026.10.0 with strict fresh
installation: metadata/import were absent in the base image and both matched
`6.21.1` after setup. No package was preloaded. A combined CA bundle was mounted
read-only for this environment's proxy, with TLS verification enabled. The new
required hosted matrix still needs its own run for the final candidate commit.

## Readiness and reporting

Wait for HA `RUNNING` before configuration and shutdown. After restart, wait for
`RUNNING` and the specific mosque entry before checking timetable values. Terminal
setup/migration errors fail separately. Polling retries refused/reset connections,
transport timeouts and HTTP 502/503/504; authentication failures, incompatible APIs,
invalid JSON and assertions fail immediately. A fixed loopback host port preserves
the origin across restart. Browser startup uses bounded debugger discovery.

Reports contain acceptance flags, source/version/image identity and failure
messages. Restart Fajr diagnostics expose only presence, availability and match
flags. Screenshots and failed assertions can contain synthetic fixture values;
private configuration files and authenticated-session logs are not exported. The
ten-minute run deadline and scoped cleanup remain mandatory. Docker creates/copies
can take several minutes in this environment.

The current runner supersedes an earlier unsuccessful attempt. Its restart timeout
was unresolved then; it is not proof of a storage bug.
Authenticated HACS installation remains outside this manual-install result.
Physical-device completion is recorded separately as user-confirmed acceptance. Fresh dependency installation is now explicitly verified
within the local 0.6.2 minimum-version run described above.
