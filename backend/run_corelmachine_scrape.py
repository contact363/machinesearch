"""
Standalone Corel Machines scraper — 3-step sync identical to VIB-KG.

  Step 1 — Fetch all live product URLs from Corel API
  Step 2 — Save any NEW machines to database
  Step 3 — Find URLs in DB but NOT on Corel anymore
              → Check each URL status
              → 404 = deleted by seller  — remove from DB
              → No content/title = machine sold — remove from DB

Run from backend/: python run_corelmachine_scrape.py
"""
import asyncio
import os
import sys
import uuid
import logging
import re
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
logger = logging.getLogger("corelmachine_runner")

API_BASE  = "https://corelmachine.com/api"
SITE_BASE = "https://www.corelmachines.com"
SITE_NAME = "corelmachine"
DELAY     = 0.5  # seconds between API calls


def _extract_brand(title: str) -> str | None:
    """Extract first meaningful word as brand from machine title."""
    if not title:
        return None
    skip = {"TON", "USED", "NEW", "EX-DEMO", "SECOND-HAND", "INCH", "MM", "AXIS"}
    for part in title.strip().split():
        clean = part.upper().rstrip(".")
        if re.match(r"^\d", clean):
            continue
        if clean in skip:
            continue
        return clean
    return None


def _parse_specs(html_desc: str) -> dict:
    """Strip HTML and extract key:value spec lines from description."""
    if not html_desc:
        return {}
    clean = re.sub(r"<[^>]+>", "\n", html_desc)
    specs = {}
    for line in clean.splitlines():
        line = line.strip()
        if not line or len(line) < 3:
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip()
            if key and val and len(key) < 60:
                specs[key] = val
    return specs


