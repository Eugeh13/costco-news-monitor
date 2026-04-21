"""Tests for the map dashboard GET /."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestMapIndex:
    async def test_index_renders_200(self, client: AsyncClient):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    async def test_index_has_map_div(self, client: AsyncClient):
        resp = await client.get("/")
        assert 'id="map"' in resp.text

    async def test_index_has_3_costcos_in_script(self, client: AsyncClient):
        body = (await client.get("/")).text
        assert "Carretera Nacional" in body
        assert "Cumbres" in body
        assert "Valle Oriente" in body

    async def test_index_has_leaflet_cdn_loaded(self, client: AsyncClient):
        body = (await client.get("/")).text
        assert "unpkg.com/leaflet" in body
