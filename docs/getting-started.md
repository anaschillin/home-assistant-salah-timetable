# Start using Salah Timetable

This quickstart is for Home Assistant users installing the integration for the first time. For detailed developer internals see [architecture](architecture.md), [test guide](testing.md) and [release acceptance](releasing.md).

## 1. Install the integration

Home Assistant 2026.10.0 or later is required. In HACS, select **Custom repositories**, add `https://github.com/anaschillin/home-assistant-salah-timetable`, choose **Integration**, download Salah Timetable, and restart Home Assistant.

Then open **Settings → Devices & services → Add integration → Salah Timetable**. Give the mosque a name, a stable ID and its own IANA timezone (for example `Europe/London`). A second mosque can be installed separately using another ID.

HACS custom-repository installation is distinct from inclusion in HACS's default catalogue.

## 2. Import prayer times

Open the mosque under **Devices & services → Configure**. Choose **Add or replace a URL source** for a public HTTPS PDF or CSV, or use the manual PDF/CSV upload options. Select the source year and whether its coverage is Annual, Monthly or Ramadan.

For PDF imports, the integration automatically recognises **only** the [documented layouts](pdf_layouts.md). Unknown layouts and scanned pages are not supported. CSV provides an alternative. Map only columns that were actually published; do not make up missing times.

Check the preview, dates and every prayer value. Use **Compare changes before approval** when replacing an existing timetable. Choose **Approve and save timetable** to make the data active; rejecting a proposal preserves approved data. An imported Ramadan timetable needs an explicit Ramadan confirmation in its settings.

## 3. Add the dashboard card

Choose **Edit dashboard → Add card → Salah Timetable** and select the mosque's **Prayer timetable** sensor, not an individual Fajr/Dhuhr sensor. The graphical editor offers Compact, Standard and Detailed views.

With multiple mosques, use the **Mosques available on this card** checkboxes to restrict which mosques this card shows. Multiple cards and separate dashboards can display different mosques. The Yesterday, Today and Tomorrow controls show only approved source rows for their selected day. The Hijri header is calculated for display; it never activates Ramadan or changes published timestamps.

For card appearance, mobile layouts, language options and screenshot caveats, see [dashboard](dashboard.md). For prayer alerts or speaker playback, see [automations](automations.md).

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
