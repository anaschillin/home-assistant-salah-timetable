# Mosque A annual synthetic fixture

The fourteen-page `mosque_a_synthetic_2026.pdf` represents cover/contact-style pages and twelve Gregorian months, with explicitly fictional values. `mosque_a_synthetic_2026.expected.csv` independently captures the test oracle without extracting from any published mosque PDF.

Run `python tests/fixtures/pdf/mosque_a_generate.py` to regenerate both. It covers the combined Dhuhr/Jumuah column, repeated Jamaat shorthand, Friday-only second-khutbah annotation, time-order checks and a deliberately wrapped or missing header. No real publisher name, website or original prayer times appear in these fixtures.

**These timings are not suitable for worship.**
