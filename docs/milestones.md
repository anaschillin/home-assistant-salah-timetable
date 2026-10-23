# Implementation plan

The [remaining-work checklist](remaining-work.md) tracks release blockers separately
from later feature additions.

Milestones 1–5 are implemented; the current candidate is 0.5.1. Keep follow-up work in focused PRs
with its own tests and documentation. A disposable HA 2026.10.2 runtime/frontend smoke check passed. Release acceptance
still includes hosted validation, HACS installation and physical-device checks.

## Milestone 1 — foundation (implemented)

HACS layout, manifest, Config Flow and Options Flow, per-mosque device, immutable
prayer vocabulary, persistent multi-year storage, timestamp sensors, tests and CI.
Release acceptance: hosted hassfest/HACS checks pass, then review an installation
in a disposable Home Assistant instance. No import or dashboard claims.

## Milestone 2 — validated manual CSV import (implemented)

1. Define parser protocol and structured staging/provenance/coverage result types.
2. Add a bounded CSV parser with explicit year/date and column mapping. Normalize
   terminology and resolve quotation-mark Jamaat repetition only from a preceding
   explicit value in the same documented column; reject unresolved repetitions.
3. Add HA UI upload/import and preview/approve/reject flows. Report incomplete dates,
   missing fields, duplicates and ambiguous 12-hour columns without guessing.
4. Persist source/staged/approved data separately with a versioned migration.
5. Test fixture imports, invalid encodings, malformed data, next-year and leap-year
   coverage, cancellation, restart, failed saves and independent mosque entries.

Acceptance verified by automated tests: authenticated upload, graphical mapping,
staging, explicit approval and real timestamp sensors after entry reload; pending
review also survives cancellation/reload. No hand-edited storage, YAML sensors or
user templates. A manual browser installation/release check remains separate.

## Milestone 3 — secure URL sources and modular PDF parsing (implemented)

1. Build a bounded HTTPS downloader with content signatures, MIME checks, timeouts,
   download limits and redirect limits. Revalidate every redirect and resolved IP;
   reject credentials in URLs, loopback, private/link-local/reserved destinations and
   unsafe schemes. Prevent DNS rebinding through connection-time address validation.
2. Run PDF extraction off the event loop with bounded resource consumption. Start
   with one documented mosque layout and licensed/sanitized golden PDF fixtures.
   Make unsupported/scanned layouts explicit errors until OCR is separately reviewed.
3. Add URL-first UI setup and optional manual uploads through the same staging path.
4. Compare digests/HTTP validators on scheduled checks. Stage changed sources for
   explicit approval, preserve the last approved source on every failure, and expose
   update status/errors without exposing credentials or private URLs in diagnostics.
5. Test SSRF redirects/rebinding, oversized/chunked files, misleading content types,
   corrupted/encrypted PDFs, parser limits, change detection and approval persistence.

Implemented and tested: HTTPS downloader, strict sample PDF adapter, isolated PDF
worker, URL-first source options/manual upload, daily/manual change checks, durable
staging/approval, status sensor, diagnostics and storage v3 migration.

The user-provided Nuneaton Muslim Society 2026 annual PDF is now inspected and supported
by `nms_annual_v1`. Its 365 dates/5,110 events match an independent extraction, including
clock changes, Friday slots and quotation marks. Original synthetic fixtures reproduce
the recognized layout for CI; the uploaded original is not redistributed. Manual UI
upload/approval/reload and changed-source staging are tested. Live access to the
website's HTTPS equivalent is unverified; HTTP downloads remain unsupported.

Acceptance: only tested layouts are listed as supported; changes never auto-activate.

## Milestone 4 — event engine and Ramadan (implemented)

1. Create a pure timezone-aware event engine for previous/next Jamaat and independent
   next Salah beginning. Use tomorrow's actual Fajr record after Isha; missing future
   data produces an unavailable result. Jamaat is one event, never a duration.
2. Define exact-boundary behavior and context states before beginning, between
   beginning/Jamaat, and after Jamaat. Offer previous/upcoming display modes.
3. Add confirmed Ramadan date ranges, manual activation/date adjustments and a
   separate effective override layer. Only confirmed dates receive Ramadan data.
