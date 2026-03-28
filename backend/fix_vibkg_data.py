"""
Re-fetch every VIB-KG machine detail page and update existing DB records
with correct brand, machine_type, year, condition, specs, images.

Run from backend/: python fix_vibkg_data.py
"""
import asyncio, os, sys, logging, re
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("vibkg_fix")

DELAY = 3
BASE_URL = "https://vib-kg.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def parse_vibkg_detail(html: str, source_url: str) -> dict | None:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")

    h1 = soup.find("h1")
    name = h1.get_text(strip=True) if h1 else ""
    if not name:
        return None

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

    skip_labels = {"PreviousNext", "Price", "Manufacturer Page"}
    specs = {k: v for k, v in specs_raw.items() if k not in skip_labels and v and v != "Request price"}

    # Images — collect only from the main article folder
    article_imgs: list[str] = []
    for img_tag in soup.find_all("img", src=re.compile(r"/data/article/")):
        src = img_tag["src"]
        if "thumbs" not in src:
            article_imgs.append(src)
    for tag in soup.find_all(style=True):
        for m in re.finditer(r"url\('(/data/article/[^']+)'\)", tag["style"]):
            path = m.group(1)
            if "thumbs" not in path and path not in article_imgs:
                article_imgs.append(path)

    main_article_id: str | None = None
    if article_imgs:
        m2 = re.match(r"/data/article/(\d+)/", article_imgs[0])
        if m2:
            main_article_id = m2.group(1)

    if main_article_id:
        machine_imgs = [
            BASE_URL + p for p in article_imgs
            if re.match(rf"/data/article/{re.escape(main_article_id)}/", p)
        ]
    else:
        machine_imgs = [BASE_URL + p for p in article_imgs[:10]]

    return {
        "name": name,
        "brand": brand or None,
        "condition": condition or None,
        "machine_type": machine_type or None,
        "location": location or "Germany",
        "catalog_id": catalog_id or None,
        "year_of_manufacture": year,
        "image_url": machine_imgs[0] if machine_imgs else None,
        "extra_images": machine_imgs[1:] if len(machine_imgs) > 1 else None,
        "specs": specs if specs else None,
    }


async def main():
    import httpx
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import text, select
    from database.models import Machine

    db_url = os.getenv("DATABASE_URL", "")
    for prefix in ("postgres://", "postgresql://"):
        if db_url.startswith(prefix):
            db_url = "postgresql+asyncpg://" + db_url[len(prefix):]

    engine = create_async_engine(db_url, echo=False, pool_pre_ping=True, pool_size=2, max_overflow=3)
    Session = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    async with Session() as s:
        rows = (await s.execute(
            text("SELECT id, source_url FROM machines WHERE site_name='vib-kg' ORDER BY created_at")
        )).fetchall()

    logger.info("Found %d VIB-KG machines to fix", len(rows))
    updated = 0
    failed  = 0

    async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        for i, (machine_id, source_url) in enumerate(rows, 1):
            try:
                await asyncio.sleep(DELAY)
                resp = await client.get(source_url)
                resp.raise_for_status()
                item = parse_vibkg_detail(resp.text, source_url)

                if not item:
                    logger.warning("[%d/%d] No data: %s", i, len(rows), source_url[-60:])
                    failed += 1
                    continue

                async with Session() as s:
                    m = await s.scalar(select(Machine).where(Machine.id == machine_id))
                    if not m:
                        failed += 1
                        continue

                    m.name         = item.get("name") or m.name
                    m.brand        = item.get("brand") or m.brand
                    m.machine_type = item.get("machine_type") or m.machine_type
                    m.condition    = item.get("condition") or m.condition
                    m.location     = item.get("location") or m.location
                    m.catalog_id   = item.get("catalog_id") or m.catalog_id
                    m.image_url    = item.get("image_url") or m.image_url
                    m.extra_images = item.get("extra_images") or m.extra_images
                    m.specs        = item.get("specs") or m.specs
                    yr = item.get("year_of_manufacture")
                    if yr:
                        m.year_of_manufacture = yr
                    m.updated_at = datetime.now(timezone.utc)
                    await s.commit()

                updated += 1
                logger.info(
                    "[%d/%d] OK: %s | Brand:%s | Type:%s | Year:%s | Imgs:%d",
                    i, len(rows),
                    (item.get("name") or "")[:35],
                    item.get("brand", "?"),
                    (item.get("machine_type") or "?")[:25],
                    item.get("year_of_manufacture", "?"),
                    1 + len(item.get("extra_images") or []),
                )

            except Exception as exc:
                failed += 1
                logger.warning("[%d/%d] FAILED %s: %s", i, len(rows), source_url[-50:], exc)

    logger.info("=" * 55)
    logger.info("VIB-KG fix COMPLETE — Updated: %d | Failed: %d", updated, failed)
    logger.info("=" * 55)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
