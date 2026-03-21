import asyncio, sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, ".")
os.environ["PLAYWRIGHT_ENABLED"] = "true"
from scraper.engine import AdaptiveEngine
from database.db import AsyncSessionLocal
from database.models import Machine, SiteConfig
from sqlalchemy import select, func, delete as sql_delete

async def full_scrape(site_name):
    print(f"\n{'='*45}")
    print(f"SCRAPING: {site_name}")

    async with AsyncSessionLocal() as session:
        cfg = await session.scalar(select(SiteConfig).where(SiteConfig.name == site_name))
        if not cfg:
            print(f"No config for {site_name}")
            return 0
        config = dict(cfg.config_json)

    config["detail_page"] = False
    engine = AdaptiveEngine()
    items = await engine.run(config)
    print(f"Items scraped: {len(items)}")

    if not items:
        print("FAILED -- 0 items")
        return 0

    new = 0
    async with AsyncSessionLocal() as session:
        await session.execute(sql_delete(Machine).where(Machine.site_name == site_name))
        for item in items:
            url = item.get("source_url")
            if not url:
                continue
            session.add(Machine(
                name=item.get("name","Unknown"),
                brand=item.get("brand"),
                price=item.get("price"),
                location=item.get("location"),
                image_url=item.get("image_url"),
                description=item.get("description"),
                source_url=url,
                site_name=site_name,
                language=config.get("language","en")
            ))
            new += 1
        await session.commit()
    print(f"Saved to DB: {new}")
    return new

async def main():
    results = {}
    for site in ["reble_machinery", "corel_machines", "zatpat_machines"]:
        n = await full_scrape(site)
        results[site] = n

    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            select(Machine.site_name, func.count(Machine.id))
            .group_by(Machine.site_name)
            .order_by(func.count(Machine.id).desc())
        )
        print(f"\n{'='*45}")
        print("FINAL DATABASE SUMMARY:")
        total = 0
        for site, count in rows:
            print(f"  {site:25} {count:6}")
            total += count
        print(f"  {'TOTAL':25} {total:6}")

    print(f"\nResults:")
    for site, n in results.items():
        if "reble" in site:
            expected = 50
        elif "corel" in site:
            expected = 200
        else:
            expected = 500
        status = "PASS" if n >= expected else "FAIL"
        print(f"  {site}: {n} [{status}]")

asyncio.run(main())
