"""Async OpenLigaDB client using Home Assistant's shared HTTP session."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

API_URL = "https://api.openligadb.de"


class OpenLigaDBError(Exception):
    """The public API could not provide usable data."""


class OpenLigaDBClient:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def _get(self, path: str) -> Any:
        try:
            async with self._session.get(
                f"{API_URL}/{path}",
                timeout=aiohttp.ClientTimeout(total=25),
                headers={"Accept": "application/json"},
            ) as response:
                response.raise_for_status()
                return await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as err:
            raise OpenLigaDBError(f"OpenLigaDB request failed: {path}") from err

    async def matches(self, league: str, season: int) -> Any:
        return await self._get(f"getmatchdata/{league}/{int(season)}")

    async def table(self, league: str, season: int) -> Any:
        return await self._get(f"getbltable/{league}/{int(season)}")
