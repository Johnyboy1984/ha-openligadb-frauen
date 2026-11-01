"""One coherent match snapshot for all entities, available before entity setup."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import OpenLigaDBClient, OpenLigaDBError
from .const import COMPETITIONS, CONF_COMPETITION, CONF_CORRECTIONS, CONF_INTERVAL, CONF_SEASON, DEFAULT_INTERVAL
from .models import build_snapshot, normalize_matches, normalize_table

LOGGER = logging.getLogger(__name__)


class OpenLigaDBCoordinator(DataUpdateCoordinator[dict]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.competition = entry.data[CONF_COMPETITION]
        self.definition = COMPETITIONS[self.competition]
        self.season = int(entry.options.get(CONF_SEASON, entry.data[CONF_SEASON]))
        self.corrections = entry.options.get(CONF_CORRECTIONS, True)
        self.client = OpenLigaDBClient(async_get_clientsession(hass))
        self._table = []
        self._table_updated = None
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=self.definition["name"],
            update_interval=timedelta(seconds=entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL)),
        )

    async def _async_update_data(self) -> dict:
        now = dt_util.utcnow()
        try:
            payload = await self.client.matches(self.definition["league"], self.season)
            matches = normalize_matches(payload, corrections=self.corrections)
            snapshot = build_snapshot(matches, now, self.definition["lead_hours"])
        except (OpenLigaDBError, ValueError, TypeError, KeyError) as err:
            raise UpdateFailed(f"Cannot update {self.definition['name']}: {err}") from err
        table_ok = bool(self._table)
        if self.competition == "bundesliga" and (
            self._table_updated is None or now - self._table_updated >= timedelta(minutes=30)
        ):
            try:
                self._table = normalize_table(await self.client.table(self.definition["league"], self.season))
                self._table_updated = now
                table_ok = True
            except (OpenLigaDBError, ValueError, TypeError, KeyError) as err:
                table_ok = False
                LOGGER.warning("Standings could not be updated: %s", err)
        snapshot.update(
            table=self._table,
            table_available=table_ok,
            table_updated=self._table_updated.isoformat() if self._table_updated else None,
            season=self.season,
        )
        return snapshot
