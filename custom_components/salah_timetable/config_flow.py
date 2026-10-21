"""UI configuration, settings and manual CSV import for a mosque."""

import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import CONF_MOSQUE_ID, CONF_TIME_ZONE, DOMAIN
from .import_flow import CsvImportOptionsFlow


def valid_zone(value: str) -> bool:
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError, ValueError, TypeError:
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
                    },
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): selector.TextSelector(),
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


class SalahOptionsFlow(CsvImportOptionsFlow):
    async def async_step_settings(self, user_input=None):
        errors = {}
        if user_input is not None:
            if valid_zone(user_input[CONF_TIME_ZONE]):
                return self.async_create_entry(title="", data=user_input)
            errors[CONF_TIME_ZONE] = "invalid_time_zone"
        current = self.config_entry.options.get(
            CONF_TIME_ZONE, self.config_entry.data[CONF_TIME_ZONE]
        )
        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema(
                {vol.Required(CONF_TIME_ZONE, default=current): selector.TextSelector()}
            ),
            errors=errors,
        )
