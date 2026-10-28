# Implementation plan

The [release checklist](releasing.md#current-release-readiness) owns publication
and manual acceptance gates. The [remaining-work backlog](remaining-work.md)
owns subsequent feature priorities. This document records implemented and
proposed milestone scope, not another current-release checklist.

The current merged integration/card version is **0.9.18** (28 October
2026), including the compact multi-mosque liquid-glass redesign in
[PR #88](https://github.com/anaschillin/home-assistant-salah-timetable/pull/88).
The final PR head passed [Validate 40744012961](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40744012961)
and [CodeQL 40744012733](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40744012733),
and was squash-merged at [`80b8017`](https://github.com/anaschillin/home-assistant-salah-timetable/commit/80b80173bc45257cc46fd31e81dcbaff87ab97ed).
Earlier 0.7.0–0.9.0 and 12-job CI evidence remains in
[validation.md](validation.md) as history. These results are code acceptance,
**not** release-tag publication, asset-rights clearance or complete HACS /
HAOS/manual physical-device sign-off.

## Next increments

Milestone 6 remains the release gate for every increment. Feature development can
continue while an external acceptance check is unavailable, but a passing unit test
does not complete that check. Milestone numbers do not promise a release version.

The enhancement review uses the official
[MAWAQIT Home Assistant integration](https://github.com/mawaqit/home-assistant)
as a reference. Planned capabilities below are additions to this integration;
their completion requires implementation and the stated acceptance evidence.

| Increment | Deliverable | Status | Dependencies |
| --- | --- | --- | --- |
| 7A | Adhan, Jamaat and Sehri automation blueprints | Implemented | Existing timestamp sensors |
| 7B | Approved-date coverage monitoring and opt-in health alerts | Implemented | Effective timetable resolver; blueprint pattern |
| 8 | Native prayer calendar | Implemented; release acceptance pending | Approved dated records and event engine |
| 9 | Inspected-edition setup picker | Retired in 0.9.1; automatic PDF recognition retained | Standard PDF/URL imports |
| 10A | Card/editor English, Arabic, bilingual labels and RTL layout | Implemented; release acceptance pending | Stable prayer keys and current card |
| 10B | Integration forms/entities and reviewed translations | Planned | 10A catalogue conventions; fluent-language review |
| 11 | Minimum/current compatibility tests and weekly validation | Implemented; hosted minimum/current validation passed | Existing CI and reproducible dependency lock |
| 12 | Richer Adhan playback controls | Implemented; release acceptance pending | 7A; calendar triggers from 8 when available |
| 13 | Pause/resume media around prayer events | Implemented; release acceptance pending | Published event timestamps; 7A/8 automation patterns |
| 14 | Calculated night midpoint and last third | Planned | Actual Maghrib and next-day Fajr timestamps |
| 15 | Mosque display mode, branding and announcements | Planned | Existing card; localization conventions from 10 |
| 16 | Published Eid and other special prayer events | Planned | Explicit dated event storage/approval; calendar from 8 |
| 17 | Before/after import change review | Implemented; release acceptance pending | Existing durable staging and source replacement scope |
| 18 | Optional offline Islamic history companion | Proposed; research only | Reviewed catalogue, date precision and attribution; 10A card conventions |

The original **8 → 12 → 13 → 9** sequence was implemented in candidate 0.7.0; the optional Milestone 9 picker was later retired in 0.9.1.
Its exact commit `737b636` passed hosted Validate, including both HA live lanes.
Milestone **17** is also implemented; candidate 0.8.0 combines its canonical
comparison with original-cell/provenance review and fresh-baseline approval checks.
Exact-commit CI and applicable real-world release acceptance remain required.
The merged dashboard enhancement adds published Fajr end
(Sunrise), MOSQUE_A Friday second-khutbah notes and a mosque-wide full-Hijri-date
display preference (see [dashboard](dashboard.md)). This addition is
**implemented, with real-device/source and restart release acceptance pending**.
REV-08's import-difference portion is fulfilled by Milestone 17. Candidate
0.9.0 implements **10A** for the card/editor, including English/Arabic selection,
bilingual known prayer labels and RTL presentation, while preserving 0.8.1's
Hijri-first header and automatic Annual/Monthly/Ramadan import choices.
Local unit/native-browser checks and 29 live HA checks passed; exact-commit CI
and applicable manual acceptance remain required. Continue **10B** (integration
translations and reviewed wording) with **11** (broader compatibility testing)
in parallel; 14–16 follow. Milestone numbering does not set release order.

Every increment needs focused tests, user documentation, successful CI for its
exact commit and applicable live checks before release. Imported values stay
immutable, missing published times stay unavailable, and timetable changes require
explicit approval. Derived night periods are labelled calculated. The calculated
Hijri display never confirms Ramadan or an Eid date.

## Milestone 1 — foundation (implemented)

HACS layout, manifest, Config Flow and Options Flow, per-mosque device, immutable
prayer vocabulary, persistent multi-year storage, timestamp sensors, tests and CI.
Release acceptance includes hosted hassfest/HACS checks and an installation in a
disposable Home Assistant instance. Import and dashboard behavior are covered in
later milestones.

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

The user-provided Mosque A 2026 annual PDF is now inspected and supported
by `mosque_a_annual_v1`. Its 365 dates/5,110 events match an independent extraction, including
clock changes, Friday slots and quotation marks. Original synthetic fixtures reproduce
the recognized layout for CI; the uploaded original is not redistributed. Manual UI
upload/approval/reload and changed-source staging are tested. Live access to the
website's HTTPS equivalent is unverified; HTTP downloads remain unsupported.

Subsequent inspected layouts add MOSQUE_A May–June 2022 monthly pages and Mosque B's
2026 annual tables and separate Ramadan page. Their independent expected-value
comparisons and publication-specific limits are documented in
[PDF layouts](pdf_layouts.md).

Acceptance: only tested layouts are listed as supported; changes never auto-activate.

## Milestone 4 — event engine and Ramadan (implemented)

1. Create a pure timezone-aware event engine for previous/next Jamaat and independent
   next Salah beginning. Use tomorrow's actual Fajr record after Isha; missing future
   data produces an unavailable result. Jamaat is one event, never a duration.
2. Define exact-boundary behavior and context states before beginning, between
   beginning/Jamaat, and after Jamaat. Offer previous/upcoming display modes.
3. Add confirmed Ramadan date ranges, manual activation/date adjustments and a
   separate effective override layer. Ramadan data applies only within the confirmed
   active window or while explicit manual activation is on.
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

1. Bundle versioned JS assets and register them through supported HA APIs.
   Provide a graphical editor selecting one or more mosque timetable sensors.
   The initial context/previous/upcoming selector was **retired**; current
   Jamaat display switches context automatically.
2. Render date/name, next beginning, contextual Jamaat, five daily prayers and Ramadan
   details. Use absolute backend timestamps and browser-local ticking countdowns;
   do not write sensor states every second.
3. Add responsive mobile/tablet layouts, HA theme variables, accessibility, empty and
   error states, locale-aware dates/times, resource lifecycle and upgrade/cache
   handling. Milestone 10A extends card/editor interface labels to English and Arabic.
4. Add frontend unit and browser tests for editor round trips, all event contexts,
   disconnections, countdown boundaries, theme switching and narrow screens.

Implemented as `custom:salah-timetable-card`, bundled with the integration,
with a graphical editor for enabled mosque Prayer timetable entities and an
optional title. Resource setup supports storage and YAML resource modes. The
current card has one mosque/Next Salah/contextual Jamaat summary, a matching
liquid-glass timetable, a header mosque selector when needed, calculated
Hijri/Gregorian dates that follow day navigation, and local decorative photos
that span the available dashboard viewport. Absolute prayer timestamps,
browser-local countdowns, Ramadan details, responsive layout and HA theme
variables remain. The earlier mode selector and photo opacity slider are
removed; no separate card download or Card Mod is required.

Node tests and an isolated headless Chromium harness cover event contexts, editor
round trips, local ticking/timer cleanup, safe text, disconnections, theme changes
and narrow layouts. HA elements are stand-ins in that harness. A separate disposable
HA 2026.10.2 manual installation verified real card/editor components and viewport
rendering. The candidate 0.6.1 HA 2026.10.0 check also exercised the actual picker,
editor controls and saved configuration after page reload. Authenticated HACS
installation, restart and updates are user-confirmed complete; actual HACS UI
uninstall/reinstallation remains outstanding. Physical-device checks were
user-confirmed on 24 October 2026 for an installation with no recorded version,
before 0.7.0 and the later dashboard additions; see the
[validation record](validation.md) and [dashboard setup](dashboard.md).

Candidate 0.6.0 added prayer emphasis, independent countdown progress,
calculated Umm al-Qura dates and graphical layout/visibility/time-format controls.
The latest dashboard changes show Fajr's **published sunrise end** within its row,
show explicitly published MOSQUE_A second-Jumu’ah khutbah times as **Friday-only notes**
without modifying existing Dhuhr/Jamaat events, and add the mosque-level full-Hijri
visibility preference during setup and under Configure → Mosque settings. The
per-card Hijri toggle and ±3-day display adjustment remain available. Candidate
0.8.1 places the full Hijri date first and adds an independent Gregorian switch;
0.9.0 retains these controls in English and Arabic. Imported times and Ramadan
activation stay unchanged; see [dashboard](dashboard.md).
The maintainer approved PR #88's final visual layout before its 0.9.18 merge.
Version-specific release and broader device/HACS acceptance remain separate;
see [validation](validation.md) and [releasing](releasing.md).

## Milestone 6 — release hardening (partially implemented)

Implemented: actionable Repairs for invalid stored records, reproducible manual-install
ZIPs with checksums, runtime-asset inclusion checks and synchronized manifest/project/
frontend cache versions, historical schema-1/schema-2 migration tests and timetable
store recovery tests. The live Home Assistant Container matrix now additionally
checks real backup-archive restoration into a separate disposable config, two-mosque
isolation and config-entry removal/re-addition. This **does not** establish full HAOS
recovery or HACS UI uninstall/reinstallation. See the [validation record](validation.md)
and [release acceptance checklist](releasing.md).

The [release guide](releasing.md#current-release-readiness)
maintains the acceptance criteria and required evidence for asset rights, full
HAOS/Supervisor recovery, HACS UI lifecycle, applicable runtime/device checks,
exact-commit validation and reviewed publication. The 24 October physical-device
confirmation applies to that earlier installation; later features still need
their applicable acceptance. Further layouts need inspectable, redistributable
fixtures and independent results. HACS default-catalogue submission remains a
later backlog item; custom-repository installation is the current route.

## Milestone 7 — ready-made automations and coverage monitoring (implemented; release acceptance pending)

Implementation and real automation-engine acceptance are covered in
`tests/automations/test_blueprints.py`; pure/coordinator coverage cases are in
`tests/core/test_coverage.py`. [User setup](automations.md) documents sensor selection,
no catch-up, pending-review deduplication and unresolved future coverage. These
local checks do not replace Milestone 6's release gate.

### 7A — prayer automation blueprints

Deliver three importable Home Assistant automation forms:

1. Play a user-selected Adhan recording on selected media players at published
   prayer beginnings. Audio remains selected by the user rather than distributed
   with the integration.
2. Run selected reminder actions before the next published Jamaat, including each
   successive Friday congregation.
3. Run selected actions before the next Sehri event whose target date is active
   Ramadan. Use the backend's Next Sehri event rather than today's Ramadan status,
   so a reminder before midnight ahead of the first fast remains possible.

Acceptance: exercise expanded blueprints with HA's actual automation engine;
verify selected targets/actions, offset scheduling, unavailable timestamps, changed
approved times, midnight boundaries, reload without catch-up and independent
mosques. Document that a trigger must be loaded before its offset instant; daily
beginning sensors cannot promise reminders before their date becomes available.

### 7B — approved coverage and opt-in alerts

Add a diagnostic Timetable coverage sensor showing no approved timetable, missing
today, missing tomorrow, approaching expiry or adequate coverage. Count consecutive
effective approved dates from the mosque-local date, stopping at the first gap.
An intentionally unpublished prayer field does not make the entire date missing.
Pending proposals never extend approved coverage. A source ambiguity beyond
tomorrow stops verified coverage and exposes an `unresolved_date`; it does not
disable valid current prayer data or pretend the uncertain date is unpublished. Warn when seven or fewer future
dates remain, and expose the final consecutive date and remaining-day count.

Provide a fourth blueprint that runs user-selected actions when coverage enters a
warning state or an import first becomes pending review. It must avoid repeated
notifications from ordinary timestamp/status-attribute updates and startup state
restoration. Alerts never approve an import or alter stored records.

Acceptance: cover internal date gaps, expired/empty imports, December/January,
mosque-local midnight, Ramadan overrides and activation windows, approval/rejection,
two mosques and alert recovery/re-entry. Verify partial daily records stay partial
and invalid source settings still preserve the last approved data.

## Milestone 8 — native prayer calendar (implemented; release acceptance pending)

Implemented: one read-only calendar per mosque, approved-only range queries,
stable IDs, explicit Iftar fallback descriptions and a documented calendar-trigger
example in [calendar guidance](calendar.md). Each event retains its exact
published start instant and uses a **60-second calendar presentation interval**
for Home Assistant's exclusive-end and automation-trigger semantics. This is **not**
a prayer or Jamaat duration. Queries cover at most 366 local dates; callers can
request later approved years separately.

Expose a calendar per mosque built from approved, explicitly dated effective
records. Publish beginning and Jamaat as distinct scheduled events, including all
Friday congregations and active-Ramadan Sehri/Iftar. Query only the requested date
range; omit absent values and pending proposals. Reuse the existing timezone and
Ramadan rules without inventing a prayer duration. Cover all approved dates,
including explicitly imported future years, rather than imposing a current/next-month
limit. Later calculated and special events retain their own identities.

Acceptance: stable event identifiers across reload and UI-language changes;
bounded range queries; DST, leap-day and year boundaries; every Friday congregation;
missing dates/fields; changed approvals; and correct HA calendar-trigger behavior.
Add calendar-based automation examples after those semantics pass.

## Milestone 9 — inspected-edition picker (retired in 0.9.1)

The previously implemented manual edition/profile picker was removed following
maintainer acceptance testing: ordinary users upload a PDF or configure a URL.
The strict MOSQUE_A and Mosque B PDF adapters, automatic layout detection, ordinary
source/URL profiles, stage/compare/approve flow and independent fixture oracles
are **retained**. Older approved records containing legacy
`publication_profile_id` remain loadable; that field is not persisted for new
imports. See [PDF layouts](pdf_layouts.md). No published times are changed.

## Milestone 10 — localization and right-to-left layouts (in progress)

### 10A — bundled card/editor (implemented; release acceptance pending)

The card/editor supports automatic HA-language selection or explicit English and
Arabic, English fallback, optional bilingual known prayer labels and RTL layout.
Date and number formatting uses the selected locale, with explicit Gregorian and
Umm al-Qura calendars. Hijri remains the primary date when enabled; the Gregorian
line is independently optional, and the mosque-wide Hijri preference remains
authoritative. Local countdowns retain stable numeric nodes through ordinary
ticks; editor language/configuration updates preserve focused title text and
selection. Stored field names, blueprint inputs, unique IDs and event identifiers
remain stable. See [dashboard options](dashboard.md#language-and-direction).

Arabic wording is a draft awaiting fluent-language review. Required validation
covers catalogue completeness, fallback, long and bilingual labels, RTL focus
order, both time formats, mosque-local dates and 200% text at narrow widths.
Record actual Home Assistant editor acceptance and physical-device results
separately from the isolated browser harness. No earlier device confirmation
establishes acceptance of these changes.

### 10B — integration translations and reviewed wording (planned)

Translate integration forms, entity labels and backend-generated summaries using
stable keys and HA's translation facilities. Review Arabic wording with a fluent
speaker before claiming reviewed translation quality. Add translated setup
guidance and further languages as reviewed contributions become available.
Keep machine identifiers, approved source data and event identities unchanged.

## Milestone 11 — compatibility and scheduled validation (implemented; hosted CI passed)

Validate includes the separately locked Home Assistant **2026.10.0** minimum and
**2026.10.3** supported-current unit suites and real disposable Container live
checks. Each compatibility lock pins the matching HA test plugin, verifies
Python/distribution/import identity and isolates its temporary directory.
The development/release lock stays on HA 2026.10.2.

An initial unsharded minimum-HA job stalled on hosted runners. The test-client
frozen-router fixture regression was fixed by
[PR #23](https://github.com/anaschillin/home-assistant-salah-timetable/pull/23).
[PR #26](https://github.com/anaschillin/home-assistant-salah-timetable/pull/26)
replaced the 16 diagnostic jobs with five deterministic, exhaustive
minimum-HA test groups; the complete supported-current suite still runs
unsharded. See the [compatibility guide](compatibility.md) for the evidence,
original-hang limitation and local commands. [Issue #24](https://github.com/anaschillin/home-assistant-salah-timetable/issues/24)
was closed after both PR and merged-main CI passed.

The calendar synchronization regression (completed
[issue #13](https://github.com/anaschillin/home-assistant-salah-timetable/issues/13))
also passed repeated normal/delayed refresh cases and subsequent hosted CI.
Both required HA versions passed the
[main Validate run 40337238065](https://github.com/anaschillin/home-assistant-salah-timetable/actions/runs/40337238065).
Reusable unit/live workflows run weekly and on demand. HACS, hassfest, native
Chromium, version assertions and the exact-release-commit gate remain required.

Further static typing and expanded lint rules are potential focused future
improvements, not prerequisites that justify weakening present test coverage.

## Milestone 12 — richer Adhan playback controls (implemented; release acceptance pending)

Implemented: graphical optional Fajr recording, per-prayer sensor/volume slots,
disabled beginnings, quiet hours in the HA timezone or UTC, and guarded delayed
volume restoration. Existing inputs remain valid. Calendar triggers are available
through the separate documented example; existing Adhan automations keep timestamp
triggers. See [automation guidance](automations.md).

Extend the existing playback blueprint with a separate optional Fajr recording,
per-prayer enable/volume settings, configurable quiet hours and optional restoration
of the speaker's previous volume. Continue using user-selected accessible media.
Keep the existing basic playback configuration valid. Quiet hours use an explicit,
documented timezone; they can span midnight. Reuse calendar triggers from 8 when
available without requiring users to migrate their working timestamp automations.

Acceptance: real HA automation tests verify each selected recording/prayer/player,
disabled prayers, quiet-hour midnight/DST transitions, unavailable speakers and
overlapping playback. Optional restoration must not overwrite a user's later volume
change or another active playback operation. Restart/reload must not replay missed
Adhans, and playback remains through HA media players rather than browser autoplay.

## Milestone 13 — pause/resume media around prayers (implemented; release acceptance pending)

Implemented: an opt-in blueprint captures the published resume anchor, validates
a 0–180 minute delay before pausing and only resumes unchanged players whose pause
context belongs to its run. Disabling or reloading a changed automation cancels
resumption; an unchanged automation can keep running across an incremental reload.
Devices that drop
service context require manual resumption. A second automation skips already-paused
players, so separate operations do not extend one another’s windows.

Add an optional blueprint that pauses only selected players currently playing and
resumes only those paused by that automation. Users select the published event
anchors and an explicit resume delay. A delay is an automation policy; Jamaat
remains a scheduled instant and gains no inferred prayer duration.

Acceptance: test initially playing/paused/stopped players, manual intervention,
multiple mosques using the same player, overlapping prayer operations, restart and
cancellation. Missing event anchors must not create guessed times or leave an
indefinite pause. Do not resume media that a user stopped or replaced meanwhile.

## Milestone 14 — calculated night periods (planned)

Expose optional calculated timestamps for the night midpoint and start of its last
third. Derive them from the actual published Maghrib beginning on one date and Fajr
beginning on the next date. Keep calculated outputs and their provenance separate
from imported prayer fields, and make them usable by HA time-trigger automations.
They do not change prayer times, Ramadan activation or the Hijri display.

Acceptance: calculate using elapsed absolute time across DST, midnight and year
boundaries; omit results when either endpoint is missing, invalid or out of order.
Test leap dates, changed approvals, independent mosques and rollover at the next
Fajr. Clearly label the calculation in entity descriptions and documentation;
never reuse a previous day's Fajr to fill a missing endpoint.

## Milestone 15 — mosque display mode and announcements (planned)

Add an optional wall-tablet/full-screen card presentation with a large clock,
prominent countdowns and readable prayer columns. Allow user-provided mosque image
or logo and dated text announcements, with clear mosque-local activation/expiry.
Announcements are managed separately from prayer data. Existing compact/expanded
cards and ordinary Home Assistant authentication continue to work.

Acceptance: test phone/tablet landscape and portrait, large text, keyboard focus,
light/dark themes, long/bilingual/RTL text and offline/stale-data indication. Render
announcement text safely, expire it at the configured local date boundary and
preserve settings through reload/restart. Keep countdown ticks local and efficient;
use supplied branding/announcements rather than assuming an external mosque feed.

## Milestone 16 — published special prayer events (planned)

Support explicitly dated Eid and other special prayer events, including multiple
published congregations, through graphical entry or a documented import path with
preview/approval. Preserve published labels, dates, times and provenance. Extend
8's calendar and appropriate dashboard details without changing ordinary daily
prayer records or inventing event durations.

Acceptance: stable event identities, explicit year/timezone, multiple congregations,
DST/year boundaries, missing dates, replacement/removal, rejection and restart.
Pending events remain inactive. Eid dates must be supplied or explicitly confirmed;
they are never inferred from the calculated Hijri header or a predicted Ramadan end.

## Milestone 17 — import change comparison (implemented; release acceptance pending)

Implemented: **Compare changes before approval** opens a read-only screen with
ten comparison entries per page, then returns to the approval/rejection review.
All added/removed dates, canonical field changes, ordered Jumu'ah sequences and
additional original-cell changes remain reachable, including legacy multi-year
and unmapped data. Source metadata and original tokens are bounded/escaped, with
URL-shaped tokens redacted. Browsing retains the pending stage ID and never
approves it. A fresh-disk check under the shared storage lock blocks approval if
the exact approved source changed after review; the comparison resets and requires
another explicit decision. No storage migration or automatic source activation
is introduced. See the [import review and comparison guide](import_review.md).
Further human acceptance on large real
PDF publications and supported UI devices is still required.

Extend import review with a date/field comparison between the approved source being
replaced and its pending proposal. Show old/new published times, added and removed
dates, changed availability and multiple Jumu’ah congregations. Identify the exact
source kind/year and whole-source replacement scope. Keep source-value changes
separate from calculated/effective Ramadan fallback and display formatting.

Acceptance: compare canonical values rather than byte hashes alone; retain access
to original tokens/provenance and distinguish identical canonical values from changes
to source bytes or original tokens. Test first
imports, unchanged values, partial replacements that remove dates, absent fields,
multiple congregations, different years/kinds and large paged comparisons. Rejecting
or cancelling preserves approved data; restart preserves the proposal. Stale review
identities cannot approve a different proposal. Diagnostics must not expose imported
values, private URLs or file contents.


## Milestone 18 — optional offline history companion (proposed)

The [source audit](islamic-history-source-audit.md) and
[candidate dataset](islamic-history-candidates.json) are research inputs for an
optional history panel. Recording this proposal does not approve implementation
or any candidate for runtime use. The current catalogue stays outside the
integration bundle; it has no effect on prayer sensors, the Prayer calendar,
Ramadan confirmation or the published special prayers proposed in Milestone 16.

First establish a versioned catalogue schema with separate occurrence and date
assessments, explicit editorial approval, pinpoint citations, original summaries
and an attribution/reuse decision. Complete the source and date-precision review
before promoting any candidate. Preserve disputed alternatives, pre-Hijrah eras
and night-boundary notes. A proposed `exact_day` display classification does not
satisfy these checks. The [research delivery criteria](islamic-history-source-audit.md#suggested-delivery-and-tests)
track this editorial work; ordinary release acceptance remains in the
[release guide](releasing.md).

If approved for implementation, use a bundled offline catalogue and the same
mosque-local calculated Hijri date and display adjustment as the card header.
Offer category filters, qualified disputed/traditional anniversaries and original
short summaries with source links. Month-only records may appear as clearly
labelled monthly highlights; year-only or undated biographies never acquire an
invented anniversary. Normal operation must not scrape or contact source sites.

Acceptance for any later implementation includes schema and approval checks,
date-selection boundaries, multiple matches, empty dates, 29/30-day months,
new-year rollover, display adjustments, filters, disputed dates and Unicode.
Verify optional controls, safe source links, translations and narrow RTL layouts
without changing published prayer data or creating prayer automation events.
