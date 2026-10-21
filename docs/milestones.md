# Implementation plan

Keep each item a focused PR with its own tests and documentation. Do not combine
all remaining milestones into one change.

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

## Milestone 3 — secure URL sources and modular PDF parsing

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

Acceptance: only tested layouts are listed as supported; changes never auto-activate.

## Milestone 4 — event engine and Ramadan

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

Acceptance: a table-driven event matrix proves each requested dashboard context.

## Milestone 5 — bundled Lovelace card

1. Bundle versioned JS assets and register them through supported HA APIs. Provide
   a graphical editor selecting a mosque and context/previous/upcoming mode.
2. Render date/name, next beginning, contextual Jamaat, five daily prayers and Ramadan
   details. Use absolute backend timestamps and browser-local ticking countdowns;
   do not write sensor states every second.
3. Add responsive mobile/tablet layouts, HA theme variables, accessibility, empty and
   error states, localization, resource lifecycle and upgrade/cache handling.
4. Add frontend unit and browser tests for editor round trips, all event contexts,
   disconnections, countdown boundaries, theme switching and narrow screens.

Acceptance: install from HACS with no separate Card Mod or card download; configure
and exercise the card entirely through the graphical editor.

## Milestone 6 — release hardening

Redacted HA diagnostics, repair notifications, migrations/backups, more independently
tested PDF layouts, end-to-end HACS upgrade/removal checks, security review of all
network/import paths, support policy and release automation. Review licensing of
fixtures/assets, publish release notes and submit to the HACS default catalogue only
once the complete user workflow is verified.
