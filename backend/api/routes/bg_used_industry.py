"""
BG Used Industry public API — full machine data for external use.

Every scraped field is exposed: name, brand, model, machine_type, condition,
year, location, catalog_id, price, currency, images (primary + all extras),
specs, description, source_url, timestamps.
"""

import uuid as _uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_db
from database.models import Machine

router = APIRouter()

SITE = "bg-used-industry"


_NAV_NOISE = "All machines Accessories and tooling"

# Keywords that signal end of actual model name
_MODEL_CUTOFFS = [
    ", in very", ", in good", ", used", ", for sale", ", poa", ", po a",
    " - poa", " poa", ", visible", ", sold", ", refurbished", ", retrofit",
]

_TYPE_KEYWORDS = {
    "lathe": "Lathe",
    "milling": "Milling Machine",
    "machining centre": "Machining Centre",
    "machining center": "Machining Centre",
    "grinder": "Grinding Machine",
    "grinding": "Grinding Machine",
    "borer": "Boring Machine",
    "boring": "Boring Machine",
    "drill": "Drilling Machine",
    "drilling": "Drilling Machine",
    "press": "Press",
    "saw": "Saw",
    "band saw": "Band Saw",
    "welder": "Welding Machine",
    "welding": "Welding Machine",
    "laser": "Laser Machine",
    "plasma": "Plasma Cutter",
    "edm": "EDM Machine",
    "router": "Router",
    "forging": "Forging Machine",
    "shear": "Shearing Machine",
    "bending": "Bending Machine",
    "folding": "Folding Machine",
    "turning": "Turning Machine",
    "gear": "Gear Machine",
    "honing": "Honing Machine",
    "broaching": "Broaching Machine",
}


def _clean_model(name: str, brand: str) -> str | None:
    """Strip brand prefix and trailing condition/sales notes from name."""
    if not name:
        return None
    model = name.strip()
    # Remove brand prefix (case-insensitive)
    if brand and model.upper().startswith(brand.upper()):
        model = model[len(brand):].strip()
    # Cut off at noise phrases
    lower = model.lower()
    for cutoff in _MODEL_CUTOFFS:
        idx = lower.find(cutoff)
        if idx != -1:
            model = model[:idx].strip()
            lower = model.lower()
    return model or None


def _clean_description(desc: str | None) -> str | None:
    """Remove site navigation menu text that got scraped into description."""
    if not desc:
        return None
    lines = desc.splitlines()
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Skip lines that are the site navigation dump
        if line.startswith(_NAV_NOISE) or line.startswith("All machines"):
            continue
        cleaned.append(line)
    result = "\n".join(cleaned).strip()
    return result or None


def _guess_type(name: str) -> str | None:
    """Guess machine type from name keywords."""
    if not name:
        return None
    lower = name.lower()
    for keyword, mtype in _TYPE_KEYWORDS.items():
        if keyword in lower:
            return mtype
    return None


def _full_dict(m: Machine) -> dict:
    name = m.name or ""
    brand = m.brand or ""
    model = _clean_model(name, brand)
    machine_type = m.machine_type or _guess_type(name)
    return {
        "type": machine_type,
        "brand": brand or None,
        "model": model,
        "year": m.year_of_manufacture,
        "location": m.location,
        "description": _clean_description(m.description),
        "source_url": m.source_url,
        "image_url": m.image_url,
        "currency": m.currency or "EUR",
        "price": m.price,
    }


@router.get("/machines")
async def list_bg_used_industry_machines(
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
    limit: int = Query(2000, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
):
    """List all BG Used Industry machines with optional filters and pagination."""
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
async def get_bg_used_industry_machine(machine_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single BG Used Industry machine by UUID."""
    try:
        uid = _uuid.UUID(machine_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid machine ID format")

    machine = await db.scalar(
        select(Machine).where(Machine.id == uid, Machine.site_name == SITE)
    )
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    return _full_dict(machine)


@router.delete("/machines/{machine_id}")
async def delete_bg_used_industry_machine(machine_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a BG Used Industry machine by UUID."""
    try:
        uid = _uuid.UUID(machine_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid machine ID format")

    machine = await db.scalar(
        select(Machine).where(Machine.id == uid, Machine.site_name == SITE)
    )
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    await db.execute(delete(Machine).where(Machine.id == uid))
    await db.commit()

    return {"deleted": True, "id": machine_id}


@router.get("/filters")
async def bg_used_industry_filters(db: AsyncSession = Depends(get_db)):
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
        "locations": locations,
    }
