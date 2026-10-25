# NMS adapter fixture provenance

`nms_synthetic_2026.pdf`, its golden CSV and `nms_generate.py` are original synthetic
MIT-licensed test data. Times are fictional and must never be used for prayer.
The public NMS name/URL identify the inspected document signature; no published
calendar graphics or source PDF are included in this synthetic fixture. The separately
contributed real `nms ramadhan.pdf` has its own attribution in [README.md](README.md).

The fourteen-page fixture models the inspected Nuneaton Muslim Society 2026
structure: cover/contact pages, twelve explicit month/year pages, thirteen physical
time columns, a combined Dhuhr/Jumu'ah column, and repeated Jamaat quotation cells.
Each monthly page also contains a **fictional second-Jumu'ah khutbah footer**
(`4:15pm`), representing a **Friday-only published note**, not an additional
congregation. The synthetic expected CSV has a `Published Second Khutbah`
provenance column containing `16:15` on Fridays and blank on other days;
the canonical prayer/Jamaat columns and event counts are unchanged.

The golden CSV is generated directly from explicit fictional 24-hour source data,
independently of the adapter. It includes a pre-noon 11:xx column, noon 12:xx,
afternoon 1:xx, weekend Isha changes and Friday column semantics. The adapter has
separate tests for straight/curly ditto markers, real-calendar validation and
separating the khutbah note from Jumu'ah congregations.

Run `python tests/fixtures/pdf/nms_generate.py` to regenerate the deterministic files.
