# Support and compatibility

Salah Timetable is a community-maintained, MIT-licensed Home Assistant custom
integration. There is no guaranteed response time or paid support service.

The declared minimum Home Assistant version is 2026.10.0. Automated Python tests
use Home Assistant 2026.10.2; the [validation record](validation.md) identifies live
versions and the scope of each check. Supported Home Assistant OS/Container systems
provide the Linux/POSIX process resource limits required for isolated PDF extraction.
Other installation methods are not part of the recorded acceptance matrix.

PDF support covers the inspected Nuneaton Muslim Society annual and May–June 2022
monthly layouts, Zakariyya Masjid's 2026 annual tables and separate Ramadan page,
and the synthetic sample layout. Other editions and layouts remain unsupported;
CSV provides the alternative for unsupported publications. Missing data remains
unavailable. The dashboard displays **Fajr ends at sunrise** only when Sunrise
is published, and NMS second-Jumu’ah khutbah footers only as separate Friday
notes; neither is an additional congregation. Full calculated Umm al-Qura Hijri
dates can be hidden during mosque setup, later under Configure → Mosque settings,
or per card. Confirm Ramadan dates explicitly: Hijri display never activates
Ramadan. See
[PDF layouts](pdf_layouts.md) and the README for file, timezone, network and parsing
limits.

For bugs, open a GitHub issue with integration/HA versions, installation method,
mosque timezone, relevant source layout, expected behavior and redacted logs or
diagnostics. Describe the date/event that failed without including private source
URLs, original imported records, credentials or a full HA configuration. Diagnostics
intentionally use allowlisted counts and availability flags.

For a new PDF layout, provide a public publication URL and explain whether its
contents may be redistributed as a test fixture. Compatibility is added only after
inspection and tests; a similar-looking table is not evidence of support.

Report security issues through the process in [SECURITY.md](../SECURITY.md).
