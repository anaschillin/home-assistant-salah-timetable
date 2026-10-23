# Dashboard card

The **Salah Timetable** card is bundled with the integration. It uses the mosque's
**Prayer timetable** sensor and requires no separate card download, Card Mod,
template sensors or YAML configuration.

## Add the card

1. Install/restart the integration, configure a mosque and approve a timetable.
2. Open a dashboard, choose **Edit dashboard → Add card**, and select
   **Salah Timetable**. Reload the browser page if a newly installed card is absent.
3. In the graphical editor, choose that mosque's **Prayer timetable** sensor. Its
   entity ID typically ends in `_prayer_timetable`; HA permits users to rename it.
   Individual beginning/Jamaat sensors do not contain the full card data.
4. Choose **Context aware**, **Previous Jamaat** or **Upcoming Jamaat**. Optionally
   enter a title, then save.

Create a separate card for each mosque. The integration creates one device/config
entry per mosque, and each card follows the selected entity's mosque timezone.

## What the card shows

- Mosque name and local date, or your optional title.
- Next Salah beginning with its absolute time and countdown.
- A Jamaat panel with a countdown to an upcoming event or elapsed time since a
  previous event.
- Fajr, Dhuhr, Asr, Maghrib and Isha beginning/Jamaat times. Published Friday Jumu'ah
  congregations appear in the Dhuhr row and retain their event identity.
- When Ramadan is active: Sehri and Iftar countdowns, plus published Taraweeh time
  or **After Isha Jamaat**.

The layout adapts to narrow screens and uses Home Assistant's light/dark theme
variables. Times use the configured mosque timezone, even when the browser is in
another timezone. Countdowns update locally once per second from absolute event
timestamps; they do not write Home Assistant sensor states or call services.

## Jamaat modes and boundaries

| Mode | Jamaat panel |
| --- | --- |
| Context aware (default) | Previous Jamaat before a prayer begins; upcoming Jamaat after beginning and before its congregation; previous Jamaat with elapsed time from its scheduled instant onward |
| Previous Jamaat | Most recent known congregation at or before the current instant |
| Upcoming Jamaat | Next known congregation strictly after the current instant |

Next Salah beginning is calculated independently in every mode. For example, after
Fajr beginning but before Fajr Jamaat, the card counts down to Fajr Jamaat while
showing Dhuhr as the next Salah beginning. At the exact Jamaat instant it becomes
the previous event with zero elapsed time. A congregation is a single scheduled
event, without an end time.

After Isha, the next Salah uses tomorrow's actual Fajr record. Missing tomorrow data
shows an unavailable result; the integration never repeats today's Fajr. Events are
drawn from yesterday, today and tomorrow, including year/leap-day boundaries. The
browser uses the supplied timeline for local boundary transitions while HA also
refreshes at event boundaries and local midnight.

## Ramadan controls

Use the mosque integration's **Configure → Ramadan settings**; the card reflects
these settings automatically.

**Automatic** needs both confirmed Gregorian start/end dates, inclusive, spanning
1–35 days. With no confirmed range it is inactive. **Manual on** explicitly activates
Ramadan until changed and ignores the date window; **Off** disables it. The whole-day
-3 to +3 adjustment shifts the confirmation window only. It never shifts source rows.
Clear both date fields to remove an old confirmation.

During active dates, a matching Ramadan row overrides the same annual date field by
field. Choose an explicit source if multiple Ramadan tables overlap; automatic
selection requires a unique match. An import's dates or printed Hijri dates alone
never confirm Ramadan. Missing override fields retain annual values; missing dates
never borrow another day's row.

A separately published Iftar time takes priority. Otherwise Iftar uses effective
Maghrib beginning if present. Missing published Taraweeh shows **After Isha Jamaat**;
the integration does not create a separate Taraweeh timestamp. Sehri/Iftar countdowns
use active Ramadan dates only. Original imported values remain unchanged.

## Resource troubleshooting

The integration serves versioned assets and automatically registers the card in
storage-mode Lovelace resources. With YAML-managed resources it uses HA's supported
extra-JavaScript registration without editing your YAML. A second manual resource
is normally unnecessary.

If the card remains unavailable after restarting the integration and reloading the
browser, check Home Assistant logs for resource-registration errors. As a fallback,
add this **JavaScript module** resource through **Settings → Dashboards → Resources**
(enable Advanced Mode in your HA profile if the Resources option is hidden):

```text
/salah_timetable/salah-timetable-card.js?v=0.5.0
```

Reload the page after saving. Check for obsolete or duplicate manual resources if an
old card version persists. The integration updates its own registration on upgrades;
manual fallback URLs may need their version changed to the installed version.

If the card reports a missing entity, choose the mosque's Prayer timetable sensor
again. If prayer values are unavailable, check the approved source's date coverage,
field mappings and mosque timezone. An empty mosque has no prayer times until an
import is approved. A connection warning means the card is displaying the last data
received; restore the HA connection before relying on it for changed timetable data.

For reference, the card's optional YAML representation is:

```yaml
type: custom:salah-timetable-card
entity: sensor.example_mosque_prayer_timetable
mode: context
```

The graphical editor produces this configuration. `mode` accepts `context`,
`previous` or `upcoming`; `title` is optional. The example entity ID must be replaced
with the selected mosque's actual entity ID.

## Validation limits

Backend event/flow tests, Node frontend tests and an isolated headless Chromium
harness cover the implemented behavior. The browser harness uses stand-ins for HA
elements. It has not verified installation in a live HA frontend, HACS setup or
visual rendering on real mobile/tablet devices. These remain release checks in
[Milestone 6](milestones.md#milestone-6--release-hardening).
