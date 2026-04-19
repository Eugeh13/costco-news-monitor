from __future__ import annotations

from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.core.config import Settings, get_settings


class Base(DeclarativeBase):
    pass


@lru_cache(maxsize=1)
def _build_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        str(settings.database_url),
        echo=not settings.is_prod,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


@lru_cache(maxsize=1)
def _build_sessionmaker(settings: Settings) -> async_sessionmaker[AsyncSession]:
    engine = _build_engine(settings)
    return async_sessionmaker(engine, expire_on_commit=False)


def get_engine(settings: Settings | None = None) -> AsyncEngine:
    return _build_engine(settings or get_settings())


def get_sessionmaker(settings: Settings | None = None) -> async_sessionmaker[AsyncSession]:
    return _build_sessionmaker(settings or get_settings())


async def get_session(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async session per request."""
    session_factory = get_sessionmaker(settings)
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
