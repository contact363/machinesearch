import asyncio, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, ".")
from database.db import AsyncSessionLocal
from database.models import SiteConfig
from sqlalchemy import select

COREL_CONFIG = {
    "name": "corel_machines",
    "display_name": "Corel Machines",
    "start_url": "https://www.corelmachines.com/usedmachinestocklist",
    "base_url": "https://www.corelmachines.com",
    "mode": "api",
    "enabled": True,
    "pagination_type": "api_corelmachines",
    "max_pages": 1,
    "detail_page": False,
    "proxy_tier": "none",
    "rate_limit_delay": 1,
    "language": "en",
    "default_location": "India",
    "selectors": {
        "listing_container": "a.card",
        "name": "h3",
        "price": "",
        "image": "img",
        "location": "",
        "detail_link": "",
        "next_page": ""
    }
}

ZATPAT_CONFIG = {
    "name": "zatpat_machines",
    "display_name": "Zatpat Machines",
    "start_url": "https://zatpatmachines.com/machines",
    "base_url": "https://zatpatmachines.com",
    "mode": "api",
    "enabled": True,
    "pagination_type": "api_zatpat",
    "max_pages": 1,
    "detail_page": False,
    "proxy_tier": "none",
    "rate_limit_delay": 1,
    "language": "en",
    "supabase_url": "https://aqhgorgilxwrhzleztby.supabase.co",
    "supabase_key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFxaGdvcmdpbHh3cmh6bGV6dGJ5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU0MjMxNDEsImV4cCI6MjA4MDk5OTE0MX0.GD_HVD-98oUUM9RteG_DxPD3Deg8lyqLpq9d8tgYA5A",
    "selectors": {
        "listing_container": "a.machine-card",
        "name": "h3",
        "price": ".price-tag",
        "image": "img",
        "location": ".text-muted-foreground.mb-3",
        "detail_link": "",
        "next_page": ""
    }
}

async def upsert_config(session, cfg_dict):
    name = cfg_dict["name"]
    existing = await session.scalar(select(SiteConfig).where(SiteConfig.name == name))
    if existing:
        existing.config_json = cfg_dict
        existing.display_name = cfg_dict.get("display_name", name)
        print(f"Updated: {name}")
    else:
        cfg = SiteConfig(
            name=name,
            display_name=cfg_dict.get("display_name", name),
            config_json=cfg_dict,
            is_active=True,
        )
        session.add(cfg)
        print(f"Created: {name}")

async def main():
    async with AsyncSessionLocal() as session:
        await upsert_config(session, COREL_CONFIG)
        await upsert_config(session, ZATPAT_CONFIG)
        await session.commit()
        print("Done")

asyncio.run(main())
