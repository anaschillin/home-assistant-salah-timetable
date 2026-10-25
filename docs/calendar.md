# Prayer calendar

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

Every item is a single instant: its start and end are equal. A beginning and Jamaat
are separate events, even if their timestamps match. No prayer duration or missing
time is invented. Missing dates stay empty. Future approved dates, including a
later year, remain queryable without reusing today's values. The calendar's next
event can therefore be beyond tomorrow, while the next-prayer sensors retain their
documented yesterday/today/tomorrow calculation horizon.

Event instants use the mosque's timezone. Home Assistant's API serializes them
in its configured timezone, and the frontend displays them in the viewer's timezone. Invalid DST gaps or
folds are rejected during normal import/timezone validation. An unresolved source
conflict in a queried date produces an error requiring source/settings review;
the calendar never silently chooses between conflicting timetables. Queries must
use timezone-aware timestamps, cover at most 366 local dates, and use an exclusive
end boundary.

Event UIDs are stable for the same mosque, timetable date, event field and absolute
instant. Changed approved times change the affected UIDs. Approval updates the
calendar; options changes reload it. The calendar provides no event creation,
editing or deletion actions: change the underlying approved source through the
integration's normal review flow.

## Calendar-trigger example

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

Use a **start** trigger: end triggers occur at the same instant because events have
no duration. Home Assistant fetches calendar events periodically, so load the
automation before its event and offset. Recently approved or changed events near
their trigger time may not be fetched in time. Past triggers are not replayed
after startup/reload. Use the [timestamp blueprints](automations.md) for the
ready-made playback and reminder policies.
