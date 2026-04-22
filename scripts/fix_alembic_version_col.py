#!/usr/bin/env python3
"""
Fix para compatibilidad de alembic_version con PostgreSQL.
Los nombres de migración del proyecto exceden el default VARCHAR(32).
Este script crea la tabla alembic_version con VARCHAR(128) antes del upgrade.
"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

async def fix_alembic_version_column():
    load_dotenv()
    url = os.environ['DATABASE_URL'].replace('postgresql+asyncpg://', 'postgresql://')
    conn = await asyncpg.connect(url, timeout=10)

    # Si la tabla existe con VARCHAR(32), alterarla
    row = await conn.fetchrow("""
        SELECT character_maximum_length
        FROM information_schema.columns
        WHERE table_name = 'alembic_version' AND column_name = 'version_num'
    """)

    if row is None:
        print("Tabla alembic_version no existe todavía. Creándola con VARCHAR(128)...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num VARCHAR(128) NOT NULL,
                CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
            )
        """)
        print("OK: alembic_version creada con VARCHAR(128).")
    elif row['character_maximum_length'] < 128:
        print(f"Tabla alembic_version tiene VARCHAR({row['character_maximum_length']}). Agrandando a VARCHAR(128)...")
        await conn.execute("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)")
        print("OK: alembic_version ahora es VARCHAR(128).")
    else:
        print(f"OK: alembic_version ya tiene VARCHAR({row['character_maximum_length']}).")

    await conn.close()

if __name__ == '__main__':
    asyncio.run(fix_alembic_version_column())
