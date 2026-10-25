# Prayer automations and coverage alerts

The integration supplies timestamp sensors, a [prayer calendar](calendar.md) and
five optional Home Assistant blueprints. Import a blueprint, choose the mosque's sensors and your own actions,
and save the resulting automation. No recording, notification service or speaker
credentials are bundled with the integration.

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
  automation can cause restoration to be skipped.

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
