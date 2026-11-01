"""Optional read-only smoke test against the real public API; no Home Assistant."""

import asyncio
from datetime import UTC, datetime
import importlib.util
from pathlib import Path
import json

import aiohttp

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "custom_components/openligadb_frauen" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def main():
    api, models = load("api"), load("models")
    async with aiohttp.ClientSession() as session:
        client = api.OpenLigaDBClient(session)
        league, cup, table = await asyncio.gather(
            client.matches("ffb1", 2026), client.matches("dfbf", 2026), client.table("ffb1", 2026)
        )
    now = datetime.now(UTC)
    report = {}
    for key, payload, lead in [("bundesliga", league, 12), ("pokal", cup, 0)]:
        parsed = models.normalize_matches(payload)
        snapshot = models.build_snapshot(parsed, now, lead)
        report[key] = {
            "season_matches": len(parsed),
            "selected_round": snapshot["round_name"],
            "current_matches": len(snapshot["spiele"]),
            "corrected_matches": [m["matchID"] for m in parsed if m["corrections"]],
        }
    report["standings_teams"] = len(models.normalize_table(table))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
