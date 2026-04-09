"""
Standalone BG Used Industry scraper runner — saves each machine to DB.
Run from: backend/ directory
  python run_bg_used_industry_scrape.py
"""
import asyncio
import os
import sys
import uuid
import logging
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("bg_used_industry_runner")

SITE_NAME = "bg-used-industry"
CONFIG = {
    "name": SITE_NAME,
    "display_name": "BG Used Industry",
    "base_url": "https://www.bg-used-industry.com",
    "start_url": "https://www.bg-used-industry.com/?lng=en",
    "mode": "static",
    "language": "en",
    "default_location": "Bulgaria",
    "id_scan_start": 3600,
    "rate_limit_delay": 1,
}


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

    # Parse price — strip currency symbol, convert to float
    price_raw = item.get("price") or ""
    price_val = None
    currency = item.get("currency") or "EUR"
    if price_raw and str(price_raw).strip():
        import re
        nums = re.findall(r"[\d\s\u00a0\.,]+", str(price_raw))
        if nums:
            try:
                cleaned = nums[0].replace("\xa0", "").replace(" ", "").replace(",", ".")
                price_val = float(cleaned)
            except ValueError:
                price_val = None

    try:
        stmt = pg_insert(Machine).values(
            id=uuid.uuid4(),
            name=name,
            brand=(item.get("brand") or None),
            price=price_val,
            currency=currency,
            location=(item.get("location") or "Bulgaria"),
            image_url=(item.get("image_url") or None),
            extra_images=(item.get("extra_images") or None),
            description=(item.get("description") or None),
            specs=(item.get("specs") or None),
            source_url=source_url,
            site_name=SITE_NAME,
            language="en",
            machine_type=(item.get("machine_type") or None),
            year_of_manufacture=_year,
            condition="used",
            catalog_id=(item.get("catalog_id") or None),
            country_of_origin=None,
            video_url=None,
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
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy import select as sa_select
    from database.models import Machine
    from database.db import Base
    from database import models  # noqa
    from scraper.engine import AdaptiveEngine
    import httpx
    from bs4 import BeautifulSoup
    import re

    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    if not db_url:
        logger.error("DATABASE_URL not set in .env")
        return

    engine_db = create_async_engine(db_url, echo=False, pool_pre_ping=True, pool_size=2, max_overflow=3)
    SessionLocal = async_sessionmaker(bind=engine_db, expire_on_commit=False, autoflush=False)

    async with engine_db.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("DB tables OK")

    # ── Load already-scraped URLs from DB (for resume support) ──────────
    async with SessionLocal() as session:
        result = await session.execute(
            sa_select(Machine.source_url).where(Machine.site_name == SITE_NAME)
        )
        already_done = set(row[0] for row in result.all())
    logger.info("Already in DB: %d machines — will skip these", len(already_done))

    scraper = AdaptiveEngine()
    base_url = CONFIG["base_url"]
    id_scan_start = CONFIG["id_scan_start"]
    headers = scraper._ua.get_headers(base_url)

    new_count = 0
    skip_count = 0
    seen_ids: set[int] = set()

    logger.info("=" * 60)
    logger.info("BG Used Industry full scrape — SAVE-AS-YOU-GO (resumable)")
    logger.info("  Pass 1: 181 category pages (10 most recent each)")
    logger.info("  Pass 2: ID scan from %d to max", id_scan_start)
    logger.info("=" * 60)

    async with httpx.AsyncClient(headers=headers, timeout=30, follow_redirects=True) as client:
        async with SessionLocal() as session:

            # ── Pass 1: category listing pages ──────────────────────────
            try:
                resp = await client.get(f"{base_url}/?lng=en")
                resp.raise_for_status()
            except Exception as exc:
                logger.error("Failed to fetch homepage: %s", exc)
                return

            soup = BeautifulSoup(resp.text, "lxml")
            cat_links: dict[str, str] = {}
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                if "t_c=" in href and "t=" in href and "lng=en" in href:
                    cat_name = a.get_text(strip=True)
                    if cat_name and href not in cat_links:
                        cat_links[href] = cat_name

            logger.info("Found %d category links", len(cat_links))

            detail_map: dict[str, str] = {}
            for cat_href, cat_name in cat_links.items():
                from urllib.parse import urljoin
                cat_url = urljoin(base_url + "/", cat_href.lstrip("./"))
                try:
                    await asyncio.sleep(1)
                    r = await client.get(cat_url)
                    r.raise_for_status()
                except Exception as exc:
                    logger.warning("Category '%s' failed: %s", cat_name, exc)
                    continue
                cat_soup = BeautifulSoup(r.text, "lxml")
                for tdprd in cat_soup.find_all("td", class_="TdPrd"):
                    link_el = tdprd.find("a", class_="topmenuCopy")
                    if link_el:
                        href = link_el.get("href", "")
                        if href:
                            detail_url = urljoin(base_url + "/", href)
                            if detail_url not in detail_map:
                                detail_map[detail_url] = cat_name
                            m_id = re.search(r"id=(\d+)", href)
                            if m_id:
                                seen_ids.add(int(m_id.group(1)))

            logger.info("Pass 1: %d unique machine URLs found", len(detail_map))

            # Scrape + save Pass 1 detail pages immediately
            total = len(detail_map)
            for i, (detail_url, machine_type) in enumerate(detail_map.items(), 1):
                if detail_url in already_done:
                    skip_count += 1
                    logger.debug("[%d/%d] SKIP (already in DB): %s", i, total, detail_url[-50:])
                    continue
                try:
                    await asyncio.sleep(1)
                    resp = await client.get(detail_url)
                    resp.raise_for_status()
                    item = scraper._parse_bg_used_industry_detail(
                        resp.text, detail_url, base_url, SITE_NAME, machine_type
                    )
                    if item:
                        saved = await save_item(session, item, pg_insert, Machine)
                        if saved:
                            new_count += 1
                            already_done.add(detail_url)
                            if new_count % 50 == 0 or new_count <= 3:
                                logger.info(
                                    "[%d/%d] SAVED #%d: %s | %s | yr=%s",
                                    i, total, new_count,
                                    (item.get("name") or "")[:35],
                                    (item.get("machine_type") or "")[:20],
                                    item.get("year_of_manufacture") or "?",
                                )
                        else:
                            skip_count += 1
                    else:
                        skip_count += 1
                except Exception as exc:
                    logger.warning("[%d/%d] FAILED %s: %s", i, total, detail_url[-50:], exc)

            logger.info("Pass 1 done — saved %d new, skipped %d", new_count, skip_count)

            # ── Pass 2: ID scan for hidden machines ─────────────────────
            id_max = max(seen_ids) if seen_ids else id_scan_start + 500
            logger.info(
                "Pass 2: scanning IDs %d → %d (%d to check, %d already seen)",
                id_scan_start, id_max, id_max - id_scan_start + 1, len(seen_ids),
            )
            p2_new = 0
            for machine_id in range(id_scan_start, id_max + 1):
                if machine_id in seen_ids:
                    continue
                detail_url = f"{base_url}/indexd?id={machine_id}&lng=en"
                if detail_url in already_done:
                    continue
                try:
                    await asyncio.sleep(1)
                    resp = await client.get(detail_url)
                    resp.raise_for_status()
                    if 'class="id_number"' not in resp.text:
                        continue
                    item = scraper._parse_bg_used_industry_detail(
                        resp.text, detail_url, base_url, SITE_NAME, ""
                    )
                    if item:
                        saved = await save_item(session, item, pg_insert, Machine)
                        if saved:
                            new_count += 1
                            p2_new += 1
                            already_done.add(detail_url)
                            logger.info(
                                "ID %d SAVED: %s | yr=%s",
                                machine_id,
                                (item.get("name") or "")[:40],
                                item.get("year_of_manufacture") or "?",
                            )
                except Exception as exc:
                    logger.debug("ID %d failed: %s", machine_id, exc)

            logger.info("Pass 2 done — %d additional machines saved", p2_new)

    logger.info("=" * 60)
    logger.info("BG Used Industry scrape COMPLETE")
    logger.info("  Total saved to DB : %d", new_count)
    logger.info("  Skipped (dupes)   : %d", skip_count)
    logger.info("=" * 60)

    await engine_db.dispose()


if __name__ == "__main__":
    asyncio.run(main())
