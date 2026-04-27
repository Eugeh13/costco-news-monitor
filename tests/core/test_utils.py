import pytest
from src.core.utils import mask_db_url


def test_masks_password_asyncpg():
    url = "postgresql+asyncpg://postgres:Tr9mK2pL7xQ4vN8w@postgres.railway.internal:5432/railway"
    assert mask_db_url(url) == "postgresql+asyncpg://postgres:***@postgres.railway.internal:5432/railway"


def test_masks_password_plain_postgres():
    url = "postgresql://user:s3cr3t@localhost:5432/mydb"
    assert mask_db_url(url) == "postgresql://user:***@localhost:5432/mydb"


def test_no_password_unchanged():
    url = "postgresql://user@localhost:5432/mydb"
    assert mask_db_url(url) == "postgresql://user@localhost:5432/mydb"


def test_sqlite_url_unchanged():
    url = "sqlite+aiosqlite:///./costco_motor.db"
    assert mask_db_url(url) == "sqlite+aiosqlite:///./costco_motor.db"


def test_empty_string():
    assert mask_db_url("") == ""


def test_already_masked():
    url = "postgresql+asyncpg://postgres:***@host:5432/db"
    assert mask_db_url(url) == "postgresql+asyncpg://postgres:***@host:5432/db"


def test_long_password():
    url = "postgresql://u:Tr9mK2pL7xQ4vN8wB5jC3dF6gH1sE0aYzRqWoXpImJkUhVgTbSyCnDlEf@host/db"
    result = mask_db_url(url)
    assert "***" in result
    assert "Tr9mK2pL7xQ4vN8w" not in result
