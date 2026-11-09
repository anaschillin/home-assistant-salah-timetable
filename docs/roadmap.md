# Roadmap

This page contains **upcoming product features only**, not delivered capabilities, routine maintenance, release procedures or historical PR milestones. Priorities are proposals, not committed dates. For released functionality, see the [README](../README.md#features) and [changelog](../CHANGELOG.md).

Documentation follow-ups belong in the [documentation simplification plan](documentation-simplification-plan.md), and release/quality procedures belong in [Releasing](releasing.md). Merged functionality is removed from this roadmap; consult the [changelog](../CHANGELOG.md) to distinguish `main` changes awaiting release from features in a published tag.

## Dashboard and card layouts

- **Jumu’ah detail:** present every published congregation clearly and, when independently published, support separate Bayaan, Adhaan and Khutbah timestamps. Allow reminder selection for a specific congregation without treating a Khutbah as a Jamaat.
- **Cross-mosque comparison:** compare today's approved Jamaat times across enabled mosques.
- **Accessibility improvements:** further improve scalable type, high-contrast options, keyboard focus and accessible touch targets across customised layouts.

## Timetable, importing and prayer events

- **Additional verified PDF layouts:** add annual, monthly and Ramadan publishers only after obtaining representative, permitted examples and independent expected rows. Keep unsupported scans/OCR out of the supported-layout claim until separately implemented and validated.
- **More informative import comparisons:** summarise precisely which approved dates and published prayer fields changed, without weakening explicit review or overwriting source values.
- **Android CSV export fallback:** provide a native or authenticated download path for WebViews that block browser Blob downloads.
- **Coverage planning:** warn before an upcoming month, journey or new publication year has insufficient approved dates or required fields, extending existing diagnostics.
- **Published special prayer events:** add explicitly dated Eid prayer sessions, venues and other verified mosque announcements without altering the daily five-prayer countdowns.
- **Time-bounded mosque exceptions:** support approved temporary schedule or venue overrides with clear effective dates, source provenance and automatic expiry.

## Holiday profiles and personal reminders

- **Temporary holiday timetable:** guide the user to select a destination mosque, timezone and travel dates; import, review and explicitly approve its published timetable before activation.
- **Scheduled activation and return:** enable the selected holiday profile during its dates, then restore the home view. Include End trip now and Extend trip actions.
- **Separate home/travel data:** preserve approved sources and settings independently, showing the selected destination, timezone and trip dates.
- **Per-person or per-dashboard selection:** ensure one traveller's holiday setting does not unexpectedly switch shared household displays or reminders; define permissions and device scope before implementation.
- **Travel reminder choice:** choose whether the traveller's destination reminders temporarily replace home reminders without changing other household users' preferences.
- **Saved destinations and readiness:** reuse configured mosques for later trips, checking approved coverage and showing missing values rather than guessing prayer times.
- **Holiday layout preset:** consider an optional travel-focused arrangement once manual holiday profiles exist; current presets already cover countdown, balanced, timetable-first, Ramadan and wall displays.
- **Leave-for-Jamaat reminders:** use a user-entered journey time and preparation buffer against the selected published congregation.
- **Reminder profiles and guided setup:** offer weekday/weekend and home/travel preferences, plus a guided setup/test flow built on existing reminder/media blueprints rather than duplicate automation engines.

## Suggested delivery order

1. Improve Jumu’ah detail and reminder targeting.
2. Deliver holiday profiles, scheduled activation and travel reminder preferences.
3. Extend verified publication imports, approved special events and export compatibility.

## Deferred or exploratory features

- **Automated publication discovery:** investigate sources beyond user-configured URL templates only with explicit review and no guessed publisher URLs.
- **Cross-year PDF/URL imports:** extend the bounded manual CSV cross-year workflow to other source formats after reviewing date and replacement semantics.
- **Scanned PDF/OCR recognition:** assess a securely isolated, reviewable OCR workflow separately from currently supported text-based PDF parsing.
- **Arabic and integration translations:** additional setup/entity translations and Arabic wording review are on hold; the card's existing bilingual/RTL capabilities are not a substitute for integration-wide translations.
- **Islamic history companion:** research only until date authenticity, editorial scope and rights are resolved; see the [source audit](../research/islamic-history/islamic-history-source-audit.md).
- **Location-based holiday activation:** explore only after predictable manual holiday profiles, with consent and card/reminder isolation.
- **Calculated travel prayer times:** consider a clearly labelled, opt-in calculation feature with explicit settings and provenance; never silently substitute estimates for approved mosque publications.
- **Travel prayer guidance:** consider separately sourced educational content about combining or shortening prayers, without having holiday profiles automatically change religious rules.

Once a feature ships, remove its proposal from this page and document its behaviour in the appropriate guide and changelog.
