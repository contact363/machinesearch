"""
Standalone EMUK scraper runner — saves each machine immediately as scraped.
Run from: backend/ directory
  python run_emuk_scrape.py
"""
import asyncio
import os
import sys
import uuid
import logging
import re
from datetime import datetime, timezone
from urllib.parse import urljoin

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

BASE_URL = "https://emuk.de"
STOCK_URL = "https://emuk.de/en/stock"
MAX_PAGES = 30
DELAY_BETWEEN = 4  # seconds between detail page requests


async def save_item(session, item: dict, pg_insert, Machine) -> bool:
    source_url = (item.get("source_url") or "").strip()
    name = (item.get("name") or "").strip()[:500]
    if not source_url or not name or len(name) < 3:
        return False

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
            price=None,
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
            condition="used",
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
        await session.commit()
        return result.rowcount > 0
    except Exception as exc:
        await session.rollback()
        logger.warning("DB save failed for %s: %s", source_url[:60], exc)
        return False


async def main():
    import httpx
    from bs4 import BeautifulSoup
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from database.models import Machine
    from scraper.engine import AdaptiveEngine

    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine_db = create_async_engine(db_url, echo=False, pool_pre_ping=True, pool_size=2, max_overflow=3)
    SessionLocal = async_sessionmaker(bind=engine_db, expire_on_commit=False, autoflush=False)

    # Ensure tables
    from database.db import Base
    from database import models  # noqa
    async with engine_db.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("DB tables OK")

    scraper = AdaptiveEngine()

    # ── Step 1: collect all detail URLs ──────────────────────────────────
    detail_urls = []
    seen = set()
    headers = scraper._ua.get_headers(BASE_URL)

    async with httpx.AsyncClient(headers=headers, timeout=30, follow_redirects=True) as client:
        for page_num in range(1, MAX_PAGES + 1):
            page_url = f"{STOCK_URL}?page={page_num}"
            logger.info("Listing page %d: %s", page_num, page_url)
            try:
                resp = await client.get(page_url)
                resp.raise_for_status()
            except Exception as exc:
                logger.warning("Listing page %d failed: %s", page_num, exc)
                break

            soup = BeautifulSoup(resp.text, "lxml")
            links = soup.find_all("a", href=re.compile(r"/en/machine/"))
            found = []
            for a in links:
                href = a.get("href", "")
                full = urljoin(BASE_URL, href)
                if full not in seen:
                    seen.add(full)
                    found.append(full)

            if not found:
                logger.info("No links on page %d — stopping.", page_num)
                break

            detail_urls.extend(found)
            logger.info("Page %d: %d links found (total %d)", page_num, len(found), len(detail_urls))
            await asyncio.sleep(2)

    logger.info("Total detail pages to scrape: %d", len(detail_urls))

    # ── Step 2: scrape + save each detail page immediately ───────────────
    new_count = 0
    skip_count = 0

    async with httpx.AsyncClient(headers=headers, timeout=30, follow_redirects=True) as client:
        async with SessionLocal() as session:
            for i, detail_url in enumerate(detail_urls, 1):
                try:
                    await asyncio.sleep(DELAY_BETWEEN)
                    resp = await client.get(detail_url)
                    resp.raise_for_status()
                    item = scraper._parse_emuk_detail(resp.text, detail_url, BASE_URL, "emuk")
                    if item:
                        saved = await save_item(session, item, pg_insert, Machine)
                        if saved:
                            new_count += 1
                            logger.info("[%d/%d] SAVED: %s | %s | %s",
                                i, len(detail_urls),
                                item.get("name", "?")[:40],
                                item.get("machine_type", "?"),
                                item.get("year_of_manufacture", "?"),
                            )
                        else:
                            skip_count += 1
                            logger.info("[%d/%d] SKIP (dupe): %s", i, len(detail_urls), detail_url[-50:])
                    else:
                        skip_count += 1
                        logger.info("[%d/%d] SKIP (no data): %s", i, len(detail_urls), detail_url[-50:])

                except Exception as exc:
                    skip_count += 1
                    logger.warning("[%d/%d] FAILED %s: %s", i, len(detail_urls), detail_url[-50:], exc)
                    continue

    logger.info("=" * 60)
    logger.info("EMUK scrape COMPLETE")
    logger.info("  Total URLs    : %d", len(detail_urls))
    logger.info("  Saved to DB   : %d", new_count)
    logger.info("  Skipped/dupes : %d", skip_count)
    logger.info("=" * 60)
    await engine_db.dispose()


if __name__ == "__main__":
    asyncio.run(main())
