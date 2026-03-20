"""
Alembic environment — async SQLAlchemy with asyncpg.

Reads DATABASE_URL from .env, imports all ORM models so Alembic can
auto-generate migrations, and runs migrations against the async engine.
"""

import asyncio
import os
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Load .env so DATABASE_URL is available
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Alembic Config object — gives access to the .ini file
config = context.config

# Override sqlalchemy.url with value from .env (never hardcoded)
db_url = os.getenv("DATABASE_URL", "")
if not db_url:
    raise RuntimeError("DATABASE_URL is not set in .env")
config.set_main_option("sqlalchemy.url", db_url)

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import Base and all models so their tables appear in metadata
from database.db import Base          # noqa: E402
import database.models                # noqa: E402, F401 — registers all tables

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline migration (generates SQL without a live DB connection)
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migration (runs against a live async DB connection)
# ---------------------------------------------------------------------------
def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations inside a sync wrapper."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
