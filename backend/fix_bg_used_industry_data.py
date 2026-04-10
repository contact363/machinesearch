"""
Re-fetch all BG Used Industry machines and update year + description in DB.

Run from: backend/
    python fix_bg_used_industry_data.py

Uses better parsing: searches full page text for "Year:" and "Location:"
instead of relying on CSS class selectors.
"""
import asyncio
import os
import re
import sys
import logging

sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import httpx
from bs4 import BeautifulSoup
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("bg_fix")

SITE_NAME = "bg-used-industry"
BASE_URL = "https://www.bg-used-industry.com"
DELAY = 1.5  # seconds between requests

# Navigation lines to exclude from description
NAV_LINES = {
    "all machines", "accessories and tooling", "borers", "cleaners",
    "construction machinery", "cutters", "drills", "food processing machinery",
    "forging machinery", "forming machinery", "furnaces, hardeners", "furnaces hardeners",
    "gear machinery", "grinders", "industrial containers", "industrial properties",
    "lathes", "lifting, transport and earthmoving", "lifting transport and earthmoving",
    "machining centres", "machining centers", "manuals",
    "measuring machines and tools", "mining industry", "paper machinery",
    "plastics machinery", "power engineering", "presses", "robots", "shavers",
    "sheet metal machinery", "threading machinery",
    "tube and bar processing machinery", "welders", "wire machinery",
}

# ── DB setup ────────────────────────────────────────────────────────────────
_db_url = os.getenv("DATABASE_URL", "")
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif _db_url.startswith("postgresql://") and "+asyncpg" not in _db_url:
    _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(_db_url, echo=False, pool_pre_ping=True)
Session = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def _parse_page(html: str) -> dict:
    """
    Parse year, location, description from a BG Used Industry detail page.
    Uses full-text search instead of CSS class selectors.
    """
    soup = BeautifulSoup(html, "lxml")
    full_text = soup.get_text(separator="\n")

    year = None
    location = None
    desc_lines = []

    # Year: search full text with regex (it's in a <p> tag, plain text)
    m_year = re.search(r"[Yy]ear\s*:\s*(\d{4})", full_text)
    if m_year:
        year = int(m_year.group(1))

    # Location: search full text with regex
    m_loc = re.search(r"[Ll]ocation\s*:?\s*([A-Za-z][^\n\r]{1,60})", full_text)
    if m_loc:
        location = m_loc.group(1).strip()

    # Description: use body2 and body1 text, skip nav lines
    for tag in soup.find_all(["td", "span", "div", "p"], class_=lambda c: c and ("body" in c.lower())):
        txt = tag.get_text(separator="\n", strip=True)
        for tline in txt.splitlines():
            tline = tline.strip()
            if not tline or len(tline) < 3:
                continue
            if tline.lower() in NAV_LINES:
                continue
            if tline.lower().startswith("all machines"):
                continue
            if re.search(r"year\s*:", tline, re.IGNORECASE):
                continue
            if re.search(r"location\s*:", tline, re.IGNORECASE):
                continue
            if tline not in desc_lines:
                desc_lines.append(tline)

    # Fallback: also check body1 / body2 by class name
    for cls in ["body1", "body2"]:
        for tag in soup.find_all(class_=cls):
            txt = tag.get_text(separator="\n", strip=True)
            for tline in txt.splitlines():
                tline = tline.strip()
                if not tline or len(tline) < 3:
                    continue
                if tline.lower() in NAV_LINES:
                    continue
                if tline.lower().startswith("all machines"):
                    continue
                if re.search(r"year\s*:|location\s*:", tline, re.IGNORECASE):
                    continue
                if tline not in desc_lines:
                    desc_lines.append(tline)

    description = "\n".join(desc_lines[:80]).strip() or None

    return {
        "year_of_manufacture": year,
        "location": location,
        "description": description,
    }


async def main():
    from database.models import Machine

    async with Session() as db:
        result = await db.execute(
            select(Machine.id, Machine.source_url, Machine.year_of_manufacture, Machine.location)
            .where(Machine.site_name == SITE_NAME)
            .order_by(Machine.id)
        )
        rows = result.all()

    logger.info(f"Total machines to re-fetch: {len(rows)}")

    updated = 0
    skipped = 0
    errors = 0

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        for i, row in enumerate(rows, 1):
            machine_id = row.id
            url = row.source_url

            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    errors += 1
                    continue

                parsed = _parse_page(resp.text)

                # Only update if we found better data
                changes = {}
                if parsed["year_of_manufacture"]:
                    changes["year_of_manufacture"] = parsed["year_of_manufacture"]
                if parsed["location"]:
                    changes["location"] = parsed["location"]
                if parsed["description"]:
                    changes["description"] = parsed["description"]

                if changes:
                    async with Session() as db:
                        await db.execute(
                            update(Machine)
                            .where(Machine.id == machine_id)
                            .values(**changes)
                        )
                        await db.commit()
                    updated += 1
                    year_val = parsed.get("year_of_manufacture") or "?"
                    logger.info(f"[{i}/{len(rows)}] UPDATED {url.split('id=')[-1].split('&')[0]} | yr={year_val} desc={'yes' if parsed['description'] else 'no'}")
                else:
                    skipped += 1

                if i % 100 == 0:
                    logger.info(f"── Progress: {i}/{len(rows)} | updated={updated} skipped={skipped} errors={errors}")

                await asyncio.sleep(DELAY)

            except Exception as e:
                logger.warning(f"[{i}] ERROR {url}: {e}")
                errors += 1
                await asyncio.sleep(DELAY)

    logger.info("=" * 60)
    logger.info(f"DONE — updated={updated} skipped={skipped} errors={errors}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
