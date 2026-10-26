# PDF layouts and fixture provenance

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
A PDF containing annual tables **and** a separate Ramadan page (Zakariyya)
is handled according to the chosen import type and never activates both.
The detected concrete parser identifier is stored with approved and
URL-update sources, so later checks do not silently change adapters.
The mapping and approval screens report recognized layout and date range.

| Layout ID | Tested against | Supported structure |
| --- | --- | --- |
| `nms_annual_v1` | Supplied Nuneaton Muslim Society 2026 annual calendar | Cover + contact page + twelve complete monthly tables |
| `nms_monthly_v1` | Maintainer-supplied NMS May–June **2022** pages | Complete consecutive monthly tables with explicit Gregorian headings |
| `zak_annual_v1` | Maintainer-supplied Zakariyya 2026 calendar | Extracts twelve complete annual tables; separate Ramadan page excluded |
| `zak_ramadan_v1` | Same publication, separate Ramadan page | Extracts only the final Ramadan table; annual tables use their own layout |
| `pdf_table_v1` | Synthetic sample only | Text-based, pipe-delimited table described below |

## Supported editions and automatic recognition

Use **Configure → Upload a supported PDF** or **Add or replace a URL source**.
Choose **Annual**, **Monthly** or **Ramadan** and the printed Gregorian year.
The integration identifies known layouts automatically and suggests their
published columns; the user must still inspect the mapping and approve.
There is no edition-specific profile picker or hard-coded mosque timezone.
All strict PDF parsers, independent fixture comparisons, limits and automatic
layout detection remain in place. Unsupported editions fail closed rather
than guessing times.

## NMS monthly pages (`nms_monthly_v1`)

Choose **Monthly**, year **2022**, and upload the matching PDF. The contributed file
named `nms ramadhan.pdf` actually contains **May and June 2022**, with 61 dates and
854 event values. Every date/value matches an independent Poppler extraction.
It is not a complete Ramadan-only publication: May 1 is printed Hijri 30, May 2
resets to Hijri 1, and June is outside Ramadan. Its moonsighting note is preserved
as document context and does not confirm any activation dates.

The adapter checks complete consecutive months in one year, exact weekdays,
recognized headings/footer, thirteen physical time cells, the known extracted
separator and month-local Jamaat ditto. Column meanings and morning/noon/evening
normalization match the annual NMS contract below. It preserves published values,
weekday and Hijri day separately. The Monthly choice stores ordinary calendar
data under its own exact date-span source. Ramadan may be selected when importing
an explicitly confirmed exact-date override source.
Selecting 2026 for this 2022 file is rejected. No Taraweeh or extra Khutbah event
is inferred. Only the inspected structure is supported.

The inspected monthly footer's explicitly printed **Second Jumu’ah khutbah**
time is preserved separately as Friday-only metadata. It is not a Jumu’ah
congregation and does not change the Dhuhr beginning or Jamaat column. An
unrecognized footer still fails validation, rather than fabricating a time.

## Zakariyya annual calendar (`zak_annual_v1`)

Choose **Annual**, year **2026**, and upload the supplied fourteen-page
`zak.pdf`. The adapter imports its twelve
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

## Zakariyya Ramadan page (`zak_ramadan_v1`)

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

## Nuneaton Muslim Society annual calendar (`nms_annual_v1`)

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

Original synthetic fixtures (`nms_synthetic_2026.pdf`, its golden CSV, and
`nms_generate.py`) reflect the identified structure with fictional values. They are
MIT-licensed; the user-uploaded original and its extracted text are not redistributed.
Fixture tests include leap-year coverage and rejection of changed/malformed structures.
This validates the identified layout, not every NMS publication or arbitrary mosque PDF.

Manual import of the attachment works without external access. The user also provided
`http://nmsuk.org/timetables/time-table.pdf`; HTTP is not accepted by the secure URL
path. The website's live HTTPS availability and current file have not been verified.
This is separate from the verified attachment/parser support. Configuring automatic
checks requires a public working HTTPS source with the same supported layout.

## Sample table layout (`pdf_table_v1`)

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