4. Default effective Iftar to published Maghrib beginning when no separate published
   Iftar exists. Default Taraweeh to the text “After Isha Jamaat”, never a fabricated
   timestamp. Expose Ramadan status and absolute Sehri/Iftar events for countdowns.
5. Test all prayer boundaries, multiple Friday congregations, DST, leap dates,
   December/January rollover, date adjustments and missing tomorrow records.

Implemented with pure event/resolution modules, HA boundary scheduling and UI options.
The integration exposes independent next-Salah/next-Jamaat, previous-Jamaat,
active-Ramadan Sehri/Iftar timestamps and Ramadan/Taraweeh status. Existing daily
sensors use the effective row while immutable imported values remain intact.

Automatic Ramadan requires an inclusive confirmed 1–35-day range; manual on is
explicit confirmation until changed and off disables the layer. A -3 to +3-day
adjustment shifts only the confirmation window. Sources match exact Gregorian
dates; overlapping Ramadan tables require explicit selection. Published Iftar is
preserved, and missing Taraweeh remains text without an invented timestamp.

Automated acceptance covers the context matrix, exact event boundaries, independent
beginning/congregation selection, multiple Friday congregations, tomorrow's actual
Fajr, missing data, DST, leap/year boundaries, confirmation ranges, source selection,
options persistence and no per-second entity writes. The coordinator schedules exact
event and midnight callbacks with a one-minute fallback.

## Milestone 5 — bundled Lovelace card (implemented)

1. Bundle versioned JS assets and register them through supported HA APIs. Provide
   a graphical editor selecting a mosque and context/previous/upcoming mode.
2. Render date/name, next beginning, contextual Jamaat, five daily prayers and Ramadan
   details. Use absolute backend timestamps and browser-local ticking countdowns;
   do not write sensor states every second.
3. Add responsive mobile/tablet layouts, HA theme variables, accessibility, empty and
   error states, localization, resource lifecycle and upgrade/cache handling.
4. Add frontend unit and browser tests for editor round trips, all event contexts,
   disconnections, countdown boundaries, theme switching and narrow screens.

Implemented as `custom:salah-timetable-card`, bundled with the integration, with a
graphical editor for the mosque's Prayer timetable entity, context/previous/upcoming
mode and optional title. Resource setup uses supported HA APIs for storage and YAML
resource modes. The card renders absolute timestamps and browser-local countdowns,
five daily prayers, Ramadan details, missing/disconnected states, responsive layouts
and HA theme variables. No separate card download or Card Mod is required.

Node tests and an isolated headless Chromium harness cover event contexts, editor
round trips, local ticking/timer cleanup, safe text, disconnections, theme changes
and narrow layouts. HA elements are stand-ins in that harness. A separate disposable
HA 2026.10.2 manual installation verified real card/editor components and viewport
rendering. Complete manual picker workflows, HACS installation and physical-device
checks remain release acceptance work; see the [validation record](validation.md)
and [dashboard setup](dashboard.md).

## Milestone 6 — release hardening (partially implemented)

Implemented: actionable Repairs for invalid stored records, reproducible manual-install
ZIPs with checksums, runtime-asset inclusion checks and synchronized manifest/project/
frontend cache versions. A real HA 2026.10.2 manual-install smoke also covers import,
restart/pending review, two-mosque isolation/removal, resource upgrade and actual
frontend/editor rendering. See the [validation record](validation.md) and
[release preparation and manual checks](releasing.md).

1. Exercise install, graphical setup, restart, upgrade and removal in a disposable
   HA instance installed through HACS; check real mobile/tablet rendering and themes.
2. Extend migration/backup recovery coverage. Invalid-record Repairs, allowlisted
   diagnostics and schema 1/2 migrations already exist.
3. Review all network/import paths and resource limits, and add independently tested,
   redistributable fixtures before supporting further PDF layouts.
4. Verify hosted pytest/frontend/lint, hassfest and HACS jobs; finalize the support
   policy and release notes, then review publication. Reproducible archive
   building is automated; review fixture/asset licensing before publishing.
5. Submit to the HACS default catalogue only once the complete user workflow is
   verified. The custom-repository installation remains the documented route.
