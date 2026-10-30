# Dashboard card

Current integration version: <!-- docs:version -->0.9.19<!-- /docs:version -->.

The **Salah Timetable** card is bundled with the integration. It uses the mosque's
**Prayer timetable** sensor and requires no separate card download, Card Mod,
template sensors or YAML configuration.

## Current layout

The card provides current-day and adjacent-day views, a multi-mosque header selector and keyboard-focus restoration after refreshes. Inspect the installed card or the frontend visual checks for its current appearance.

## Add the card

1. Install the integration, configure a mosque and approve a timetable.
2. Choose **Edit dashboard → Add card → Salah Timetable**.
3. Choose a **Prayer timetable** sensor in the graphical editor.
4. Select **Card detail**: **Compact**, **Standard** (default) or **Detailed**.
   Set optional title, language, time format and visibility preferences, then save.

When two or more mosque timetable sensors are available, the editor shows
**Mosques available on this card** checkboxes. By default all mosques are enabled
for backwards compatibility. Uncheck mosques to exclude them from this card;
at least one mosque must remain enabled. The primary **Prayer timetable** selection
controls which mosque appears first, and is kept within the enabled set.

When multiple mosques are enabled, a native selector in the header replaces
the duplicated mosque name and wide tab strip. With one enabled mosque, the
header displays a plain title. An optional custom title replaces the primary
mosque's selector label. Switching mosques resets day navigation to Today without
changing Home Assistant entity states. Each card has independent selections:
add multiple cards to one dashboard, restrict each to one mosque, or use separate
dashboards. Existing cards without `mosque_entities` continue to show all
discovered mosques, including newly added ones.

## Day navigation

The **Yesterday / Today / Tomorrow** controls sit in a slim footer inside the
timetable frame, rather than above the prayer summaries. Today is selected initially.
The header's Gregorian **and calculated Hijri dates**, plus the contextual
Hijri month description, update with the selected day whenever those fields
are visible (Standard/Detailed; Compact hides those dates). The timetable does not repeat
the Gregorian date when it is already in the header; a date label remains if
the Gregorian header is disabled or the card is in Compact mode.
All three views share the same table styling, labels, time formatting and responsive
layout. Yesterday and Tomorrow hide **both** prayer summary cards, live countdowns,
current-prayer highlighting, and today's Ramadan/status sections. They show only
the selected day's actual approved beginning and Jamaat timetable. This also
applies when Compact is selected: its adjacent-day views show the full table.
On a date with no approved times, the footer stays visible beneath an unavailable
message so users can return to Today.

The backend supplies independent published rows for the three local dates using
its already-resolved effective timetables. Missing approved rows display
**No approved timetable is available for this date** rather than copying today's
times. Date selection does not modify Home Assistant sensor state or stored data.

## Card detail levels

| Level | Today's display |
| --- | --- |
| Compact | Next Salah countdown with beginning and Jamaat, plus context-aware upcoming/previous Jamaat; active Ramadan details when enabled |
| Standard (default) | Both matching prayer cards, full timetable, Hijri date (if enabled), and active Ramadan details |
| Detailed | Standard plus published Fajr sunrise/end and second Friday khutbah (if present) |

**Next Salah** always means the next *beginning* time, even if the current
prayer's Jamaat is still upcoming. The countdown and published times from that
event's actual date appear together. **Next Jamaat** counts down while the
current prayer's congregation is still approaching; at its exact instant the
same panel becomes **Previous Jamaat** and shows elapsed time.
The mosque title, Hijri date/description, Gregorian date and both countdown
sections now live inside **one CSS-first liquid-glass summary card**. The
timetable has the **same balanced, readable glass material**: an 84–88%
theme-aware surface with a restrained gradient, frosted blur and small
specular edge highlights. This restores some visibility of the mosque photo
through both cards without returning to the earlier washed-out glass effect.
Table headings and day navigation do not add a second tint. The background photograph remains
unobscured outside the panels. There is no WebGL runtime, animated
distortion or remote dependency. Both countdown halves share **identical
transparent surfaces, padding, label typography, countdown sizing and
time-grid formatting**, separated by a fine divider. Each countdown still has its own published
beginning/Jamaat values, label and live timer. A faint **minaret silhouette** decorates Next Salah and a faint
**dome silhouette** decorates the contextual Next/Previous Jamaat countdown.
Both are inline local SVG with `aria-hidden`, carry no data and do not
represent the selected mosque. The two summaries sit side by side on most
phones/tablets, stack on very narrow cards, and collapse independently through
the card's existing visibility options. On Yesterday/Tomorrow, the shared
surface retains the mosque/date heading but hides the live countdowns.
The old context/upcoming/previous Jamaat panel selector has been removed.

