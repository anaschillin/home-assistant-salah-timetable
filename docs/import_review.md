# Review and compare an imported timetable

Every PDF, CSV or URL proposal requires an explicit **Approve and save timetable**
decision. Nothing is activated automatically, including a changed publication
download. The review includes date coverage, missing fields, warnings, sample
values, Ramadan effects, and an optional read-only comparison against the
currently approved publication.

## Configuration fields and defaults

Open the mosque's **Configure** menu in **Settings → Devices & services**. Saved
settings are reused when reopening a form. Import choices below describe a new
import; no timetable is active until you explicitly approve it.

| Form / field | Values and initial default | Effect |
| --- | --- | --- |
| Mosque settings → Mosque timezone | Current saved IANA timezone | Reinterprets published local clock times in the chosen zone; check timestamps after changing it. |
| Mosque settings → Show full calculated Hijri date | Saved preference; initially enabled | Dashboard display only. Card preferences can hide the header independently. |
| Add or replace a URL source → URL | Required; no default | Public HTTPS PDF/CSV address, without credentials or private-network destinations, using port 443. |
| URL source → File type | PDF (default) or CSV | Select the actual publication format; neither an HTML page nor a scanned PDF is supported. |
| PDF upload → PDF file | Required; no default | Text PDF, at most 4 MiB and 16 pages, in a [supported layout](#supported-pdf-layouts). |
| CSV upload → CSV file | Required; no default | UTF-8 CSV, at most 512 KiB, with a header and ISO `YYYY-MM-DD` dates. |
| PDF/URL → Timetable type | Annual (default), Monthly or Ramadan | Monthly creates a separate exact-date-span ordinary source. Ramadan is a separately activated override. |
| CSV upload → Timetable type | Annual (default) or Ramadan | A partial Annual CSV replaces that whole year's ordinary source. For a separate Monthly CSV source, use a public HTTPS CSV URL and choose Monthly. |
| All imports → Year | Current year in the mosque's timezone; whole number 1900–2199 | Must match the publication's Gregorian dates. One import cannot span two years. |
| Map columns → Date column | Matching `Date` header, otherwise the first column | Select the explicit date column and check every row's date interpretation. |
| Map columns → Time format | 24-hour (default) or 12-hour | General input requires `HH:MM` or explicit `HH:MM AM/PM`, respectively. Known PDF adapters normalize their documented column conventions before mapping. |
| Map columns → Prayer fields | Unique recognised headers are suggested; otherwise Do not import this field | Map only published fields. At least one prayer field is required; a physical column cannot be reused or also mapped as the date. All sixteen supported fields are listed in the [entity reference](automations.md#entities-per-mosque). |
| Review → Action | Compare changes, Approve and save timetable, or Reject and keep the active timetable; no default decision | Comparison is read-only. Approval replaces the complete target source; rejection retains approved data. |
| Compare → Next step | Return to approval/rejection, plus Previous/Next page when available | Navigate all change pages without approving or changing the timetable. |
| Manage URL sources → Source | One configured source; no default | Select the source to check or remove. |
| Manage URL sources → Action | Check or Remove; no default | Check stages valid changes for approval. Remove stops checks while retaining approved timetable rows. |

**Check URL sources now** has no parameters: submit its confirmation form to
check every configured URL. **Manage URL sources** and **Check URL sources now**
appear only when URL sources exist; **Review pending import** appears when a
proposal is staged. To replace a URL, import and approve another URL for the same
source identity; check the [replacement scope](#replacement-scope) first.

### Ramadan settings

| Field | Initial default | Meaning |
| --- | --- | --- |
| Activation | Automatic | Automatic applies only inside the confirmed window. Manual on remains active until changed and ignores the window; Off prevents Ramadan overrides/defaults. |
| Confirmed first / last date | Both empty | Inclusive Gregorian window of 1–35 days. Set both dates or clear both; imported rows and calculated Hijri dates do not confirm them. |
| Adjust confirmed window (days) | `0` | Whole days from −3 to +3, shifting the activation window only; source row dates stay unchanged. |
| Ramadan source | Use the unique matching source | Automatic selection requires a unique source on each active date. Alternatively choose an approved Ramadan source explicitly; other Ramadan sources are then excluded. |

An import and its activation settings are separate. See [Ramadan timetable
validation](#ramadan-timetable-validation) for merging, warnings and Iftar/Taraweeh
fallbacks, and [Dashboard](dashboard.md#ramadan-controls) for display behaviour.

### When data updates

The coordinator refreshes date/event snapshots once per minute while the mosque
is loaded; card countdowns tick in the browser. These refreshes use already
approved data and do not download a timetable. Uploaded files change only after
another import is approved.

Configured URL sources are checked when due and then once every 24 hours while
loaded. Due times use saved check timestamps across restarts; an overdue source
is checked after startup. Manual checks use the same validation and approval
rules. A valid changed download becomes a pending proposal, never an automatic
replacement. Failed checks retain the approved timetable. Review any existing
pending proposal before importing another file.

The diagnostic **Source status** sensor exposes `configured_sources`,
`pending_review`, `error_count`, `last_checked` and `last_success`, without the
URLs or published prayer values. Its states are:

| State | Meaning |
| --- | --- |
| `not_configured` | No URL sources are configured. Uploaded timetables can still be active. |
| `configured` | A URL source has no successful validated check recorded yet. |
| `up_to_date` | The latest successfully checked publication matches the approved source. |
| `rejected_version` | A checked publication has been explicitly rejected. |
| `differs_from_approved` | A checked publication is not the approved version. |
| `pending_review` | A proposal awaits approval or rejection. |
| `error` | A URL source check or source-state storage operation failed. |

With several sources this is a summary; **Manage URL sources** shows each
source's check status. Pending review takes precedence over errors in the summary;
the `error_count` attribute still exposes failures. This sensor remains readable
when prayer data is unavailable. Use the [Timetable coverage](automations.md#read-timetable-coverage)
sensor to check approved date coverage separately.

## Replacement scope

A comparison targets the **exact source ID** that approval will replace (for
example, `annual-2026`), not an unrelated timetable with overlapping dates.
Approving a replacement changes the **whole source**, not just the dates
displayed in the preview. Separate approved source IDs, other mosques and
separately approved Ramadan tables are unchanged. A legacy source containing
multiple years is compared across all of its dates.

An initial import has no previous source: its published dates and values are
additions. Before replacing any existing source, check whether a shorter
publication removes previously available dates or prayers.

## Understanding the changes

The comparison uses the original source's **canonical published** prayer values,
indexed by Gregorian date and prayer field. Times are displayed as 24-hour
HH:MM. Every published Friday Jumu’ah congregation remains in its ordered
sequence, not just the first time.

| Difference | Meaning |
| --- | --- |
| Added date | A date is present only in the new source; its published fields are also additions |
| Removed date | A date is present only in the approved source and would be removed on replacement |
| Changed time | Both sources publish a field but its canonical time or ordered Jumu’ah list differs |
| Added or removed field | An explicit published value appears or disappears on an existing date; missing is **absent**, never `00:00` |
| Additional original-cell change | Retained text or unmapped source cells differ beyond the canonical prayer values |
| No canonical changes | Published prayer values agree, although the file, provenance, checksum or original text may still differ |

One field on one date counts as a single changed entry, even when Jumu’ah
contains multiple times. Date and field ordering is deterministic.

Source details may also identify differences in available parser, time format,
column mapping, checksum or publication-profile metadata. Retained original
tokens are escaped and truncated for safe display; URL-shaped text is redacted
and actual download URLs are not included. Where older stored records lack
original provenance, the UI reports the limitation rather than inventing the
previous values.

**A matching canonical timetable does not prove that two source files are
identical.** Changes in notes, labels, original cells or layout still require
review of the actual mosque publication.

## Ramadan and calculated values

The source comparison shows what was **printed and imported**, not derived
dashboard values. Effective Ramadan overrides, the documented Maghrib-to-Iftar
fallback and other approved annual sources are evaluated separately in the
Ramadan review. No calculated Hijri dates, time-zone conversions or effective
fallbacks are inserted into the published-value comparison. The comparison
never rewrites the publication or Ramadan settings.

## Browse, approve or reject

1. In the pending import review, choose **Compare changes before approval**.
2. Inspect **every page** of additions, removals, canonical field differences
   and extra original-cell changes. Each page contains at most **10 entries**.
   **Next page** and **Previous page** are available where applicable;
   summary counts cover the full comparison.
3. Choose **Return to approval/rejection**. The comparison does not save,
   reject or replace anything. Explicitly select **Approve and save timetable**
   or **Reject and keep the active timetable**.

Closing the review retains the staged proposal under **Configure → Review
pending import**, including after a Home Assistant restart. The current page
position is temporary and resets when a new review flow opens. Rejection
removes the pending proposal but preserves approved data. A failed save leaves
the approved snapshot intact.

If the approved baseline for the target source changes during review, the
comparison refreshes, returns to its first page and requires another explicit
approval. Changes to unrelated source IDs or other mosques do not invalidate
this baseline. Approval checks the baseline again under the shared storage
lock; an old preview cannot silently overwrite a changed source. If the
pending stage is rejected/replaced, or the integration reloads mid-flow,
reopen the current pending review before deciding.

## Security and limitations

The comparison is displayed in the authenticated Home Assistant Options UI.
Private source bodies, URLs, original cells, validators and published times
are **not logged or exposed through diagnostics** by this comparison; stored
source provenance remains protected. Existing atomic storage approvals and
Ramadan validation remain authoritative.

Inspect the complete original PDF/CSV as well as **all** pages before
approving. Comparison does **not** assess copyright, religious authenticity,
source accuracy or redistribution permission.

## Guided annual publication rollover

When an approved full-year HTTPS URL profile is configured, **Configure →
Prepare next year's URL publication** can start a new-year import from that
approved profile. Select the previous year's source and **enter the actual
new year's public HTTPS URL**. The integration derives the next Gregorian
year from the approved profile and reuses the existing bounded download,
layout detection, column mapping, preview, comparison and explicit
approval flow. It never guesses publisher URL patterns, overwrites the
prior year's data or activates a new source without review.

The flow appears only for a canonical approved annual URL profile with
substantial yearly coverage. It is unavailable if another import awaits
review; it also rejects a year that already has approved annual data or
an existing URL profile. This initial guided rollover does not
automatically discover future publications; auto-discovery needs an
explicitly configured publisher URL template and independent tests.

## Supported PDF layouts

Every supported layout has a bounded adapter, explicit column meanings and golden
tests. For ordinary PDF uploads and PDF/HTTPS sources, choose **Annual**,
**Monthly** or **Ramadan** plus the printed Gregorian year. Recognition is
automatic; there is no PDF-layout selector.
The bounded PDF is extracted once for inspection and every *known strict adapter*
is checked against that same text. Only one recognized matching adapter may
proceed; an unsupported or ambiguous PDF is rejected with no guessed time.
There is no OCR, fuzzy layout guessing or fallback to calculated prayer times.

**Monthly** describes normal partial coverage and remains internal `annual`
kind (with only published dates present). Unlike an ordinary `annual-YEAR`
import, the Monthly choice for a PDF upload or PDF/CSV URL source uses a unique
source ID for its **exact first/last published dates**, e.g. `annual-2026-monthly-0101-0131`. This permits
nonoverlapping months to coexist while retaining each original PDF's provenance.
Reimporting the *same* span replaces that source; overlapping source dates
are rejected, rather than silently deleting earlier rows. A previously
configured monthly **URL update**, whether PDF or CSV, cannot silently move into
a different date span; import the new period separately. **Ramadan** creates a separate
override source; its effective dates must still be confirmed explicitly.
A PDF containing annual tables **and** a separate Ramadan page (Mosque B)
is handled according to the chosen import type and never activates both.
The detected concrete parser identifier is stored with approved and
URL-update sources, so later checks do not silently change adapters.
The mapping and approval screens report recognized layout and date range.

| Layout ID | Tested against | Supported structure |
| --- | --- | --- |
| `mosque_a_annual_v1` | Supplied Mosque A 2026 annual calendar | Cover + contact page + twelve complete monthly tables |
| `mosque_a_monthly_v1` | Maintainer-supplied MOSQUE_A May–June **2022** pages | Complete consecutive monthly tables with explicit Gregorian headings |
| `mosque_b_annual_v1` | Maintainer-supplied Mosque B 2026 calendar | Extracts twelve complete annual tables; separate Ramadan page excluded |
| `mosque_b_ramadan_v1` | Same publication, separate Ramadan page | Extracts only the final Ramadan table; annual tables use their own layout |
| `pdf_table_v1` | Synthetic sample only | Text-based, pipe-delimited table described below |

### Supported editions and automatic recognition

Use **Configure → Upload a supported PDF** or **Add or replace a URL source**.
Choose **Annual**, **Monthly** or **Ramadan** and the printed Gregorian year.
The integration identifies known layouts automatically and suggests their
published columns; the user must still inspect the mapping and approve.
There is no edition-specific profile picker or hard-coded mosque timezone.
All strict PDF parsers, independent fixture comparisons, limits and automatic
layout detection remain in place. Unsupported editions fail closed rather
than guessing times.

### MOSQUE_A monthly pages (`mosque_a_monthly_v1`)

Choose **Monthly**, year **2022**, and upload the matching PDF. The contributed file
named `mosque_a_monthly_2022.pdf` actually contains **May and June 2022**, with 61 dates and
854 event values. Every date/value matches an independent Poppler extraction.
It is not a complete Ramadan-only publication: May 1 is printed Hijri 30, May 2
resets to Hijri 1, and June is outside Ramadan. Its moonsighting note is preserved
as document context and does not confirm any activation dates.

The adapter checks complete consecutive months in one year, exact weekdays,
recognized headings/footer, thirteen physical time cells, the known extracted
separator and month-local Jamaat ditto. Column meanings and morning/noon/evening
normalization match the annual MOSQUE_A contract below. It preserves published values,
weekday and Hijri day separately. The Monthly choice stores ordinary calendar
data under its own exact date-span source. Ramadan may be selected when importing
an explicitly confirmed exact-date override source.
Selecting 2026 for this 2022 file is rejected. No Taraweeh or extra Khutbah event
is inferred. Only the inspected structure is supported.

The inspected monthly footer's explicitly printed **Second Jumu’ah khutbah**
time is preserved separately as Friday-only metadata. It is not a Jumu’ah
congregation and does not change the Dhuhr beginning or Jamaat column. An
unrecognized footer still fails validation, rather than fabricating a time.

### Mosque B annual calendar (`mosque_b_annual_v1`)

Choose **Annual**, year **2026**, and upload the supplied fourteen-page
`mosque_b_2026.pdf`. The adapter imports its twelve
annual tables only. The separate Ramadan page remains an independently approved
Ramadan source; importing the annual tables never activates Ramadan.

All **365 dates and 3,770 published values** match an independent Poppler extraction.
The field meanings match the Ramadan mapping below, with **Sehri published only
from February through May (120 dates)**. Other months have no published Sehri
value. No Maghrib Jamaat, Iftar, Jumu'ah, Istewa or Taraweeh timestamp is invented.
Friday's Arabic weekday cell does not turn the Zohar Jamaat column into Jumu'ah.

The adapter recognizes the tested 2026 cover, twelve ordered Gregorian titles,
known header variations, full month row counts, exact weekdays, ten/eleven physical
time cells, the printed daily order and expected footers. Pre-noon **11:xx AM**
Dhuhr values remain before noon, rather than being changed to 23:xx. Stored
`Europe/London` timestamps validate the spring/autumn clock changes.

One source date cell is visibly clipped to **“May …”**. It is accepted as
**2026-05-01** only in the first row of the complete May 2026 table, with the
printed Friday weekday and exact subsequent dates 2–31 all matching the calendar.
Changing the heading, weekday, row position or date sequence is rejected. The
original token and a date-interpretation note are preserved, and the import review
explicitly calls out this interpretation for approval. This is a documented
Gregorian-date reconstruction, not a calculated or repaired prayer time.

May's printed Hijri caption says **1446 AH**, unlike adjacent months. The adapter
preserves the publication; it does not correct that caption, change Gregorian
2026 dates or use Hijri text to activate Ramadan. Binary source/checksum, raw
physical time values, weekday, Hijri day and date interpretation survive approval
and reload. Unknown clipping or missing time cells are rejected.

### Mosque B Ramadan page (`mosque_b_ramadan_v1`)

Choose **Ramadan**, year **2026**, and upload the matching PDF. The supplied 3,213,250-byte, fourteen-page publication fits the bounded
4 MiB input limit. The cover and twelve ordered monthly titles establish the known
publication; only its final **Ramadhan 2026 / 1447 AH** table is imported. This does
not import its annual tables; choose Annual to import those separately. Other editions
remain unsupported.

All **31 dates and 341 published event values** match an independent Poppler
extraction. The table spans February 18–March 20, 2026, including a final Hijri-1
row after the thirty printed Ramadan rows. **Do not confirm 31 Ramadan days from
this row count.** Confirm the actual start/end dates independently in Ramadan
settings. Tests use February 18–March 19 as an explicit example, not a declaration
of observed Ramadan dates.

| Printed column | Imported field |
| --- | --- |
| Sehri End | Sehri ends |
| Fajr Start / Jamaat | Fajr beginning / Jamaat |
| Sunrise | Sunrise |
| Zohar Start / Jamaat | Dhuhr beginning / Jamaat |
| Asar Start / Jamaat | Asr beginning / Jamaat |
| Magrib Start | Maghrib beginning |
| Isha Start / Jamaat | Isha beginning / Jamaat |

There is no separate published Maghrib Jamaat, Iftar, Taraweeh, Istewa or Jumu'ah
column. The Arabic Friday label is a weekday, not a congregation field; Zohar
Jamaat keeps its printed meaning on Fridays. Active Ramadan may use Maghrib
beginning as the documented Iftar default; that timestamp is not written into the
imported source. Taraweeh remains “After Isha Jamaat” without a fabricated time.

The strict adapter checks the tested publication/year, table headers, eleven time
cells, explicit Gregorian month changes, consecutive dates, weekdays and daily
ordering. Original binary PDF, displayed date tokens, raw times and Hijri/weekday
cells are retained. It never derives Gregorian dates from Hijri values or changes
the user-confirmed window. Fixture hashes and attribution are recorded in the
[fixture README](../tests/fixtures/pdf/README.md).

### Mosque A annual calendar (`mosque_a_annual_v1`)

Choose **Upload a supported PDF**, **Annual** and the printed year (2026 for
the supplied file). Use mosque timezone
`Europe/London`. Keep the Date column, 24-hour format and the suggested labelled
prayer fields. Fields may be left unselected; their meaning cannot be reassigned.

The supplied 14-page, 1,622,704-byte PDF was tested directly. Its SHA-256 is:

```text
cf6edb8672436821b62ebbf9abf4cb773030990fef64b7708d6a27c1745e4aaf
```

All **365 dates and 5,110 event values** matched a separate extraction. Date/weekday,
annual coverage, source serialization and `Europe/London` event timestamps were
validated, including the March 29 and October 25 clock changes, Friday slots and
published weekend Isha changes. No time was calculated from a prayer algorithm.

The adapter requires the recognized cover/contact pages and twelve monthly tables.
It checks the explicit year/month headings, ordered Gregorian dates, printed weekdays,
row counts, column headings and all thirteen physical time cells. Quotation marks
resolve only within a Jamaat source column, resetting at the month boundary. A
missing/malformed time or unknown table layout is rejected rather than repaired.

| Published column | Canonical meaning |
| --- | --- |
| Sehri Ends | Sehri ends, separate from Fajr beginning |
| Dawn | Fajr beginning |
| Sunrise | Sunrise |
| Istewa (Noon) | Istewa |
| Dhuhr Start | Dhuhr beginning |
| Asr Start | Asr beginning |
| Sunset | Maghrib beginning |
| Esha Start | Isha beginning |
| Fajr in Jamaat group | Fajr Jamaat |
| Dhuhr/Jumu’ah | Jumu’ah on Friday; Dhuhr Jamaat on other days |
| Asr in Jamaat group | Asr Jamaat |
| Maghrib (Iftaar) | Both the explicitly labelled Maghrib Jamaat and published Iftar |
| Esha in Jamaat group | Isha Jamaat |

The PDF uses 12-hour numbers without a general AM/PM legend. This adapter explicitly
defines the inspected layout's morning/noon/evening convention: Sehri, Dawn, Sunrise
and Fajr Jamaat are morning; Istewa/Dhuhr beginning use **11:xx AM, 12:xx PM or
1:xx PM**; afternoon/evening columns are PM. Daily ordering validates that convention
and rejects inconsistencies. Canonical import data is then 24-hour `HH:MM`; printed
values, including quotation marks, remain in separate `Published ...` columns and
in the original binary PDF provenance.

The second-Jumu’ah footer announces **Khutbah** start times, not confirmed
additional Jamaat times. When its explicit clock time matches the inspected
pattern, it is preserved as Friday-only **Second Jumu’ah khutbah** source
metadata and shown as a separate dashboard note. It is **never** an extra
congregation event. Fajr's separate **Ends at sunrise** display uses the
published Sunrise column, not a calculated dawn interval. The calendar's
printed Hijri days and Ramadan notes remain subject to announcement/moonsighting:
they do not activate Ramadan. There is no published Taraweeh timestamp.
On Fridays Dhuhr Jamaat is absent while Jumu’ah is present; on other days
Jumu’ah is absent. These intentional missing fields remain unavailable.

Original synthetic fixtures (`mosque_a_synthetic_2026.pdf`, its golden CSV, and
`mosque_a_generate.py`) reflect the identified structure with fictional values. They are
MIT-licensed; the user-uploaded original and its extracted text are not redistributed.
Fixture tests include leap-year coverage and rejection of changed/malformed structures.
This validates the identified layout, not every MOSQUE_A publication or arbitrary mosque PDF.

Manual import of the attachment works without external access. The user also provided
`http://mosque-a.example.org/timetables/time-table.pdf`; HTTP is not accepted by the secure URL
path. The website's live HTTPS availability and current file have not been verified.
This is separate from the verified attachment/parser support. Configuring automatic
checks requires a public working HTTPS source with the same supported layout.

### Sample table layout (`pdf_table_v1`)

Each page contains a text table with the same header:

```text
Salah Timetable
Year 2026
Date | Fajr Begin | Fajr Jamaat | Sunrise
2026-01-01 | 06:15 | 06:45 | 08:10
2026-01-02 | 06:16 | " | 08:11
```

`Salah Timetable`, `Year YYYY` and `Mosque: <name>` preambles are optional. The
visible `|` separators, `Date` header, explicit ISO dates and matching row lengths
are required. Every page needs a header and dated rows; repeated headers must be
identical. Unrecognized text and footers are rejected. The explicit year must agree
with row dates and the user's declared import year. Missing cells stay absent;
Jamaat quotation marks resolve only from a preceding explicit same-column value.

The sample fixtures in `tests/fixtures/pdf/` and their deterministic generator are
original synthetic MIT examples. They are not real published prayer timetables and
do not establish compatibility with any other mosque.

## Ramadan timetable validation

Import approval and Ramadan activation are separate decisions. A publication may
include days before Ramadan, Eid, later months or provisional Hijri labels. None
of those confirms the mosque's observed Ramadan dates.

The contributed MOSQUE_A file is May–June **2022**, not a complete current Ramadan
timetable. The Mosque B 2026 publication has a separate Ramadan page containing
thirty Ramadan rows plus a following Hijri-1 row. Both are useful regression cases
against activating every imported date. See [PDF layouts](import_review.md#supported-pdf-layouts).

### What is rejected

- Invalid PDF/CSV shape, size, encryption or unsupported layout; malformed times,
  duplicate/unordered dates, wrong declared Gregorian year and invalid column mapping.
- Known mosque-layout contradictions in headers, dates, weekdays, physical time
  cells and the tested AM/PM convention. No automatic correction is attempted.
- Ambiguous or nonexistent timezone timestamps, including DST transitions.
- Competing Ramadan source rows on active dates when no unique source is selected.
  This is checked both when saving settings and again at approval using current
  options. Approval failure retains the pending proposal and approved data.

### What review shows

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

### Remaining limits

Confirmation accepts a 1–35-day activation window to support partial periods and
manual adjustments; it does not certify a 29/30-day lunar month. Import coverage
counts are not lunar-date validation. Users must confirm observed dates themselves.

Each import is still limited to one declared Gregorian year. A publication crossing
December–January needs separate year-specific sources; native cross-year PDF
imports require further work. The supplied MOSQUE_A sample does not validate a complete
Ramadan publication. Mosque B's annual and Ramadan tables use separate explicit
layouts; neither source confirms observed Ramadan dates.
