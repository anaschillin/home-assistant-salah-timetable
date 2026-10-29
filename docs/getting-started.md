# Start using Salah Timetable

This quickstart is for Home Assistant users installing the integration for the first time. For detailed developer internals see [architecture](architecture.md), [test guide](testing.md) and [release acceptance](releasing.md).

## Install the integration

Home Assistant 2026.10.0 or later is required.

1. In HACS, choose **Custom repositories**, add `https://github.com/anaschillin/home-assistant-salah-timetable` and select **Integration**.
2. Download **Salah Timetable** and restart Home Assistant.
3. Open **Settings → Devices & services → Add integration → Salah Timetable**.
4. Enter the mosque name, a stable mosque ID and its IANA timezone (for example, `Europe/London`). Repeat with another ID for an additional mosque.

HACS custom-repository installation is distinct from inclusion in HACS's default catalogue.

## Import prayer times

1. Under **Devices & services**, open the mosque's **Configure** menu.
2. Choose **Add or replace a URL source** for a public HTTPS PDF/CSV, or use a manual PDF/CSV upload.
3. Select the printed Gregorian year and **Annual**, **Monthly** or **Ramadan** source type; map only columns that the mosque actually published.
4. Review the detected layout, dates, warnings and prayer values. Use **Compare changes before approval** when replacing approved data.
5. Choose **Approve and save timetable** to activate it, or reject it to retain existing approved data. If importing Ramadan times, confirm the Ramadan date window separately in mosque settings.

PDF imports recognise **only** [documented layouts](pdf_layouts.md). Scanned pages and unknown layouts are unsupported; CSV may be a suitable alternative. Never invent missing times.

## Add the dashboard card

1. Choose **Edit dashboard → Add card → Salah Timetable**.
2. Select the mosque's **Prayer timetable** sensor (not an individual Fajr or Dhuhr sensor).
3. Choose **Compact**, **Standard** or **Detailed** in the graphical editor.
4. If more than one mosque is configured, use **Mosques available on this card** to select which mosques appear. Separate cards and dashboards may show different mosques.

The Yesterday, Today and Tomorrow controls display approved source rows for the selected day. The calculated Hijri header is for display only; it does not activate Ramadan or change published timestamps.

For appearance, mobile layouts and language options see [Dashboard](dashboard.md). For prayer alerts and speaker playback see [Automations](automations.md).

## Common problems

| Symptom | Check |
| --- | --- |
| Salah Timetable not found in Add integration | Confirm HACS downloaded the integration to `custom_components/salah_timetable`, then restart HA |
| PDF not recognised | Compare with [supported layouts](pdf_layouts.md). Scanned/encrypted/unknown layouts fail closed; convert a legitimate published timetable to CSV when appropriate |
| URL download fails | Use a publicly accessible HTTPS URL on port 443, without credentials or private-network destinations. HTTPS redirects, types and sizes are strictly checked |
| No prayer times or countdown | Confirm import approval, correct mosque timezone and date coverage. Missing tomorrow means the next Fajr may be unavailable after Isha |
| Card missing from dashboard picker | Confirm the integration is loaded; reload the HA frontend, inspect the bundled `/salah_timetable/salah-timetable-card.js` resource, and follow [resource troubleshooting](dashboard.md#resource-troubleshooting) |
| Card shows another mosque | Set the correct **Prayer timetable** sensor and optionally restrict the per-card mosque list |
| Ramadan data not shown | Verify explicit Ramadan start/end, active mode, selected source and source date coverage; Hijri display alone is not activation |
| Changed URL source not applied | Open **Configure → Review pending import**; remote updates are staged, never automatically approved |
| Prayer automation doesn't fire | Ensure the selected timestamp entity is available *before* its event/offset, and use rolling **Next Jamaat**/**Next Sehri** for early reminders |

## When asking for support

Include the Home Assistant version, integration version, whether you installed via HACS/manual method, the selected mosque timezone, a screenshot of the problem using synthetic or redacted data, and the expected versus actual date/time. The [support policy](support.md) explains safe diagnostic sharing. Do **not** post private source URLs, security tokens, full config backups or original non-redistributable PDFs.

[Back to main README](../README.md)

## Support and compatibility policy

Salah Timetable is a community-maintained, MIT-licensed Home Assistant custom
integration. There is no guaranteed response time or paid support service.

The declared minimum Home Assistant version is 2026.10.0. Automated Python tests
use Home Assistant 2026.10.3 in the root lock, plus full pinned 2026.10.0
and 2026.10.3 compatibility lanes; the [validation record](validation.md) identifies live
versions and the scope of each check. Supported Home Assistant OS/Container systems
provide the Linux/POSIX process resource limits required for isolated PDF extraction.
Other installation methods are not part of the recorded acceptance matrix.

PDF support covers the inspected Mosque A annual and May–June 2022
monthly layouts, Mosque B Masjid's 2026 annual tables and separate Ramadan page,
and the synthetic sample layout. Other editions and layouts remain unsupported;
CSV provides the alternative for unsupported publications. Missing data remains
unavailable. The dashboard displays **Fajr ends at sunrise** only when Sunrise
is published, and MOSQUE_A second-Jumu’ah khutbah footers only as separate Friday
notes; neither is an additional congregation. Full calculated Umm al-Qura Hijri
dates can be hidden during mosque setup, later under Configure → Mosque settings,
or per card. Confirm Ramadan dates explicitly: Hijri display never activates
Ramadan. See
[PDF layouts](pdf_layouts.md) and the README for file, timezone, network and parsing
limits.

For installation and import problems, start with the [quickstart and troubleshooting guide](getting-started.md).

For bugs, open a GitHub issue with integration/HA versions, installation method,
mosque timezone, relevant source layout, expected behavior and redacted logs or
diagnostics. Describe the date/event that failed without including private source
URLs, original imported records, credentials or a full HA configuration. Diagnostics
intentionally use allowlisted counts and availability flags.

For a new PDF layout, provide a public publication URL and explain whether its
contents may be redistributed as a test fixture. Compatibility is added only after
inspection and tests; a similar-looking table is not evidence of support.

Report security issues through the process in [SECURITY.md](../SECURITY.md).
