import asyncio, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, ".")
from database.db import AsyncSessionLocal
from database.models import SiteConfig
from sqlalchemy import select

# reble-machinery.de embeds its machines via an iframe from maschinensucher.de
# The widget URL is: https://www.maschinensucher.de/fy/customerwidget?kd=44381
# It returns static HTML with 25 items per page, 43 total (2 pages)
# The list page URL for pagination: https://www.maschinensucher.de/customerwidget/list/listings?kd=44381&page=2
# Machine cards have class: list-slide
# Name is in the <a aria-label="..."> attribute or text
# Price is in .price text
# Image: img.first-image src attribute
# Detail link: /customerwidget/detail/listing?id=...&customerNumber=44381
# Detail base: https://www.maschinensucher.de

REBLE_CONFIG = {
    "name": "reble_machinery",
    "display_name": "Reble Machinery",
    "start_url": "https://www.maschinensucher.de/customerwidget/list/listings?kd=44381",
    "base_url": "https://www.maschinensucher.de",
    "mode": "static",
    "enabled": True,
    "pagination_type": "page_param",
    "pagination_param": "page",
    "max_pages": 5,
    "detail_page": False,
    "proxy_tier": "none",
    "rate_limit_delay": 2,
    "language": "de",
    "default_location": "Germany",
    "selectors": {
        "listing_container": "section.grid-card",
        "name": "a[data-grid='title'] h2",
        "price": ".price .text-dark.h4",
        "image": "img.first-image",
        "location": ".trader-location .country-name",
        "detail_link": "a[data-grid='title']",
        "next_page": ""
    }
}

async def main():
    async with AsyncSessionLocal() as session:
        existing = await session.scalar(
            select(SiteConfig).where(SiteConfig.name == "reble_machinery")
        )
        if existing:
            existing.config_json = REBLE_CONFIG
            existing.display_name = REBLE_CONFIG["display_name"]
            print(f"Updated existing reble_machinery config")
        else:
            cfg = SiteConfig(
                name=REBLE_CONFIG["name"],
                display_name=REBLE_CONFIG["display_name"],
                config_json=REBLE_CONFIG,
                is_active=True,
            )
            session.add(cfg)
            print(f"Created new reble_machinery config")
        await session.commit()
        print("Done")
        print(json.dumps(REBLE_CONFIG, indent=2))

asyncio.run(main())
