# Live smoke runner — work in progress

This is an experimental opt-in Docker/Chromium acceptance runner.
Its readiness helpers have automated coverage; the full runner has not passed live acceptance. No credentials, private HA
configuration or source timetables are included.

Requirements: Docker, Node.js 24 and Chromium/Chrome. Example:

```sh
node scripts/live_smoke.mjs --ha-version 2026.10.0 --output-dir /tmp/salah-live-results
```

The optional `--preload-pypdf` supplies the exact manifest-pinned pure-Python
package/metadata from the repository's development venv to the disposable image.
It is an explicit workaround for this test environment's proxy CA, not proof that
fresh dependency installation works. TLS verification remains enabled.

Latest observations:

- HA 2026.10.0 starts, onboarding/configuration/import/approval work, 25 sensors
  appear, Ramadan defaults work, and removing a second mosque preserves the first.
- Docker's automatic published port changed on restart. The runner now allocates
  a host loopback port and publishes it explicitly, preserving the origin.
- The next run still failed to confirm approved Fajr after restart. Investigate HA
  startup readiness, persisted config-entry state and reload/setup errors. Wait
  for HA RUNNING before testing shutdown; do not infer a storage defect from the
  runner's current generic timeout alone.
- The full real picker/theme/keyboard driver is implemented but has not been
  reached by this runner. Previous main-branch HA 2026.10.2 card/editor smoke is
  recorded separately in docs/validation.md.
- Docker uses costly image copies in this environment; creating/cleaning a single
  HA container can take over a minute. Keep one large test image at a time and
  retain enough free disk space. Cleanup is scoped to the generated container and
  temporary directory. Completed runs remove private configuration/tokens.

Next: improve sanitized failure diagnostics and startup/readiness checks, finish
minimum-version restart plus real picker acceptance, then review cleanup/cancel
paths before adding a manual-only CI workflow. Rebase on current main first.

## Readiness hardening — 24 October 2026

The runner now waits for `/api/config` to report `RUNNING` before configuring
mosques and before restarting. After restart it waits for `RUNNING` and the
specific mosque entry to load before asserting Fajr. Terminal setup/migration
errors are reported separately from missing or mismatched timetable state. The
JSON result records only presence, availability and match flags for restart Fajr,
without exporting prayer values or configuration. Browser startup uses the same
bounded debugger discovery as the existing Chromium harness.

Docker socket access is blocked in the current workspace sandbox, so these changes
have not resolved or reproduced the original live restart failure. No minimum-version
acceptance is claimed. Run the command above in an environment with Docker access.
