"""Coordinator-backed sensor entities and backwards-compatible match attributes."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo, DeviceEntryType
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, VERSION
from .coordinator import OpenLigaDBCoordinator
from .models import flat_match, score_text


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    entities = [
        OpenLigaDBSensor(coordinator, "round"),
        OpenLigaDBSensor(coordinator, "next"),
        OpenLigaDBSensor(coordinator, "last"),
    ]
    entities.extend(OpenLigaDBSensor(coordinator, "match", index) for index in range(coordinator.definition["slots"]))
    if coordinator.competition == "bundesliga":
        entities.append(OpenLigaDBSensor(coordinator, "table"))
        entities.extend(OpenLigaDBSensor(coordinator, "rank", index) for index in range(14))
    async_add_entities(entities)


class OpenLigaDBSensor(CoordinatorEntity[OpenLigaDBCoordinator], SensorEntity):
    _attr_icon = "mdi:soccer"
    _unrecorded_attributes = frozenset({"spiele", "matches", "table", "team1", "team2", "matchResults", "corrections"})

    def __init__(self, coordinator: OpenLigaDBCoordinator, kind: str, index: int = 0) -> None:
        super().__init__(coordinator)
        self.kind, self.index = kind, index
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{kind}_{index}"
        label = {
            "round": "aktuelle Runde",
            "next": "nächstes Spiel",
            "last": "letztes Spiel",
            "table": "Tabelle",
            "match": f"Spiel {index + 1:02d}",
            "rank": f"Platz {index + 1:02d}",
        }[kind]
        self._attr_name = f"OpenLigaDB {coordinator.definition['name']} {label}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            entry_type=DeviceEntryType.SERVICE,
            name=f"OpenLigaDB {coordinator.definition['name']}",
            manufacturer="OpenLigaDB",
            model=coordinator.definition["name"],
            sw_version=VERSION,
            configuration_url=f"https://www.openligadb.de/Matches/{coordinator.definition['league']}/{coordinator.season}",
        )
        if kind in ("round", "table", "rank"):
            self._attr_icon = "mdi:trophy-outline" if kind == "round" else "mdi:format-list-numbered"

    @property
    def _match(self):
        data = self.coordinator.data
        if self.kind == "match":
            return data["matches"][self.index] if self.index < len(data["matches"]) else None
        return data.get("next_match" if self.kind == "next" else "last_match")

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        data = self.coordinator.data
        if self.kind == "match":
            return self.index < len(data["matches"])
        if self.kind in ("next", "last"):
            return self._match is not None
        if self.kind in ("table", "rank"):
            return data["table_available"] and (self.kind == "table" or self.index < len(data["table"]))
        return True

    @property
    def native_value(self):
        data = self.coordinator.data
        if self.kind == "round":
            return data["round_name"]
        if self.kind == "table":
            return len(data["table"])
        if self.kind == "rank":
            return data["table"][self.index]["teamName"] if self.index < len(data["table"]) else None
        match = self._match
        if not match:
            return None
        middle = score_text(match) if match.get("matchIsFinished") else "–"
        return f"{match['team1']['teamName']} {middle} {match['team2']['teamName']}"[:255]

    @property
    def entity_picture(self):
        if self.kind == "rank" and self.index < len(self.coordinator.data["table"]):
            return self.coordinator.data["table"][self.index].get("teamIconUrl") or None
        return None

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data
        common = {"saison": data["season"], "quelle": "OpenLigaDB", "aktualisiert": data["updated"]}
        if self.kind == "round":
            return {
                **common,
                "runde_nummer": data["round_number"],
                "anzahl_spiele": len(data["matches"]),
                "spiele": data["spiele"],
                "matches": data["matches"],
                "vorlauf_stunden": self.coordinator.definition["lead_hours"],
            }
        if self.kind == "table":
            return {**common, "table": data["table"], "aktualisiert": data["table_updated"]}
        if self.kind == "rank":
            return (
                {**common, **data["table"][self.index], "aktualisiert": data["table_updated"]}
                if self.index < len(data["table"])
                else common
            )
        match = self._match
        if not match:
            return common
        return {
            **common,
            **flat_match(match),
            **{
                key: match.get(key)
                for key in (
                    "group",
                    "matchDateTime",
                    "matchDateTimeUTC",
                    "team1",
                    "team2",
                    "matchResults",
                    "matchIsFinished",
                    "location",
                )
            },
        }
