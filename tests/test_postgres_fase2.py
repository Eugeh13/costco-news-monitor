"""
Tests de PostgresRepository (Fase 2) — SIN servidor PostgreSQL.

psycopg2 está instalado (sus clases de error son reales) pero nunca se
conecta: ThreadedConnectionPool se reemplaza por un MagicMock y la conexión/
cursor son mocks. Cubre:

(a) constructor lazy: instanciar el repo NO crea el pool ni conecta;
(b) UniqueViolation en save_incident → None benigno (UNIQUE url+fuente
    que el ON CONFLICT por noticia_hash no cubre), sin propagar;
(c) otra IntegrityError (CheckViolation) SÍ propaga;
(d) el INSERT incluye fecha_evento y usa el placeholder "sin-url:<hash>"
    cuando news.url es None o vacía;
(e) pool: putconn(close=False) en éxito y putconn(close=True) tras
    OperationalError (conexión rota se descarta del pool).
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import psycopg2
import pytest
import pytz
from psycopg2 import errors as pg_errors

import app.infrastructure.persistence.postgres as postgres_mod
from app.domain.models import (
    Alert,
    AnalysisResult,
    Coordinates,
    IncidentCategory,
    LocationInfo,
    NewsItem,
    ProximityResult,
    TrafficImpact,
)
from app.infrastructure.persistence.postgres import PostgresRepository

_TZ = pytz.timezone("America/Chicago")
_FECHA_PUB = _TZ.localize(datetime(2026, 6, 9, 14, 30, 0))


# ============================================================
# Helpers — alerta sintética y pool mockeado
# ============================================================

def _alerta(url: str | None = "https://ejemplo.test/nota-1") -> Alert:
    return Alert(
        news=NewsItem(
            titulo="Balacera en avenida del sur de Monterrey",
            contenido="Se reporta una balacera con personas lesionadas.",
            url=url,
            fuente="fuente-sintetica",
            fecha_pub=_FECHA_PUB,
        ),
        analysis=AnalysisResult(
            is_relevant=True,
            category=IncidentCategory.SEGURIDAD,
            severity=8,
            summary="Balacera reportada cerca de zona comercial.",
            location=LocationInfo(extracted="Av. Lázaro Cárdenas 800"),
            victims=1,
            traffic_impact=TrafficImpact.HIGH,
            emergency_services=True,
        ),
        proximity=ProximityResult(
            is_within_radius=True,
            costco_nombre="Costco Valle Oriente",
            distancia_km=1.2,
            event_coords=Coordinates(lat=25.64, lon=-100.31),
        ),
    )


@pytest.fixture
def pool_falso(monkeypatch):
    """Reemplaza ThreadedConnectionPool por un mock; expone conn y cursor."""
    cursor = MagicMock(name="cursor")
    conn = MagicMock(name="conn")
    conn.closed = False  # MagicMock sería truthy y el repo la descartaría
    conn.cursor.return_value = cursor

    pool = MagicMock(name="pool")
    pool.getconn.return_value = conn

    pool_cls = MagicMock(name="ThreadedConnectionPool", return_value=pool)
    monkeypatch.setattr(postgres_mod, "ThreadedConnectionPool", pool_cls)
    return SimpleNamespace(cls=pool_cls, pool=pool, conn=conn, cursor=cursor)


def _repo() -> PostgresRepository:
    return PostgresRepository("postgresql://usuario:clave@db-falsa:5432/test")


# ============================================================
# (a) Constructor lazy — no conecta
# ============================================================

def test_constructor_no_crea_el_pool(pool_falso):
    repo = _repo()
    assert repo._pool is None
    pool_falso.cls.assert_not_called()


def test_pool_se_crea_una_sola_vez_en_la_primera_operacion(pool_falso):
    repo = _repo()
    pool_falso.cursor.fetchone.return_value = None

    repo.is_duplicate("titulo x", "https://ejemplo.test/x", "fuente")
    repo.is_duplicate("titulo y", "https://ejemplo.test/y", "fuente")

    pool_falso.cls.assert_called_once_with(
        minconn=1, maxconn=4, dsn="postgresql://usuario:clave@db-falsa:5432/test"
    )


# ============================================================
# (b) UniqueViolation → duplicado benigno, no error
# ============================================================

def test_unique_violation_en_save_incident_devuelve_none(pool_falso):
    pool_falso.cursor.execute.side_effect = pg_errors.UniqueViolation(
        "duplicate key value violates unique constraint \"noticias_url_fuente_key\""
    )
    assert _repo().save_incident(_alerta()) is None


def test_unique_violation_hace_rollback_y_devuelve_la_conexion_sana(pool_falso):
    pool_falso.cursor.execute.side_effect = pg_errors.UniqueViolation()
    _repo().save_incident(_alerta())

    pool_falso.conn.rollback.assert_called_once()
    # La conexión no está rota: vuelve al pool sin cerrarse
    pool_falso.pool.putconn.assert_called_once_with(pool_falso.conn, close=False)


# ============================================================
# (c) Otra IntegrityError (CheckViolation) SÍ propaga
# ============================================================

def test_check_violation_si_propaga(pool_falso):
    pool_falso.cursor.execute.side_effect = pg_errors.CheckViolation(
        "new row violates check constraint \"noticias_severidad_check\""
    )
    with pytest.raises(pg_errors.CheckViolation):
        _repo().save_incident(_alerta())


# ============================================================
# (d) El INSERT incluye fecha_evento y el placeholder sin-url
# ============================================================

def _captura_insert(pool_falso, alerta: Alert):
    pool_falso.cursor.fetchone.return_value = (42,)
    incident_id = _repo().save_incident(alerta)
    assert incident_id == 42
    sql, params = pool_falso.cursor.execute.call_args.args
    return sql, params


def test_insert_incluye_fecha_evento(pool_falso):
    alerta = _alerta()
    sql, params = _captura_insert(pool_falso, alerta)

    assert "fecha_evento" in sql
    # Con fecha_pub presente, Alert.fecha_evento == fecha_pub
    assert params[16] == _FECHA_PUB  # fecha_publicacion
    assert params[17] == _FECHA_PUB  # fecha_evento


def test_url_none_usa_placeholder_sin_url_con_hash(pool_falso):
    alerta = _alerta(url=None)
    _, params = _captura_insert(pool_falso, alerta)

    hash_esperado = PostgresRepository._hash_title(alerta.news.titulo)
    assert params[3] == f"sin-url:{hash_esperado}"


def test_url_vacia_usa_placeholder_sin_url_con_hash(pool_falso):
    alerta = _alerta(url="")
    _, params = _captura_insert(pool_falso, alerta)

    hash_esperado = PostgresRepository._hash_title(alerta.news.titulo)
    assert params[3] == f"sin-url:{hash_esperado}"


def test_url_presente_se_guarda_tal_cual(pool_falso):
    alerta = _alerta(url="https://ejemplo.test/nota-1")
    _, params = _captura_insert(pool_falso, alerta)
    assert params[3] == "https://ejemplo.test/nota-1"


# ============================================================
# (e) Pool — putconn según el desenlace de la operación
# ============================================================

def test_exito_devuelve_la_conexion_con_close_false(pool_falso):
    pool_falso.cursor.fetchone.return_value = None
    _repo().is_duplicate("titulo", "https://ejemplo.test/n", "fuente")

    pool_falso.conn.commit.assert_called_once()
    pool_falso.pool.putconn.assert_called_once_with(pool_falso.conn, close=False)


def test_operational_error_descarta_la_conexion_con_close_true(pool_falso):
    pool_falso.cursor.execute.side_effect = psycopg2.OperationalError(
        "server closed the connection unexpectedly"
    )
    with pytest.raises(psycopg2.OperationalError):
        _repo().is_duplicate("titulo", "https://ejemplo.test/n", "fuente")

    # Conexión rota: ni commit ni rollback, y se descarta del pool
    pool_falso.conn.rollback.assert_not_called()
    pool_falso.pool.putconn.assert_called_once_with(pool_falso.conn, close=True)
