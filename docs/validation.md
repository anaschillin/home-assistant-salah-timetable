# Validation record — 23 October 2026

Source tested: `9c613caae88fe66e86a09f44ee86f8749241afdb` (integration 0.5.1).
This records observed results, not certification of every supported installation.

## Automated checks

- `uv run --frozen pytest`: **551 passed**, 94% aggregate integration line coverage.
  PDF worker behavior is tested through its subprocess; the isolated worker does
  not inherit coverage instrumentation.
- `npm test`: **31 passed**.
- `REQUIRE_BROWSER_TESTS=1 npm run test:browser`: passed native Chromium checks
  at 360px and 900px, with 20 assertions per viewport. These fixtures use stand-in
  Home Assistant controls, separately from the live runtime check below.
- Ruff lint and formatting checks passed.
- The official hassfest container reported one integration and zero invalid
  integrations, including manifest, dependencies and translations.
- Release consistency checks and archive construction passed. Packaging tests
  verify required assets, private-file exclusion, version consistency, checksums
  and reproducibility across source timestamps/permissions.

## Disposable Home Assistant runtime

The official `ghcr.io/home-assistant/home-assistant:2026.10.2` image ran with a
fresh temporary configuration and loopback-only HTTP access. The integration was
mounted as a manual installation; this was not a HACS installation.

Observed through real authenticated Home Assistant APIs:

- Initial onboarding and mosque Config Flow completed.
- A synthetic CSV for the current date and tomorrow passed authenticated upload,
  graphical-mapping flow, persisted preview and explicit approval.
- All 25 mosque sensors were registered with actual Home Assistant states.
- The bundled card resource was registered automatically.
- Reload retained approved values and avoided duplicate resource registration.
- A dashboard configuration containing the bundled card was saved successfully.
- Confirmed-date Ramadan settings persisted across restart. Iftar used the published
  Maghrib beginning when no separate Iftar existed; Taraweeh remained text without
  an invented timestamp.
- A staged replacement survived restart alongside the approved source. Rejecting
  it retained approved values. Removing a second mosque preserved the first
  mosque's entity IDs and states.
- Upgrading from the initial 0.5.0 runtime to 0.5.1 preserved approved/pending data
  and changed the existing card resource to the new version without duplicates.
- The supplied Nuneaton Muslim Society 2026 PDF passed authenticated upload,
  isolated extraction, layout mapping and review of all 365 dates. Rejection kept
  approved data intact. The original PDF was not copied into the repository.

Chromium also opened the actual HA frontend at phone/tablet viewport sizes. The
bundled card loaded from its automatically registered resource. Its editor used
real HA selectors and the native title input; programmatic mode/title changes,
`config-changed` round trips, focus preservation and picker registration passed.
This exercises real components but does not replace manual exploration of every
picker/editor interaction or physical mobile/tablet devices.

This live check found a final-date Ramadan display bug, fixed in 0.5.1: today’s
published Sehri/Iftar values now remain visible after their events when no future
confirmed event exists. The browser showed Sehri **05:55 / Passed** while the next
Sehri timestamp remained unavailable. Regression tests cover both a final confirmed
date and a following active date. See the [screenshots](dashboard.md#preview).

The container's package installer could not validate this environment's outbound
proxy certificate. The exact locked `pypdf==6.21.1` package and its metadata were
supplied from the existing local development environment into the disposable
container’s normal global site-packages directory. TLS verification and integration dependency requirements were kept enabled. This
validates runtime behavior with that dependency present, not fresh dependency
installation through the affected proxy.

## Remaining acceptance

The [release checklist](releasing.md) still requires the HACS custom-repository
installation route, upgrades from a previous release, minimum-version checks and
real mobile/tablet devices. The NMS website's live HTTPS availability is unverified;
manual PDF compatibility is established by the inspected layout, fixture tests
and this live import check.
Hosted GitHub Actions results were not readable from this environment and must be
reviewed on GitHub before publishing a tested release. No release/tag was published.
