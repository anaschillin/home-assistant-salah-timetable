# Dorar historical source — Hijri calendar coverage and licensing audit

**Status:** RESEARCH ONLY — not suitable for runtime publication or redistribution.

## Verified source facts (27 October 2026)
- Dorar historical index: https://dorar.net/history — approximately 6,222 indexed historical entries visible in its index at time of review, spanning multiple eras. Count changes over time.
- Official history API documented at https://dorar.net/api-services/history; requests require access approval. Published terms at https://dorar.net/api-services/terms **prohibit bulk scraping/downloading, repackaging, and storage of the complete database** and restrict cached API responses to 24–48 hours. API attribution and a clickable source URL are required for responses.
- We have **not** harvested the site's dataset. The presence of an official API is **not** permission to mirror the source database into this public open-source repository.
- https://dorar.net/history/event/289: death of al-Husayn (RA) at Karbala, 10 Muharram 61 AH; day appears in event narrative.
- https://dorar.net/history/event/122: Mu'tah, Jumada al-Ula 8 AH; source does **not** establish a particular day.
- Original existing research candidates remain in `docs/islamic-history-candidates.json`, with no production approval implied.

## Important calendar correction
365 is the count for a normal **Gregorian** year, not a Hijri year. A Hijri year has 354 or 355 days, while the calendar has 12 nominal months of up to 30 days (360 possible month-day keys). Each month has 29 or 30 actual days; whether day 30 exists depends on the calendar/year. The separate `islamic-history-day-coverage.json` enumerates all **360 possible Hijri month/day keys**, marking day 30 conditional. It is a research tracker, not an invented 365-event catalogue.

## Editorial policy
- Separate *event occurred* confidence from *date/day established* confidence.
- If no exact-day evidence, place the event in a **month highlight** or **year-only biography**, never a random day.
- Explicitly keep disputed anniversaries and dates (e.g., 12 Rabi al-Awwal for the Prophet's birth; 27 Rajab for Mi'raj) apart from attested precise dates.
- Use independently authored brief English descriptions, not Dorar article text or translated verbatim reconstructions.
- A Dorar page URL is evidence/provenance, not automatic approval to export or reproduce its content.
- Prefer original classical sources and specific passages for each date claim; record contradictions.
- Focus the research first on Prophetic life, Sahabah through ~110 AH, and notable Sunni hadith transmitters and scholars thereafter.

## Roadmap
- Obtain **written permission** from Dorar for any bulk extraction, long-lived caching, redistribution or derivative event compilation; otherwise do not bulk fetch.
- Grow an **independently written**, manually verified event dataset from permitted historical factual references with pinpoint citations, preserving uncertainty.
- Audit exact-day and month-only records independently; each source claim needs per-entry editorial approval before runtime.
- Do not introduce network calls into the Home Assistant card or prayer engines.
- Track total researched dates, supported day-events, month-only entries, disputes, and unknown dates. **Never** use 365/365 as a misleading authenticity target.

## Coverage at creation
- 360 possible Hijri date keys (12 × 30), day 30 in each month is conditional.
- 1 Dorar date-supported research candidate added to day tracker, 1 month-only research candidate held separately.
- All remaining keys marked `unresearched`, not `no_event`. Existing independent candidates in the original JSON have not been silently promoted.
