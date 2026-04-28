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

    async def test_index_has_google_maps_cdn_or_error_fallback(self, client: AsyncClient):
        body = (await client.get("/")).text
        # Either Google Maps is loaded (key configured) or the error fallback is rendered
        has_google_maps = "maps.googleapis.com/maps/api/js" in body
        has_error_fallback = "GOOGLE_MAPS_BROWSER_KEY" in body
        assert has_google_maps or has_error_fallback
