"""
VIB-KG public API — full machine data for external use (e.g. Lovable / zatpatmachines).

Every scraped field is exposed: name, brand, model, machine_type, condition,
year, location, catalog_id, price, currency, images (primary + all extras),
specs, description, video_url, country_of_origin, source_url, timestamps.
"""

import uuid as _uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_db
from database.models import Machine

router = APIRouter()


def _full_dict(m: Machine) -> dict:
    """Return every available field for a VIB-KG machine."""
    specs = m.specs or {}

    # Build a unified images list: primary image first, then extras (no duplicates)
    primary = m.image_url
    extras = m.extra_images or []
    all_images: list[str] = []
    if primary:
        all_images.append(primary)
    for img in extras:
        if img and img not in all_images:
            all_images.append(img)

    return {
        # ── Identity ──────────────────────────────────────────────────────────
        "id": str(m.id),
        "catalog_id": m.catalog_id,           # VIB-Nr (e.g. "VIB-12345")
        "source": "vib-kg",
        "source_url": m.source_url,            # direct link to VIB-KG listing

        # ── Machine info ──────────────────────────────────────────────────────
        "name": m.name,
        "brand": m.brand,
        "model": specs.get("Model") or specs.get("model"),
        "machine_type": m.machine_type,        # e.g. "Turret Punch Press"
        "condition": m.condition,              # e.g. "Good", "Used"
        "year_of_manufacture": m.year_of_manufacture,
        "country_of_origin": m.country_of_origin,
        "language": m.language,               # "de" for VIB-KG

        # ── Location ──────────────────────────────────────────────────────────
        "location": m.location,

        # ── Pricing ───────────────────────────────────────────────────────────
        "price": m.price,                     # None = "price on request"
        "currency": m.currency or "EUR",

        # ── Media ─────────────────────────────────────────────────────────────
        "image_url": primary,                 # main/cover image
        "extra_images": extras,               # additional images list
        "all_images": all_images,             # primary + extras combined
        "video_url": m.video_url,

        # ── Full specs dict ───────────────────────────────────────────────────
        "specs": specs,                       # raw key-value pairs from listing

        # ── Description ───────────────────────────────────────────────────────
        "description": m.description,

        # ── Stats ─────────────────────────────────────────────────────────────
        "view_count": m.view_count,
        "click_count": m.click_count,
        "is_featured": m.is_featured,

        # ── Timestamps ────────────────────────────────────────────────────────
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }


