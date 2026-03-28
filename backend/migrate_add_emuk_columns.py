"""
One-time migration: add new Machine columns for EMUK + training system.
Run from backend/ directory: python migrate_add_emuk_columns.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()


async def main():
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)

    migrations = [
        # Machine extended fields
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS machine_type VARCHAR(200)",
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS year_of_manufacture INTEGER",
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS condition VARCHAR(100)",
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS video_url TEXT",
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS catalog_id VARCHAR(100)",
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS country_of_origin VARCHAR(200)",
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS extra_images JSON",
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS is_trained BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS type_id UUID REFERENCES machine_types(id) ON DELETE SET NULL",
        "ALTER TABLE machines ADD COLUMN IF NOT EXISTS brand_id UUID REFERENCES machine_brands(id) ON DELETE SET NULL",

        # Indexes for new columns
        "CREATE INDEX IF NOT EXISTS idx_machines_is_trained ON machines (is_trained)",
        "CREATE INDEX IF NOT EXISTS idx_machines_type_id ON machines (type_id)",
        "CREATE INDEX IF NOT EXISTS idx_machines_brand_id ON machines (brand_id)",

        # New tables (safe if already exist)
        """CREATE TABLE IF NOT EXISTS machine_types (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(200) NOT NULL UNIQUE,
            aliases JSON,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""",
        """CREATE TABLE IF NOT EXISTS machine_brands (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(200) NOT NULL UNIQUE,
            aliases JSON,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )""",
    ]

    async with engine.begin() as conn:
        for sql in migrations:
            try:
                await conn.execute(text(sql))
                print(f"OK: {sql[:70]}...")
            except Exception as e:
                print(f"SKIP ({e}): {sql[:70]}...")

    print("\nMigration complete!")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
