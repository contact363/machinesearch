import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import asyncio, httpx, json
sys.path.insert(0, ".")
from database.db import AsyncSessionLocal
from database.models import SiteConfig
from sqlalchemy import select

async def get_config():
    async with AsyncSessionLocal() as session:
        cfg = await session.scalar(
            select(SiteConfig).where(SiteConfig.name == "corel_machines")
        )
        if cfg:
            return cfg.config_json
    return None

config = asyncio.run(get_config())
print("Corel config:")
print(json.dumps(config, indent=2))

if config:
    # Try to get all categories and their machine counts
    base_url = "https://corelmachine.com"

    try:
        r = httpx.get(f"{base_url}/api/subcategory/all", timeout=15)
        categories = r.json()
        print(f"\nTotal categories: {len(categories)}")

        total = 0
        for cat in categories[:5]:
            slug = cat.get("slug") or cat.get("name", "").lower().replace(" ", "-")
            print(f"Category: {cat.get('name')} | slug: {slug}")
            try:
                r2 = httpx.get(f"{base_url}/api/product/{slug}", timeout=15)
                machines = r2.json()
                if isinstance(machines, list):
                    print(f"  -> {len(machines)} machines")
                    total += len(machines)
                else:
                    print(f"  -> response: {str(machines)[:100]}")
            except Exception as e:
                print(f"  -> ERROR: {e}")

        print(f"\n(Showed first 5 categories. Total from first 5: {total})")
        print(f"If avg per category = {total//5 if total else 0}, then {len(categories)} categories = ~{(total//5)*len(categories) if total else 0}")
    except Exception as e:
        print(f"ERROR fetching categories: {e}")
