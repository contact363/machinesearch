import asyncio, json, sys
sys.path.insert(0, ".")
from scraper.engine import AdaptiveEngine
from database.db import AsyncSessionLocal, init_db
from database.models import Machine
from sqlalchemy import select

NEW_SITES = ["fm_machines", "ucy_machines", "lrtt", "cnc_toerner"]

async def save_site(config):
    config["max_pages"] = 1
    config["detail_page"] = False
    engine = AdaptiveEngine()
    items = await engine.run(config)
    new, skipped = 0, 0
    async with AsyncSessionLocal() as session:
        for item in items:
            url = item.get("source_url")
            if not url:
                continue
            exists = await session.scalar(
                select(Machine).where(Machine.source_url == url)
            )
            if exists:
                skipped += 1
                continue
            session.add(Machine(
                name=item.get("name","Unknown"),
                brand=item.get("brand"),
                price=item.get("price"),
                location=item.get("location"),
                image_url=item.get("image_url"),
                description=item.get("description"),
                source_url=url,
                site_name=config["name"],
                language=config.get("language","en")
            ))
            new += 1
        await session.commit()
    print(f"[{config['name']}] {len(items)} scraped -> {new} new, {skipped} skipped")

async def main():
    await init_db()
    total = 0
    for name in NEW_SITES:
        try:
            with open(f"site_configs/{name}.json") as f:
                config = json.load(f)
            await save_site(config)
        except Exception as e:
            print(f"[{name}] ERROR: {e}")

    async with AsyncSessionLocal() as session:
        from sqlalchemy import func
        count = await session.scalar(
            select(func.count(Machine.id))
        )
        print(f"\nTotal machines in database: {count}")

asyncio.run(main())
