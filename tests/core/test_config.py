from __future__ import annotations

import pytest

from src.core.config import Environment, LogLevel, Settings


def _make_settings(**overrides: str) -> Settings:
    base = {
        "database_url": "postgresql+asyncpg://user:pass@localhost/testdb",
        "anthropic_api_key": "sk-test-key",
        "telegram_bot_token": "123456:ABC",
        "telegram_chat_id": "-100123456",
    }
    base.update(overrides)
    return Settings.model_validate(base)


def test_defaults() -> None:
    s = _make_settings()
    assert s.log_level is LogLevel.INFO
    assert s.environment is Environment.dev
    assert s.is_prod is False


def test_prod_environment() -> None:
    s = _make_settings(environment="prod")
    assert s.is_prod is True
    assert s.environment is Environment.prod


def test_coerce_plain_postgresql_scheme() -> None:
    s = _make_settings(database_url="postgresql://user:pass@localhost/db")
    assert str(s.database_url).startswith("postgresql+asyncpg://")


def test_coerce_legacy_postgres_scheme() -> None:
    s = _make_settings(database_url="postgres://user:pass@localhost/db")
    assert str(s.database_url).startswith("postgresql+asyncpg://")


def test_invalid_environment_raises() -> None:
    with pytest.raises(Exception):
        _make_settings(environment="staging")


def test_log_level_case_insensitive() -> None:
    s = _make_settings(log_level="debug")
    assert s.log_level is LogLevel.DEBUG
