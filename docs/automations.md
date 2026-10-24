# Prayer automations and coverage alerts

The integration supplies timestamp sensors and four optional Home Assistant
blueprints. Import a blueprint, choose the mosque's sensors and your own actions,
and save the resulting automation. No recording, notification service or speaker
credentials are bundled with the integration.

## Import a blueprint

Open **Settings → Automations & scenes → Blueprints → Import blueprint** and paste
one of these GitHub URLs:

- [Adhan playback](https://github.com/anaschillin/home-assistant-salah-timetable/blob/main/blueprints/automation/salah_timetable/adhan.yaml)
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
| Adhan playback | Daily Beginning sensors, selected media players and your recording | Plays at each selected published beginning. Optional volume setting remains after playback. |
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
