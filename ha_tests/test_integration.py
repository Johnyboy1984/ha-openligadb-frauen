"""Full HA tests for the Linux CI runner; not part of the portable unit suite."""

from copy import deepcopy
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

DOMAIN = "openligadb_frauen"
MATCHES = [
    {
        "matchID": 100,
        "leagueSeason": 2026,
        "group": {"groupOrderID": 8, "groupName": "8. Spieltag"},
        "matchDateTimeUTC": "2026-10-23T16:30:00Z",
        "team1": {"teamId": 1, "teamName": "Heim Frauen", "teamIconUrl": "https://example.com/a.png"},
        "team2": {"teamId": 2, "teamName": "Gast Frauen", "teamIconUrl": "https://example.com/b.png"},
        "matchIsFinished": True,
        "matchResults": [{"resultTypeID": 2, "resultOrderID": 2, "pointsTeam1": 1, "pointsTeam2": 0}],
    }
]


@pytest.fixture(autouse=True)
def custom_integrations(enable_custom_integrations):
    yield


async def test_config_flow_creates_and_prevents_duplicate(hass):
    with (
        patch(f"custom_components.{DOMAIN}.config_flow.OpenLigaDBClient.matches", return_value=deepcopy(MATCHES)),
        patch(f"custom_components.{DOMAIN}.async_setup_entry", return_value=True),
    ):
        flow = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        assert flow["type"] is FlowResultType.FORM
        result = await hass.config_entries.flow.async_configure(
            flow["flow_id"], {"competition": "bundesliga", "season": 2026}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        await hass.async_block_till_done()
        second = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        duplicate = await hass.config_entries.flow.async_configure(
            second["flow_id"], {"competition": "bundesliga", "season": 2026}
        )
        assert duplicate["type"] is FlowResultType.ABORT


async def test_first_snapshot_sensor_and_unload(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={"competition": "bundesliga", "season": 2026}, unique_id="bundesliga")
    entry.add_to_hass(hass)
    with (
        patch(f"custom_components.{DOMAIN}.api.OpenLigaDBClient.matches", return_value=deepcopy(MATCHES)),
        patch(
            f"custom_components.{DOMAIN}.api.OpenLigaDBClient.table",
            return_value=[{"teamName": "Heim Frauen", "points": 3}],
        ),
        patch(f"custom_components.{DOMAIN}.coordinator.dt_util.utcnow", return_value=datetime(2026, 11, 1, tzinfo=UTC)),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        from homeassistant.helpers import entity_registry as er

        registry = er.async_get(hass)
        round_id = registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_round_0")
        state = hass.states.get(round_id)
        assert state.state == "8. Spieltag"
        assert state.attributes["spiele"][0]["ergebnis"] == "1:0"
        match_id = registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_match_0")
        assert hass.states.get(match_id).attributes["group"]["groupOrderID"] == 8
        unused_id = registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_match_1")
        assert hass.states.get(unused_id).state == "unavailable"
        assert await hass.config_entries.async_unload(entry.entry_id)


async def test_failed_first_refresh_has_no_placeholder_entities(hass):
    entry = MockConfigEntry(domain=DOMAIN, data={"competition": "pokal", "season": 2026}, unique_id="pokal")
    entry.add_to_hass(hass)
    from custom_components.openligadb_frauen.api import OpenLigaDBError

    with patch(f"custom_components.{DOMAIN}.api.OpenLigaDBClient.matches", side_effect=OpenLigaDBError("offline")):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        from homeassistant.config_entries import ConfigEntryState

        assert entry.state is ConfigEntryState.SETUP_RETRY
