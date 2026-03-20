"""
save_to_db.py — scrape all 4 sites and persist results to PostgreSQL.

Usage (from backend/ with venv active):
    python save_to_db.py
"""

import asyncio
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select, func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from database.db import AsyncSessionLocal, init_db, engine
from database.models import Machine
from scraper.engine import AdaptiveEngine

CONFIGS = [
    "vib_kg.json",
    "bidspotter.json",
    "exapro.json",
    "used_machines.json",
]
CONFIGS_DIR = Path(__file__).parent / "site_configs"


async def upsert_machines(session, items: list[dict]) -> tuple[int, int]:
    """
    Insert items that don't exist yet (keyed on source_url).
    Returns (new_count, skipped_count).
    """
    if not items:
        return 0, 0

    new_count = 0
    skipped_count = 0

    for item in items:
        source_url = item.get("source_url", "").strip()
        if not source_url:
            skipped_count += 1
            continue

        # Check if already exists
        existing = await session.scalar(
            select(Machine.id).where(Machine.source_url == source_url)
        )
        if existing:
            skipped_count += 1
            continue

        machine = Machine(
            id=uuid.uuid4(),
            name=item.get("name", "")[:500],
            brand=item.get("brand") or None,
            price=item.get("price") or None,
            currency=item.get("currency") or "USD",
            location=item.get("location") or None,
            image_url=item.get("image_url") or None,
            description=item.get("description") or None,
            specs=item.get("specs") or None,
            source_url=source_url,
            site_name=item.get("site_name", ""),
            language=item.get("language", "en"),
        )
        session.add(machine)
        new_count += 1

    await session.commit()
    return new_count, skipped_count


async def main() -> None:
    print("Initialising database...\n")
    await init_db()

    engine_obj = AdaptiveEngine()
    total_new = 0
    total_skipped = 0
    total_scraped = 0

    for filename in CONFIGS:
        config_path = CONFIGS_DIR / filename
        if not config_path.exists():
            print(f"[SKIP] {filename} not found")
            continue

        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        # Fast single-page run
        config["max_pages"] = 1
        config["detail_page"] = False

        site_name = config.get("name", filename)
        try:
            items = await engine_obj.run(config)
        except Exception as exc:
            print(f"[{site_name}] SCRAPE ERROR: {exc}")
            continue

        scraped = len(items)
        total_scraped += scraped

        async with AsyncSessionLocal() as session:
            new_count, skipped_count = await upsert_machines(session, items)

        total_new += new_count
        total_skipped += skipped_count

        print(f"[{site_name:<15}] {scraped:>3} scraped  ->  {new_count:>3} new, {skipped_count:>3} skipped")

    print(f"\nTOTAL: {total_new} inserted into PostgreSQL  ({total_skipped} duplicates skipped)")

    # Verification COUNT query
    async with engine.connect() as conn:
        count = await conn.scalar(text("SELECT COUNT(*) FROM machines"))
    print(f"Machines in database: {count}")


if __name__ == "__main__":
    asyncio.run(main())