async def main():
    import httpx
    from bs4 import BeautifulSoup
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy import select as sa_select, delete as sa_delete
    from database.models import Machine

    db_url = os.getenv("DATABASE_URL", "")
    for prefix in ("postgres://", "postgresql://"):
        if db_url.startswith(prefix):
            db_url = "postgresql+asyncpg://" + db_url[len(prefix):]

    engine_db = create_async_engine(db_url, echo=False, pool_pre_ping=True, pool_size=2, max_overflow=3)
    SessionLocal = async_sessionmaker(bind=engine_db, expire_on_commit=False, autoflush=False)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    # ── Step 1: fetch all live products from Corel API ────────────────
    logger.info("Step 1 — Fetching all live products from Corel API...")
    all_products: list[dict] = []

    async with httpx.AsyncClient(headers=headers, timeout=30, follow_redirects=True) as client:
        resp = await client.get(f"{API_BASE}/subcategory/all")
        resp.raise_for_status()
        subcategories = resp.json()
        logger.info("Found %d subcategories", len(subcategories))

        for cat in subcategories:
            slug = cat.get("url", "")
            cat_title = cat.get("title", slug)
            parent_cat = cat.get("category", {}).get("name", "")
            if not slug:
                continue
            try:
                await asyncio.sleep(DELAY)
                prod_resp = await client.get(f"{API_BASE}/product/{slug}")
                prod_resp.raise_for_status()
                products = prod_resp.json()
                if not isinstance(products, list):
                    continue
                for p in products:
                    p["_sub_category_name"] = cat_title
                    p["_parent_category"] = parent_cat
                    p["_sub_category_slug"] = slug
                    all_products.append(p)
                logger.info("  %s (%s): %d products", cat_title, parent_cat, len(products))
            except Exception as exc:
                logger.warning("  Failed %s: %s", slug, exc)

    logger.info("Total live products from API: %d", len(all_products))

    # Build the set of all live source URLs
    live_urls: set[str] = set()
    for p in all_products:
        prod_slug = p.get("url", "")
        sub_slug  = p.get("_sub_category_slug", "")
        if prod_slug:
            url = f"{SITE_BASE}/usedmachinestocklist/{sub_slug}/{prod_slug}"
        else:
            url = f"{SITE_BASE}/usedmachinestocklist/{sub_slug}"
        live_urls.add(url)

    # ── Step 2: save any NEW machines to DB ───────────────────────────
    logger.info("Step 2 — Saving new machines to DB...")
    new_count  = 0
    skip_count = 0

    async with SessionLocal() as session:
        for i, p in enumerate(all_products, 1):
            title = (p.get("title") or "").strip()
            if not title:
                skip_count += 1
                continue

            prod_slug = p.get("url", "")
            sub_slug  = p.get("_sub_category_slug", "")
            source_url = (
                f"{SITE_BASE}/usedmachinestocklist/{sub_slug}/{prod_slug}"
                if prod_slug
                else f"{SITE_BASE}/usedmachinestocklist/{sub_slug}"
            )

            brand        = _extract_brand(title)
            machine_type = p.get("_sub_category_name") or p.get("_parent_category") or None
            year_raw     = str(p.get("year_of_construction") or "")
            year         = None
            if year_raw:
                m = re.search(r"\b(19|20)\d{2}\b", year_raw)
                year = int(m.group()) if m else None

            catalog_id = str(p.get("reference_no", "")) if p.get("reference_no") else None

            desc_html   = p.get("description") or ""
            specs       = _parse_specs(desc_html)
            if p.get("capacity"):
                specs["Capacity"] = p["capacity"]
            description = re.sub(r"<[^>]+>", " ", desc_html).strip() or None

            raw_images  = p.get("image") or []
            images      = []
            if isinstance(raw_images, list):
                sorted_imgs = sorted(raw_images, key=lambda x: (not x.get("is_featured", False), int(x.get("order") or 99)))
                images = [img["image"] for img in sorted_imgs if img.get("image")]
            image_url    = images[0] if images else None
            extra_images = images[1:] if len(images) > 1 else None

            try:
                stmt = pg_insert(Machine).values(
                    id=uuid.uuid4(),
                    name=title[:500],
                    brand=brand or None,
                    price=None,
                    currency="USD",
                    location="India",
                    image_url=image_url,
                    extra_images=extra_images,
                    description=description,
                    specs=specs if specs else None,
                    source_url=source_url,
                    site_name=SITE_NAME,
                    language="en",
                    machine_type=machine_type,
                    year_of_manufacture=year,
                    condition="used",
                    catalog_id=catalog_id,
                    is_trained=False,
                    is_featured=False,
                    view_count=0,
                    click_count=0,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                ).on_conflict_do_nothing(index_elements=["source_url"])
                result = await session.execute(stmt)
                await session.commit()
                if result.rowcount > 0:
                    new_count += 1
                    logger.info(
                        "[%d/%d] SAVED: %s | Brand:%s | Type:%s | Year:%s | Imgs:%d",
                        i, len(all_products), title[:35], brand,
                        (machine_type or "?")[:25], year, len(images),
                    )
                else:
                    skip_count += 1
            except Exception as exc:
                await session.rollback()
                logger.warning("[%d/%d] FAILED %s: %s", i, len(all_products), title[:30], exc)
                skip_count += 1

    logger.info("=" * 60)
    logger.info("Corel Machines scrape COMPLETE")
    logger.info("  Total products : %d", len(all_products))
    logger.info("  Saved to DB    : %d", new_count)
    logger.info("  Skipped/dupes  : %d", skip_count)
    logger.info("=" * 60)

    # ── Step 3: sync deletions — remove sold/gone machines from DB ─────
    # Any URL in our DB that is no longer in the live API set
    # gets its status checked. If 404 / no machine content → delete from DB.
    logger.info("Step 3 — Syncing deletions: checking for sold/removed machines...")

    async with SessionLocal() as session:
        result = await session.execute(
            sa_select(Machine.id, Machine.source_url).where(Machine.site_name == SITE_NAME)
        )
        db_machines = result.all()

    missing = [(row.id, row.source_url) for row in db_machines if row.source_url not in live_urls]
    logger.info("  URLs in DB not in live API: %d — checking each...", len(missing))

    deleted_count = 0
    async with httpx.AsyncClient(headers=headers, timeout=15, follow_redirects=True) as client:
        async with SessionLocal() as session:
            for machine_id, url in missing:
                try:
                    await asyncio.sleep(1)
                    resp = await client.get(url)

                    # 404 = deleted by seller
                    if resp.status_code == 404:
                        await session.execute(sa_delete(Machine).where(Machine.id == machine_id))
                        await session.commit()
                        deleted_count += 1
                        logger.info("  DELETED (404): %s", url[-70:])
                        continue

                    # Page exists — check if machine content is still there
                    soup_check = BeautifulSoup(resp.text, "lxml")
                    # Corelmachines uses Next.js — check for product title in __NEXT_DATA__ or h1
                    h1 = soup_check.find("h1")
                    next_data = soup_check.find("script", id="__NEXT_DATA__")
                    has_content = bool(h1) or bool(next_data and "title" in (next_data.string or ""))

                    if not has_content:
                        # No machine title = sold / page emptied
                        await session.execute(sa_delete(Machine).where(Machine.id == machine_id))
                        await session.commit()
                        deleted_count += 1
                        logger.info("  DELETED (no content): %s", url[-70:])

                except Exception as exc:
                    logger.warning("  CHECK FAILED %s: %s", url[-60:], exc)

    logger.info("Sync complete — deleted %d sold/removed Corel machines from DB", deleted_count)
    logger.info("=" * 60)
    await engine_db.dispose()


if __name__ == "__main__":
    asyncio.run(main())
