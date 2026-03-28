"""
Re-fetch all Corel machines from their API and update DB records with
correct brand, machine_type, year, specs, extra_images, catalog_id.

Run from backend/: python fix_corel_data.py
"""
import asyncio, os, sys, logging, re, uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("corel_fix")

API_BASE   = "https://corelmachine.com/api"
SITE_BASE  = "https://www.corelmachines.com"


def extract_brand_from_title(title: str) -> str:
    """
    Extract brand from machine title.
    e.g. 'TAKISAWA EX-122 CNC LATHE' -> 'TAKISAWA'
         'DAEWOO PAN20 FLAT BED CNC LATHE' -> 'DAEWOO'
         '2 TON GORBEL ELECTRIC HOIST' -> 'GORBEL'
         '2012 LEADWELL V40 VMC' -> 'LEADWELL'
         '5-AXIS MATSUURA MAM72-25V' -> 'MATSUURA'
    """
    if not title:
        return ""
    # Skip non-brand leading tokens: numbers, measurements, year prefixes, axis counts
    skip = {"TON", "USED", "NEW", "EX-DEMO", "SECOND-HAND", "INCH", "MM"}
    parts = title.strip().split()
    for part in parts:
        clean = part.upper().rstrip(".")
        # Skip purely numeric or starts-with-digit tokens (years, counts, measurements)
        if re.match(r'^\d', clean):
            continue
        # Skip known non-brand words
        if clean in skip:
            continue
        return clean
    return parts[0].upper() if parts else ""


def parse_description_specs(html_desc: str) -> dict:
    """Strip HTML tags and extract key-value specs from description."""
    if not html_desc:
        return {}
    # Remove HTML tags
    clean = re.sub(r"<[^>]+>", "\n", html_desc)
    specs = {}
    for line in clean.splitlines():
        line = line.strip()
        if not line or len(line) < 3:
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if key and val and len(key) < 60:
                specs[key] = val
    return specs


async def main():
    import httpx
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy import select, text
    from database.models import Machine

    db_url = os.getenv("DATABASE_URL", "")
    for prefix in ("postgres://", "postgresql://"):
        if db_url.startswith(prefix):
            db_url = "postgresql+asyncpg://" + db_url[len(prefix):]

    engine = create_async_engine(db_url, echo=False, pool_pre_ping=True, pool_size=2, max_overflow=3)
    Session = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    # ── Step 1: Fetch all products from Corel API ─────────────────────
    all_products = []
    async with httpx.AsyncClient(headers=headers, timeout=30, follow_redirects=True) as client:
        # Get all subcategories
        resp = await client.get(f"{API_BASE}/subcategory/all")
        subcategories = resp.json()
        logger.info("Found %d subcategories", len(subcategories))

        for cat in subcategories:
            slug = cat.get("url", "")
            cat_title = cat.get("title", slug)
            parent_cat = cat.get("category", {}).get("name", "")
            if not slug:
                continue
            try:
                await asyncio.sleep(0.5)
                prod_resp = await client.get(f"{API_BASE}/product/{slug}")
                prod_resp.raise_for_status()
                products = prod_resp.json()
                if not isinstance(products, list):
                    continue
                logger.info("  %s (%s): %d products", cat_title, parent_cat, len(products))
                for p in products:
                    p["_sub_category_name"] = cat_title
                    p["_parent_category"] = parent_cat
                    p["_sub_category_slug"] = slug
                    all_products.append(p)
            except Exception as exc:
                logger.warning("  Failed %s: %s", slug, exc)

    logger.info("Total products from API: %d", len(all_products))

    # ── Step 2: Update each product in DB ────────────────────────────
    updated = 0
    inserted = 0
    skipped = 0

    async with Session() as session:
        for i, p in enumerate(all_products, 1):
            title = (p.get("title") or "").strip()
            if not title:
                skipped += 1
                continue

            prod_url_slug = p.get("url", "")
            sub_slug = p.get("_sub_category_slug", "")
            source_url = f"{SITE_BASE}/usedmachinestocklist/{sub_slug}/{prod_url_slug}" if prod_url_slug else f"{SITE_BASE}/usedmachinestocklist/{sub_slug}"

            # Extract fields
            brand = extract_brand_from_title(title)
            machine_type = p.get("_sub_category_name", "") or p.get("_parent_category", "")
            year_raw = p.get("year_of_construction", "") or ""
            year = None
            if year_raw:
                m = re.search(r"\b(19|20)\d{2}\b", str(year_raw))
                year = int(m.group()) if m else None

            catalog_id = str(p.get("reference_no", "")) if p.get("reference_no") else None

            # Description + specs
            desc_html = p.get("description", "") or ""
            specs = parse_description_specs(desc_html)
            # Add capacity if present
            if p.get("capacity"):
                specs["Capacity"] = p["capacity"]
            description = re.sub(r"<[^>]+>", " ", desc_html).strip() if desc_html else None

            # Images
            raw_images = p.get("image") or []
            images = []
            if isinstance(raw_images, list):
                # Sort by order, prefer featured
                sorted_imgs = sorted(raw_images, key=lambda x: (not x.get("is_featured", False), int(x.get("order") or 99)))
                images = [img["image"] for img in sorted_imgs if img.get("image")]
            image_url = images[0] if images else None
            extra_images = images[1:] if len(images) > 1 else None

            try:
                # Try to find existing record by source_url
                existing = await session.scalar(
                    select(Machine).where(Machine.source_url == source_url)
                )

                if existing:
                    existing.name = title[:500]
                    existing.brand = brand or existing.brand
                    existing.machine_type = machine_type or existing.machine_type
                    existing.year_of_manufacture = year or existing.year_of_manufacture
                    existing.catalog_id = catalog_id or existing.catalog_id
                    existing.image_url = image_url or existing.image_url
                    existing.extra_images = extra_images or existing.extra_images
                    existing.description = description or existing.description
                    existing.specs = specs if specs else existing.specs
                    existing.updated_at = datetime.now(timezone.utc)
                    await session.commit()
                    updated += 1
                    logger.info("[%d/%d] UPDATED: %s | Brand:%s | Type:%s | Year:%s | Imgs:%d",
                        i, len(all_products), title[:35], brand, machine_type[:25] if machine_type else "?", year, len(images))
                else:
                    # Insert new record
                    stmt = pg_insert(Machine).values(
                        id=uuid.uuid4(),
                        name=title[:500],
                        brand=brand or None,
                        price=None,
                        currency="USD",
                        location="India",
                        image_url=image_url,
                        description=description,
                        specs=specs if specs else None,
                        source_url=source_url,
                        site_name="corelmachine",
                        language="en",
                        machine_type=machine_type or None,
                        year_of_manufacture=year,
                        catalog_id=catalog_id,
                        extra_images=extra_images,
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
                        inserted += 1
                        logger.info("[%d/%d] INSERTED: %s | Brand:%s | Type:%s | Year:%s",
                            i, len(all_products), title[:35], brand, machine_type[:25] if machine_type else "?", year)
                    else:
                        skipped += 1

            except Exception as exc:
                await session.rollback()
                logger.warning("[%d/%d] FAILED %s: %s", i, len(all_products), title[:30], exc)
                skipped += 1

    logger.info("=" * 55)
    logger.info("Corel fix COMPLETE")
    logger.info("  Updated  : %d", updated)
    logger.info("  Inserted : %d", inserted)
    logger.info("  Skipped  : %d", skipped)
    logger.info("=" * 55)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
