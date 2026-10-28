# Islamic history display defaults — shipped behavior and future specification

**Current status (0.9.18, 28 October 2026):** The card shows an optional,
short, offline description of the **selected day's Hijri month** directly
beneath the calculated Hijri date in the mosque header. It does not repeat
the month name or create a separate history panel. The explanation updates
when switching Yesterday/Today/Tomorrow, and disappears in Compact mode
or if the full Hijri date is hidden or `show_hijri_month_info` is disabled. This feature defaults
to enabled on new and existing cards.

The four additional history options are **disabled as coming soon** in the
graphical editor. Their previously saved values have no effect; no day-event
or monthly-highlights catalogue is rendered. `history-utils.js` is an offline
research/test prototype, not a runtime dependency of the bundled card.

## Default behaviour
- Show **information about the current Hijri month** by default for new installations, using short original educational descriptions for all 12 months.
- Historical exact-day events: **off** by default.
- Month-level historical highlights: **off** by default.
- Disputed/traditional anniversaries: **off** by default and always visibly qualified if enabled.
- Show source references in the card: **off** by default, but store provenance with every record.
- **Implemented:** show month explanation as subordinate text in the header,
  only when the Hijri date is visible; no separate history section or disclosure.
- **Proposed only:** if day/month events are implemented later, show them
  without duplicating the header's month explanation. Preserve explicit
  choices to hide optional history content.

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

The same saved per-card settings work on tablet and mobile. The month
description is deliberately a small header subtitle, not a large new panel.
The proposed event flags are reserved for future editorial and frontend work.

## Date and editorial rules
- Use the same mosque-local Hijri date and per-card adjustment as the existing timetable header.
- A supported day event appears only on its supported Hijri day. Month-only events appear as monthly highlights, never assigned to a day.
- Keep occurrence certainty separate from precise-date certainty; no invented anniversaries.
- If several supported day events occur on one day, show a concise list or expand affordance, not duplicates.
- Do not make runtime network calls to Dorar. Original summaries, documented citations, and explicit editorial approval are required before bundling events.
- Month information should avoid asserting special religious merit for months without supporting evidence.
- Month summaries are informational, not a religious observance schedule or prayer automation.

## Acceptance criteria and current status
1. **Implemented:** Month explanation defaults on, appears only beneath a
   visible Hijri date in Standard/Detailed mode, and follows day navigation
   and the per-card adjustment.
2. **Implemented:** Disabling month information removes the subtitle without
   changing the date, timetable or countdowns.
3. **Implemented:** The four historical-event/source/dispute options are shown
   disabled in the graphical editor; saved legacy values remain inert.
4. **Not implemented:** Turning on events to show a catalogue, date-level
   citations, or monthly historical highlights. These require editorial approval
   and separate frontend acceptance.
5. **Future requirement:** No exact-day event claim without date-level evidence;
   no implied religious merit where there is no sound source.
6. **Implemented for month text:** All 12 educational descriptions are bundled
   offline. Historical day-event selectors remain research-only.

## Delivery sequence
1. Curate and audit 12 original month explanations with citations.
2. Add offline month data and selector tests.
3. Add per-card controls and responsive rendering.
4. Integrate separately approved historical event candidates behind optional toggles.
5. Run frontend and Home Assistant smoke tests before release.