Fajr end is the *published sunrise*, never a calculated estimate. Published
Jumu’ah congregations remain in Dhuhr's Jamaat row, and the separately published
second khutbah (if any) is not treated as a Jamaat. Missing times are displayed
as unavailable rather than inferred. Ramadan details are shown in all three display levels when Ramadan is active and the card's Ramadan details option is enabled.

## Timing and boundaries

Next Salah and the contextual Next/Previous Jamaat are selected independently from the published
absolute event timeline. After Isha, the next Salah uses tomorrow's actual Fajr
record; missing tomorrow data yields an unavailable countdown. Its time grid also
uses tomorrow's actual published Fajr, Jamaat and sunrise, never today's row. At a prayer
beginning boundary, the next Salah advances to the next published beginning.
Events are drawn from yesterday, today and tomorrow, including leap-year and
year-end transitions. The card updates the live countdown in the browser without
per-second Home Assistant state writes.

Today's full timetable highlights the relevant prayer and dims completed rows;
Yesterday and Tomorrow have no current-prayer highlighting. Tables retain semantic
headers, LTR-isolated numeric times, a keyboard-focusable scroll region, and
responsive handling for narrow screens.

## Language and direction

The card editor offers **Automatic (Home Assistant)**, **English** and
**العربية**. Automatic uses Arabic labels and right-to-left layout for an Arabic
Home Assistant interface, with English label fallback for other interface
languages. Supported Home Assistant regional locales are retained for date and
number formatting; choosing an explicit card language uses a matching regional
locale when available.

Enable **Bilingual prayer labels** to show both English and Arabic names, with
the selected language first. Each name carries its own language and direction;
clock values remain isolated in left-to-right order in both layouts. This applies
to known prayer names in the timetable and event panels. Custom mosque titles
remain user-supplied text. Language changes affect presentation only: prayer
keys, entity IDs, stored values and event identities stay unchanged.

The bundled card/editor supports the described language and direction options.
Additional integration translations and reviewed Arabic wording are deferred.
Automated browser checks do not establish full Arabic/RTL acceptance on physical devices.

## Dates and customization

In Standard/Detailed mode, the **primary Hijri header** uses the browser's **Umm al-Qura** calendar to
convert the mosque's Gregorian timetable date, displaying its Islamic day,
**named Hijri month** and year. The Gregorian date is a separate secondary
header field; hide it via the card's `show_gregorian_date: false` switch without
hiding Hijri. Both default to visible for existing cards.
It advances at mosque-local midnight, not sunset. The default is visible; choose
**Show full calculated Hijri date on dashboards** during initial mosque setup,
or change it later via **Configure → Mosque settings**. Older mosque entries
without a stored preference default to visible. The card editor's
`show_hijri_date` option is an additional per-card hide switch: the header is
visible only if **both** the mosque and that card permit it.
The optional −3 to +3 day adjustment changes only the displayed Hijri date. It does
not shift imported records, prayer events, Ramadan confirmation or Ramadan's separate
date adjustment. The date is labelled calculated; unsupported browsers show
**Hijri date unavailable** rather than silently substituting another calendar.

The following *card-specific* options are available in the graphical editor.
The mosque-wide Hijri preference is managed separately in the integration settings:

| YAML option | Values and default |
| --- | --- |
| `entity` | The initial/primary `sensor.*_prayer_timetable` entity on the card |
| `mosque_entities` | Optional list of enabled Prayer timetable sensor IDs; omit to show all configured mosques (legacy behaviour); requires at least one when set |
| `language` | `auto` (default), `en`, `ar`; automatic follows the HA interface language with English label fallback |
| `bilingual_prayer_labels` | `false` (default); show English and Arabic known prayer names |
| `detail_level` | `standard` (default), `compact`, `detailed` |
| `layout` | Legacy `compact` maps to Compact; `expanded` maps to Standard if no `detail_level` is saved |
| `mode` | Legacy setting ignored; no longer exposed in the editor |
| `time_format` | `24h` (default), `12h`; applies to every absolute time |
| `show_salah_countdown` | `true` |
| `show_jamaat_countdown` | `true` |
| `show_hijri_date` | `true`; further hides the mosque-enabled full Hijri date on this card |
| `show_gregorian_date` | `true`; independently displays the secondary Gregorian date |
| `show_hijri_month_info` | `true`; shows a short, non-repeating description directly beneath the visible Hijri date in the header; hidden when the Hijri date is hidden |
| `hijri_adjustment` | Whole days −3 through +3; default `0` |
| `show_ramadan_details` | `true`; controls the entire Ramadan section |
| `show_night_calculations` | `false` (default); in Standard/Detailed Today view, display night midpoint and final-third start calculated between approved Maghrib and the following day’s Fajr |
| `show_sehri_countdown` | `true`; hiding retains the displayed absolute time |
| `show_iftar_countdown` | `true`; hiding retains the displayed absolute time |
| `show_timezone_note` | `true`; controls the timezone and missing-time note |
| `show_mosque_background` | `true`; enables the full-strength bundled mosque photograph; `false` disables the image |
| `mosque_background` | `daily` (default); `none`, or a bundled mosque ID for a fixed photo |

Hiding either main countdown half removes it; the remaining half fills
the available summary width. Hiding both leaves the mosque header and
the timetable **when Standard or Detailed is selected**; Compact still
omits today's full timetable (but retains the date footer). Connection warnings and narrow-card
scrolling guidance remain available when the timezone note is hidden. Taraweeh
belongs to the Ramadan details section. Countdown durations use hours/minutes/seconds
with a day prefix when needed, independent of 12/24-hour time format.
The legacy `mode` option is accepted but ignored for all cards. The Jamaat panel automatically
switches between the upcoming congregation and the previous one.

The four **coming soon** Islamic-history settings for day events, monthly
highlights, visible sources and disputed dates are disabled in the editor until
those features are implemented. Previously saved values remain inert. The Hijri
month description is implemented separately and can be hidden with
`show_hijri_month_info: false`. The description appears only as smaller text
beneath the full Hijri date, without a duplicate heading, separate panel or
footer disclosure. It follows the **selected** Gregorian/Hijri day when browsing
Yesterday or Tomorrow, and hides when the Hijri date is hidden.

## Optional mosque photograph backgrounds

The card bundles 20 WebP photographs from free Unsplash photo pages. They
are served from the integration itself, without remote requests or an Unsplash
account. Photo backgrounds rotate once per mosque-local published date by
default and do not repeat until all 20 have appeared. Choose a fixed mosque
from **Mosque background** in the card editor, or switch off
**Show mosque background** entirely. The old background-opacity overlay and
editor option have been removed. Saved cards containing
`mosque_background_opacity` are accepted, but that obsolete value is ignored
and stripped when the configuration is normalised.

The mosque photograph fills the **available dashboard viewport height as well
as the full card width**, rather than cutting off where the Today, Yesterday or
Tomorrow timetable ends. The summary and timetable remain compact and anchored
at the top; the remaining area shows the photograph instead of a blank black
dashboard background. A short day view no longer causes the background canvas
itself to disappear halfway down the screen. On cards with content taller than
the viewport, the canvas grows naturally with the content.

The image layer also retains Today's photographic framing when switching to
adjacent-day views. Small Home Assistant width changes, such as scrollbars
appearing and disappearing, preserve its measured dimensions. Genuine device
resizes (for example tablet rotation) can reframe the image. Because this mode
uses a viewport-height **card**, placing it among other stacked dashboard cards
will reserve that vertical space in the Home Assistant layout. Use a dedicated
full-width view for the best photographic presentation. The timetable,
header and countdowns remain in an independently centred content column
(up to 1160px wide). On narrow cards and mobile screens, the content naturally
fills the available width. This creates wider photographic wings on landscape
tablets and desktops without stretching the prayer table excessively.

The photograph is shown without a global opacity tint. Liquid-glass styling
now applies only to the **summary and timetable surfaces**, with matching
backdrop blur, layered translucent gradients, subtle specular edge lighting and
a calm inset shadow. The photograph remains visible around them. The full-width
outer card has **no drop shadow**, avoiding a dark halo. Text remains crisp.
High-contrast/reduced-transparency preferences show opaque panel surfaces
and hide the photo; browsers without backdrop filtering also use opaque panels.
The Hijri date, Gregorian date and month explanation occupy separate header
rows on mobile, tablet and desktop. Photo visibility remains controlled by `show_mosque_background`.
Increased-contrast and reduced-transparency preferences hide the image and
disable glass effects.

