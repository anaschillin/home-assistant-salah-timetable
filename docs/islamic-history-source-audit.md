# Sunni Islamic historical events — source audit and proposed integration

**Status:** research / editorial proposal only, 25 October 2026. **No event-feed or dashboard implementation has been approved or deployed by this document.**

## Scope and rationale

A history companion to the existing Salah Timetable dashboard, prioritising:

1. The Prophet Muhammad ﷺ: birth, revelation, Hijrah, campaigns, treaties, the Farewell Hajj, and passing.
2. Sahabah, the Mothers of the Believers, Ahl al-Bayt, the Rightly Guided Caliphs, and major events until the last surviving Companion (the year is disputed).
3. Tabi'un, notable transmitters of hadith, and Sunni scholars, including the authors of the six major Sunni hadith collections (thus extending beyond the Sahabi era).

This is **Sunni-source-led**, not a filter excluding the Prophet's family. The deaths and martyrdoms of Ahl al-Bayt belong in any sound account of Sunni history. Do not conflate the historical authenticity of an occurrence with the authenticity of its *specific day*; do not label every report a sahih hadith simply because an event page cites a sahih collection.

## Sources and reuse safeguards

- Discovery index: [IslamicDates — On This Day](https://islamicdates.org/en/on-this-day) (lists **88 records** on 25 October 2026; includes an explicit warning on many uncertain dates). Its month-neighbour fallback can show a historically real event on a day when nothing is documented *for that day*; **never promote the fallback day to an attested anniversary**.
- Independent verification and expansion: [Dorar al-Saniyyah historical encyclopedia](https://dorar.net/history). Dorar frequently indexes to **year or month only**, which should not be inflated into exact days. See its [history methodology](https://dorar.net/history).
- Classical Sunni material: Ibn Kathir, *al-Bidaya wa'l-Nihaya*; al-Dhahabi, *Siyar A'lam al-Nubala'*; Ibn Hisham, *al-Sirah al-Nabawiyyah*; authoritative biographical/rijal books. Prefer a **specific passage, volume/page or hadith number** over an unlocated book title.
- Narrator discovery and identity validation: Sunni biographical libraries such as IslamWeb's editions of the classical texts; inspect possible variant names and dates.
- **Copyright and terms are not established:** do not scrape/repackage all IslamicDates or Dorar prose or expose either site's content through automatic harvesting without permission. Create **original short descriptions**; store link-backed factual references with source provenance. This document and the candidate JSON contain original abbreviated descriptions, **not copied source articles**.

Source documents may disagree. Such disagreement is a reason for additional review, not an automatic rejection of the event itself.

## Audit of representative events

| Event | IslamicDates placement | Verification and editorial decision |
| --- | --- | --- |
| Battle of Badr | **17 Ramadan 2 AH** | Supported specific day: [IslamicDates](https://islamicdates.org/en/on-this-day/badr/); [Sunni commentary on Qur'an 3:123](https://www.islamweb.net/ar/library/index.php?ID=386&bk_no=215&flag=1&page=bookcontents) places Badr on 17 Ramadan. Candidate **day-level** entry. |
| Martyrdom of al-Husayn ibn Ali (RA) | **10 Muharram 61 AH** | [IslamicDates](https://islamicdates.org/en/on-this-day/karbala/); [Dorar](https://dorar.net/history/event/289) expressly identifies 10 Muharram. Candidate **day-level** entry. |
| Death of Imam Ahmad ibn Hanbal | **12 Rabi al-Awwal 241 AH** | [IslamicDates](https://islamicdates.org/en/on-this-day/imam-ahmad-death/); [Ibn Kathir's account via IslamWeb](https://islamweb.net/ar/library/content/200/19422/) specifies Friday, 12 Rabi al-Awwal. Candidate day-level entry; retain scholarly review gate. |
| Birth of Imam al-Bukhari | **13 Shawwal 194 AH** | [Ibn Kathir's biography](https://www.islamweb.net/ar/library/content/59/1380/) explicitly reports the date. This is an **additional hadith-scholar birthday** beyond the 88-event discovery index. Candidate day-level entry. |
| Death of Imam al-Bukhari | **1 Shawwal 256 AH** | [IslamicDates](https://islamicdates.org/en/on-this-day/bukhari-death/) says the **night of Eid**; [Dorar](https://dorar.net/history/event/845) indexes the death to **Ramadan 256 AH** while describing the same night. Mark a **night/boundary convention** instead of silently treating the indexes as contradictory. Check classical passage before publishing. |
| Birth of the Prophet ﷺ | **12 Rabi al-Awwal, Year of the Elephant** | [IslamicDates](https://islamicdates.org/en/on-this-day/mawlid/) acknowledges several competing day reports. Event is certain, **day disputed**. Keep proposed anniversary separate from documented event date. |
| Isra and Mi'raj | **27 Rajab, pre-Hijrah** | [IslamicDates](https://islamicdates.org/en/on-this-day/isra-miraj/) explicitly says **no authentic hadith fixes the night**. Event certain, anniversary **traditional and not established**; no default exact-day entry. |
| Battle of Mu'tah | **15 Jumada al-Ula 8 AH** | Both [IslamicDates](https://islamicdates.org/en/on-this-day/mutah/) and [Dorar](https://dorar.net/history/event/122) support **Jumada al-Ula 8 AH**, not its day. Publish as a **month highlight**, **not** an event on the 15th. |
| Death of Imam Malik | **14 Rabi al-Awwal 179 AH** | [IslamicDates](https://islamicdates.org/en/on-this-day/imam-malik-death/) warns of disagreement; [al-Dhahabi's biography](https://islamweb.net/ar/library/index.php?ID=1200&bk_no=60&idfrom=1298&idto=1298&page=bookcontents_ver3) recounts reported Rabi al-Awwal days **10, 11, 13 and 14** and an alternative **Safar**; [Dorar](https://dorar.net/history/event/585) indexes **Safar**. Event certain, **month and day disputed**; year-only by default. |
| Death of Anas ibn Malik (RA) | **93 AH** | [Dorar](https://dorar.net/history/event/374) identifies the year and role as a prolific Companion narrator, without month/day. Year-only biographical entry; not an exact anniversary. |
| Last surviving Sahabi: Abu al-Tufayl Amir ibn Wathilah | **100 or 110 AH** | [Al-Dhahabi](https://g1.islamweb.net/ar/library/content/60/627/) reports 110 AH and identifies him as last to die among those who saw the Prophet ﷺ; [Ibn Abd al-Barr](https://www.islamweb.net/amp/ar/library/content/1080/3094/) records 100 AH. **Death year disputed, day/month unknown**; biography-only until stronger evidence. |

The [candidate research dataset](islamic-history-candidates.json) keeps these events **out of runtime**. It must not be treated as a validated release dataset.

## Proposed editorial classification

Every event needs **two separate judgments**:

- **Occurrence evidence:** established / historically reported / uncertain.
- **Date evidence:** day supported / day disputed / only month supported / only year supported / traditional placement / unknown.

A source supporting that a battle happened is not automatically evidence for the day. Keep *observed/traditional anniversary* in a different field from *historical attested date*. Preserve explicit alternatives and any evening/night boundary note. The event year may precede 1 AH (e.g. the Prophet's birth) and must not be fabricated. If only a year is known, show the biography in a separate browse/history view, **never assign an arbitrary date** to fill the calendar.

Recommended record fields: `id`, `title_en`, `title_ar` (when independently verified), `summary_en` (original), `people`, `categories`, `event_type` (birth, death, battle, treaty, revelation, etc.), `era`, `hijri_year`, `hijri_month`, `hijri_day`, `date_precision`, `date_status`, `traditional_placement`, `alternative_dates`, `date_note`, `sources` (URLs and pinpoint citations), `editorial_review` and `display_policy`.

## Proposed Home Assistant behaviour

- Keep historical events **separate from the prayer-time event engine and read-only Prayer calendar**, which concern approved mosque-published *instants*. Historical content must not generate prayer sensors, trigger Jamaat automations or imply liturgical observance.
- Use the card's existing **full calculated Umm al-Qura Hijri header** and its **per-card ±3-day display adjustment** to select the event. Match the selected mosque-local dashboard day; do not run an independent unadjusted API lookup. Explain that the Hijri display uses a calculated civil midnight boundary and can differ from observed moon sighting and religious sunset conventions.
- Feature should be **optional**, with category filters (Prophetic life, Sahabah, Ahl al-Bayt, battles, hadith narrators/scholars) and an optional toggle for **traditional/disputed anniversaries**, which always carry visible qualification. No automatic site scraping or third-party requests in the dashboard.
- Exact-day records appear only when independently supported. On an empty date, prefer **“From this month in Islamic history”** using *month-supported* records, explicitly labelled as monthly highlights; otherwise say no confidently dated event is available. Do **not** display year-only biographies as if they occurred that day.
- Show a compact original summary, date qualifier, and clickable source links. Avoid implying the historical date of the event changes with a modern Hijri/Gregorian converter or a user display offset.
- For event chronology, retain any Hijri-evening transition note (e.g. “night of Eid”) in the title/details; never auto-resolve contested date nomenclature with software.

## Suggested delivery and tests

1. Audit the current 88 IslamicDates index **record-by-record** (source, pinpoint reference, event-vs-date support, pre-Hijrah handling, licensed reuse). Status on 25 October: **small representative sample only**. Do not claim all 88 verified.
2. Expand with Sahabah and early narrators **to approximately 110 AH**, retaining Abu al-Tufayl's year dispute; independently expand major hadith scholars **to at least 303 AH**.
3. Write a versioned, offline JSON catalogue with an explicit review checklist and schema validation. Only approved events enter the runtime bundle. Maintain a corrections process and a source/attribution document.
4. Add pure date selector with deterministic tests for multiple events on one day, 29/30-day months, 1 Muharram rollover, per-card adjustment, night-boundary notes, empty day, month-only fallback, disputed/traditional toggle, category filters and Unicode names.
5. Add the optional dashboard panel, options UI and frontend tests; keep no dependency on source sites for normal HA operation. Verify setup/removal, translations, source links, responsive layouts, and release/licensing gates.

**Release gate:** editorial sign-off on each exact-day claim, attribution/reuse decision, and tested code. Research candidates by themselves are not a release.
