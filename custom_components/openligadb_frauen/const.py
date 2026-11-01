"""Constants for OpenLigaDB Frauen."""

DOMAIN = "openligadb_frauen"
NAME = "OpenLigaDB Frauen"
VERSION = "0.1.0b1"
DEFAULT_INTERVAL = 300
CONF_COMPETITION = "competition"
CONF_SEASON = "season"
CONF_INTERVAL = "scan_interval"
CONF_CORRECTIONS = "known_corrections"
COMPETITIONS = {
    "bundesliga": {"league": "ffb1", "name": "Frauen-Bundesliga", "lead_hours": 12, "slots": 7},
    "pokal": {"league": "dfbf", "name": "DFB-Pokal Frauen", "lead_hours": 0, "slots": 16},
}
