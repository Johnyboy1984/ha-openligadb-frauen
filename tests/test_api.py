"""HTTP error handling and shared-session behavior, without network calls."""

import asyncio
import importlib.util
from pathlib import Path
import unittest

try:
    import aiohttp
except ImportError:
    aiohttp = None


class Response:
    def __init__(self, payload=None, error=None):
        self.payload, self.error = payload, error

    async def __aenter__(self):
        if self.error:
            raise self.error
        return self

    async def __aexit__(self, *args):
        return False

    def raise_for_status(self):
        pass

    async def json(self):
        return self.payload


class Session:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


@unittest.skipUnless(aiohttp, "Install aiohttp to run API tests")
class APITests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / "custom_components/openligadb_frauen/api.py"
        spec = importlib.util.spec_from_file_location("ol_api", path)
        self.api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.api)

    async def test_shared_session_and_https_path(self):
        session = Session(Response([{"matchID": 1}]))
        client = self.api.OpenLigaDBClient(session)
        self.assertEqual(await client.matches("ffb1", 2026), [{"matchID": 1}])
        self.assertEqual(session.calls[0][0], "https://api.openligadb.de/getmatchdata/ffb1/2026")
        self.assertEqual(session.calls[0][1]["timeout"].total, 25)

    async def test_table_endpoint(self):
        session = Session(Response([]))
        await self.api.OpenLigaDBClient(session).table("ffb1", 2026)
        self.assertTrue(session.calls[0][0].endswith("getbltable/ffb1/2026"))

    async def test_timeout_becomes_integration_error(self):
        client = self.api.OpenLigaDBClient(Session(Response(error=asyncio.TimeoutError())))
        with self.assertRaises(self.api.OpenLigaDBError):
            await client.matches("dfbf", 2026)

    async def test_connection_error_becomes_integration_error(self):
        client = self.api.OpenLigaDBClient(Session(Response(error=aiohttp.ClientConnectionError())))
        with self.assertRaises(self.api.OpenLigaDBError):
            await client.matches("dfbf", 2026)

    async def test_invalid_json_becomes_integration_error(self):
        response = Response()

        async def invalid_json():
            raise ValueError("invalid JSON")

        response.json = invalid_json
        client = self.api.OpenLigaDBClient(Session(response))
        with self.assertRaises(self.api.OpenLigaDBError):
            await client.matches("dfbf", 2026)
