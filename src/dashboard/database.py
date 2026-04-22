"""
Dashboard-local async DB setup.

Separate from src.core.database because:
- Fase A uses SQLite (aiosqlite) — no pool_size / max_overflow
- Settings.database_url validates as PostgresDsn which rejects sqlite:// URLs
- The dashboard reads DATABASE_URL from env directly, defaulting to SQLite

When Fase A ends and the project moves to PostgreSQL, swap the default URL and
remove the connect_args override.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

load_dotenv()

_raw_url = os.getenv("DATABASE_URL", "")
if _raw_url:
    _raw_url = _raw_url.strip().strip('"\'').lstrip('\ufeff\u200b')

_DATABASE_URL = _raw_url or "sqlite+aiosqlite:///./costco_motor.db"

_connect_args: dict = {}
if _DATABASE_URL.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}

_engine = create_async_engine(
    _DATABASE_URL,
    echo=False,
    connect_args=_connect_args,
)

_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


def get_engine():
    return _engine


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields one AsyncSession per request."""
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DbSession = Annotated[AsyncSession, Depends(get_session)]
