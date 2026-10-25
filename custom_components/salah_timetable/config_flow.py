"""UI configuration, settings and manual CSV import for a mosque."""

import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import CONF_MOSQUE_ID, CONF_SHOW_HIJRI_DATE, CONF_TIME_ZONE, DOMAIN
from .ramadan import RamadanSettings
from .ramadan_validation import validate_ramadan_selection
from .source_flow import SourceOptionsFlow


def valid_zone(value: str) -> bool:
    try:
        ZoneInfo(value)
    except (
        ZoneInfoNotFoundError,
        ValueError,
        TypeError,
    ):
        return False
    return True


class SalahConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            mosque_id = user_input[CONF_MOSQUE_ID].strip().lower()
            name = user_input[CONF_NAME].strip()
            if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", mosque_id):
                errors[CONF_MOSQUE_ID] = "invalid_mosque_id"
            if not name or len(name) > 100:
                errors[CONF_NAME] = "invalid_name"
            if not valid_zone(user_input[CONF_TIME_ZONE]):
                errors[CONF_TIME_ZONE] = "invalid_time_zone"
            if not errors:
                await self.async_set_unique_id(mosque_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=name,
                    data={
                        CONF_NAME: name,
                        CONF_MOSQUE_ID: mosque_id,
                        CONF_TIME_ZONE: user_input[CONF_TIME_ZONE],
                        CONF_SHOW_HIJRI_DATE: user_input.get(
                            CONF_SHOW_HIJRI_DATE, True
                        ),
                    },
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): selector.TextSelector(),
                    vol.Optional(
                        CONF_SHOW_HIJRI_DATE, default=True
                    ): selector.BooleanSelector(),
                    vol.Required(CONF_MOSQUE_ID): selector.TextSelector(),
                    vol.Required(
                        CONF_TIME_ZONE, default=self.hass.config.time_zone
                    ): selector.TextSelector(),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SalahOptionsFlow()


class SalahOptionsFlow(SourceOptionsFlow):
    async def async_step_settings(self, user_input=None):
        errors = {}
        if user_input is not None:
            if valid_zone(user_input[CONF_TIME_ZONE]):
                return self.async_create_entry(
                    title="", data={**self.config_entry.options, **user_input}
                )
            errors[CONF_TIME_ZONE] = "invalid_time_zone"
        current = self.config_entry.options.get(
            CONF_TIME_ZONE, self.config_entry.data[CONF_TIME_ZONE]
        )
        show_hijri = self.config_entry.options.get(
            CONF_SHOW_HIJRI_DATE, self.config_entry.data.get(CONF_SHOW_HIJRI_DATE, True)
        )
        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TIME_ZONE, default=current
                    ): selector.TextSelector(),
                    vol.Optional(
                        CONF_SHOW_HIJRI_DATE, default=show_hijri
                    ): selector.BooleanSelector(),
                }
            ),
            errors=errors,
        )

    async def async_step_ramadan(self, user_input=None):
        errors = {}
        detail = ""
        coordinator = getattr(self.config_entry, "runtime_data", None)
        tables = coordinator.storage.timetables if coordinator else ()
        sources = [table.timetable_id for table in tables if table.kind == "ramadan"]
        if user_input is not None:
            try:
                values = dict(user_input)
                if values.get("ramadan_source_id") == "__auto__":
                    values["ramadan_source_id"] = None
                settings = RamadanSettings.from_options(values)
                if settings.source_id is not None and settings.source_id not in sources:
                    raise ValueError("Select an imported Ramadan source")
                validate_ramadan_selection(tables, settings)
            except ValueError as err:
                errors["base"] = "invalid_ramadan"
                detail = str(err)
            else:
                return self.async_create_entry(
                    title="",
                    data={**self.config_entry.options, **settings.as_options()},
                )
        try:
            current = RamadanSettings.from_options(self.config_entry.options)
        except ValueError:
            current = RamadanSettings()
        schema = {
            vol.Required("ramadan_mode", default=current.mode): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=["auto", "on", "off"], translation_key="ramadan_mode"
                )
            ),
            vol.Optional(
                "ramadan_start",
                description={
                    "suggested_value": current.confirmed_start.isoformat()
                    if current.confirmed_start
                    else None
                },
            ): selector.DateSelector(),
            vol.Optional(
                "ramadan_end",
                description={
                    "suggested_value": current.confirmed_end.isoformat()
                    if current.confirmed_end
                    else None
                },
            ): selector.DateSelector(),
            vol.Required(
                "ramadan_adjustment", default=current.date_adjustment
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=-3, max=3, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Required(
                "ramadan_source_id",
                default=current.source_id
                if current.source_id in sources
                else "__auto__",
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {
                            "value": "__auto__",
                            "label": "Use the unique matching source",
                        },
                        *({"value": source, "label": source} for source in sources),
                    ]
                )
            ),
        }
        return self.async_show_form(
            step_id="ramadan",
            data_schema=vol.Schema(schema),
            errors=errors,
            description_placeholders={"detail": detail},
        )
