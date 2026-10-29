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
CI uses this flag. The runner verifies before/after dependency versions, but
public `results.json` records only boolean outcomes, including
`dependency.fresh_install_verified`, to avoid copying raw API or process data.

When a test environment uses a private outbound proxy CA, pass
`--ca-bundle /path/to/combined-ca-bundle.pem`. The bundle is mounted read-only and
selected with `SSL_CERT_FILE`/`PIP_CERT`; normal TLS verification stays enabled.
This opt-in trust setup is separate from preloading and supplies no package files.

## Readiness and reporting

Wait for HA `RUNNING` before configuration and shutdown. After restart, wait for
`RUNNING` and the specific mosque entry before checking timetable values. Terminal
setup/migration errors fail separately. Polling retries refused/reset connections,
transport timeouts and HTTP 502/503/504; authentication failures, incompatible APIs,
invalid JSON and assertions fail immediately. A fixed loopback host port preserves
the origin across restart. Browser startup uses bounded debugger discovery.

`results.json` contains fixed acceptance check names, boolean dependency,
restart and browser outcomes, the validated local source commit, and a generic
failure marker directing reviewers to the job log. It deliberately does not
persist raw HTTP responses, process output, image IDs, startup diagnostics,
or untrusted exception messages. Runtime diagnostics remain visible in the runner
logs, while screenshots can contain synthetic fixture values. Private
configuration files and authenticated-session logs are not exported. The
ten-minute run deadline and scoped cleanup remain mandatory. Docker creates/copies
can take several minutes in this environment.

The current runner supersedes an earlier unsuccessful attempt. Its restart timeout
was unresolved then; it is not proof of a storage bug.
Authenticated HACS installation remains outside this manual-install result.
Physical-device completion is recorded separately as user-confirmed acceptance. Fresh dependency installation is now explicitly verified
within the local 0.6.2 minimum-version run described above.

## UTC midnight stability

The disposable live-acceptance smoke creates synthetic annual records and confirms Ramadan for the current UTC day **and the following day**. Otherwise a real Home Assistant date rollover can deactivate a one-day Ramadan fixture while the card editor is being tested, making a valid preview falsely fail its visibility assertion. The December 31 boundary uses separate annual CSV imports for each year. The browser permits approved prayer timestamps to advance exactly one day while still checking Ramadan activation and the published prayer fields. See `scripts/live_dates.mjs` and `tests/frontend/live-dates.test.mjs`.
