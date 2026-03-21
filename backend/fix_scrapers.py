"""
Fix scraper configs for zatpatmachines, corelmachine, and vib-kg.

Problems diagnosed:
  zatpatmachines - mode=static/page_param with empty container → needs api_zatpat mode
  corelmachine   - mode=dynamic/page_param with empty container → needs api_corelmachines mode
  vib-kg         - container=div.container (57 false matches) → needs li.list-group-item.p-0,
                   max_pages=50 → should be 1 (all 128 machines on single page, no URL pagination)
"""
import asyncio, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, ".")

from database.db import AsyncSessionLocal
from database.models import SiteConfig
from sqlalchemy import select


FIXES = {
    "zatpatmachines": {
        "mode": "api",
        "pagination_type": "api_zatpat",
        "max_pages": 1,
        "start_url": "https://zatpatmachines.com/machines",
        "base_url": "https://zatpatmachines.com",
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
            "listing_container": "a.machine-card",
            "name": "h3",
            "price": ".price-tag",
            "image": "img",
            "location": ".text-muted-foreground.mb-3",
            "detail_link": "",
            "next_page": "",
        },
    },
    "corelmachine": {
        "mode": "api",
        "pagination_type": "api_corelmachines",
        "max_pages": 1,
        "start_url": "https://www.corelmachines.com/usedmachinestocklist",
        "base_url": "https://www.corelmachines.com",
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
            "next_page": "",
        },
    },
    "vib-kg": {
        # All 128 machines are on a single page — no URL pagination.
        # Each machine is a <li class="list-group-item p-0"> element.
        # Image: .machine-index-slider-img uses CSS background:url(...) — engine handles this.
        # Name: .machine-index-link (anchor text)
        # Link: a.machine-index-link
        "mode": "static",
        "pagination_type": "page_param",
        "pagination_param": "page",
        "max_pages": 1,
        "start_url": "https://vib-kg.com/usedmachines",
        "base_url": "https://vib-kg.com",
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
    },
}


async def apply_fixes():
    async with AsyncSessionLocal() as session:
        for name, patch in FIXES.items():
            row = await session.scalar(select(SiteConfig).where(SiteConfig.name == name))
            if not row:
                print(f"[{name}] NOT FOUND in DB — skipping")
                continue

            # Merge patch into existing config
            existing = dict(row.config_json or {})
            existing.update(patch)
            existing["name"] = name  # ensure name field is consistent

            row.config_json = existing
            print(f"[{name}] Updated:")
            print(f"  mode={existing['mode']}  pagination={existing['pagination_type']}  max_pages={existing.get('max_pages')}")
            print(f"  listing_container={existing.get('selectors', {}).get('listing_container')}")
            print(f"  supabase_key={'PRESENT' if existing.get('supabase_key') else 'MISSING'}")

        await session.commit()
        print("\nAll fixes committed.")


asyncio.run(apply_fixes())
