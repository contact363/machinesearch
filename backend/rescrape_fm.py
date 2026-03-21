import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import asyncio, os
sys.path.insert(0, ".")
os.environ.setdefault("PLAYWRIGHT_ENABLED", "false")
from scraper.engine import AdaptiveEngine
from database.db import AsyncSessionLocal
from database.models import Machine, SiteConfig
from sqlalchemy import select, func, delete as sql_delete

async def rescrape(site_name):
    async with AsyncSessionLocal() as session:
        cfg = await session.scalar(
            select(SiteConfig).where(SiteConfig.name == site_name)
        )
        if not cfg:
            print(f"No config for {site_name}")
            return 0
        config = dict(cfg.config_json)

    print(f"Config: {config.get('start_url')}")
    config["detail_page"] = False
    engine = AdaptiveEngine()
    items = await engine.run(config)
    print(f"[{site_name}] scraped: {len(items)}")

    if not items:
        return 0

    async with AsyncSessionLocal() as session:
        await session.execute(sql_delete(Machine).where(Machine.site_name == site_name))
        new = 0
        for item in items:
            url = item.get("source_url")
            if not url:
                continue
            session.add(Machine(
                name=item.get("name", "Unknown"),
                brand=item.get("brand"),
                price=item.get("price"),
                location=item.get("location"),
                image_url=item.get("image_url"),
                description=item.get("description"),
                source_url=url,
                site_name=site_name,
                language=config.get("language", "en")
            ))
            new += 1
        await session.commit()
    print(f"[{site_name}] saved: {new}")
    return new

async def main():
    for site in ["fm_machines", "fm-machines"]:
        n = await rescrape(site)
        if n > 0:
            break

asyncio.run(main())
