# Prayer automations and coverage alerts

The integration supplies timestamp sensors, a [prayer calendar](automations.md#prayer-calendar) and
five optional Home Assistant blueprints. Import a blueprint, choose the mosque's sensors and your own actions,
and save the resulting automation. No recording, notification service or speaker
credentials are bundled with the integration.

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
| Prayer timetable / `dashboard` | Mosque-local date plus approved yesterday/today/tomorrow rows, event selections and display/status attributes for the bundled card. |
| Prayer calendar | Read-only approved prayer events, as described [below](#prayer-calendar). It omits Istewa and untimed Taraweeh. |

**Previous Jamaat** is disabled by default for new entity registrations: the
bundled card reads the same event from **Prayer timetable**, and no bundled
blueprint requires the standalone sensor. Enable it in **Settings → Devices &
services → Entities → Previous Jamaat → Settings** if needed. The other sensors
and calendar are enabled by default. Existing enabled/disabled entity preferences
are retained during upgrades. Keep **Prayer timetable** enabled for the card and
choose the needed timestamp/status sensors for your automations.

All sixteen daily timestamp sensors have `timetable_date` and `scheduled_times`
attributes. All five rolling event sensors have `prayer` and `field` attributes.
Missing dates or fields make the affected timestamp sensor unavailable; they
never reuse another date's time. Ramadan and Taraweeh status describe activation
even when a date has no published prayer values. The Prayer timetable sensor is
the bundled card's data source; choose it when adding the card.

The integration provides no integration-owned actions, conditions or automation
trigger platform. Use Home Assistant's standard time/calendar/state triggers with
these entities, or the optional blueprints below. Importing, approval and source
management use the mosque's **Configure** menu.

## Import a blueprint

Open **Settings → Automations & scenes → Blueprints → Import blueprint** and paste
one of these GitHub URLs:

- [Adhan playback](https://github.com/anaschillin/home-assistant-salah-timetable/blob/main/blueprints/automation/salah_timetable/adhan.yaml)
- [Pause and resume media](https://github.com/anaschillin/home-assistant-salah-timetable/blob/main/blueprints/automation/salah_timetable/pause_resume_media.yaml)
- [Before Jamaat reminder](https://github.com/anaschillin/home-assistant-salah-timetable/blob/main/blueprints/automation/salah_timetable/jamaat_reminder.yaml)
- [Sehri reminder](https://github.com/anaschillin/home-assistant-salah-timetable/blob/main/blueprints/automation/salah_timetable/sehri_reminder.yaml)
- [Timetable health alert](https://github.com/anaschillin/home-assistant-salah-timetable/blob/main/blueprints/automation/salah_timetable/timetable_health_alert.yaml)

Choose **Create automation** for the imported blueprint. Use the sensors belonging
to one mosque; create separate automations for other mosques. Home Assistant imports
blueprints separately from HACS integration updates. Reimport a changed blueprint
and review its inputs before relying on the update.

## Select the right timestamp

| Blueprint | Sensor/input | Behavior |
| --- | --- | --- |
| Adhan playback | Daily Beginning sensors, selected media players and your recording | Plays at each enabled published beginning, with optional Fajr audio, per-prayer volume, quiet hours and conservative volume restoration. |
| Pause and resume media | One daily Beginning sensor, a later published anchor and selected media players | Pauses players currently playing; resumes unchanged players after the anchor plus an explicit user-selected delay. |
| Before Jamaat | Next Jamaat and a negative minute offset | Schedules each successive congregation, including multiple Jumu’ah times. Action variables include `prayer` and `scheduled_time`. |
| Sehri | Next Sehri and a negative minute offset | Uses the target event's active Ramadan date, so an offset before midnight can precede the first confirmed fast. `scheduled_time` is available to actions. |
| Timetable health | Timetable coverage and Source status for the same mosque | Runs selected actions on a new missing/expiring coverage state or a transition into pending review. |

For Adhan, select daily beginning entities rather than Next Salah. The form filters
timestamp sensors, so check their names: the selector cannot determine your intended
prayer. The media recording must be reachable by the selected speakers. No daily
prayer value is estimated when a publication omits it.

Time triggers must be loaded before their event/offset instant. Unknown or
unavailable values do not schedule actions. Changing an approved timestamp replaces
its pending trigger; a time already passed is not replayed after reload/startup.
Daily beginning entities become available on their local timetable date, so they
cannot promise reminders before that date. The two reminder blueprints use the
rolling Next Jamaat/Next Sehri events instead.

## Adhan playback controls

The ordinary recording and selected beginnings remain the only required prayer
inputs. Extra controls are optional:

- **Disabled prayer beginnings** skips selected sensor triggers without changing
  the timetable or the other selected beginnings.
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

Unavailable/unknown players are skipped. Player support and network latency affect
playback; conservative ownership checks can leave the chosen volume in place when
a player does not report the action context. Check your speakers before relying on
restoration. This automation permits one active run, so a trigger arriving while
restoration is pending is ignored. Choose a restoration delay shorter than the
interval between your selected beginnings. Disabling the automation or reloading a
changed automation cancels a pending restoration. On the supported HA version,
reloading unchanged automation configuration preserves its active run and restoration.

## Pause and resume media

Create a separate automation for each prayer or policy. Choose its daily
**Beginning** sensor and a **published resume anchor** later than that beginning,
such as the same prayer's daily Jamaat sensor. Set the desired delay after the
anchor. The published anchor is captured when the operation starts; the delay is
your policy and is never an inferred prayer ending.

The automation checks the anchor before pausing. Missing, invalid or earlier anchors,
or a resume instant already passed, skip the whole operation. Only selected players
currently **playing** are paused. Already paused, idle, unavailable and unknown
players are left alone. It claims only players whose resulting pause reports this
operation's context and unchanged content. At the resume instant a claimed player
must still be paused with the same content, application, context and last-update
time. A manual change, another automation or an unsupported context report prevents
automatic resumption. Resume those players manually when appropriate.

Each automation permits one active window and ignores overlapping triggers. Separate
automations do not combine or extend pause windows: a second automation skips a
player already paused by the first. Avoid competing policies on the same speaker.
Disabling, restarting or reloading changed automation settings cancels pending
resumption. Paused players then remain under manual control. An incremental HA
reload can retain an unchanged automation and its pending resumption; turn it off
to cancel explicitly. There is no catch-up playback on startup.

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

The existing **Timetable coverage** sensor and timetable-health blueprint
retain their date-based meaning. Completeness alerts are deferred until
the optional blueprint behaviour is separately reviewed.

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
[timestamp blueprints](automations.md) for ready-made playback and reminder policies.
