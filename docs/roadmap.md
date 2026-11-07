# Roadmap

This page records **upcoming features only**, not delivered changes or old pull request history. The order below is indicative, not a commitment.

Already delivered capabilities, including v3.1.0 countdown layout improvements,
are documented in the [README](../README.md#features), [dashboard guide](dashboard.md)
and [changelog](../CHANGELOG.md); they are not repeated here.

## Planned improvements

- **Verified timetable coverage:** support additional annual, monthly and Ramadan publications only with reviewed examples and independent expected results; preserve strict date, format and HTTPS validation.
- **Monthly/export follow-up:** consider a native download fallback for Android WebViews that restrict browser Blob downloads. [Monthly browsing and approved-year CSV export](getting-started.md#browse-yesterday-and-the-monthly-timetable) are implemented; keep any fallback within authenticated Home Assistant APIs.
- **Import usability:** evaluate further improvements from concrete user feedback. Readiness shortcuts, missing-field names, saved manual-CSV mapping suggestions, removed-date warnings and comparison filters already exist; build on these with clearer summaries of exactly which dates and prayer fields changed, and preserve explicit approval.

## Dashboard and configurable card layouts

- **Upcoming changes:** highlight tomorrow's approved Jamaat changes, including how much earlier or later they occur.
- **Timetable health:** show approved coverage remaining, missing required fields and pending updates, with links to the relevant setup or review controls. Build on the existing diagnostics.
- **Jumu’ah view:** clearly display every published congregation and allow users to select the congregation targeted by their reminders.
- **Mosque comparison:** compare today's published Jamaat times across selected mosques side by side.
- **Visual layout editor:** add a Layout tab with presets, section ordering, visibility controls, full-width or half-width placement, and phone/tablet/desktop previews before saving.
- **Layout presets:** offer Compact/Quick glance, Balanced, Timetable first/Full timetable, Ramadan, Wall display and Holiday arrangements, reusing existing detail levels where appropriate.
- **Movable sections:** support arranging the mosque selector, Gregorian/Hijri dates, Next Salah, Next Jamaat, timetable, Ramadan details, calculated night information and timetable status. Consider a large clock for wall layouts and destination/trip dates for holiday layouts.
- **Accessible arrangement controls:** provide drag-and-drop plus keyboard-accessible Move up/Move down controls. Adapt side-by-side sections to narrow screens without clipping or losing content.
- **Independent saved layouts:** save arrangements per card so home, holiday and wall dashboards can differ. Preserve existing card appearances and provide Reset layout.
- **Example arrangements:** countdown-focused cards place dates above side-by-side Salah/Jamaat panels and the timetable; timetable-focused cards put the full timetable before compact countdowns; Ramadan cards prioritise Sehri/Iftar; wall displays prioritise a large clock, dates and countdowns; holiday cards prioritise destination, trip dates and destination-local times.
- **Accessibility polish:** improve scalable text, touch targets, keyboard navigation and high-contrast presentation.

## Holiday profiles and additional Salah features

- **Temporary holiday timetable:** provide a guided flow to choose a destination mosque, IANA timezone and trip dates, import and explicitly approve its published timetable, preview the temporary card and choose reminder preferences.
- **Scheduled activation and return:** activate the travel profile for the selected dates and restore the home view afterward. Provide End trip now and Extend trip controls.
- **Separate home and travel data:** retain independent approved timetables and settings, and clearly label the active destination, timezone and trip dates.
- **Personal travel selection:** support per-person or per-dashboard activation so one traveller does not switch the household's wall display. Define selection and permissions explicitly before implementation.
- **Travel reminders:** explicitly choose whether destination reminders replace that person's home reminders, preserving other household users' preferences.
- **Saved destinations:** reuse a previously configured destination mosque for another trip, checking current approved coverage before activation.
- **Trip coverage checks:** flag missing dates or required prayer fields before activation and show unavailable values rather than copying or inventing times.
- **Leave-for-Jamaat reminders:** support a user-entered journey duration and preparation buffer before the selected published congregation.
- **Date-limited mosque exceptions:** support explicitly approved temporary schedule or venue changes, with clear effective dates and automatic expiry.
- **Published Eid schedules:** support explicitly published dates, multiple prayer sessions and venues. Extend the special-event proposal only with verified source data.
- **Reminder profiles:** offer weekday, weekend, home and travel delivery preferences. Coordinate with the existing reminder blueprints and the proposed Before Salah reminder work rather than duplicating them.

## Setup, coverage and recovery

- **Coverage planning:** warn when an upcoming trip, month or new year lacks approved timetable data, extending the existing coverage diagnostics and alert blueprints.
- **Automation setup wizard:** guide users through existing reminder and media blueprints, device selection and a test notification.
- **Backup and restore guidance:** document how to preserve and recover approved timetables and mosque settings, with clearly stated verification limits.

## Suggested delivery order

The sequence is indicative and does not set release dates:

1. Upcoming-change summaries and timetable health information.
2. Layout presets, section ordering and full-width/half-width placement, followed by richer visual previews.
3. Holiday profiles using manually selected dates and approved destination publications.
4. Jumu’ah congregation selection and travel-aware reminders.
5. Other dashboard, setup, recovery and verified publication improvements as supporting work permits.

## Deferred or exploratory

- **Publication discovery:** consider automated discovery beyond the user-configured template and confirmation flow; no publisher URLs are guessed.
- **Cross-year imports:** consider PDF and URL support beyond the manual CSV upload; see [import limits](import_review.md#remaining-limits).
- **Additional integration translations and Arabic wording review:** on hold. The card already supports English/Arabic labels and RTL; Home Assistant setup/entity translations currently ship in English. Preserve identifiers and data behaviour; no target release date is assigned.
- **Special prayer events:** consider only events with verified publication dates.
- **Location-based travel activation:** explore only after manual holiday profiles, with explicit opt-in and predictable effects on individual cards and reminders.
- **Calculated travel times:** consider as a separate, clearly labelled feature with explicit calculation settings and provenance; never silently substitute calculations for approved mosque publications.
- **Travel prayer guidance:** consider separately sourced educational material about combining or shortening prayers. Holiday activation must not automatically change religious rules or alter published times.
- **Islamic history companion:** research only; resolve date authenticity, editorial scope and rights before considering a runtime dataset. See [source review](../research/islamic-history/islamic-history-source-audit.md).

Completed work belongs in the implementation and Git history, not this roadmap.
