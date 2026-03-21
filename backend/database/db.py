"""
Database engine, session factory, and initialisation for MachineSearch.

Uses SQLAlchemy 2.0 async engine backed by asyncpg (PostgreSQL).
Connection pool: min_size=2, max_size=10.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://user:password@localhost:5432/machinesearch",
)

# Fix Render's postgres:// to postgresql+asyncpg://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
engine = create_async_engine(
    DATABASE_URL,
    echo=False,                   # set True to log all SQL in dev
    pool_pre_ping=True,           # detect stale connections before use
    pool_size=2,                  # min persistent connections
    max_overflow=8,               # additional connections → total max = 10
    pool_timeout=30,              # seconds to wait for a connection
    pool_recycle=1800,            # recycle connections every 30 min
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# Declarative base shared by all models
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Dependency injection helper
# ---------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — yields an AsyncSession per request and guarantees
    the session is closed (and rolled back on error) when the request ends.

    Usage:
        db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Database initialisation
# ---------------------------------------------------------------------------
_EXTRA_DDL = [
    # Full-text search GIN index across name, brand, description
    """
    CREATE INDEX IF NOT EXISTS idx_machines_fts
    ON machines
    USING GIN(
        to_tsvector(
            'english',
            coalesce(name, '') || ' ' ||
            coalesce(brand, '') || ' ' ||
            coalesce(description, '')
        )
    )
    """,
    # Composite B-tree index for price/location/site_name filter queries
    """
    CREATE INDEX IF NOT EXISTS idx_machines_price_location_site
    ON machines (price, location, site_name)
    """,
]


async def init_db() -> None:
    """
    Create all ORM-mapped tables (if they don't exist) and apply extra DDL.
    Then seed any production site configs that are missing from the DB.

    Safe to call on every startup — all operations are idempotent:
      - CREATE TABLE IF NOT EXISTS
      - CREATE INDEX IF NOT EXISTS
      - INSERT site configs only when the row is absent

    NOTE: for production schema migrations use Alembic instead of this
    function.  Keep this for development / test bootstrapping only.
    """
    # Import models so SQLAlchemy registers them on Base.metadata
    from database import models  # noqa: F401

    async with engine.begin() as conn:
        logger.info("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)

        logger.info("Applying extra DDL (FTS index, composite index)...")
        for ddl in _EXTRA_DDL:
            await conn.execute(text(ddl))

    logger.info("Database initialisation complete.")

    # Restore any production configs missing from the DB (e.g. after a DB wipe).
    # Never overwrites configs that already exist — admin edits are preserved.
    from database.seed_configs import seed_site_configs
    async with AsyncSessionLocal() as session:
        await seed_site_configs(session)
