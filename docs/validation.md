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


## Follow-up hardening after repository updates

The maintainer's changes through `5966ab0` were pulled and preserved. Formatting
was reconciled in `d876793` with parenthesized exception handlers retained.
Upgrade/recovery and diagnostic hardening are recorded in `806776c`.

The combined Python suite passed **569 tests**, with 94% aggregate integration
coverage. New cases include literal historical schema-1/schema-2 fixtures, pending
approval after migration, exact preservation/retry after failed migration writes,
future-schema rejection and complete timetable-store restoration with stable entity
IDs and Repair cleanup. This does not substitute for a full HA backup-archive restore.
Diagnostics now distinguish unloaded entries from retained runtime objects and expose
only allowlisted coverage/event flags.

Local release-note preparation passed its seven tests and generated a ZIP, checksum
and version-specific notes. The manual draft-release workflow was parsed and reviewed
but was not triggered; GitHub API access remains blocked in this environment.


A new Chromium check reproduced phone-width overflow at 200% root text size. The
prayer table now stays in a labelled, keyboard-focusable scroll region; the enlarged
layout passes at both 360px and 900px. The native fixture now has 21 checks per
viewport. Asset cache versions are advanced in candidate 0.5.2.

A separate minimum-version runner started HA 2026.10.0 and completed configuration,
CSV approval, Ramadan and independent-mosque checks. Its first restart failed because
Docker reassigned an automatic host port; an explicit stable port corrected that
runner issue. A subsequent attempt still did not confirm expected Fajr after restart.
Full minimum-version acceptance remains unverified. The draft runner is preserved
on `codex/live-smoke-runner` for startup/state investigation, and is not included in
main-branch validation tooling. Task containers and private configurations were removed.


Final candidate 0.5.2 checks after merging the maintainer updates: **569 Python
tests**, **31 Node frontend tests**, both native Chromium viewport fixtures
(including the enlarged-text regression), Ruff lint/format, release asset/note
preparation and official hassfest all passed. No GitHub release/tag was published.


## Contributed Ramadan publications — candidate 0.5.3

Pulled maintainer fixtures through `daa6a1a`. The original binary files are unchanged;
attribution and SHA-256 hashes are recorded in the [fixture README](../tests/fixtures/pdf/README.md).

- NMS `nms ramadhan.pdf` is May–June **2022**, not a complete Ramadan-only file.
  The strict monthly adapter produces 61 exact dates and 854 event values.
- Zakariyya `zak.pdf` is the 2026 annual calendar plus a final Ramadan page. The new
  adapter imports only that page: February 18–March 20, 31 dates and 341 published
  values. Its final post-Ramadan Hijri-1 row does not activate Ramadan.
- Every date and event value matched separately constructed Poppler spatial-text
  CSV oracles, independently of production pypdf extraction and layout helpers.
- Actual isolated extraction and native HA authenticated upload/map/review/approve
  flows passed for both real PDFs. Source binary/checksum and parsed provenance
  round-trip through persistence and config-entry reload without activation.
- Explicit confirmation in the example February 18–March 19 window enables
  Zakariyya's permitted default Iftar and text-only Taraweeh; March 20 stays inactive.
  This test window is not a declaration of observed Ramadan dates.
- Confirmed-window edge gaps, annual field retention, unavailable fields, default
  Iftar, manual/off modes, date adjustment, source exclusion, advisory source/effective
  chronology and legacy-source conflicts have regression coverage. Approval checks
  current options and retains both approved data and pending proposals on conflict;
  a conflicting proposal can still be rejected normally.
- The PDF input bound is 4 MiB. Tests exercise acceptance at the exact boundary and
  rejection above it by the isolated worker, plus upload/download limits. Page,
  stream, text, decompression, CPU/memory and timeout protections are unchanged.

The full Python suite passed **670 tests** (95% aggregate integration coverage;
the isolated worker remains outside coverage instrumentation). After the metadata
update, **23** frontend/packaging/release-preparation cases passed. Ruff lint/format,
**31** Node tests, Chromium smoke at 360/900 pixels and official hassfest all passed.
The reproducible 0.5.3 integration ZIP builds successfully and excludes PDF fixtures.
No hosted Actions result, HACS installation, release or tag is claimed by these checks.

The complete NMS Ramadan publication, full Zakariyya annual parsing and native
cross-Gregorian-year PDF imports remain outside this change. See
[Ramadan validation](ramadan_validation.md) and [remaining work](remaining-work.md).


## Zakariyya annual tables and README badges — candidate 0.5.4

The same maintainer-supplied `zak.pdf` now has a separate annual adapter:
`zak_annual_v1`. It imports twelve complete monthly tables and excludes the
separate Ramadan appendix. All **365 Gregorian dates and 3,770 published event
values** match a separately constructed Poppler spatial-text CSV oracle; no
production pypdf extraction or adapter helpers generated that oracle.

Sehri is published on 120 dates, February–May; the other 245 dates retain no Sehri
value. No Maghrib Jamaat, Jumu'ah, Iftar, Istewa or Taraweeh value is invented.
November's pre-noon Dhuhr values remain 11:xx AM. All published timestamps validate
in `Europe/London`, including both DST changes.

The visually clipped first May date, “May …”, is interpreted as 2026-05-01 only
with its printed May 2026 heading, Friday weekday, complete 31-row month and exact
subsequent dates 2–31. The original token and explicit interpretation note persist,
and the review screen calls this out before approval. May's printed Hijri 1446
caption remains unchanged in the binary publication; it never changes Gregorian
dates or confirms Ramadan activation.

Native HA tests cover authenticated PDF upload, suggested mappings, review,
approval/reload, original provenance, Friday column meanings and absent fields.
They also cover URL profile persistence, separate Ramadan source confirmation,
permitted effective Iftar fallback, text-only Taraweeh and post-Ramadan annual
fallback without mutating sources. Exact UTC sensor states on March 29 and October
25 pass; after Isha on March 28, next Salah uses March 29's actual printed Fajr
across the clock change. Incorrect column reassignment remains unstaged and allows
a corrected retry.

**724 Python tests passed**, with 95% aggregate integration coverage. Ruff
lint/format, **31 Node tests**, real Chromium smoke at 360/900 pixels, official
hassfest and reproducible 0.5.4 release-asset/note preparation passed. PDF fixtures
remain outside integration release archives.

README badges now show dynamic Validate status for main, HACS **Custom** repository
support and the code's MIT license. The GitHub badge endpoint was fetched and
reported passing for main before these commits. This coarse status is not proof of
validation for the new release commit: GitHub API access still returns Forbidden,
so exact hosted results and the remaining release acceptance checks remain pending.
A release badge is deferred until an actual tagged release is published.
