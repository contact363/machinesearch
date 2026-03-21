"""
Fix all broken site configs and delete bad machine data.
Run once: python fix_all_site_configs.py
"""
import asyncio
from database.db import AsyncSessionLocal
from database.models import Machine, SiteConfig
from sqlalchemy import select, delete, update

SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFxaGdvcmdpbHh3cmh6bGV6dGJ5Iiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NjU0MjMxNDEsImV4cCI6MjA4MDk5OTE0MX0."
    "GD_HVD-98oUUM9RteG_DxPD3Deg8lyqLpq9d8tgYA5A"
)

FIXES = {
    # API sites — just need pagination_type restored
    "zatpatmachines": {
        "name": "zatpatmachines",
        "display_name": "Zatpat Machines",
        "start_url": "https://zatpatmachines.com/machines",
        "base_url": "https://zatpatmachines.com",
        "mode": "api",
        "pagination_type": "api_zatpat",
        "max_pages": 1,
        "detail_page": False,
        "proxy_tier": "none",
        "rate_limit_delay": 1,
        "language": "en",
        "supabase_url": "https://aqhgorgilxwrhzleztby.supabase.co",
        "supabase_key": SUPABASE_KEY,
        "selectors": {"listing_container": "", "name": "", "price": "", "image": "", "location": "", "detail_link": "", "next_page": ""},
    },
    "bade-maschinen": {
        "name": "bade-maschinen",
        "display_name": "Bade Maschinen",
        "start_url": "https://www.bade-maschinen.de/maschinen/",
        "base_url": "https://www.bade-maschinen.de",
        "mode": "api",
        "pagination_type": "api_bade_maschinen",
        "max_pages": 1,
        "detail_page": False,
        "proxy_tier": "none",
        "rate_limit_delay": 1,
        "language": "de",
        "selectors": {"listing_container": "", "name": "", "price": "", "image": "", "location": "", "detail_link": "", "next_page": ""},
    },
    "mbrmachinery": {
        "name": "mbrmachinery",
        "display_name": "MBR Machinery",
        "start_url": "https://www.mbrmachinery.com/second-hand-machines-for-sale",
        "base_url": "https://www.mbrmachinery.com",
        "mode": "dynamic",
        "pagination_type": "api_mbrmachinery",
        "max_pages": 1,
        "detail_page": False,
        "proxy_tier": "none",
        "rate_limit_delay": 1,
        "language": "en",
        "selectors": {"listing_container": "", "name": "", "price": "", "image": "", "location": "", "detail_link": "", "next_page": ""},
    },
    "corelmachine": {
        "name": "corelmachine",
        "display_name": "Corel Machines",
        "start_url": "https://corelmachine.com/",
        "base_url": "https://www.corelmachines.com",
        "mode": "api",
        "pagination_type": "api_corelmachines",
        "max_pages": 1,
        "detail_page": False,
        "proxy_tier": "none",
        "rate_limit_delay": 1,
        "language": "en",
        "selectors": {"listing_container": "", "name": "", "price": "", "image": "", "location": "", "detail_link": "", "next_page": ""},
    },
    # cnc-toerner — was scraping /kontakt/ (contact page), fix to machines listing
    "cnc-toerner": {
        "name": "cnc-toerner",
        "display_name": "CNC Toerner",
        "start_url": "https://cnc-toerner.de/maschinen/maschinenuebersicht/",
        "base_url": "https://cnc-toerner.de",
        "mode": "static",
        "pagination_type": "page_param",
        "pagination_param": "query-19-page",
        "max_pages": 10,
        "detail_page": False,
        "proxy_tier": "none",
        "rate_limit_delay": 2,
        "language": "de",
        "selectors": {
            "listing_container": ".wp-block-post",
            "name": "h2 a, h3 a",
            "price": ".price",
            "image": "img",
            "location": "",
            "detail_link": "h2 a, h3 a",
            "next_page": "",
        },
    },
    # reble-machinery — was scraping homepage, fix to maschinensucher widget
    "reble-machinery": {
        "name": "reble-machinery",
        "display_name": "Reble Machinery",
        "start_url": "https://www.maschinensucher.de/customerwidget/list/listings?kd=44381",
        "base_url": "https://www.maschinensucher.de",
        "mode": "static",
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
            "next_page": "",
        },
    },
    # ajmeramachines — needs custom API scraper
    "ajmeramachines": {
        "name": "ajmeramachines",
        "display_name": "Ajmera Machines",
        "start_url": "https://ajmeramachines.com/stocklist",
        "base_url": "https://ajmeramachines.com",
        "mode": "api",
        "pagination_type": "api_ajmeramachines",
        "max_pages": 1,
        "detail_page": False,
        "proxy_tier": "none",
        "rate_limit_delay": 1,
        "language": "en",
        "selectors": {"listing_container": "", "name": "", "price": "", "image": "", "location": "", "detail_link": "", "next_page": ""},
    },
    # vib-kg — was picking up generic page title, fix to dynamic with product selectors
    "vib-kg": {
        "name": "vib-kg",
        "display_name": "VIB KG",
        "start_url": "https://vib-kg.com/usedmachines",
        "base_url": "https://vib-kg.com",
        "mode": "dynamic",
        "pagination_type": "page_param",
        "pagination_param": "page",
        "max_pages": 20,
        "detail_page": False,
        "proxy_tier": "none",
        "rate_limit_delay": 2,
        "language": "en",
        "selectors": {
            "listing_container": "li.product, .product-item, article.product",
            "name": "h2, .woocommerce-loop-product__title",
            "price": ".price",
            "image": "img",
            "location": "",
            "detail_link": "a",
            "next_page": "",
        },
    },
}

# Sites whose existing machines are all garbage — delete and re-scrape
DELETE_BAD_DATA = ["cnc-toerner", "reble-machinery", "vib-kg"]


async def main():
    async with AsyncSessionLocal() as session:
        # 1. Delete bad machine records
        for site in DELETE_BAD_DATA:
            result = await session.execute(
                delete(Machine).where(Machine.site_name == site)
            )
            print(f"Deleted {result.rowcount} bad machines for '{site}'")

        await session.commit()

        # 2. Update all site configs
        for name, new_cfg in FIXES.items():
            existing = await session.scalar(
                select(SiteConfig).where(SiteConfig.name == name)
            )
            if existing:
                existing.config_json = new_cfg
                print(f"Updated config for '{name}'")
            else:
                print(f"WARNING: Site '{name}' not found in DB — skipping")

        await session.commit()
        print("\nDone. Re-run scrapers from admin panel.")

asyncio.run(main())
