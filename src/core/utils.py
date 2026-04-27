from __future__ import annotations

import re


def mask_db_url(url: str) -> str:
    """Mask the password in a DATABASE_URL for safe logging.

    Input:  postgresql+asyncpg://user:secret@host:5432/db
    Output: postgresql+asyncpg://user:***@host:5432/db
    """
    return re.sub(r"(://[^:]+:)[^@]+(@)", r"\1***\2", url)
