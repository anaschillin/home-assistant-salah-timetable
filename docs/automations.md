# Prayer automations and coverage alerts

Use [Prayer reminders](#guided-prayer-reminders) to configure beginning and Jamaat
alerts for one or more masjids. The [blueprints](#import-a-blueprint) also provide
manual reminders, Adhan/media playback and timetable alerts, including
[prayer completeness alerts](#prayer-completeness) for missing fields. You can use
the [prayer calendar](#prayer-calendar) or [entities](#entities-per-mosque) with
Home Assistant's standard automation triggers. Provide your own recordings,
speakers and notification destinations.

## Guided prayer reminders

**Prayer reminders** is included in the published integration. If the button is
missing, first update the installed integration to a current release, restart
Home Assistant and reload the dashboard. You can also use the
[manual blueprint setup](#import-a-blueprint) independently of the wizard.

As a Home Assistant administrator, edit the timetable card and open **Prayer reminders** below the
detail-level selection. The button is hidden in kiosk mode. If it is missing after updating,
check that you are an administrator and kiosk mode is off. The integration
registers a content-fingerprinted frontend URL to replace outdated browser
assets; see [resource troubleshooting](dashboard.md#resource-troubleshooting) for
obsolete manual resource entries. The wizard creates one normal Home
Assistant automation, without requiring individual sensor selection:

1. Select one or more masjids. This screen is skipped when only one is configured.
2. Select beginning and/or Jamaat times for each masjid. You can apply the same
   prayer choices to all selected masjids, then adjust individual selections.
3. For each masjid, enter **minutes before** the selected beginnings and Jamaat
   times. Only selected categories appear. Use a whole number from
   `0` to `180`; `10` means ten minutes before and `0` means at the published time.
   Beginning and Jamaat offsets can differ, as can each masjid's offsets.
4. Choose a name, then configure **Beginning reminders** and **Jamaat reminders**
   separately. Only selected reminder types appear. Each page has **Notifications**
   and **Sound** tabs, and keeps your choices when switching tabs or using Back.
   Choose different phones, speakers, recordings, media types and optional volumes
   for each reminder type. Each type's delivery settings apply across the selected
   masjids; advance minutes remain configurable per masjid.
   Friendly names and exact action/entity IDs appear in selection and review.
   Both tabs offer **Integration** and **Device type** filters. For example, choose
   **Companion app** for phone notification routes, or **Music Assistant** for
   Music Assistant player entities. Filters combine and only change the visible
   list: already-selected destinations remain selected and appear in review, with
   a hidden-selection count shown when appropriate.
   Device types use Home Assistant's reported class. When a phone or tablet has no
   reported type, assign its HA device or entity an explicit **Phone** or **Tablet**
   label, then reopen setup. Unclassified or conflicting labels appear under
   **Other / unknown**; hardware models are not guessed. Streaming devices follow
   their integration's reported class: Android TV/Fire TV commonly use **TV**,
   while standalone Roku players commonly use **Receiver**.
   Notification actions and notification entities are listed separately: a phone
   can appear through both routes, so choose one route per device to avoid doubles.
5. Review the masjids, selected times, offsets and destinations. Use **Back** to
   revise choices, or **Cancel** to discard the draft.
6. Choose **Finish** to save the automation, then open it to check that it is
   enabled. No automation is saved and no test notification or sound is sent
   while stepping through the wizard.

Follow the saved automation link, or open **Settings → Automations & scenes**, to
edit, disable or delete it. The wizard creates new automations; reopening it does
not edit the existing one. If replacing a blueprint reminder, disable the old
automation yourself after checking the replacement, to avoid duplicate alerts.
Existing imported Before Salah and Before Jamaat blueprint automations keep working.

**Testing delivery:** in the saved automation, expand the **Beginning reminders**
or **Jamaat reminders** Choose branch and run an individual delivery action. Running
the entire separate-delivery automation manually does not select a prayer category,
so it does not broadcast both configurations. Individual actions do not supply the
prayer trigger payload; their generated messages send an explicit test notification
in that case. Real scheduled runs use
the masjid, prayer, published time and advance minutes. For a custom title, use a
manual-test fallback such as `{{ trigger.prayer if trigger is defined and
trigger.prayer is defined else 'Prayer reminder test' }}`. Updating the integration
does not rewrite messages or titles in automations you already saved.

The reminder uses approved timetable values, including tomorrow's events when an
offset falls before midnight. Selecting Jumu’ah covers every published
congregation. Approved time changes replace pending alerts; unavailable masjids,
missing dates and omitted fields do not produce estimated reminders. Past alerts
are not replayed after setup, restart or reload. Simultaneous selected events each
run the delivery actions.

A media player must support the chosen media ID or URL and content type. Optional
playback volume changes the selected players' volume without restoring it
later. Phone notification sounds depend on the Companion app and device settings.
These reminders do not track whether you have prayed or determine the end of the
current prayer's valid time.

## Entities per mosque

Each configured mosque has one logical Home Assistant device with **27 sensors
and one read-only calendar**. Select entities by mosque and displayed name; Home
Assistant permits entity IDs to be renamed. Timestamp values are absolute
date/times interpreted in the mosque's configured timezone. Daily sensors retain
today's published instant after it passes; rolling Next sensors advance to a later
event.

| Sensor / key | Supported function |
| --- | --- |
| Fajr beginning / `fajr_begin`, Fajr Jamaat / `fajr_jamaat` | Today's published Fajr beginning and congregation. |
| Sunrise / `sunrise`, Sehri ends / `sehri_ends` | Today's published sunrise and Sehri cutoff, independently available when present. |
| Dhuhr beginning / `dhuhr_begin`, Dhuhr Jamaat / `dhuhr_jamaat` | Today's published Dhuhr beginning and congregation; Friday Jumu’ah is separate. |
| Jumu’ah / `jumuah` | Today's first published Jumu’ah congregation. The `scheduled_times` attribute includes every published congregation in order. |
| Asr beginning / `asr_begin`, Asr Jamaat / `asr_jamaat` | Today's published Asr beginning and congregation. |
| Maghrib beginning / `maghrib_begin`, Maghrib Jamaat / `maghrib_jamaat` | Today's published Maghrib beginning and congregation, without equating the two. |
| Isha beginning / `isha_begin`, Isha Jamaat / `isha_jamaat` | Today's published Isha beginning and congregation. |
| Istewa / `istewa`, Iftar / `iftar`, Taraweeh / `taraweeh` | Today's effective values when published; active Ramadan alone permits the documented Maghrib-to-Iftar fallback. Taraweeh text is not a timestamp. |
| Next Salah / `next_salah` | Next of the five daily beginnings, from today or tomorrow. |
| Next Jamaat / `next_jamaat` | Next published congregation, including each Jumu’ah congregation, from today or tomorrow. |
| Previous Jamaat / `previous_jamaat` | Most recent congregation from yesterday or today. |
| Next Sehri / `next_sehri`, Next Iftar / `next_iftar` | Next matching event from today/tomorrow whose target date has active Ramadan. |
| Ramadan status / `ramadan_status` | `active` or `inactive`, from the saved activation settings. |
| Taraweeh status / `taraweeh_status` | `inactive`, `scheduled`, or `after_isha_jamaat`; the last state supplies the display text, not an inferred time. |
| Source status / `source_status` | Diagnostic summary of URL checks and pending approval; see [source states and cadence](import_review.md#when-data-updates). |
| Timetable coverage / `coverage_status` | Diagnostic summary of consecutive effective approved dates; [states and attributes](#read-timetable-coverage) below. |
| Prayer completeness / `completeness_status` | Field-level completeness of approved effective timetables; [details](#prayer-completeness) below. |
| Prayer timetable / `dashboard` | Mosque-local date plus approved yesterday/today/tomorrow rows, event selections and display/status attributes for the bundled card. Since v3.5.0, the bundled status widgets use sanitised `timetable_health` coverage/completeness/source summaries and `config_entry_id` for setup links; staged prayer values remain excluded. |
| Prayer calendar | Read-only approved prayer events, as described [below](#prayer-calendar). It omits Istewa and untimed Taraweeh. |

**Previous Jamaat** is disabled by default for new registrations; the card uses
the same event from **Prayer timetable**, and no bundled blueprint needs the
standalone sensor. Enable it under **Settings → Devices & services → Entities →
Previous Jamaat → Settings** if needed. Other sensors and the calendar are enabled
by default, and upgrades retain existing preferences. Keep **Prayer timetable**
enabled for the card.

The sixteen daily timestamp sensors expose `timetable_date` and `scheduled_times`
when an effective daily row exists. The five rolling event sensors expose `prayer`
and `field` when a matching event exists.
Missing dates or fields make the affected timestamp sensor unavailable; they
never reuse another date's time. Ramadan and Taraweeh status describe activation
even when a date has no published prayer values.

The guided reminder automation uses the integration's prayer-time trigger to
follow approved timetable changes. For other policies, use Home Assistant's
standard triggers or the blueprints below. Import and source management use the
mosque's **Configure** menu.

## Import a blueprint

For new beginning or Jamaat reminders, prefer the [guided setup](#guided-prayer-reminders).
The separate reminder blueprints remain available for existing installations and
manual automation policies. They are not removed or automatically migrated.

Open **Settings → Automations & scenes → Blueprints → Import blueprint** and paste
one of these GitHub URLs:

- [Adhan playback](https://github.com/anaschillin/home-assistant-salah-timetable/blob/main/blueprints/automation/salah_timetable/adhan.yaml)
- [Pause and resume media](https://github.com/anaschillin/home-assistant-salah-timetable/blob/main/blueprints/automation/salah_timetable/pause_resume_media.yaml)
- [Before Salah reminder](https://github.com/anaschillin/home-assistant-salah-timetable/blob/main/blueprints/automation/salah_timetable/salah_reminder.yaml)
- [Before Jamaat reminder](https://github.com/anaschillin/home-assistant-salah-timetable/blob/main/blueprints/automation/salah_timetable/jamaat_reminder.yaml)
- [Sehri reminder](https://github.com/anaschillin/home-assistant-salah-timetable/blob/main/blueprints/automation/salah_timetable/sehri_reminder.yaml)
- [Timetable health alert](https://github.com/anaschillin/home-assistant-salah-timetable/blob/main/blueprints/automation/salah_timetable/timetable_health_alert.yaml)
- [Prayer completeness alert](https://github.com/anaschillin/home-assistant-salah-timetable/blob/main/blueprints/automation/salah_timetable/prayer_completeness_alert.yaml)

Choose **Create automation**, select sensors for one mosque and configure the
blueprint's inputs, including your actions where offered. Create a separate
automation for another mosque. Blueprints update separately from
the integration; reimport changed blueprints and review their inputs.

## Select the right timestamp

| Blueprint | Sensor/input | Behavior |
| --- | --- | --- |
| Adhan playback | Daily Beginning sensors, selected media players and your recording | Plays at each enabled published beginning, with optional Fajr audio, per-prayer volume, quiet hours and conservative volume restoration. |
| Pause and resume media | One daily Beginning sensor, a later published anchor and selected media players | Pauses players currently playing; resumes unchanged players after the anchor plus an explicit user-selected delay. |
| Before Salah | Next Salah and a negative minute offset | Runs chosen notification and/or sound actions before the next published beginning. `prayer` and `scheduled_time` are available. |
| Before Jamaat | Next Jamaat and a negative minute offset | Schedules each successive congregation, including multiple Jumu’ah times. Action variables include `prayer` and `scheduled_time`. |
| Sehri | Next Sehri and a negative minute offset | Uses the target event's active Ramadan date, so an offset before midnight can precede the first confirmed fast. `scheduled_time` is available to actions. |
| Timetable health | Timetable coverage and Source status for the same mosque | Runs selected actions on a new missing/expiring coverage state or a transition into pending review. |
| Prayer completeness | Prayer completeness sensor | Runs selected actions when required fields become missing today or tomorrow. |

For Adhan, select daily beginning entities rather than Next Salah. Check the names:
the timestamp selector cannot determine your intended prayer. The recording must
be reachable by the selected speakers. Omitted prayer times are not estimated.

Time triggers must be loaded before their event or offset. Unknown or unavailable
values do not schedule actions, and past events are not replayed after startup or
reload. Changing an approved timestamp replaces its pending trigger. Daily beginning
entities become available on their local date, so use the rolling Next Salah, Next Jamaat or
Next Sehri reminders for an offset that may fall before that date.

## Before Salah notifications and sounds

For the manual blueprint path, import **Before Salah reminder**, select your
mosque's **Next Salah** sensor,
and set **Reminder offset** to `-10` for ten minutes before each next beginning
(range: 1–180 minutes before). Under **Reminder actions**, add a Companion app
notification action, a media player **Play media** action with your chosen sound,
or both. Add more actions for other devices or notification groups supported by
Home Assistant. Sound playback requires a compatible player and reachable media;
phone notification sounds depend on the Companion app and device settings.

For example, a Companion app action can use:

```yaml
action: notify.mobile_app_your_phone
data:
  title: Salah reminder
  message: "{{ prayer | title }} begins at {{ as_local(as_datetime(scheduled_time)).strftime('%H:%M') }}."
```

Replace the action name with your registered notification action. The variables
refer to the upcoming prayer. This can prompt users who have delayed praying,
but it does not know whether you have prayed and does not establish the end of
the current prayer's valid time. In particular, the next Salah beginning must not
be treated as a universal prayer deadline. Create separate automations if you
want several advance reminders with different offsets.

## Adhan playback controls

Select the ordinary recording, prayer-beginning sensors and media players.
Optional controls:

- **Disabled prayer beginnings** skips selected triggers without changing the timetable.
- Expand **Fajr recording and per-prayer volume** to identify the daily Beginning
  sensor for each override. Keep that sensor in **Prayer beginning sensors** as
  well: the override slots do not add triggers. Enable the separate Fajr recording
  and choose your own media; an empty override uses the ordinary recording.
- Enable **Set playback volume** to use the global volume. Enable **Use per-prayer
  volumes** for the identified sensor slots; other selected beginnings retain the
  global volume. No volume is changed when **Set playback volume** is off.
- **Quiet hours** can use the Home Assistant timezone, including its daylight-saving
  changes, or UTC. Set HA's timezone under **Settings → System → General**; it can
  differ from the mosque timezone. The window includes its start and excludes its
  end, may cross midnight, and is disabled when start and end are equal.
- **Restore previous volume** allows up to five seconds for the player to acknowledge
  playback, then waits the selected number of seconds before attempting restoration.
  This delay is a playback preference. It does not describe the prayer's
  duration. Restoration requires a previously known volume, the volume still set by
  this operation and unchanged playback ownership/content. Manual changes or another
  automation can cause restoration to be skipped. Intervening reported state or
  attribute changes also skip restoration, even if the player later returns to the
  same volume and recording.

Unavailable or unknown players are skipped. Test your speakers: player support,
network latency and missing action context can prevent restoration. The automation
allows one active run and ignores triggers while restoration is pending, so choose a
delay shorter than the interval between selected beginnings. Disabling the automation
or reloading changed settings cancels restoration; reloading unchanged automation
configuration on the supported HA version retains its active run.

## Pause and resume media

Create a separate automation for each prayer or policy. Choose its daily
**Beginning** sensor, a later **published resume anchor** such as that prayer's
Jamaat sensor, and your desired delay after it. The anchor is captured at the start;
the delay is your preference, not an inferred prayer ending.

The operation is skipped if the anchor is missing, invalid or earlier than the
beginning, or if the anchor plus delay has already passed. Only selected players
currently **playing** are paused.
Automatic resume requires the player to report this operation's pause context and
unchanged content, application, context and last-update time at the resume instant.
A manual change, another automation or an unsupported context report prevents
resumption; resume the player manually when appropriate.

Each automation permits one active window and ignores overlapping triggers. A
separate automation skips a player already paused by the first; avoid competing
policies on one speaker. Disabling, restarting or reloading changed settings cancels
pending resumption, leaving players under manual control. An incremental HA reload
can retain unchanged automations; turn one off to cancel explicitly. There is no
catch-up playback on startup.

## Prayer completeness

The separate diagnostic **Prayer completeness** sensor checks each mosque's
required published fields. Select them under **Configure → Mosque settings**.
The five daily Salah beginnings are required by default; optional Jamaat and
Sunrise fields may be selected if a mosque consistently publishes them.
Jumu’ah congregation is not treated as a substitute for Dhuhr beginning.

The state describes **today**: `not_configured` (no approved source),
`missing_today` (no effective row), `partial` (required fields missing)
or `complete` (all required fields are published today).
Attributes include `required_fields`, `missing_today`,
`missing_tomorrow`, `complete_days_remaining` (future consecutive dates,
excluding today), `first_incomplete_date` and `unresolved_date`.
Tomorrow's omissions do not change today's state. Future ambiguous sources
are not treated as complete. Only approved effective sources count, including
explicitly active Ramadan overrides.

To set up a completeness alert:

1. [Import the Prayer completeness alert blueprint](#import-a-blueprint) and choose **Create automation**.
2. Select the mosque's **Prayer completeness** sensor. Choose today, tomorrow or both (both are enabled by default).
3. Add your notification or other actions and save the automation.

The alert runs when a field is added to the corresponding missing-fields list.
Unchanged or removal-only lists do not repeat it, and existing gaps are not replayed
on startup or recovery from unknown/unavailable. A resolved field that later becomes
missing can alert again.

The actions can use `alert_kind` (`missing_today` or `missing_tomorrow`),
`missing_fields` (the current list), `newly_missing_fields` (the fields just
added), and `required_fields`. The blueprint queues runs and does not change
the timetable. The existing **Timetable coverage** sensor and timetable-health
blueprint retain their date-based meaning.

## Read timetable coverage

The diagnostic **Timetable coverage** sensor counts consecutive effective approved
dates from mosque-local today, stopping at the first gap. A partial row with at
least one published field counts as a date; this does not promise every prayer is
available. Pending imports never extend approved coverage.

| State | Meaning |
| --- | --- |
| `not_configured` | No approved timetable is stored. |
| `missing_today` | No effective published values exist for today. |
| `missing_tomorrow` | Today is covered but tomorrow is not. |
| `expiring` | Tomorrow is covered but at most seven future consecutive dates remain. |
| `covered` | More than seven future consecutive dates remain. |

Attributes include `today_available`, `tomorrow_available`, `available_through`,
`days_remaining` (excluding today), and `warning_days` (seven). Coverage crosses
calendar years when approved sources join without a gap. Ramadan-only dates count
only when the existing confirmed/manual settings make them active.

A future source ambiguity beyond the current prayer-event horizon stops coverage
conservatively. `unresolved_date` identifies that first uncertain future date;
it does not claim the date is unpublished. Review the conflicting sources before
that date; for a Ramadan conflict, select the correct source in mosque settings. Valid current prayer values remain available;
ambiguity in today's/tomorrow's actual event data still requires correction.

## Alert behavior

The health blueprint exposes `alert_kind`, `days_remaining`, `available_through`
and `pending_review` to your actions. Ordinary timestamp/attribute refreshes do not
repeat an unchanged warning. Recovery followed by a new warning can alert again.
Existing warnings when the automation is enabled and restoration from unknown or
unavailable are not replayed. An initial unconfigured mosque is not a coverage
warning. The blueprint never approves/rejects an import or changes stored values.

## Prayer calendar

Each mosque exposes one read-only **Prayer calendar** alongside its timestamp
sensors. Add that entity to a Home Assistant calendar card, use **Calendar: Get
events**, or select it in an automation's calendar trigger. Entity IDs can be
renamed in Home Assistant; choose the entity belonging to the intended mosque.

The calendar reads approved, explicitly dated effective records. Pending imports
never appear. It includes published daily prayer beginnings and Jamaat, Sunrise,
each published Jumu’ah congregation, and active-Ramadan Sehri, Iftar and explicitly
timed Taraweeh. It applies the same approved Ramadan overrides as the sensors.
During active Ramadan, effective Iftar can use the documented Maghrib-beginning
fallback when no separate Iftar time is published. Taraweeh has no timed event
when the publication only supports the “After Isha Jamaat” display.

Every event has an exact published **start instant** and a 60-second **calendar
presentation interval** (the exclusive end is one minute after the start). This is
solely for Home Assistant calendar display and start/end trigger compatibility:
it is **not** a prayer, Jamaat, Sehri or Iftar duration. The calendar entity briefly
shows `on` during that minute, even though prayer and Jamaat times remain exact
instants. A beginning and Jamaat are separate events, even if their starts match.
No missing published time is invented. Missing dates stay empty. Future approved
dates, including a later year, remain queryable without reusing today's values.
The calendar's next event can therefore be beyond tomorrow, while the
next-prayer sensors retain their documented yesterday/today/tomorrow horizon.

Event instants use the mosque's timezone. Home Assistant's API serializes them
in its configured timezone, and the frontend displays them in the viewer's timezone. Invalid DST gaps or
folds are rejected during normal import/timezone validation. An unresolved source
conflict in a queried date produces an error requiring source/settings review;
the calendar never silently chooses between conflicting timetables. Queries must
use timezone-aware timestamps, cover at most 366 local dates, and use an exclusive
end boundary. Queries include events that *overlap* their range, even when an
event began in the preceding minute or the previous local calendar day.

Event UIDs are stable for the same mosque, timetable date, event field and absolute
instant. Changed approved times change the affected UIDs. Approval updates the
calendar; options changes reload it. The calendar provides no event creation,
editing or deletion actions: change the underlying approved source through the
integration's normal review flow.

### Calendar-trigger example

This example notifies five minutes before each calendar event named **Fajr
beginning**. Replace the entity and notification action with your own. It does not
require a YAML timestamp sensor.

```yaml
alias: Fajr calendar reminder
triggers:
  - trigger: calendar
    entity_id: calendar.your_mosque_prayer_calendar
    event: start
    offset: "-00:05:00"
conditions:
  - condition: template
    value_template: "{{ trigger.calendar_event.summary == 'Fajr beginning' }}"
actions:
  - action: persistent_notification.create
    data:
      title: Fajr reminder
      message: Fajr begins in five minutes.
mode: queued
```

Use a **start** trigger for the published prayer/Jamaat instant. An **end**
trigger fires 60 seconds later for calendar presentation purposes only; it must
not be interpreted as the end of prayer or congregation. Home Assistant fetches
calendar events periodically, so load the automation before its event and offset.
Recently approved or changed events near their trigger time may not be fetched
in time. Past triggers are not replayed after startup/reload. Use the
[guided reminders](#guided-prayer-reminders) for approved prayer-time alerts, or the
[timestamp blueprints](#import-a-blueprint) for manual playback and reminder policies.

