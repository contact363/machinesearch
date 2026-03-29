"""
Standalone VIB-KG scraper — scrapes every machine with full details and saves to DB.
Run from backend/: python run_vibkg_scrape.py
"""
import asyncio, os, sys, uuid, logging, re
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
logger = logging.getLogger("vibkg_runner")

BASE_URL      = "https://vib-kg.com"
LISTING_URL   = "https://vib-kg.com/usedmachines"
DELAY         = 3   # seconds between detail page requests
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def parse_vibkg_detail(html: str, source_url: str) -> dict | None:
    """Parse a VIB-KG machine detail page into a dict."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")

    # ── Name ──────────────────────────────────────────────────────────
    h1 = soup.find("h1")
    name = h1.get_text(strip=True) if h1 else ""
    if not name:
        return None

    # ── Spec rows: div.row > col-X + col-Y ───────────────────────────
    # Collect first occurrence of each label
    specs_raw: dict[str, str] = {}
    for row in soup.find_all("div", class_="row"):
        cols = row.find_all("div", recursive=False)
        if len(cols) == 2:
            label = cols[0].get_text(strip=True)
            value = cols[1].get_text(strip=True)
            if label and value and len(label) < 60 and label not in specs_raw:
                specs_raw[label] = value

    brand        = specs_raw.get("Producer", "")
    model        = specs_raw.get("Model", "")
    condition    = specs_raw.get("Condition", "")
    machine_type = specs_raw.get("Type", "")
    location     = specs_raw.get("Location", "Germany")
    catalog_id   = specs_raw.get("VIB-Nr", "")
    year_raw     = specs_raw.get("Year", "")

    year: int | None = None
    if year_raw:
        m = re.search(r"\b(19|20)\d{2}\b", year_raw)
        year = int(m.group()) if m else None

    # Price is always "Request price" on VIB-KG
    price = None

    # ── Description ───────────────────────────────────────────────────
    desc_div = soup.select_one("[class*='desc']") or soup.select_one(".machine-detail-desc")
    description = desc_div.get_text(strip=True) if desc_div else None

    # Build clean specs dict (skip generic labels)
    skip_labels = {"PreviousNext", "Price", "Manufacturer Page"}
    specs = {k: v for k, v in specs_raw.items() if k not in skip_labels and v and v != "Request price"}

    # ── Images ────────────────────────────────────────────────────────
    # Extract article folder from catalog_id embedded in URL slug
    # e.g. /data/article/2035/Index ABC (01-29434) (1).jpg
    # Strategy: collect all /data/article/ images, pick article_id from first img tag,
    # then keep only images from that same folder.
    article_imgs: list[str] = []

    # From <img src=>
    for img_tag in soup.find_all("img", src=re.compile(r"/data/article/")):
        src = img_tag["src"]
        if "thumbs" not in src:
            article_imgs.append(src)

    # From style="background:url(...)"
    for tag in soup.find_all(style=True):
        for m in re.finditer(r"url\('(/data/article/[^']+)'\)", tag["style"]):
            path = m.group(1)
            if "thumbs" not in path and path not in article_imgs:
                article_imgs.append(path)

    # Determine the article_id for THIS machine = folder of the first image
    main_article_id: str | None = None
    if article_imgs:
        m = re.match(r"/data/article/(\d+)/", article_imgs[0])
        if m:
            main_article_id = m.group(1)

    # Keep only images from the main article folder
    if main_article_id:
        machine_imgs = [
            BASE_URL + p for p in article_imgs
            if re.match(rf"/data/article/{re.escape(main_article_id)}/", p)
        ]
    else:
        machine_imgs = [BASE_URL + p for p in article_imgs[:10]]

    image_url    = machine_imgs[0] if machine_imgs else None
    extra_images = machine_imgs[1:] if len(machine_imgs) > 1 else None

    return {
        "name": name,
        "brand": brand or None,
        "model": model or None,
        "condition": condition or None,
        "machine_type": machine_type or None,
        "location": location or "Germany",
        "catalog_id": catalog_id or None,
        "year_of_manufacture": year,
        "price": price,
        "image_url": image_url,
        "extra_images": extra_images,
        "description": description,
        "specs": specs if specs else None,
        "source_url": source_url,
    }


async def save_item(session, item: dict, pg_insert, Machine) -> bool:
    source_url = (item.get("source_url") or "").strip()
    name       = (item.get("name") or "").strip()[:500]
    if not source_url or not name:
        return False

    try:
        stmt = pg_insert(Machine).values(
            id=uuid.uuid4(),
            name=name,
            brand=(item.get("brand") or None),
            price=None,
            currency="EUR",
            location=(item.get("location") or "Germany"),
            image_url=(item.get("image_url") or None),
            extra_images=(item.get("extra_images") or None),
            description=(item.get("description") or None),
            specs=(item.get("specs") or None),
            source_url=source_url,
            site_name="vib-kg",
            language="en",
            machine_type=(item.get("machine_type") or None),
            year_of_manufacture=(item.get("year_of_manufacture") or None),
            condition=(item.get("condition") or None),
            catalog_id=(item.get("catalog_id") or None),
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
        logger.warning("DB save failed for %s: %s", source_url[-60:], exc)
        return False


async def main():
    from bs4 import BeautifulSoup
    import httpx
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from database.models import Machine

    db_url = os.getenv("DATABASE_URL", "")
    for prefix in ("postgres://", "postgresql://"):
        if db_url.startswith(prefix):
            db_url = "postgresql+asyncpg://" + db_url[len(prefix):]

    engine_db  = create_async_engine(db_url, echo=False, pool_pre_ping=True, pool_size=2, max_overflow=3)
    SessionLocal = async_sessionmaker(bind=engine_db, expire_on_commit=False, autoflush=False)

    # ── Step 1: collect all detail URLs from listing page ─────────────
    logger.info("Fetching listing page: %s", LISTING_URL)
    async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        resp = await client.get(LISTING_URL)
        resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "lxml")
    detail_urls: list[str] = []
    seen: set[str] = set()

    for item in soup.select("li.list-group-item.p-0"):
        a = item.select_one("a.machine-index-link")
        if a and a.get("href"):
            full = urljoin(BASE_URL, a["href"])
            if full not in seen:
                seen.add(full)
                detail_urls.append(full)

    logger.info("Found %d unique machine detail URLs", len(detail_urls))

    # ── Step 2: scrape each detail page and save ───────────────────────
    new_count  = 0
    skip_count = 0

    async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        async with SessionLocal() as session:
            for i, detail_url in enumerate(detail_urls, 1):
                try:
                    await asyncio.sleep(DELAY)
                    resp = await client.get(detail_url)
                    resp.raise_for_status()
                    item = parse_vibkg_detail(resp.text, detail_url)

                    if not item:
                        skip_count += 1
                        logger.warning("[%d/%d] No data: %s", i, len(detail_urls), detail_url[-60:])
                        continue

                    saved = await save_item(session, item, pg_insert, Machine)
                    if saved:
                        new_count += 1
                        logger.info(
                            "[%d/%d] SAVED: %s | Brand:%s | Type:%s | Year:%s | Imgs:%d",
                            i, len(detail_urls),
                            item["name"][:40],
                            item.get("brand", "?"),
                            (item.get("machine_type") or "?")[:25],
                            item.get("year_of_manufacture", "?"),
                            1 + len(item.get("extra_images") or []),
                        )
                    else:
                        skip_count += 1
                        logger.info("[%d/%d] SKIP (dupe): %s", i, len(detail_urls), detail_url[-60:])

                except Exception as exc:
                    skip_count += 1
                    logger.warning("[%d/%d] FAILED %s: %s", i, len(detail_urls), detail_url[-60:], exc)

    logger.info("=" * 60)
    logger.info("VIB-KG scrape COMPLETE")
    logger.info("  Total URLs    : %d", len(detail_urls))
    logger.info("  Saved to DB   : %d", new_count)
    logger.info("  Skipped/dupes : %d", skip_count)
    logger.info("=" * 60)

    # ── Step 3: sync deletions — remove sold/gone machines from DB ─────
    # Any URL in our DB that is no longer on the VIB-KG listing page
    # gets its status checked. If 404 / no machine content → delete from DB.
    logger.info("Starting sync: checking for sold/removed machines...")
    from sqlalchemy import select as sa_select, delete as sa_delete

    live_urls = set(detail_urls)

    async with SessionLocal() as session:
        result = await session.execute(
            sa_select(Machine.id, Machine.source_url).where(Machine.site_name == "vib-kg")
        )
        db_machines = result.all()  # list of (id, source_url)

    # Find URLs in DB but no longer on VIB-KG listing page
    missing = [(row.id, row.source_url) for row in db_machines if row.source_url not in live_urls]
    logger.info("  URLs in DB not on listing page: %d — checking each...", len(missing))

    deleted_count = 0
    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        async with SessionLocal() as session:
            for machine_id, url in missing:
                try:
                    await asyncio.sleep(1)
                    resp = await client.get(url)

                    # 404 or redirect away = definitely gone
                    if resp.status_code == 404:
                        await session.execute(sa_delete(Machine).where(Machine.id == machine_id))
                        await session.commit()
                        deleted_count += 1
                        logger.info("  DELETED (404): %s", url[-70:])
                        continue

                    # Page exists but check if machine content is still there
                    from bs4 import BeautifulSoup as _BS
                    soup_check = _BS(resp.text, "lxml")
                    h1 = soup_check.find("h1")
                    has_specs = soup_check.find("div", class_="row")

                    if not h1 or not has_specs:
                        # No machine title or specs = sold / page emptied
                        await session.execute(sa_delete(Machine).where(Machine.id == machine_id))
                        await session.commit()
                        deleted_count += 1
                        logger.info("  DELETED (no content): %s", url[-70:])

                except Exception as exc:
                    logger.warning("  CHECK FAILED %s: %s", url[-60:], exc)

    logger.info("Sync complete — deleted %d sold/removed machines from DB", deleted_count)
    logger.info("=" * 60)
    await engine_db.dispose()


if __name__ == "__main__":
    asyncio.run(main())
