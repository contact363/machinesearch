"""Fix configs, clear stale data, and rescrape vib-kg + zatpatmachines."""
import asyncio, sys, io, uuid, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")

from datetime import datetime, timezone
from sqlalchemy import select, delete as sql_delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from database.db import AsyncSessionLocal
from database.models import Machine, SiteConfig
from scraper.engine import AdaptiveEngine

VIB_CONFIG = {
    "name": "vib-kg",
    "display_name": "VIB KG",
    "start_url": "https://vib-kg.com/usedmachines",
    "base_url": "https://vib-kg.com",
    "mode": "static",
    "enabled": True,
    "pagination_type": "page_param",
    "pagination_param": "page",
    "max_pages": 1,
    "detail_page": False,
    "proxy_tier": "none",
    "rate_limit_delay": 2,
    "language": "de",
    "selectors": {
        "listing_container": "li.list-group-item.p-0",
        "name": "a.machine-index-link",
        "price": "",
        "image": ".machine-index-slider-img",
        "location": "",
        "detail_link": "a.machine-index-link",
        "next_page": "",
    },
}

ZATPAT_CONFIG = {
    "name": "zatpatmachines",
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
    "supabase_key": (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFxaGdvcmdpbHh3cmh6bGV6dGJ5Iiw"
        "icm9sZSI6ImFub24iLCJpYXQiOjE3NjU0MjMxNDEsImV4cCI6MjA4MDk5OTE0MX0."
        "GD_HVD-98oUUM9RteG_DxPD3Deg8lyqLpq9d8tgYA5A"
    ),
    "selectors": {
        "listing_container": "a.machine-card", "name": "h3",
        "price": ".price-tag", "image": "img",
        "location": ".text-muted-foreground.mb-3",
        "detail_link": "", "next_page": "",
    },
}


async def fix_config(session, cfg_dict):
    row = await session.scalar(
        select(SiteConfig).where(SiteConfig.name == cfg_dict["name"])
    )
    if row:
        row.config_json = cfg_dict
        row.is_active = True
        print(f"[{cfg_dict['name']}] config updated")
    else:
        session.add(SiteConfig(
            name=cfg_dict["name"],
            display_name=cfg_dict["display_name"],
            config_json=cfg_dict,
            is_active=True,
        ))
        print(f"[{cfg_dict['name']}] config inserted")


async def save_machines(site_name, items, language, batch_size=200):
    """Save machines in batches to avoid DB connection timeouts."""
    total_saved = 0
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        async with AsyncSessionLocal() as session:
            for item in batch:
                src = (item.get("source_url") or "").strip()
                if not src:
                    continue
                raw_price = item.get("price") or None
                if raw_price is not None:
                    try:
                        # Strip currency suffixes like "1262500.0 INR"
                        price_val = float(re.sub(r"[^\d.]", "", str(raw_price).split()[0]))
                    except (ValueError, IndexError):
                        price_val = None
                else:
                    price_val = None
                stmt = pg_insert(Machine).values(
                    id=uuid.uuid4(),
                    name=(item.get("name") or "Unknown")[:500],
                    brand=(item.get("brand") or None),
                    price=price_val,
                    location=(item.get("location") or None),
                    image_url=(item.get("image_url") or None),
                    description=(item.get("description") or None),
                    source_url=src,
                    site_name=site_name,
                    language=language,
                    view_count=0,
                    click_count=0,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                ).on_conflict_do_nothing(index_elements=["source_url"])
                r = await session.execute(stmt)
                if r.rowcount > 0:
                    total_saved += 1
            await session.commit()
        print(f"[{site_name}] saved batch {i // batch_size + 1} ({total_saved} total so far)")
    return total_saved


async def main():
    # Step 1: fix configs
    async with AsyncSessionLocal() as session:
        await fix_config(session, VIB_CONFIG)
        await fix_config(session, ZATPAT_CONFIG)
        await session.commit()

    # Step 2: clear stale machines
    async with AsyncSessionLocal() as session:
        r1 = await session.execute(sql_delete(Machine).where(Machine.site_name == "vib-kg"))
        r2 = await session.execute(sql_delete(Machine).where(Machine.site_name == "zatpatmachines"))
        await session.commit()
        print(f"Cleared: vib-kg={r1.rowcount}, zatpatmachines={r2.rowcount}")

    engine = AdaptiveEngine()

    # Step 3: scrape vib-kg
    print("\nScraping vib-kg...")
    vib_items = await engine.run(VIB_CONFIG)
    print(f"[vib-kg] scraped {len(vib_items)} items")
    saved = await save_machines("vib-kg", vib_items, "de")
    print(f"[vib-kg] total saved: {saved}")

    # Step 4: scrape zatpat
    print("\nScraping zatpatmachines...")
    zatpat_items = await engine.scrape_zatpat_api(ZATPAT_CONFIG)
    print(f"[zatpatmachines] scraped {len(zatpat_items)} items")
    saved = await save_machines("zatpatmachines", zatpat_items, "en", batch_size=500)
    print(f"[zatpatmachines] total saved: {saved}")

    print("\nDone.")


asyncio.run(main())
