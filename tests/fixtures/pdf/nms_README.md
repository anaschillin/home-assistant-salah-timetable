# NMS adapter fixture provenance

`nms_synthetic_2026.pdf`, its golden CSV and `nms_generate.py` are original synthetic
MIT-licensed test data. Times are fictional and must never be used for prayer.
The public NMS name/URL identify the inspected document signature; no published
calendar graphics, contact details, or source PDF are redistributed here.

The fourteen-page fixture models the inspected Nuneaton Muslim Society 2026
structure: cover/contact pages, twelve explicit month/year pages, thirteen physical
time columns, a combined Dhuhr/Jumu'ah column, and repeated Jamaat quotation cells.
The golden CSV is generated directly from explicit fictional 24-hour source data,
independently of the adapter. It includes a pre-noon 11:xx column, noon 12:xx,
afternoon 1:xx, weekend Isha changes and Friday column semantics. The adapter also
has separate tests for straight/curly ditto markers and real-calendar validation.

Run `python tests/fixtures/pdf/nms_generate.py` to regenerate the deterministic files.
