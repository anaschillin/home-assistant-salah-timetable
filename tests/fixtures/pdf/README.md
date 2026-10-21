# PDF fixture provenance and supported sample layout

All fixture PDFs, expected values and generation code in this directory are
original synthetic examples under this repository's MIT license. They contain no
real mosque prayer times and are not evidence of compatibility with any mosque.

Run `python tests/fixtures/pdf/generate.py` to deterministically recreate fixtures.
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