@router.get("/machines")
async def list_vibkg_machines(
    q: Optional[str] = Query(None, description="Search name, brand, type or description"),
    brand: Optional[str] = Query(None, description="Filter by brand (partial match)"),
    machine_type: Optional[str] = Query(None, description="Filter by machine type (partial match)"),
    condition: Optional[str] = Query(None, description="Filter by condition"),
    location: Optional[str] = Query(None, description="Filter by location (partial match)"),
    year_min: Optional[int] = Query(None, description="Minimum year of manufacture"),
    year_max: Optional[int] = Query(None, description="Maximum year of manufacture"),
    has_price: Optional[bool] = Query(None, description="true = only machines with price, false = price on request"),
    has_image: Optional[bool] = Query(None, description="true = only machines with at least one image"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    List all VIB-KG machines with optional filters.

    Returns full machine data including every image, spec, location, brand,
    condition, year, catalog ID, and source URL.
    """
    stmt = select(Machine).where(Machine.site_name == "vib-kg")

    if q:
        stmt = stmt.where(
            Machine.name.ilike(f"%{q}%")
            | Machine.brand.ilike(f"%{q}%")
            | Machine.machine_type.ilike(f"%{q}%")
            | Machine.description.ilike(f"%{q}%")
        )
    if brand:
        stmt = stmt.where(Machine.brand.ilike(f"%{brand}%"))
    if machine_type:
        stmt = stmt.where(Machine.machine_type.ilike(f"%{machine_type}%"))
    if condition:
        stmt = stmt.where(Machine.condition.ilike(f"%{condition}%"))
    if location:
        stmt = stmt.where(Machine.location.ilike(f"%{location}%"))
    if year_min is not None:
        stmt = stmt.where(Machine.year_of_manufacture >= year_min)
    if year_max is not None:
        stmt = stmt.where(Machine.year_of_manufacture <= year_max)
    if has_price is True:
        stmt = stmt.where(Machine.price.isnot(None))
    if has_price is False:
        stmt = stmt.where(Machine.price.is_(None))
    if has_image is True:
        stmt = stmt.where(Machine.image_url.isnot(None))

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.order_by(Machine.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(stmt)
    machines = result.scalars().all()

    return {
        "source": "vib-kg",
        "page": page,
        "limit": limit,
        "total": total,
        "results": [_full_dict(m) for m in machines],
    }


@router.get("/machines/{machine_id}")
async def get_vibkg_machine(machine_id: str, db: AsyncSession = Depends(get_db)):
    """
    Get a single VIB-KG machine by its UUID.

    Returns all fields: name, brand, model, specs, all images, location,
    condition, year, catalog_id, source URL, timestamps, etc.
    """
    try:
        uid = _uuid.UUID(machine_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid machine ID format")

    machine = await db.scalar(
        select(Machine).where(Machine.id == uid, Machine.site_name == "vib-kg")
    )
    if not machine:
        raise HTTPException(status_code=404, detail="VIB-KG machine not found")

    return _full_dict(machine)


@router.get("/filters")
async def vibkg_filters(db: AsyncSession = Depends(get_db)):
    """
    Returns all distinct filter values for VIB-KG stock:
    brands, machine types, conditions, locations, year range.

    Use this to populate dropdowns in your UI.
    """
    # Total count
    total = await db.scalar(
        select(func.count(Machine.id)).where(Machine.site_name == "vib-kg")
    )

    # Brands
    brands_rows = await db.execute(
        select(Machine.brand, func.count(Machine.id).label("count"))
        .where(Machine.site_name == "vib-kg", Machine.brand.isnot(None))
        .group_by(Machine.brand)
        .order_by(func.count(Machine.id).desc())
    )
    brands = [{"brand": r.brand, "count": r.count} for r in brands_rows]

    # Machine types
    types_rows = await db.execute(
        select(Machine.machine_type, func.count(Machine.id).label("count"))
        .where(Machine.site_name == "vib-kg", Machine.machine_type.isnot(None))
        .group_by(Machine.machine_type)
        .order_by(func.count(Machine.id).desc())
    )
    machine_types = [{"type": r.machine_type, "count": r.count} for r in types_rows]

    # Conditions
    cond_rows = await db.execute(
        select(Machine.condition, func.count(Machine.id).label("count"))
        .where(Machine.site_name == "vib-kg", Machine.condition.isnot(None))
        .group_by(Machine.condition)
        .order_by(func.count(Machine.id).desc())
    )
    conditions = [{"condition": r.condition, "count": r.count} for r in cond_rows]

    # Locations
    loc_rows = await db.execute(
        select(Machine.location, func.count(Machine.id).label("count"))
        .where(Machine.site_name == "vib-kg", Machine.location.isnot(None))
        .group_by(Machine.location)
        .order_by(func.count(Machine.id).desc())
    )
    locations = [{"location": r.location, "count": r.count} for r in loc_rows]

    # Year range
    year_row = await db.execute(
        select(
            func.min(Machine.year_of_manufacture).label("min"),
            func.max(Machine.year_of_manufacture).label("max"),
        ).where(Machine.site_name == "vib-kg", Machine.year_of_manufacture.isnot(None))
    )
    year_range = year_row.one()

    # With image / without image counts
    with_image = await db.scalar(
        select(func.count(Machine.id)).where(
            Machine.site_name == "vib-kg", Machine.image_url.isnot(None)
        )
    )
    with_price = await db.scalar(
        select(func.count(Machine.id)).where(
            Machine.site_name == "vib-kg", Machine.price.isnot(None)
        )
    )

    return {
        "source": "vib-kg",
        "total_machines": total,
        "with_image": with_image,
        "with_price": with_price,
        "year_range": {
            "min": year_range.min,
            "max": year_range.max,
        },
        "brands": brands,
        "machine_types": machine_types,
        "conditions": conditions,
        "locations": locations,
    }
