"""
Twitter/X source — scrapes recent tweets from monitored accounts using cookie auth.

No se necesita API key oficial. Se autentica con cookies de tu sesión de navegador.

Variables de entorno requeridas:
  TWITTER_AUTH_TOKEN  — valor de la cookie 'auth_token' de tu cuenta de X
  TWITTER_CT0         — valor de la cookie 'ct0' de tu cuenta de X

Cómo obtener las cookies:
  1. Abre x.com en Chrome con tu sesión iniciada
  2. DevTools → Application → Cookies → https://x.com
  3. Copia los valores de auth_token y ct0
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from typing import Optional

import pytz

from app.domain.models import NewsItem
from app.domain.ports import NewsSource

CENTRAL_TZ = pytz.timezone("America/Chicago")

# Cuentas a monitorear — relevantes para la zona Costco Monterrey
TWITTER_ACCOUNTS = [
    # ── Generales MTY ──────────────────────────────────────
    {"handle": "pc_mty",            "nombre": "Protección Civil MTY"},
    {"handle": "mtytrafico",        "nombre": "Tráfico MTY"},
    {"handle": "seguridadmtymx",    "nombre": "Seguridad Monterrey"},
    {"handle": "QueSucedeEnMty",    "nombre": "Qué Sucede en MTY"},
    # ── Carretera Nacional ─────────────────────────────────
    {"handle": "Kilometro264",      "nombre": "Carretera Nacional km 264"},
    {"handle": "GN_Carreteras",     "nombre": "Guardia Nacional Carreteras"},
    # ── Cumbres / San Pedro ────────────────────────────────
    {"handle": "SSPCMonterrey",     "nombre": "SSPC Monterrey"},
    {"handle": "Rescate911SP",      "nombre": "Rescate 911 San Pedro"},
    # ── Valle Oriente / Lázaro Cárdenas ───────────────────
    {"handle": "TraficoenMty",      "nombre": "Tráfico en Monterrey"},
    {"handle": "SanPedroNL",        "nombre": "Municipio San Pedro"},
]

# Cuántos tweets por cuenta (los más recientes)
TWEETS_PER_ACCOUNT = 15

# Nombre de usuario ficticio para el pool de twscrape
_POOL_USERNAME = "costco_monitor_account"


class TwitterSource(NewsSource):
    """
    Recolecta tweets de cuentas clave usando autenticación por cookies.

    El método collect() es síncrono por compatibilidad con el pipeline.
    Internamente usa asyncio para twscrape.
    """

    def source_name(self) -> str:
        return "Twitter/X"

    def collect(self) -> list[NewsItem]:
        auth_token = os.getenv("TWITTER_AUTH_TOKEN", "").strip()
        ct0 = os.getenv("TWITTER_CT0", "").strip()

        if not auth_token or not ct0:
            print("  ⚠️ Twitter desactivado — configura TWITTER_AUTH_TOKEN y TWITTER_CT0")
            return []

        try:
            return asyncio.run(self._collect_async(auth_token, ct0))
        except RuntimeError as e:
            # Si ya hay un event loop activo (e.g., Jupyter / uvicorn)
            if "cannot run nested" in str(e).lower():
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(self._collect_async(auth_token, ct0))
            print(f"  ⚠️ Twitter: error de event loop — {e}")
            return []
        except Exception as e:
            print(f"  ⚠️ Twitter: error inesperado — {e}")
            return []

    # ── Private ──────────────────────────────────────────────────────────────

    async def _collect_async(self, auth_token: str, ct0: str) -> list[NewsItem]:
        try:
            import twscrape
        except ImportError:
            print("  ⚠️ twscrape no instalado — ejecuta: pip install twscrape")
            return []

        proxy = os.getenv("TWITTER_PROXY")
        api = twscrape.API(proxy=proxy)
        if proxy:
            print(f"  🌐 Twitter: usando proxy")

        # Registrar cuenta con cookies (twscrape usa cookies; password es placeholder)
        cookies_str = f"auth_token={auth_token}; ct0={ct0}"
        try:
            await api.pool.add_account(
                username=_POOL_USERNAME,
                password="placeholder_not_used",
                email="placeholder@placeholder.com",
                email_password="placeholder_not_used",
                cookies=cookies_str,
            )
            # No llamar login_all() — con cookie auth la cuenta ya está autenticada.
            # login_all() es para user/password y causa IndexError con cookie auth.
        except Exception as e:
            print(f"  ⚠️ Twitter: error al configurar cookies — {e}")
            return []

        items: list[NewsItem] = []
        seen_ids: set[int] = set()

        for account in TWITTER_ACCOUNTS:
            handle = account["handle"]
            nombre = account["nombre"]
            try:
                fetched = await self._scrape_account(api, handle, nombre, seen_ids)
                items.extend(fetched)
            except Exception as e:
                print(f"  ⚠️ Twitter @{handle}: {e}")

        print(f"  ✓ Twitter: {len(items)} tweets recolectados de {len(TWITTER_ACCOUNTS)} cuentas")
        return items

    async def _scrape_account(
        self,
        api,
        handle: str,
        nombre: str,
        seen_ids: set[int],
    ) -> list[NewsItem]:
        items: list[NewsItem] = []

        try:
            user = await api.user_by_login(handle)
        except Exception:
            return items

        if not user:
            return items

        async for tweet in api.user_tweets(user.id, limit=TWEETS_PER_ACCOUNT):
            if tweet.id in seen_ids:
                continue
            seen_ids.add(tweet.id)

            # Convertir fecha a zona horaria Central
            fecha: Optional[datetime] = None
            if tweet.date:
                fecha = tweet.date.astimezone(CENTRAL_TZ)

            url = f"https://x.com/{handle}/status/{tweet.id}"
            texto = tweet.rawContent or ""

            items.append(
                NewsItem(
                    titulo=texto[:280],        # Twitter limit
                    contenido=texto,
                    url=url,
                    fuente=f"Twitter @{handle} — {nombre}",
                    fecha_pub=fecha,
                    source_type="twitter",
                )
            )

        return items
