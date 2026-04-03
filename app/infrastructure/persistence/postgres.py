"""
PostgreSQL repository — persists and queries incidents.

Implements the NewsRepository port using psycopg2 with proper context managers.
"""

from __future__ import annotations

import hashlib
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional

import pytz

from app.domain.models import Alert
from app.domain.ports import NewsRepository

CENTRAL_TZ = pytz.timezone("America/Chicago")

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


class PostgresRepository(NewsRepository):
    """PostgreSQL-backed incident repository."""

    def __init__(self, database_url: str) -> None:
        if not PSYCOPG2_AVAILABLE:
            raise ImportError("pip install psycopg2-binary")
        self._db_url = database_url

    @contextmanager
    def _connection(self):
        """Context manager for safe connection handling."""
        conn = psycopg2.connect(self._db_url)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ── NewsRepository interface ─────────────────────────────

    def save_incident(self, alert: Alert) -> Optional[int]:
        news_hash = self._hash_title(alert.news.titulo)
        a = alert.analysis
        p = alert.proximity

        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO noticias (
                    noticia_hash, titulo, descripcion, url, fuente,
                    categoria, severidad,
                    ubicacion_texto, latitud, longitud,
                    costco_nombre, costco_distancia_km,
                    victimas, heridos, impacto_trafico, servicios_emergencia,
                    fecha_publicacion, alerta_enviada
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s,
                    %s, %s
                )
                ON CONFLICT (noticia_hash) DO NOTHING
                RETURNING id
                """,
                (
                    news_hash,
                    alert.news.titulo,
                    a.summary,
                    alert.news.url or "",
                    alert.news.fuente,
                    a.category.value,
                    a.severity,
                    a.location.extracted,
                    p.event_coords.lat if p.event_coords else 0,
                    p.event_coords.lon if p.event_coords else 0,
                    p.costco_nombre,
                    p.distancia_km,
                    a.victims,
                    0,  # heridos (legacy field)
                    a.traffic_impact.value,
                    a.emergency_services,
                    alert.news.fecha_pub,
                    True,
                ),
            )
            row = cursor.fetchone()
            if row:
                print(f"  💾 Guardada en DB (ID: {row[0]})")
                return row[0]
            print("  ⚠️ Duplicado en DB, omitida")
            return None

    def is_duplicate(
        self, titulo: str, url: str, fuente: str, max_hours: int = 24
    ) -> bool:
        news_hash = self._hash_title(titulo)
        cutoff = datetime.now(CENTRAL_TZ) - timedelta(hours=max_hours)

        with self._connection() as conn:
            cursor = conn.cursor()
            if url:
                cursor.execute(
                    """
                    SELECT id FROM noticias
                    WHERE (noticia_hash = %s OR (url = %s AND fuente = %s))
                      AND fecha_deteccion >= %s
                    LIMIT 1
                    """,
                    (news_hash, url, fuente, cutoff),
                )
            else:
                cursor.execute(
                    """
                    SELECT id FROM noticias
                    WHERE noticia_hash = %s AND fecha_deteccion >= %s
                    LIMIT 1
                    """,
                    (news_hash, cutoff),
                )
            return cursor.fetchone() is not None

    def get_incidents(
        self,
        hours: int = 24,
        category: Optional[str] = None,
        costco: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        cutoff = datetime.now(CENTRAL_TZ) - timedelta(hours=hours)

        conditions = ["fecha_deteccion >= %s"]
        params: list = [cutoff]

        if category:
            conditions.append("categoria = %s")
            params.append(category)
        if costco:
            conditions.append("costco_nombre ILIKE %s")
            params.append(f"%{costco}%")

        params.append(limit)
        where = " AND ".join(conditions)

        with self._connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                f"""
                SELECT * FROM noticias
                WHERE {where}
                ORDER BY fecha_deteccion DESC
                LIMIT %s
                """,
                params,
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_stats(self, hours: int = 24) -> dict:
        cutoff = datetime.now(CENTRAL_TZ) - timedelta(hours=hours)

        with self._connection() as conn:
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # Total incidents
            cursor.execute(
                "SELECT COUNT(*) as total FROM noticias WHERE fecha_deteccion >= %s",
                (cutoff,),
            )
            total = cursor.fetchone()["total"]

            # By category
            cursor.execute(
                """
                SELECT categoria, COUNT(*) as count
                FROM noticias WHERE fecha_deteccion >= %s
                GROUP BY categoria ORDER BY count DESC
                """,
                (cutoff,),
            )
            by_category = {row["categoria"]: row["count"] for row in cursor.fetchall()}

            # By severity
            cursor.execute(
                """
                SELECT
                    CASE
                        WHEN severidad >= 9 THEN 'critica'
                        WHEN severidad >= 7 THEN 'grave'
                        WHEN severidad >= 5 THEN 'moderada'
                        ELSE 'menor'
                    END as nivel,
                    COUNT(*) as count
                FROM noticias WHERE fecha_deteccion >= %s
                GROUP BY nivel ORDER BY count DESC
                """,
                (cutoff,),
            )
            by_severity = {row["nivel"]: row["count"] for row in cursor.fetchall()}

            # By location
            cursor.execute(
                """
                SELECT costco_nombre, COUNT(*) as count
                FROM noticias WHERE fecha_deteccion >= %s
                GROUP BY costco_nombre ORDER BY count DESC
                """,
                (cutoff,),
            )
            by_costco = {row["costco_nombre"]: row["count"] for row in cursor.fetchall()}

            return {
                "hours": hours,
                "total_incidents": total,
                "by_category": by_category,
                "by_severity": by_severity,
                "by_costco": by_costco,
            }

    def initialize_schema(self) -> bool:
        try:
            with open("database_schema.sql", "r", encoding="utf-8") as f:
                schema_sql = f.read()
            with self._connection() as conn:
                conn.cursor().execute(schema_sql)
            print("  ✓ DB schema initialized")
            return True
        except Exception as e:
            print(f"  ⚠️ Schema init error: {e}")
            return False

    # ── Private ──────────────────────────────────────────────

    @staticmethod
    def _hash_title(titulo: str) -> str:
        normalized = " ".join(titulo.lower().strip().split())
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()
