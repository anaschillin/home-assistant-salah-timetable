"""Remind against approved published fields, independently of dashboard sensors."""

from datetime import datetime, time, timedelta, timezone

import probatio
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_OPTIONS
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.trigger import (
    Trigger,
    TriggerActionRunner,
    TriggerConfig,
    TriggerNotTriggeredReporter,
)
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .domain.model import PrayerField

REMINDER_FIELDS = (
    PrayerField.FAJR_BEGIN,
    PrayerField.DHUHR_BEGIN,
    PrayerField.ASR_BEGIN,
    PrayerField.MAGHRIB_BEGIN,
    PrayerField.ISHA_BEGIN,
    PrayerField.FAJR_JAMAAT,
    PrayerField.DHUHR_JAMAAT,
    PrayerField.ASR_JAMAAT,
    PrayerField.MAGHRIB_JAMAAT,
    PrayerField.ISHA_JAMAAT,
    PrayerField.JUMUAH,
)
FIELD_LABELS = {
    field: field.value.replace("_", " ").title().replace("Begin", "beginning")
    for field in REMINDER_FIELDS
}
FIELD_LABELS[PrayerField.JUMUAH] = "Jumu’ah Jamaat"


def _minutes_before(value: object) -> int:
    """Reject fractional values and booleans instead of coercing them."""
    if type(value) is not int or not 0 <= value <= 180:
        raise probatio.Invalid("Minutes before must be an integer from 0 to 180")
    return value


_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_OPTIONS): {
            probatio.Required("mosque_id"): cv.string,
            probatio.Required("fields"): probatio.All(
                [probatio.In([field.value for field in REMINDER_FIELDS])],
                probatio.Length(min=1, max=len(REMINDER_FIELDS)),
            ),
            probatio.Required("minutes_before"): _minutes_before,
        }
    }
)


class PrayerTimeTrigger(Trigger):
    """Schedule every selected published occurrence and replace changed timers."""

    @classmethod
    async def async_validate_config(
        cls, hass: HomeAssistant, config: ConfigType
    ) -> ConfigType:
        """Validate fields and a nonnegative number of minutes before the event."""
        return _SCHEMA(config)

    def __init__(self, hass: HomeAssistant, config: TriggerConfig) -> None:
        super().__init__(hass, config)
        assert config.options is not None
        self._options = config.options

    async def async_attach_runner(
        self,
        run_action: TriggerActionRunner,
        did_not_trigger: TriggerNotTriggeredReporter | None = None,
    ) -> CALLBACK_TYPE:
        """Follow coordinator availability and reloads, including startup races."""
        entry = self._hass.config_entries.async_get_entry(self._options["mosque_id"])
        if entry is None or entry.domain != DOMAIN or not entry.unique_id:
            raise HomeAssistantError("Select a configured Salah Timetable masjid")
        fields = tuple(dict.fromkeys(PrayerField(f) for f in self._options["fields"]))
        minutes = self._options["minutes_before"]
        offset = timedelta(minutes=minutes)
        timers: dict[tuple[PrayerField, datetime], tuple[object, CALLBACK_TYPE]] = {}
        unsubscribe_update: CALLBACK_TYPE | None = None
        midnight_unsub: CALLBACK_TYPE | None = None
        coordinator = None
        active = True

        @callback
        def cancel_timers() -> None:
            nonlocal midnight_unsub
            for _token, remove in timers.values():
                remove()
            timers.clear()
            if midnight_unsub is not None:
                midnight_unsub()
                midnight_unsub = None

        @callback
        def reschedule() -> None:
            nonlocal midnight_unsub
            if (
                not active
                or entry.state is not ConfigEntryState.LOADED
                or coordinator is None
                or not coordinator.last_update_success
                or coordinator.data is None
            ):
                cancel_timers()
                return
            now = dt_util.utcnow()
            today = now.astimezone(coordinator.zone).date()
            tomorrow = today + timedelta(days=1)
            desired = {}
            for effective in coordinator.data.days:
                row = effective.row
                if row is None or row.day not in (today, tomorrow):
                    continue
                for field in fields:
                    stamps = row.timestamps(field, coordinator.zone)
                    for position, stamp in enumerate(stamps, 1):
                        instant = stamp.astimezone(timezone.utc)
                        key = (field, instant)
                        fire_at = instant - offset
                        # Retain unchanged due callbacks across a coordinator
                        # update at the exact trigger instant; never replay a miss.
                        if fire_at <= now and key not in timers:
                            continue
                        prayer = FIELD_LABELS[field]
                        if len(stamps) > 1:
                            prayer += f" {position}"
                        desired[key] = (
                            fire_at,
                            {
                                "mosque": entry.title,
                                "mosque_id": entry.entry_id,
                                "prayer": prayer,
                                "field": field.value,
                                "scheduled_time": stamp.isoformat(),
                                "minutes_before": minutes,
                            },
                        )
            for key in set(timers) - desired.keys():
                timers.pop(key)[1]()
            for key, (fire_at, payload) in desired.items():
                if key in timers:
                    continue
                token = object()

                @callback
                def fire(
                    _now: datetime,
                    key=key,
                    token=token,
                    payload=payload,
                    owner=coordinator,
                ) -> None:
                    current = timers.get(key)
                    if current is None or current[0] is not token:
                        return
                    timers.pop(key)
                    if (
                        active
                        and entry.state is ConfigEntryState.LOADED
                        and coordinator is owner
                        and owner.last_update_success
                    ):
                        run_action(payload, f"{payload['mosque']}: {payload['prayer']}")

                timers[key] = (
                    token,
                    async_track_point_in_utc_time(self._hass, fire, fire_at),
                )
            if midnight_unsub is not None:
                midnight_unsub()
            midnight = datetime.combine(tomorrow, time.min, coordinator.zone)

            @callback
            def midnight_reached(_now: datetime) -> None:
                reschedule()

            midnight_unsub = async_track_point_in_utc_time(
                self._hass, midnight_reached, midnight
            )

        @callback
        def entry_changed() -> None:
            nonlocal coordinator, unsubscribe_update
            cancel_timers()
            if unsubscribe_update is not None:
                unsubscribe_update()
                unsubscribe_update = None
            coordinator = None
            if entry.state is ConfigEntryState.LOADED:
                coordinator = getattr(entry, "runtime_data", None)
                if coordinator is not None:
                    unsubscribe_update = coordinator.async_add_listener(reschedule)
            reschedule()

        unsubscribe_state = entry.async_on_state_change(entry_changed)
        entry_changed()

        @callback
        def detach() -> None:
            nonlocal active
            active = False
            cancel_timers()
            unsubscribe_state()
            if unsubscribe_update is not None:
                unsubscribe_update()

        return detach


async def async_get_triggers(hass: HomeAssistant) -> dict[str, type[Trigger]]:
    """Expose the published-time reminder trigger."""
    return {"prayer_time": PrayerTimeTrigger}
