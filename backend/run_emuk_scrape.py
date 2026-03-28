"""
Standalone EMUK scraper runner.
Run from: backend/ directory
  python run_emuk_scrape.py
"""
import asyncio
import os
import sys
import uuid
import logging
from datetime import datetime, timezone

# ── path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("emuk_runner")

EMUK_CONFIG = {
    "name": "emuk",
    "display_name": "EMUK Werkzeugmaschinen",
    "start_url": "https://emuk.de/en/stock",
    "base_url": "https://emuk.de",
    "mode": "static",
    "pagination_type": "api_emuk",
    "max_pages": 30,
    "detail_page": False,
    "deep_scrape": True,
    "proxy_tier": "none",
    "rate_limit_delay": 2,
    "language": "en",
    "default_location": "Offenbach, Germany",
}


async def main():
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy import select

    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    # ── Ensure tables exist ───────────────────────────────────────────────────
    logger.info("Ensuring DB tables exist...")
    from database.db import Base
    from database import models  # noqa — registers all models
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tables OK")

    # ── Run the scraper ───────────────────────────────────────────────────────
    from scraper.engine import AdaptiveEngine
    engine_obj = AdaptiveEngine()

    logger.info("Starting EMUK scrape...")
    t0 = datetime.now()
    raw_items = await engine_obj.scrape_emuk(EMUK_CONFIG)
    elapsed = (datetime.now() - t0).total_seconds()
    logger.info("Scrape complete in %.1fs — %d raw items", elapsed, len(raw_items))

    if not raw_items:
        logger.warning("No items returned. Exiting.")
        return

    # ── Save to DB ────────────────────────────────────────────────────────────
    from database.models import Machine

    new_count = 0
    skip_count = 0

    async with SessionLocal() as session:
        for item in raw_items:
            source_url = (item.get("source_url") or "").strip()
            if not source_url:
                skip_count += 1
                continue

            name = (item.get("name") or "Unknown")[:500]
            if name == "Unknown" or len(name) < 2:
                skip_count += 1
                continue

            _year = item.get("year_of_manufacture")
            try:
                _year = int(_year) if _year else None
            except (TypeError, ValueError):
                _year = None

            try:
                stmt = pg_insert(Machine).values(
                    id=uuid.uuid4(),
                    name=name,
                    brand=(item.get("brand") or None),
                    price=None,   # EMUK is always price on request
                    currency="EUR",
                    location=(item.get("location") or "Offenbach, Germany"),
                    image_url=(item.get("image_url") or None),
                    description=(item.get("description") or None),
                    specs=(item.get("specs") or None),
                    source_url=source_url,
                    site_name="emuk",
                    language="en",
                    machine_type=(item.get("machine_type") or None),
                    year_of_manufacture=_year,
                    condition=(item.get("condition") or "used"),
                    video_url=(item.get("video_url") or None),
                    catalog_id=(item.get("catalog_id") or None),
                    country_of_origin=(item.get("country_of_origin") or None),
                    extra_images=(item.get("extra_images") or None),
                    is_trained=False,
                    is_featured=False,
                    view_count=0,
                    click_count=0,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                ).on_conflict_do_nothing(index_elements=["source_url"])
                result = await session.execute(stmt)
                if result.rowcount > 0:
                    new_count += 1
            except Exception as exc:
                logger.warning("DB insert failed for %s: %s", source_url, exc)
                continue

        await session.commit()

    logger.info("=" * 60)
    logger.info("EMUK scrape finished!")
    logger.info("  Total scraped : %d", len(raw_items))
    logger.info("  New saved     : %d", new_count)
    logger.info("  Skipped/dupes : %d", len(raw_items) - new_count)
    logger.info("=" * 60)

    # ── Print sample ──────────────────────────────────────────────────────────
    logger.info("Sample of first 5 machines:")
    for m in raw_items[:5]:
        logger.info(
            "  [%s] %s | Type: %s | Year: %s | Image: %s",
            m.get("catalog_id", "?"),
            m.get("name", "?"),
            m.get("machine_type", "?"),
            m.get("year_of_manufacture", "?"),
            "YES" if m.get("image_url") else "NO",
        )


if __name__ == "__main__":
    asyncio.run(main())
