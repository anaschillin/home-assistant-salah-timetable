# PDF fixture provenance and supported sample layout

`sample_table.pdf`, `unsupported_layout.pdf` and their generator/expected CSV are
original synthetic examples under this repository's MIT license. The synthetic
NMS fixtures have their own [provenance](nms_README.md).

Two real publications were contributed by the repository maintainer. Their layout,
graphics and publisher marks are not claimed as original MIT-licensed artwork:

| File | Publisher / actual content | SHA-256 |
| --- | --- | --- |
| `nms ramadhan.pdf` | Nuneaton Muslim Society, May–June **2022** monthly calendar; 61 dates, mostly outside Ramadan | `b5c7ca73f3fd659322c292745081a499152e77b5e40f228807221f224b6c96b0` |
| `zak.pdf` | Zakariyya Jaam'e Masjid, Bolton, 2026 annual calendar plus a separate Ramadan page | `3809418e4ac386f5d0a03cbed82b6e09861e79c323af47db6be39584113ce8c1` |

The corresponding `nms_monthly_2022.expected.csv` and
`zak_ramadan_2026.expected.csv`, plus `zak_annual_2026.expected.csv`, are independent
factual-value oracles built using Poppler `pdftotext -layout`, rather than
production pypdf extraction or adapter helpers. They cover all 61/854 NMS
dates/event values and all 31/341 Zakariyya Ramadan
page dates/event values, and all 365/3,770 Zakariyya annual dates/event values.
The annual oracle uses the documented May-first date reconstruction and preserves
11:xx AM Dhuhr values; Sehri is present only February–May (120 dates). The Zakariyya
Ramadan table includes March 20, after its Ramadan rows; source coverage never confirms Ramadan activation. These fixtures are
excluded from integration release archives. The NMS monthly adapter additionally
preserves the publisher's separate second-Jumu'ah khutbah footer as Friday-only
source metadata; it does **not** add a prayer or Jamaat to these event-value counts.
Publisher permissions for repository redistribution remain part of the
maintainer's asset-provenance review.

Run `python tests/fixtures/pdf/generate.py` to deterministically recreate only the
two synthetic sample PDFs and `sample_table.expected.csv`. This generator does not
recreate the contributed publications or their independent CSV oracles.
`sample_table.pdf` is a two-page, text-based table; `sample_table.expected.csv` is
its golden extraction. `unsupported_layout.pdf` is deliberately free-form text.

The `pdf_table_v1` adapter accepts only this strict sample layout:

- Optional preamble: `Salah Timetable`, `Mosque: <name>`, `Year YYYY`.
- A visible pipe-delimited header starting `Date | ...` on every page.
- Explicit ISO-date rows with the same number of pipe-delimited cells.
- Repeated identical headers allowed; unrelated text/footer lines rejected.
- Empty published values remain blank. Quotation marks are passed unchanged to
  the existing CSV parser for explicit same-column Jamaat ditto resolution.

This adapter performs no OCR and does not attempt to infer unknown PDF layouts.
