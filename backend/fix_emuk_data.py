"""
Re-fetch every EMUK machine detail page and update existing DB records
with correct brand, machine_type, year, specs, images.

Run from backend/: python fix_emuk_data.py
"""
import asyncio, os, sys, logging, re
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("emuk_fix")

DELAY = 3  # seconds between requests


async def main():
    import httpx
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import text, select
    from database.models import Machine
    from scraper.engine import AdaptiveEngine

    db_url = os.getenv("DATABASE_URL", "")
    for prefix in ("postgres://", "postgresql://"):
        if db_url.startswith(prefix):
            db_url = "postgresql+asyncpg://" + db_url[len(prefix):]

    engine = create_async_engine(db_url, echo=False, pool_pre_ping=True, pool_size=2, max_overflow=3)
    Session = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    scraper = AdaptiveEngine()

    # Get all EMUK source URLs from DB
    async with Session() as s:
        rows = (await s.execute(
            text("SELECT id, source_url FROM machines WHERE site_name='emuk' ORDER BY created_at")
        )).fetchall()

    logger.info("Found %d EMUK machines to fix", len(rows))

    updated = 0
    failed = 0
    headers = scraper._ua.get_headers("https://emuk.de")

    async with httpx.AsyncClient(headers=headers, timeout=30, follow_redirects=True) as client:
        for i, (machine_id, source_url) in enumerate(rows, 1):
            try:
                await asyncio.sleep(DELAY)
                resp = await client.get(source_url)
                resp.raise_for_status()
                item = scraper._parse_emuk_detail(resp.text, source_url, "https://emuk.de", "emuk")

                if not item:
                    logger.warning("[%d/%d] No data parsed: %s", i, len(rows), source_url[-50:])
                    failed += 1
                    continue

                async with Session() as s:
                    m = await s.scalar(select(Machine).where(Machine.id == machine_id))
                    if not m:
                        continue

                    m.name = (item.get("name") or m.name)[:500]
                    m.brand = item.get("brand") or m.brand
                    m.machine_type = item.get("machine_type") or m.machine_type
                    m.location = item.get("location") or m.location
                    m.country_of_origin = item.get("country_of_origin") or m.country_of_origin
                    m.catalog_id = item.get("catalog_id") or m.catalog_id
                    m.video_url = item.get("video_url") or m.video_url
                    m.image_url = item.get("image_url") or m.image_url
                    m.extra_images = item.get("extra_images") or m.extra_images
                    m.description = item.get("description") or m.description
                    m.specs = item.get("specs") or m.specs
                    yr = item.get("year_of_manufacture")
                    if yr:
                        m.year_of_manufacture = yr
                    m.updated_at = datetime.now(timezone.utc)
                    await s.commit()

                updated += 1
                logger.info("[%d/%d] OK: %s | Brand:%s | Type:%s | Year:%s | Img:%s",
                    i, len(rows),
                    (item.get("name") or "")[:35],
                    item.get("brand", "?"),
                    (item.get("machine_type") or "?")[:25],
                    item.get("year_of_manufacture", "?"),
                    "YES" if item.get("image_url") else "NO",
                )

            except Exception as exc:
                failed += 1
                logger.warning("[%d/%d] FAILED %s: %s", i, len(rows), source_url[-40:], exc)
                continue

    logger.info("=" * 55)
    logger.info("Fix complete — Updated: %d | Failed: %d", updated, failed)
    logger.info("=" * 55)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
