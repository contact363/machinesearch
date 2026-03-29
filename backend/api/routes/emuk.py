"""
EMUK Werkzeugmaschinen public API — full machine data for external use.

Every scraped field is exposed: name, brand, model, machine_type, condition,
year, location, catalog_id, price, currency, images (primary + all extras),
specs, description, video_url, country_of_origin, source_url, timestamps.
"""

import uuid as _uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_db
from database.models import Machine

router = APIRouter()

SITE = "emuk"


def _full_dict(m: Machine) -> dict:
    """Return every available field for an EMUK machine."""
    specs = m.specs or {}

    primary = m.image_url
    extras = m.extra_images or []
    all_images: list[str] = []
    if primary:
        all_images.append(primary)
    for img in extras:
        if img and img not in all_images:
            all_images.append(img)

    return {
        "id": str(m.id),
        "catalog_id": m.catalog_id,
        "source": SITE,
        "source_url": m.source_url,
        "name": m.name,
        "brand": m.brand,
        "model": specs.get("Model") or specs.get("model"),
        "machine_type": m.machine_type,
        "condition": m.condition,
        "year_of_manufacture": m.year_of_manufacture,
        "country_of_origin": m.country_of_origin,
        "language": m.language,
        "location": m.location,
        "price": m.price,
        "currency": m.currency or "EUR",
        "image_url": primary,
        "extra_images": extras,
        "all_images": all_images,
        "video_url": m.video_url,
        "specs": specs,
        "description": m.description,
        "view_count": m.view_count,
        "click_count": m.click_count,
        "is_featured": m.is_featured,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }


@router.get("/machines")
async def list_emuk_machines(
    q: Optional[str] = Query(None, description="Search name, brand, type or description"),
    brand: Optional[str] = Query(None),
    machine_type: Optional[str] = Query(None),
    condition: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    year_min: Optional[int] = Query(None),
    year_max: Optional[int] = Query(None),
    has_price: Optional[bool] = Query(None),
    has_image: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all EMUK machines with optional filters and pagination."""
    stmt = select(Machine).where(Machine.site_name == SITE)

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
        "source": SITE,
        "page": page,
        "limit": limit,
        "total": total,
        "results": [_full_dict(m) for m in machines],
    }


@router.get("/machines/{machine_id}")
async def get_emuk_machine(machine_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single EMUK machine by UUID — all fields."""
    try:
        uid = _uuid.UUID(machine_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid machine ID format")

    machine = await db.scalar(
        select(Machine).where(Machine.id == uid, Machine.site_name == SITE)
    )
    if not machine:
        raise HTTPException(status_code=404, detail="EMUK machine not found")

    return _full_dict(machine)


@router.delete("/machines/{machine_id}")
async def delete_emuk_machine(machine_id: str, db: AsyncSession = Depends(get_db)):
    """Delete an EMUK machine by UUID."""
    try:
        uid = _uuid.UUID(machine_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid machine ID format")

    machine = await db.scalar(
        select(Machine).where(Machine.id == uid, Machine.site_name == SITE)
    )
    if not machine:
        raise HTTPException(status_code=404, detail="EMUK machine not found")

    await db.execute(delete(Machine).where(Machine.id == uid))
    await db.commit()

    return {"deleted": True, "id": machine_id}


@router.get("/filters")
async def emuk_filters(db: AsyncSession = Depends(get_db)):
    """All distinct filter values — brands, types, conditions, locations, year range."""
    total = await db.scalar(
        select(func.count(Machine.id)).where(Machine.site_name == SITE)
    )

    brands_rows = await db.execute(
        select(Machine.brand, func.count(Machine.id).label("count"))
        .where(Machine.site_name == SITE, Machine.brand.isnot(None))
        .group_by(Machine.brand)
        .order_by(func.count(Machine.id).desc())
    )
    brands = [{"brand": r.brand, "count": r.count} for r in brands_rows]

    types_rows = await db.execute(
        select(Machine.machine_type, func.count(Machine.id).label("count"))
        .where(Machine.site_name == SITE, Machine.machine_type.isnot(None))
        .group_by(Machine.machine_type)
        .order_by(func.count(Machine.id).desc())
    )
    machine_types = [{"type": r.machine_type, "count": r.count} for r in types_rows]

    cond_rows = await db.execute(
        select(Machine.condition, func.count(Machine.id).label("count"))
        .where(Machine.site_name == SITE, Machine.condition.isnot(None))
        .group_by(Machine.condition)
        .order_by(func.count(Machine.id).desc())
    )
    conditions = [{"condition": r.condition, "count": r.count} for r in cond_rows]

    loc_rows = await db.execute(
        select(Machine.location, func.count(Machine.id).label("count"))
        .where(Machine.site_name == SITE, Machine.location.isnot(None))
        .group_by(Machine.location)
        .order_by(func.count(Machine.id).desc())
    )
    locations = [{"location": r.location, "count": r.count} for r in loc_rows]

    year_row = await db.execute(
        select(
            func.min(Machine.year_of_manufacture).label("min"),
            func.max(Machine.year_of_manufacture).label("max"),
        ).where(Machine.site_name == SITE, Machine.year_of_manufacture.isnot(None))
    )
    year_range = year_row.one()

    with_image = await db.scalar(
        select(func.count(Machine.id)).where(
            Machine.site_name == SITE, Machine.image_url.isnot(None)
        )
    )
    with_price = await db.scalar(
        select(func.count(Machine.id)).where(
            Machine.site_name == SITE, Machine.price.isnot(None)
        )
    )

    return {
        "source": SITE,
        "total_machines": total,
        "with_image": with_image,
        "with_price": with_price,
        "year_range": {"min": year_range.min, "max": year_range.max},
        "brands": brands,
        "machine_types": machine_types,
        "conditions": conditions,
        "locations": locations,
    }
