"""UI setup and options. No YAML and no API key required."""

from __future__ import annotations

from datetime import datetime

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .api import OpenLigaDBClient, OpenLigaDBError
from .const import (
    COMPETITIONS,
    CONF_COMPETITION,
    CONF_CORRECTIONS,
    CONF_INTERVAL,
    CONF_SEASON,
    DEFAULT_INTERVAL,
    DOMAIN,
)
from .models import normalize_matches


def default_season(now: datetime | None = None) -> int:
    now = now or dt_util.now()
    return now.year if now.month >= 7 else now.year - 1


class OpenLigaDBFrauenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            competition = user_input[CONF_COMPETITION]
            await self.async_set_unique_id(competition)
            self._abort_if_unique_id_configured()
            try:
                client = OpenLigaDBClient(async_get_clientsession(self.hass))
                normalize_matches(await client.matches(COMPETITIONS[competition]["league"], user_input[CONF_SEASON]))
            except OpenLigaDBError:
                errors["base"] = "cannot_connect"
            except (ValueError, TypeError, KeyError):
                errors["base"] = "no_matches"
            else:
                return self.async_create_entry(title=COMPETITIONS[competition]["name"], data=user_input)
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_COMPETITION, default="bundesliga"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=[{"value": key, "label": value["name"]} for key, value in COMPETITIONS.items()]
                        )
                    ),
                    vol.Required(CONF_SEASON, default=default_season()): vol.All(
                        vol.Coerce(int), vol.Range(min=2020, max=2100)
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OpenLigaDBFrauenOptionsFlow()


class OpenLigaDBFrauenOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = {}
        entry = self.config_entry
        if user_input is not None:
            try:
                client = OpenLigaDBClient(async_get_clientsession(self.hass))
                normalize_matches(
                    await client.matches(COMPETITIONS[entry.data[CONF_COMPETITION]]["league"], user_input[CONF_SEASON])
                )
            except OpenLigaDBError:
                errors["base"] = "cannot_connect"
            except (ValueError, TypeError, KeyError):
                errors["base"] = "no_matches"
            else:
                return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SEASON, default=entry.options.get(CONF_SEASON, entry.data[CONF_SEASON])): vol.All(
                        vol.Coerce(int), vol.Range(min=2020, max=2100)
                    ),
                    vol.Required(CONF_INTERVAL, default=entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL)): vol.All(
                        vol.Coerce(int), vol.Range(min=60, max=3600)
                    ),
                    vol.Required(CONF_CORRECTIONS, default=entry.options.get(CONF_CORRECTIONS, True)): bool,
                }
            ),
            errors=errors,
        )
