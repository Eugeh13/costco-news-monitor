"""
Tests for src/dashboard/routes.py.

All DB interaction uses an in-memory SQLite seeded via conftest fixtures.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.dashboard._model_stubs import DecisionLog, HumanFeedback
from tests.dashboard.conftest import _RUN_ID_A, _RUN_ID_B


# ── GET /health ───────────────────────────────────────────────

class TestHealth:
    async def test_returns_ok(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "decision_log_count" in data

    async def test_count_increments_with_data(self, client: AsyncClient, seed_logs):
        resp = await client.get("/health")
        assert resp.json()["decision_log_count"] >= 5


# ── GET / ─────────────────────────────────────────────────────

class TestIndex:
    async def test_returns_200(self, client: AsyncClient, seed_logs):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    async def test_shows_articles(self, client: AsyncClient, seed_logs):
        resp = await client.get("/")
        body = resp.text
        assert "Choque en Carretera Nacional" in body
        assert "Incendio en bodega Escobedo" in body

    async def test_filter_by_run_id(self, client: AsyncClient, seed_logs):
        resp = await client.get(f"/?run_id={_RUN_ID_A}")
        body = resp.text
        assert "Choque en Carretera Nacional" in body
        # Run B article should not appear
        assert "Balacera en Apodaca" not in body

    async def test_filter_by_final_decision(self, client: AsyncClient, seed_logs):
        resp = await client.get("/?final_decision=alert_sent")
        body = resp.text
        # alert_sent articles must appear
        assert "Choque en Carretera Nacional" in body
        # dismissed article title must NOT appear in table rows
        assert "Nota sin relevancia local" not in body

    async def test_filter_only_unreviewed(self, client: AsyncClient, seed_logs, db_session):
        # Add feedback to first log
        fb = HumanFeedback(
            decision_log_id=seed_logs[0].id,
            was_correct=True,
            created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        )
        db_session.add(fb)
        await db_session.commit()

        resp = await client.get("/?only_unreviewed=true")
        body = resp.text
        # First article (reviewed) should not appear; others should
        assert "Incendio en bodega Escobedo" in body

    async def test_pagination_page_param(self, client: AsyncClient, seed_logs):
        resp = await client.get("/?page=1")
        assert resp.status_code == 200

    async def test_empty_db_returns_200_no_crash(self, client: AsyncClient):
        resp = await client.get("/")
        assert resp.status_code == 200


# ── GET /log/{id} ─────────────────────────────────────────────

class TestLogDetail:
    async def test_returns_200_with_data(self, client: AsyncClient, seed_logs):
        log_id = seed_logs[0].id
        resp = await client.get(f"/log/{log_id}")
        assert resp.status_code == 200
        body = resp.text
        assert "Choque en Carretera Nacional" in body

    async def test_shows_all_sections(self, client: AsyncClient, seed_logs):
        log_id = seed_logs[0].id
        resp = await client.get(f"/log/{log_id}")
        body = resp.text
        assert "Artículo" in body
        assert "Triage" in body
        assert "Clasificación" in body
        assert "Geolocalización" in body
        assert "Decisión final" in body
        assert "Tokens" in body

    async def test_shows_keyboard_hints(self, client: AsyncClient, seed_logs):
        resp = await client.get(f"/log/{seed_logs[0].id}")
        body = resp.text
        assert "Atajos" in body
        assert "kbd" in body

    async def test_404_for_missing_id(self, client: AsyncClient):
        resp = await client.get("/log/999999")
        assert resp.status_code == 404

    async def test_shows_existing_feedback(self, client: AsyncClient, seed_logs, db_session):
        log = seed_logs[1]
        fb = HumanFeedback(
            decision_log_id=log.id,
            was_correct=False,
            should_have_been="should_have_dismissed",
            notes="Demasiado lejos para ser relevante",
            created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        )
        db_session.add(fb)
        await db_session.commit()

        resp = await client.get(f"/log/{log.id}")
        body = resp.text
        assert "Feedback previo" in body
        assert "Demasiado lejos" in body

    async def test_contains_feedback_form(self, client: AsyncClient, seed_logs):
        resp = await client.get(f"/log/{seed_logs[0].id}")
        body = resp.text
        assert 'action="/log/' in body
        assert 'name="was_correct"' in body


# ── POST /log/{id}/feedback ───────────────────────────────────

class TestSaveFeedback:
    async def test_save_correct_feedback(self, client: AsyncClient, seed_logs, db_session):
        log = seed_logs[2]
        resp = await client.post(
            f"/log/{log.id}/feedback",
            data={"was_correct": "true", "notes": "Bien clasificada"},
            follow_redirects=False,
        )
        assert resp.status_code == 303

        result = await db_session.execute(
            select(HumanFeedback).where(HumanFeedback.decision_log_id == log.id)
        )
        fb = result.scalar_one_or_none()
        assert fb is not None
        assert fb.was_correct is True
        assert fb.notes == "Bien clasificada"

    async def test_save_incorrect_feedback_with_should_have_been(self, client: AsyncClient, seed_logs, db_session):
        log = seed_logs[3]
        resp = await client.post(
            f"/log/{log.id}/feedback",
            data={
                "was_correct": "false",
                "should_have_been": "should_have_alerted",
                "notes": "Estaba dentro del radio",
            },
            follow_redirects=False,
        )
        assert resp.status_code == 303

        result = await db_session.execute(
            select(HumanFeedback).where(HumanFeedback.decision_log_id == log.id)
        )
        fb = result.scalar_one_or_none()
        assert fb is not None
        assert fb.was_correct is False
        assert fb.should_have_been == "should_have_alerted"

    async def test_redirect_to_next_id_when_provided(self, client: AsyncClient, seed_logs):
        log = seed_logs[0]
        next_log = seed_logs[1]
        resp = await client.post(
            f"/log/{log.id}/feedback",
            data={"was_correct": "true", "next_id": str(next_log.id)},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert f"/log/{next_log.id}" in resp.headers["location"]

    async def test_redirect_to_index_when_no_next(self, client: AsyncClient, seed_logs):
        log = seed_logs[0]
        resp = await client.post(
            f"/log/{log.id}/feedback",
            data={"was_correct": "true"},
            follow_redirects=False,
        )
        assert resp.status_code == 303
        assert resp.headers["location"] in ("/", "http://test/")

    async def test_upsert_updates_existing_feedback(self, client: AsyncClient, seed_logs, db_session):
        log = seed_logs[4]
        # First save
        await client.post(
            f"/log/{log.id}/feedback",
            data={"was_correct": "true"},
            follow_redirects=False,
        )
        # Second save (update)
        await client.post(
            f"/log/{log.id}/feedback",
            data={"was_correct": "false", "notes": "Actualizado"},
            follow_redirects=False,
        )
        result = await db_session.execute(
            select(HumanFeedback).where(HumanFeedback.decision_log_id == log.id)
        )
        fbs = result.scalars().all()
        assert len(fbs) == 1
        assert fbs[0].was_correct is False
        assert fbs[0].notes == "Actualizado"

    async def test_404_for_nonexistent_log(self, client: AsyncClient):
        resp = await client.post(
            "/log/999999/feedback",
            data={"was_correct": "true"},
            follow_redirects=False,
        )
        assert resp.status_code == 404


# ── GET /runs ─────────────────────────────────────────────────

class TestRuns:
    async def test_returns_200(self, client: AsyncClient, seed_logs):
        resp = await client.get("/runs")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    async def test_shows_run_ids(self, client: AsyncClient, seed_logs):
        resp = await client.get("/runs")
        body = resp.text
        assert _RUN_ID_A[:8] in body
        assert _RUN_ID_B[:8] in body

    async def test_empty_runs_no_crash(self, client: AsyncClient):
        resp = await client.get("/runs")
        assert resp.status_code == 200
