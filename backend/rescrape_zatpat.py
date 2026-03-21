import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import asyncio, os, sys
sys.path.insert(0, ".")
os.environ.setdefault("PLAYWRIGHT_ENABLED", "false")
from scraper.engine import AdaptiveEngine
from database.db import AsyncSessionLocal
from database.models import Machine, SiteConfig
from sqlalchemy import select, delete as sql_delete

async def rescrape_zatpat():
    async with AsyncSessionLocal() as session:
        cfg = await session.scalar(
            select(SiteConfig).where(SiteConfig.name == "zatpat_machines")
        )
        if not cfg:
            print("No zatpat config found!")
            return
        config = dict(cfg.config_json)

    config["detail_page"] = False
    engine = AdaptiveEngine()
    items = await engine.run(config)
    print(f"Scraped: {len(items)}")

    async with AsyncSessionLocal() as session:
        await session.execute(sql_delete(Machine).where(Machine.site_name == "zatpat_machines"))
        saved = 0
        for item in items:
            if not item.get("source_url"):
                continue
            session.add(Machine(
                name=item.get("name", "Unknown"),
                brand=item.get("brand"),
                price=item.get("price"),
                location=item.get("location"),
                image_url=item.get("image_url"),
                description=item.get("description"),
                source_url=item.get("source_url"),
                site_name="zatpat_machines",
                language=config.get("language", "en")
            ))
            saved += 1
        await session.commit()
    print(f"Saved: {saved}")

asyncio.run(rescrape_zatpat())
