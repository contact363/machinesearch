"""
Analytics router.

Exposes aggregated statistics about the platform: total listings indexed,
per-site counts, scrape success/failure rates, price trends over time,
and search term frequency.
"""

from fastapi import APIRouter, Query

router = APIRouter()

# TODO: inject read-only DB session via dependency
# TODO: add caching (Redis / in-process TTL cache) for expensive aggregations


@router.get("/summary")
async def get_summary():
    """
    High-level dashboard summary: total machines, sites, last scrape times.

    TODO: query DB for counts grouped by site and return structured summary.
    """
    return {
        "total_machines": 0,
        "total_sites": 0,
        "last_scrape": None,
    }


@router.get("/by-site")
async def listings_by_site():
    """
    Return listing counts broken down by source site.

    TODO: GROUP BY site_name query with active listing filter.
    """
    return {"by_site": []}


@router.get("/price-trend")
async def price_trend(
    category: str = Query(None, description="Optional machine category filter"),
    days: int = Query(30, ge=1, le=365),
):
    """
    Average price trend over the last N days for a given category.

    TODO: time-series aggregation from DB (date_trunc by day).
    TODO: return list of {date, avg_price} dicts.
    """
    return {"category": category, "days": days, "trend": []}


@router.get("/top-searches")
async def top_searches(limit: int = Query(10, ge=1, le=100)):
    """
    Return the most frequent search queries recorded by the platform.

    TODO: query search_log table, order by count DESC.
    """
    return {"top_searches": []}