Home Assistant determines each card's **parent column width**, and the card
cannot paint outside that column or across a sidebar. To fill a wider dashboard
canvas, place the card in a full-width section or panel view. Photographer
credit stays with the centred content and links to the original photo. See
[image credits and source links](asset-provenance.json).

These decorative backgrounds do not represent the currently configured mosque
and cannot influence prayers, mosque identity, calculations or data imports.

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
/salah_timetable/salah-timetable-card.js
```

Reload the page after saving. Check for obsolete or duplicate manual resources if an
old card version persists. The integration updates its own registration on upgrades;
for manual fallback resources, add the installed version as a cache key only if required after an upgrade. The version is shown at the top of this guide.

If the card reports a missing entity, choose the mosque's Prayer timetable sensor
again. If prayer values are unavailable, check the approved source's date coverage,
field mappings and mosque timezone. An empty mosque has no prayer times until an
import is approved. A connection warning means the card is displaying the last data
received; restore the HA connection before relying on it for changed timetable data.

For reference, the card's optional YAML representation is:

```yaml
type: custom:salah-timetable-card
entity: sensor.example_mosque_prayer_timetable
detail_level: standard
language: auto
bilingual_prayer_labels: false
time_format: 24h
show_hijri_date: true
show_gregorian_date: true
show_hijri_month_info: true
show_mosque_background: true
mosque_background: daily
hijri_adjustment: 0
```

The graphical editor can produce equivalent configuration; omitted fields use
their defaults. The legacy `mode` property is ignored and legacy `layout`
values are normalised. The retired `mosque_background_opacity` value is ignored.
`title` is optional. For multi-mosque filtering, add a nonempty `mosque_entities`
list of Prayer timetable sensor IDs. Replace the example entity ID with the
actual timetable sensor.

## Validation limits

Frontend tests cover card navigation and responsive rendering, but acceptance on real phones and tablets remains a separate [release check](releasing.md#manual-hacs-and-home-assistant-acceptance).

## Mosque photograph implementation and maintenance

**Current behaviour:** The 20 locally bundled WebP
photographs and their sources are catalogued in the integration and the
machine-readable asset inventory. See the [asset provenance inventory](asset-provenance.json) and
[display options](#optional-mosque-photograph-backgrounds).

### What the card does

- **Show mosque background** is enabled by default; users can disable it per
  card. **Mosque background** defaults to a deterministic daily rotation, or
  may be set to one of the 20 bundled images (or `none`).
- Rotation is keyed to the mosque-local published date. It cycles through the
  bundled photographs without repeating until the cycle has been exhausted.
  The photograph is decorative: it does not identify the configured mosque or
  influence its timetable, Ramadan calculations or sensors.
- The full-strength photograph is served locally. There is **no global photo
  opacity/tint overlay and no background-opacity editor control**. The removed
  `mosque_background_opacity` option is ignored and discarded during card
  configuration normalisation for older saved dashboards.
- The card covers its allocated dashboard width and at least the available
  viewport height, so Yesterday/Tomorrow do not expose an empty black canvas
  when their countdowns disappear. The inner summary and timetable remain
  centred (up to 1160px) and top-aligned. This intentionally reserves viewport
  height when other dashboard cards are stacked below.
- A consistent **CSS-first liquid-glass** style applies to both the summary
  and timetable: 84–88% HA-theme-aware surfaces, frosted blur, subdued edge
  highlights and readable text. There is no external shader or image service.
  Higher-contrast/reduced-transparency preferences disable the photo and
  use opaque panels; browsers without backdrop-filter support also receive
  opaque panels.
- Background sizing is insulated from small card-width changes caused by
  scrollbars and date-tab switching; genuine dashboard resizing may reframe
  the photograph. The card clips the image and blur rim to its rounded edge,
  and displays the attribution link.

### Asset rights and additions

The bundled images were sourced from reviewed **free Unsplash** photographs
under the applicable Unsplash License. The card does not download images or
fetch licensing metadata while running. See
[credits and source pages](asset-provenance.json) and the
[machine-readable provenance inventory](asset-provenance.json). Additional
photographs require individual attribution, source and redistribution-rights
review before bundling; a search-result licence label is insufficient.

The research alternatives remain:

- [Unsplash License](https://unsplash.com/license): use only permitted free
  photos; exclude paid/Unsplash+ items and competing standalone image libraries.
- [Wikimedia Commons reuse guidance](https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia):
  verify each image's individual rights and satisfy attribution/share-alike
  requirements where applicable.
- [Pixabay terms](https://pixabay.com/service/terms/): do not assume that every
  current free item is CC0. The project's conservative legacy-CC0 review
  requires verifiable publication **before 9 January 2019**.
- [Pexels terms](https://help.pexels.com/hc/en-us/articles/900005880463-What-are-the-Terms-and-Conditions):
  additional redistribution review is needed before bundling standalone files.

Always distinguish the Al-Qibli Mosque from the wider Al-Aqsa compound when
naming images, and never imply a pictured mosque supplies the selected prayer
times.

### Validation

The frontend visual checks verify photo layout and accessibility behaviour.
Photograph licensing and physical-device acceptance require separate review.
See [asset provenance](asset-provenance.md) and [release acceptance](releasing.md).


## Hijri month information and future history options

**Current behaviour:** The card shows an optional,
short, offline description of the **selected day's Hijri month** directly
beneath the calculated Hijri date in the mosque header. It does not repeat
the month name or create a separate history panel. The explanation updates
when switching Yesterday/Today/Tomorrow, and disappears in Compact mode
or if the full Hijri date is hidden or `show_hijri_month_info` is disabled. This feature defaults
to enabled on new and existing cards.

The four additional history options are **disabled as coming soon** in the
graphical editor. Their previously saved values have no effect; no day-event
or monthly-highlights catalogue is rendered. `history-utils.js` is an offline
research/test prototype, not a runtime dependency of the bundled card.

### Default behaviour
- Show **information about the current Hijri month** by default for new installations, using short original educational descriptions for all 12 months.
- Historical exact-day events: **off** by default.
- Month-level historical highlights: **off** by default.
- Disputed/traditional anniversaries: **off** by default and always visibly qualified if enabled.
- Show source references in the card: **off** by default, but store provenance with every record.
- **Implemented:** show month explanation as subordinate text in the header,
  only when the Hijri date is visible; no separate history section or disclosure.
- **Proposed only:** if day/month events are implemented later, show them
  without duplicating the header's month explanation. Preserve explicit
  choices to hide optional history content.

### Card-level configuration (month info live; other flags reserved)
```json
{
  "show_hijri_month_info": true,
  "show_historical_day_events": false,
  "show_historical_month_highlights": false,
  "show_historical_sources": false,
  "show_disputed_historical_dates": false
}
```

The same saved per-card settings work on tablet and mobile. The month
description is deliberately a small header subtitle, not a large new panel.
The proposed event flags are reserved for future editorial and frontend work.

### Date and editorial rules
- Use the same mosque-local Hijri date and per-card adjustment as the existing timetable header.
- A supported day event appears only on its supported Hijri day. Month-only events appear as monthly highlights, never assigned to a day.
- Keep occurrence certainty separate from precise-date certainty; no invented anniversaries.
- If several supported day events occur on one day, show a concise list or expand affordance, not duplicates.
- Do not make runtime network calls to Dorar. Original summaries, documented citations, and explicit editorial approval are required before bundling events.
- Month information should avoid asserting special religious merit for months without supporting evidence.
- Month summaries are informational, not a religious observance schedule or prayer automation.

### Acceptance criteria and current status
- **Implemented:** Month explanation defaults on, appears only beneath a
   visible Hijri date in Standard/Detailed mode, and follows day navigation
   and the per-card adjustment.
- **Implemented:** Disabling month information removes the subtitle without
   changing the date, timetable or countdowns.
- **Implemented:** The four historical-event/source/dispute options are shown
   disabled in the graphical editor; saved legacy values remain inert.
- **Not implemented:** Turning on events to show a catalogue, date-level
   citations, or monthly historical highlights. These require editorial approval
   and separate frontend acceptance.
- **Future requirement:** No exact-day event claim without date-level evidence;
   no implied religious merit where there is no sound source.
- **Implemented for month text:** All 12 educational descriptions are bundled
   offline. Historical day-event selectors remain research-only.

### Future editorial work

- Review historical event candidates independently and document pinpoint sources, disputed dates and redistribution rights.
- Add only explicitly approved event records to an optional offline catalogue; do not enable reserved history controls until their feature exists.
- Validate event selection, card rendering and Home Assistant integration before releasing any future event display.
