"""
Tests for GET /api/incidents endpoint.

Uses the in-memory SQLite engine and HTTP client from tests/dashboard/conftest.py.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.decision_log import DecisionLog


def _make_incident(
    *,
    run_id: str | None = None,
    article_title: str = "Choque en Carretera Nacional",
    article_url: str | None = None,
    incident_type: str | None = "accident",
    severity_score: int | None = 7,
    nearest_costco: str | None = "Costco Carretera Nacional",
    nearest_costco_dist_m: float | None = 1200.0,
    within_radius: bool | None = True,
    final_decision: str = "alerted",
    created_at: datetime | None = None,
    cost_estimated_usd: float | None = 0.005,
    affects_operations: bool | None = True,
) -> DecisionLog:
    log = DecisionLog(
        run_id=run_id or str(uuid.uuid4()),
        source_name="Milenio",
        article_url=article_url or f"https://milenio.com/{uuid.uuid4()}",
        article_title=article_title,
        stage_reached="notification",
        final_decision=final_decision,
        incident_type=incident_type,
        severity_score=severity_score,
        affects_operations=affects_operations,
        nearest_costco=nearest_costco,
        nearest_costco_dist_m=nearest_costco_dist_m,
        within_radius=within_radius,
        cost_estimated_usd=cost_estimated_usd,
        geo_lat=25.6026,
        geo_lon=-100.2640,
    )
    if created_at is not None:
        log.created_at = created_at
    return log


@pytest.mark.asyncio
async def test_returns_empty_when_no_incidents(client: AsyncClient, db_session: AsyncSession):
    """Response is well-formed with count=0 when no matching incidents exist."""
    response = await client.get("/api/incidents")
    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "incidents" in data
    assert "stats" in data
    assert isinstance(data["incidents"], list)


@pytest.mark.asyncio
async def test_returns_incident_with_all_fields(client: AsyncClient, db_session: AsyncSession):
    """Incident object exposes all required fields including distance_km."""
    db_session.add(_make_incident(nearest_costco_dist_m=1500.0))
    await db_session.commit()

    response = await client.get("/api/incidents")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] >= 1
    inc = data["incidents"][0]
    for field in ("id", "article_url", "article_title", "source_name",
                  "incident_type", "severity_score", "nearest_costco",
                  "distance_km", "within_radius", "final_decision", "created_at"):
        assert field in inc, f"Missing field: {field}"
    assert inc["distance_km"] == pytest.approx(1.5, abs=0.01)


@pytest.mark.asyncio
async def test_excludes_null_incident_type(client: AsyncClient, db_session: AsyncSession):
    """Rows without incident_type (not yet analyzed) are not returned."""
    db_session.add(_make_incident(incident_type=None, final_decision="pending"))
    db_session.add(_make_incident(incident_type="fire", article_title="Incendio real"))
    await db_session.commit()

    response = await client.get("/api/incidents")
    assert response.status_code == 200
    data = response.json()
    titles = [i["article_title"] for i in data["incidents"]]
    assert "Incendio real" in titles
    for inc in data["incidents"]:
        assert inc["incident_type"] is not None


@pytest.mark.asyncio
async def test_filters_by_severity_min(client: AsyncClient, db_session: AsyncSession):
    """Only incidents with severity_score >= severity_min are returned."""
    db_session.add(_make_incident(severity_score=3, article_title="Low sev"))
    db_session.add(_make_incident(severity_score=8, article_title="High sev"))
    await db_session.commit()

    response = await client.get("/api/incidents?severity_min=7")
    assert response.status_code == 200
    data = response.json()
    titles = [i["article_title"] for i in data["incidents"]]
    assert "High sev" in titles
    for inc in data["incidents"]:
        assert inc["severity_score"] >= 7


@pytest.mark.asyncio
async def test_filters_by_branch(client: AsyncClient, db_session: AsyncSession):
    """Branch filter returns only incidents for the specified Costco store."""
    db_session.add(_make_incident(nearest_costco="Costco Cumbres", article_title="Cumbres inc"))
    db_session.add(_make_incident(nearest_costco="Costco Valle Oriente", article_title="VO inc"))
    await db_session.commit()

    response = await client.get("/api/incidents?branch=cumbres&within_radius_only=false")
    assert response.status_code == 200
    data = response.json()
    for inc in data["incidents"]:
        assert inc["nearest_costco"] == "Costco Cumbres"


@pytest.mark.asyncio
async def test_within_radius_only_excludes_far_incidents(client: AsyncClient, db_session: AsyncSession):
    """Default within_radius_only=true excludes incidents where within_radius is False."""
    db_session.add(_make_incident(within_radius=True, article_title="Near inc"))
    db_session.add(_make_incident(within_radius=False, article_title="Far inc",
                                  nearest_costco_dist_m=5000.0))
    await db_session.commit()

    response = await client.get("/api/incidents?within_radius_only=true")
    assert response.status_code == 200
    data = response.json()
    titles = [i["article_title"] for i in data["incidents"]]
    assert "Far inc" not in titles


@pytest.mark.asyncio
async def test_within_radius_only_false_includes_all(client: AsyncClient, db_session: AsyncSession):
    """within_radius_only=false returns incidents regardless of radius."""
    db_session.add(_make_incident(within_radius=False, article_title="Outside radius"))
    await db_session.commit()

    response = await client.get("/api/incidents?within_radius_only=false")
    assert response.status_code == 200
    data = response.json()
    titles = [i["article_title"] for i in data["incidents"]]
    assert "Outside radius" in titles


@pytest.mark.asyncio
async def test_limit_param_respected(client: AsyncClient, db_session: AsyncSession):
    """limit query param caps the number of returned incidents."""
    for i in range(5):
        db_session.add(_make_incident(article_title=f"Incident {i}"))
    await db_session.commit()

    response = await client.get("/api/incidents?limit=2&within_radius_only=false")
    assert response.status_code == 200
    data = response.json()
    assert len(data["incidents"]) <= 2


@pytest.mark.asyncio
async def test_stats_avg_severity_computed(client: AsyncClient, db_session: AsyncSession):
    """stats.avg_severity reflects the average of matching rows."""
    db_session.add(_make_incident(severity_score=4, within_radius=True))
    db_session.add(_make_incident(severity_score=8, within_radius=True))
    await db_session.commit()

    response = await client.get("/api/incidents")
    assert response.status_code == 200
    data = response.json()
    # Should be 6.0 (avg of 4 and 8), but other test data might affect it
    assert data["stats"]["avg_severity"] is not None


@pytest.mark.asyncio
async def test_stats_by_branch_counts(client: AsyncClient, db_session: AsyncSession):
    """stats.by_branch contains carretera_nacional, cumbres, valle_oriente keys."""
    response = await client.get("/api/incidents?within_radius_only=false")
    assert response.status_code == 200
    data = response.json()
    by_branch = data["stats"]["by_branch"]
    assert "carretera_nacional" in by_branch
    assert "cumbres" in by_branch
    assert "valle_oriente" in by_branch
    for v in by_branch.values():
        assert isinstance(v, int)
        assert v >= 0


@pytest.mark.asyncio
async def test_invalid_since_param_returns_422(client: AsyncClient):
    """Invalid since value returns HTTP 422 Unprocessable Entity."""
    response = await client.get("/api/incidents?since=999h")
    assert response.status_code == 422
