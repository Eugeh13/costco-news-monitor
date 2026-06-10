"""
Nitter source — recolecta tweets de cuentas clave vía RSS de instancias Nitter.

Reemplazó a TwitterSource (twscrape, ya eliminado) sin cookies, proxies ni API:
Railway le pega a una instancia pública de Nitter (su backend hace el scraping),
así que la IP de datacenter de Railway deja de importar.

Estrategia de resiliencia: lista de instancias con fallback. Si la primera no
responde para una cuenta, prueba la siguiente. La primera instancia que funcione
se recuerda y se prueba primero para el resto de las cuentas del ciclo.

Las instancias de Nitter son frágiles (pueden caer). Actualiza NITTER_INSTANCES
cuando alguna deje de funcionar — ver https://status.d420.de/ para instancias vivas.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import feedparser
import pytz
import requests

from app.domain.models import NewsItem
from app.domain.ports import NewsSource

CENTRAL_TZ = pytz.timezone("America/Chicago")

# Cuentas a monitorear — validadas en vivo vía Nitter el 2026-06-10 por frescura
# (¿Nitter devuelve tweets recientes?) y relevancia por zona. Las cuentas muertas
# o que Nitter sirve obsoletas se removieron.
# (Lista movida aquí desde twitter_source.py al eliminar la vía twscrape.)
TWITTER_ACCOUNTS = [
    # ── Zona Costco Carretera Nacional (sur de MTY) ────────
    {"handle": "AtentosMTYSur",   "nombre": "Atentos MTY Sur (vecinal Carr. Nacional)"},
    {"handle": "autopistasalmty", "nombre": "Autopista Saltillo-Monterrey"},
    {"handle": "reanloficial",    "nombre": "REANL — autopistas/Periférico NL"},
    # ── Zona Costco Valle Oriente (San Pedro) ──────────────
    {"handle": "SanPedroNL",      "nombre": "Municipio San Pedro"},
    # ── Protección Civil / Emergencias (cubren ambas zonas) ─
    {"handle": "pc_nuevoleon",    "nombre": "Protección Civil NL (estatal)"},
    {"handle": "pc_mty",          "nombre": "Protección Civil Monterrey"},
    {"handle": "BomberosNL",      "nombre": "Bomberos Nuevo León"},
    # ── Seguridad ──────────────────────────────────────────
    {"handle": "FuerzaCivil_NL",  "nombre": "Fuerza Civil NL"},
    {"handle": "seguridadmtymx",  "nombre": "Seguridad Monterrey"},
    {"handle": "C5NuevoLeon",     "nombre": "C5 Nuevo León (emergencias)"},
    # ── Tráfico metropolitano ──────────────────────────────
    {"handle": "trafico889",      "nombre": "Radio Tráfico Total"},
]

# Instancias en orden de preferencia. La primera que responda se usa para todas
# las cuentas del ciclo; las demás son respaldo si esa cae.
NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.privacyredirect.com",
    "https://nitter.poast.org",
]

# Máximo de tweets por cuenta (el RSS de Nitter entrega ~20).
TWEETS_PER_ACCOUNT = 15

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


class NitterSource(NewsSource):
    """Recolecta tweets de cuentas clave vía RSS de Nitter, con fallback de instancias."""

    def __init__(self, instances: list[str] | None = None) -> None:
        self._instances = instances or NITTER_INSTANCES
        self._preferred: Optional[str] = None  # instancia que funcionó en este proceso

    def source_name(self) -> str:
        return "Nitter (Twitter/X)"

    def collect(self) -> list[NewsItem]:
        items: list[NewsItem] = []
        cuentas_ok = 0

        for account in TWITTER_ACCOUNTS:
            handle = account["handle"]
            nombre = account["nombre"]
            fetched = self._fetch_account(handle, nombre)
            if fetched:
                cuentas_ok += 1
                items.extend(fetched)

        print(
            f"  ✓ Nitter: {len(items)} tweets de {cuentas_ok}/{len(TWITTER_ACCOUNTS)} cuentas"
            + (f" (instancia: {self._preferred})" if self._preferred else " (ninguna instancia respondió)")
        )
        return items

    # ── Private ──────────────────────────────────────────────

    def _fetch_account(self, handle: str, nombre: str) -> list[NewsItem]:
        """Prueba las instancias en orden hasta que una devuelva tweets."""
        # Prueba primero la instancia que ya funcionó este proceso
        ordered = self._instances
        if self._preferred:
            ordered = [self._preferred] + [i for i in self._instances if i != self._preferred]

        for instance in ordered:
            try:
                entries = self._fetch_rss(instance, handle)
            except Exception as e:
                print(f"  ⚠️ Nitter @{handle} en {instance}: {e}")
                continue

            if entries:
                self._preferred = instance
                return self._to_items(entries, handle, nombre)

        return []

    def _fetch_rss(self, instance: str, handle: str) -> list:
        url = f"{instance}/{handle}/rss"
        response = requests.get(url, headers={"User-Agent": _BROWSER_UA}, timeout=15)
        response.raise_for_status()
        feed = feedparser.parse(response.content)
        return feed.entries[:TWEETS_PER_ACCOUNT]

    def _to_items(self, entries: list, handle: str, nombre: str) -> list[NewsItem]:
        items: list[NewsItem] = []
        for entry in entries:
            texto = (entry.get("title") or "").strip()
            if not texto:
                continue

            tweet_id = entry.get("id") or entry.get("guid") or ""
            # El guid de Nitter es solo el ID numérico → URL canónica de X
            url = (
                f"https://twitter.com/{handle}/status/{tweet_id}"
                if tweet_id.isdigit()
                else entry.get("link", "").replace("#m", "")
            )

            items.append(
                NewsItem(
                    titulo=texto[:280],
                    contenido=texto,
                    url=url or None,
                    fuente=f"Twitter @{handle} — {nombre}",
                    fecha_pub=self._parse_date(entry),
                    source_type="nitter",
                )
            )
        return items

    @staticmethod
    def _parse_date(entry) -> Optional[datetime]:
        # feedparser entrega published_parsed como struct_time en UTC
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        if not parsed:
            return None
        try:
            dt = datetime(*parsed[:6], tzinfo=timezone.utc)
            return dt.astimezone(CENTRAL_TZ)
        except Exception:
            return None
