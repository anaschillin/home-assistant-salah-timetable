# PDF layouts and fixture provenance

A PDF's visual appearance does not establish parser compatibility. Every advertised
layout must have a bounded adapter, explicit dates/column meanings and golden tests.
There is no OCR, fuzzy layout guessing or fallback to calculated prayer times.

| Layout ID | Status | Supported structure |
| --- | --- | --- |
| `pdf_table_v1` | Tested sample only | Text-based, pipe-delimited table described below |
| NMS UK `time-table.pdf` | Not yet inspected or supported | Awaiting access to the user-provided source |

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
with row dates and the user's declared import year. Column mapping/time-format choice
then uses the same validated CSV engine. Missing cells stay absent; a Jamaat quotation
mark resolves only from its own preceding explicit source column.

Fixtures in `tests/fixtures/pdf/` are original synthetic PDFs, golden CSV and a
deterministic generator, released under this repository's MIT license. They are not
real published prayer timetables. No mosque layout compatibility follows from them.

## Adding a mosque layout

The user provided `http://nmsuk.org/timetables/time-table.pdf`. The integration accepts
HTTPS sources only; its HTTPS equivalent must be checked before use. Cloud access to
`nmsuk.org` is currently blocked, so neither the file contents nor HTTPS availability
has been validated. An environment domain allowance has been drafted. This is a
specific outstanding prerequisite, not a claim that the site or PDF is broken.

Once accessible, inspect original extraction/positions, implement a bounded adapter,
and add sanitized synthetic fixtures reflecting the layout with independently checked
expected dates and prayer values. Keep the original outside the repository unless its
redistribution license is established. Test multiple months, year boundaries, repeated
Jamaat markers and incomplete/unrecognized columns before listing it as supported.
