# PDF layouts and fixture provenance

Every supported layout has a bounded adapter, explicit column meanings and golden
tests. There is no OCR, fuzzy layout guessing or fallback to calculated prayer times.

| Layout ID | Tested against | Supported structure |
| --- | --- | --- |
| `nms_annual_v1` | Supplied Nuneaton Muslim Society 2026 annual calendar | Cover + contact page + twelve complete monthly tables |
| `pdf_table_v1` | Synthetic sample only | Text-based, pipe-delimited table described below |

## Nuneaton Muslim Society annual calendar (`nms_annual_v1`)

Choose **Upload a supported PDF → Nuneaton Muslim Society annual calendar (v1)**,
Annual kind and the printed year (2026 for the supplied file). Use mosque timezone
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

The second-Jumu’ah footer announces **Khutbah** start times, not confirmed additional
Jamaat times, so it supplies no congregation sensor events. The calendar's Hijri days
and Ramadan notes are explicitly subject to announcement/moonsighting: they do not
activate Ramadan. There is no published Taraweeh timestamp. On Fridays Dhuhr Jamaat
is absent while Jumu’ah is present; on other days Jumu’ah is absent. These intentional
missing fields remain unavailable.

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
