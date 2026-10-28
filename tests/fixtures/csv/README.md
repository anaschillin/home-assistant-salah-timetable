# Synthetic CSV parsing fixtures

These three small CSV tables were authored for parser regression tests. They
contain **fictional times**, not published mosque timetables, and are covered by
the repository's MIT licence.

- `annual.csv`: intentionally unusual notes, ditto quotation marks, and multiple
  Jumu'ah values to check exact CSV token handling.
- `explicit_ampm.csv`: a deliberately small 12-hour AM/PM example.
- `ramadan.csv`: example Sehri, Iftar, and Taraweeh columns, including a
  missing entry and a leap-day boundary.

These are test data, not an accurate source of prayer times. Their provenance,
byte checksums, and redistribution classification are recorded in
[`docs/asset-provenance.json`](../../../docs/asset-provenance.json).
