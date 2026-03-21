"""Test the fixed scrapers before running full scrape jobs."""
import asyncio, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")

from scraper.engine import AdaptiveEngine
from database.db import AsyncSessionLocal
from database.models import SiteConfig
from sqlalchemy import select


async def test_site(name):
    async with AsyncSessionLocal() as session:
        row = await session.scalar(select(SiteConfig).where(SiteConfig.name == name))
        if not row:
            print(f"[{name}] NOT IN DB")
            return
        config = dict(row.config_json)
        config["name"] = name

    print(f"\n{'='*50}")
    print(f"Testing: {name}")
    print(f"  mode={config.get('mode')}  pagination={config.get('pagination_type')}")

    engine = AdaptiveEngine()
    try:
        items = await engine.run(config)
        print(f"  RESULT: {len(items)} items scraped")
        if items:
            print(f"  Sample: {items[0].get('name', '?')} | url={items[0].get('source_url', '?')[:60]}")
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback; traceback.print_exc()


async def main():
    # Test all three fixed sites
    await test_site("vib-kg")        # expect ~128
    await test_site("zatpatmachines") # expect ~5000
    await test_site("corelmachine")   # expect 500+


asyncio.run(main())
