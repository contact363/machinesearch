"""
full_scrape.py — Full scrape of all 8 working sites and save to PostgreSQL.

Usage (from backend/ with venv active):
    python full_scrape.py
"""

import asyncio
import io
import json
import sys
import uuid
from pathlib import Path

# UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select, func
from database.db import AsyncSessionLocal, init_db
from database.models import Machine
from scraper.engine import AdaptiveEngine

SITES = [
    "vib_kg",
    "bidspotter",
    "exapro",
    "used_machines",
    "fm_machines",
    "ucy_machines",
    "lrtt",
    "cnc_toerner",
]

CONFIGS_DIR = Path(__file__).parent / "site_configs"


async def save_site(config: dict) -> tuple[int, int]:
    config = {**config, "detail_page": False}
    engine = AdaptiveEngine()
    items = await engine.run(config)

    new_count = 0
    skipped_count = 0

    async with AsyncSessionLocal() as session:
        for item in items:
            url = (item.get("source_url") or "").strip()
            if not url:
                skipped_count += 1
                continue

            exists = await session.scalar(
                select(Machine.id).where(Machine.source_url == url)
            )
            if exists:
                skipped_count += 1
                continue

            machine = Machine(
                id=uuid.uuid4(),
                name=(item.get("name") or "Unknown")[:500],
                brand=item.get("brand") or None,
                price=item.get("price") or None,
                currency=item.get("currency") or "USD",
                location=item.get("location") or None,
                image_url=item.get("image_url") or None,
                description=item.get("description") or None,
                specs=item.get("specs") or None,
                source_url=url,
                site_name=config["name"],
                language=config.get("language", "en"),
            )
            session.add(machine)
            new_count += 1

        await session.commit()

    print(
        f"[{config['name']:15}] "
        f"{len(items):5} scraped  ->  {new_count:5} new,  {skipped_count:5} skipped"
    )
    return new_count, len(items)


async def main() -> None:
    await init_db()
    print("Starting full scrape of all 8 sites...\n")

    total_new = 0
    total_scraped = 0

    for name in SITES:
        config_path = CONFIGS_DIR / f"{name}.json"
        if not config_path.exists():
            print(f"[{name:15}] SKIP — config not found")
            continue

        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        try:
            new, scraped = await save_site(config)
            total_new += new
            total_scraped += scraped
        except Exception as exc:
            print(f"[{name:15}] ERROR: {exc}")

    # Final DB summary
    async with AsyncSessionLocal() as session:
        total_db = await session.scalar(select(func.count(Machine.id)))
        by_site_result = await session.execute(
            select(Machine.site_name, func.count(Machine.id).label("cnt"))
            .group_by(Machine.site_name)
            .order_by(func.count(Machine.id).desc())
        )
        by_site = list(by_site_result)

    print(f"\n{'='*55}")
    print("FULL SCRAPE COMPLETE")
    print(f"{'='*55}")
    print(f"Total scraped this run : {total_scraped}")
    print(f"New machines added     : {total_new}")
    print(f"Total in database      : {total_db}")
    print(f"\nBy site:")
    print(f"  {'Site':<22} {'Machines':>8}")
    print(f"  {'-'*22} {'-'*8}")
    for site, count in by_site:
        print(f"  {site:<22} {count:>8}")
    print(f"  {'-'*22} {'-'*8}")
    print(f"  {'TOTAL':<22} {total_db:>8}")


if __name__ == "__main__":
    asyncio.run(main())
