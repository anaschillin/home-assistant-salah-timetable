# Ramadan timetable validation

Import approval and Ramadan activation are separate decisions. A publication may
include days before Ramadan, Eid, later months or provisional Hijri labels. None
of those confirms the mosque's observed Ramadan dates.

The contributed NMS file is May–June **2022**, not a complete current Ramadan
timetable. The Zakariyya 2026 publication has a separate Ramadan page containing
thirty Ramadan rows plus a following Hijri-1 row. Both are useful regression cases
against activating every imported date. See [PDF layouts](pdf_layouts.md).

## What is rejected

- Invalid PDF/CSV shape, size, encryption or unsupported layout; malformed times,
  duplicate/unordered dates, wrong declared Gregorian year and invalid column mapping.
- Known mosque-layout contradictions in headers, dates, weekdays, physical time
  cells and the tested AM/PM convention. No automatic correction is attempted.
- Ambiguous or nonexistent timezone timestamps, including DST transitions.
- Competing Ramadan source rows on active dates when no unique source is selected.
  This is checked both when saving settings and again at approval using current
  options. Approval failure retains the pending proposal and approved data.

## What review shows

Review separates source omissions from effective availability. In automatic mode
with confirmed dates, it checks **every date in the adjusted confirmed window**,
including missing dates before the first or after the last imported row. It shows:

- Dates with an active Ramadan source row, dates using only annual data, dates
  without effective prayer timestamps and candidate dates outside the saved window.
- Annual field values retained, default Iftar from effective Maghrib beginning,
  Taraweeh text without a timestamp, and fields still unavailable after merging.
- Advisory time-order warnings on imported rows even while Ramadan is inactive,
  and separately on effective merged values. These compare same-date local times,
  such as Jamaat before its beginning, Sehri after Fajr or Iftar before Maghrib.
  Published values are unchanged and warnings require checking the publication.

An unconfirmed import cannot establish full-month coverage. Manual On has no end
date; its preview is limited to the candidate dates and clearly states that mode
stays active until changed. Off applies no Ramadan overrides or defaults. An
explicit source selection is retained and the review identifies excluded imports.

Partial sources remain valid: an Iftar/Sehri-only publication need not contain all
daily prayers. Blank override fields retain exact-date annual values when present;
missing dates never borrow another day's values. The permitted Iftar default is
the only generated timestamp; Taraweeh's default is text, not an invented time.

## Remaining limits

Confirmation accepts a 1–35-day activation window to support partial periods and
manual adjustments; it does not certify a 29/30-day lunar month. Import coverage
counts are not lunar-date validation. Users must confirm observed dates themselves.

Each import is still limited to one declared Gregorian year. A publication crossing
December–January needs separate year-specific sources; native cross-year PDF
imports require further work. The supplied NMS sample does not validate a complete
Ramadan publication. Zakariyya's annual and Ramadan tables use separate explicit
layouts; neither source confirms observed Ramadan dates.
