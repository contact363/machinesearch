"""
Production site config seeds.

These are the authoritative configs for all production scrape sites.
Called from init_db() on every startup with INSERT-IF-NOT-EXISTS semantics:
  - Config already in DB → left completely untouched (admin changes respected)
  - Config missing from DB (e.g. after DB wipe) → restored automatically

To permanently remove a site: set is_active=False here AND delete it via
the admin panel. Do NOT use raw DELETE scripts against the DB.

To add a new site: add it here so it survives future DB resets.
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Production configs — edit here to add / update sites
# ---------------------------------------------------------------------------
PRODUCTION_CONFIGS = [
    {
        "name": "zatpatmachines",
        "display_name": "Zatpat Machines",
        "is_active": True,
        "config": {
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
                "listing_container": "a.machine-card",
                "name": "h3",
                "price": ".price-tag",
                "image": "img",
                "location": ".text-muted-foreground.mb-3",
                "detail_link": "",
                "next_page": "",
            },
        },
    },
    {
        "name": "ucymachines",
        "display_name": "UCY Machines",
        "is_active": True,
        "config": {
            "start_url": "https://www.ucymachines.com/en/machine-tools",
            "base_url": "https://www.ucymachines.com",
            "mode": "static",
            "pagination": True,
            "pagination_type": "page_param",
            "pagination_param": "page",
            "max_pages": 50,
            "detail_page": False,
            "proxy_tier": "none",
            "rate_limit_delay": 2,
            "language": "en",
            "selectors": {
                "listing_container": "div.listing__wrapper",
                "name": "h4.listing__title",
                "price": "",
                "image": "img.listing__image",
                "location": "",
                "detail_link": "a.w-100",
                "next_page": "",
            },
        },
    },
    {
        "name": "corelmachine",
        "display_name": "Corel Machines",
        "is_active": True,
        "config": {
            "name": "corelmachine",
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
                "next_page": "",
            },
        },
    },
    {
        "name": "reble-machinery",
        "display_name": "Reble Machinery",
        "is_active": True,
        "config": {
            "name": "reble-machinery",
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
                "next_page": "",
            },
        },
    },
    {
        "name": "bade-maschinen",
        "display_name": "Bade Maschinen",
        "is_active": True,
        "config": {
            "name": "bade-maschinen",
            "display_name": "Bade Maschinen",
            "start_url": "https://www.bade-maschinen.de/maschinen/",
            "base_url": "https://www.bade-maschinen.de",
            "mode": "api",
            "enabled": True,
            "pagination_type": "api_bade_maschinen",
            "max_pages": 1,
            "detail_page": False,
            "proxy_tier": "none",
            "rate_limit_delay": 1,
            "language": "de",
            "selectors": {
                "listing_container": ".maschine-item",
                "name": ".maschine-name",
                "price": ".price",
                "image": ".maschine-image",
                "location": "",
                "detail_link": "",
                "next_page": "",
            },
        },
    },
    {
        "name": "vib-kg",
        "display_name": "VIB KG",
        "is_active": True,
        "config": {
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
        },
    },
    {
        "name": "mbrmachinery",
        "display_name": "MBR Machinery",
        "is_active": True,
        "config": {
            "name": "mbrmachinery",
            "display_name": "MBR Machinery",
            "start_url": "https://www.mbrmachinery.com/second-hand-machines-for-sale",
            "base_url": "https://www.mbrmachinery.com",
            "mode": "dynamic",
            "enabled": True,
            "pagination_type": "api_mbrmachinery",
            "max_pages": 1,
            "detail_page": False,
            "proxy_tier": "none",
            "rate_limit_delay": 1,
            "language": "en",
            "selectors": {
                "listing_container": "",
                "name": "",
                "price": "",
                "image": "",
                "location": "",
                "detail_link": "",
                "next_page": "",
            },
        },
    },
    {
        "name": "ajmeramachines",
        "display_name": "Ajmera Machines",
        "is_active": True,
        "config": {
            "name": "ajmeramachines",
            "display_name": "Ajmera Machines",
            "start_url": "https://ajmeramachines.com/stocklist",
            "base_url": "https://ajmeramachines.com",
            "mode": "api",
            "enabled": True,
            "pagination_type": "api_ajmeramachines",
            "max_pages": 1,
            "detail_page": False,
            "proxy_tier": "none",
            "rate_limit_delay": 1,
            "language": "en",
            "selectors": {
                "listing_container": "",
                "name": "",
                "price": "",
                "image": "",
                "location": "",
                "detail_link": "",
                "next_page": "",
            },
        },
    },
    {
        "name": "cnc-toerner",
        "display_name": "CNC Toerner",
        "is_active": True,
        "config": {
            "name": "cnc-toerner",
            "display_name": "CNC Toerner",
            "start_url": "https://cnc-toerner.de/maschinen/maschinenuebersicht/",
            "base_url": "https://cnc-toerner.de",
            "mode": "static",
            "enabled": True,
            "pagination_type": "page_param",
            "pagination_param": "query-19-page",
            "max_pages": 5,
            "detail_page": False,
            "proxy_tier": "none",
            "rate_limit_delay": 2,
            "language": "de",
            "selectors": {
                "listing_container": "li.wp-block-post",
                "name": ".wp-block-post-title a",
                "price": "",
                "image": "img",
                "location": "",
                "detail_link": ".wp-block-post-title a",
                "next_page": "",
            },
        },
    },
    {
        "name": "lrtt",
        "display_name": "LRTT",
        "is_active": True,
        "config": {
            "name": "lrtt",
            "display_name": "LRTT",
            "start_url": "https://www.lrtt.de/",
            "base_url": "https://www.lrtt.de",
            "mode": "static",
            "enabled": True,
            "pagination_type": "page_param",
            "pagination_param": "seite",
            "max_pages": 10,
            "detail_page": False,
            "proxy_tier": "none",
            "rate_limit_delay": 2,
            "language": "de",
            "selectors": {
                "listing_container": "div.teaser",
                "name": "a.title",
                "price": "",
                "image": "img",
                "location": "",
                "detail_link": "a",
                "next_page": "",
            },
        },
    },
    {
        "name": "fm-machines",
        "display_name": "FM Machines",
        "is_active": True,
        "config": {
            "name": "fm-machines",
            "display_name": "FM Machines",
            "start_url": "https://www.fm-machines.com/",
            "base_url": "https://www.fm-machines.com",
            "mode": "static",
            "enabled": True,
            "pagination_type": "page_param",
            "pagination_param": "seite",
            "max_pages": 20,
            "detail_page": False,
            "proxy_tier": "none",
            "rate_limit_delay": 2,
            "language": "de",
            "selectors": {
                "listing_container": "div.listing__wrapper",
                "name": "h4.listing-info__title",
                "price": ".listing-price",
                "image": "img.listing__image",
                "location": ".listing-info__location",
                "detail_link": "a.listing__link",
                "next_page": "",
            },
        },
    },
]


async def seed_site_configs(session: AsyncSession) -> None:
    """
    Insert any production configs that are missing from the DB.
    Never updates configs that already exist — admin edits are preserved.
    """
    from database.models import SiteConfig  # avoid circular import at module level

    inserted = 0
    for entry in PRODUCTION_CONFIGS:
        name = entry["name"]
        existing = await session.scalar(
            select(SiteConfig).where(SiteConfig.name == name)
        )
        if existing is None:
            session.add(SiteConfig(
                name=name,
                display_name=entry["display_name"],
                config_json=entry["config"],
                is_active=entry["is_active"],
            ))
            inserted += 1
            logger.info("seed_configs: inserted missing config '%s'", name)

    if inserted:
        await session.commit()
        logger.info("seed_configs: restored %d missing site config(s)", inserted)
    else:
        logger.info("seed_configs: all %d production configs present", len(PRODUCTION_CONFIGS))
