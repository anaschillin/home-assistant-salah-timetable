# Islamic History display defaults — implementation specification

**Status (27 October 2026): partially implemented in 0.9.3.** The bundled card now
shows an optional offline description for each of the 12 Hijri months, with
`show_hijri_month_info` enabled by default. The historical day-event and
month-highlight catalogue remains research-only; it is **not** rendered by
the running card. The other four history toggles are marked **coming soon**
in the editor and persist their selections but do not enable an event feed.
The independently tested `history-utils.js` selector is a prototype, not an
imported dependency of the live card.

## Default behaviour
- Show **information about the current Hijri month** by default for new installations, using short original educational descriptions for all 12 months.
- Historical exact-day events: **off** by default.
- Month-level historical highlights: **off** by default.
- Disputed/traditional anniversaries: **off** by default and always visibly qualified if enabled.
- Show source references in the card: **off** by default, but store provenance with every record.
- Show month information **above** optional historical events; events never replace the month explanation.
- Respect an explicit user choice to hide month information; if every content type is disabled, hide the history section entirely.

## Card-level configuration (month info live; other flags reserved)
```json
{
  "show_hijri_month_info": true,
  "show_historical_day_events": false,
  "show_historical_month_highlights": false,
  "show_historical_sources": false,
  "show_disputed_historical_dates": false
}
```

Use per-card options to allow different layouts on tablet and mobile. Keep integration-level defaults for newly created cards; do not override explicitly saved settings. Existing installations should not unexpectedly gain a large panel: include an unobtrusive default month summary, with a migration/visual-regression check before release.

## Date and editorial rules
- Use the same mosque-local Hijri date and per-card adjustment as the existing timetable header.
- A supported day event appears only on its supported Hijri day. Month-only events appear as monthly highlights, never assigned to a day.
- Keep occurrence certainty separate from precise-date certainty; no invented anniversaries.
- If several supported day events occur on one day, show a concise list or expand affordance, not duplicates.
- Do not make runtime network calls to Dorar. Original summaries, documented citations, and explicit editorial approval are required before bundling events.
- Month information should avoid asserting special religious merit for months without supporting evidence.
- Month summaries are informational, not a religious observance schedule or prayer automation.

## Acceptance criteria (complete for the delivered month display; remainder proposed)
1. **Implemented:** New cards default to a compact Hijri month explanation.
2. **Implemented as settings only:** Historical events, monthly highlights, disputed dates, and visible citations start disabled; no historical events are rendered yet.
3. Turning on events adds them below month information; turning off month information removes only that section.
4. Five toggle values are defined and persist in card configuration; end-to-end
   historical-event display remains unimplemented.
5. Mobile/tablet layout remains readable, with no effect on Salah/Jamaat sensors or countdowns.
6. No exact-day claim appears without date-level evidence and editorial sign-off.
7. All 12 month summaries have source attribution and original English wording.
8. 29/30-day Hijri boundaries, calendar adjustment, empty dates and multiple events are tested.

## Delivery sequence
1. Curate and audit 12 original month explanations with citations.
2. Add offline month data and selector tests.
3. Add per-card controls and responsive rendering.
4. Integrate separately approved historical event candidates behind optional toggles.
5. Run frontend and Home Assistant smoke tests before release.
