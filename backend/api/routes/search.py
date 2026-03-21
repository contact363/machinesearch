"""
Search router — full-text and filtered search across machine listings.
"""

import uuid as _uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_db
from database.models import Machine, ClickEvent

router = APIRouter()


def _machine_to_dict(m: Machine) -> dict:
    return {
        "id": str(m.id),
        "name": m.name,
        "brand": m.brand,
        "price": m.price,
        "currency": m.currency,
        "location": m.location,
        "image_url": m.image_url,
        "site_name": m.site_name,
        "source_url": m.source_url,
        "language": m.language,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


@router.get("/")
async def search_machines(
    q: Optional[str] = Query(None, description="Search query string"),
    site: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    price_min: Optional[float] = Query(None, ge=0),
    price_max: Optional[float] = Query(None, ge=0),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Full-text and filtered search across machine listings."""
    stmt = select(Machine)

    if q:
        stmt = stmt.where(
            or_(
                Machine.name.ilike(f"%{q}%"),
                Machine.brand.ilike(f"%{q}%"),
                Machine.description.ilike(f"%{q}%"),
            )
        )
    if site:
        stmt = stmt.where(Machine.site_name == site)
    if brand:
        stmt = stmt.where(Machine.brand.ilike(f"%{brand}%"))
    if price_min is not None:
        stmt = stmt.where(Machine.price >= price_min)
    if price_max is not None:
        stmt = stmt.where(Machine.price <= price_max)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    stmt = stmt.order_by(Machine.created_at.desc()).offset((page - 1) * limit).limit(limit)
    result = await db.execute(stmt)
    machines = result.scalars().all()

    return {
        "query": q,
        "page": page,
        "limit": limit,
        "total": total,
        "results": [_machine_to_dict(m) for m in machines],
    }


@router.get("/filters")
async def get_filters(db: AsyncSession = Depends(get_db)):
    """Return available filter values: sites, brands, price range."""
    sites_result = await db.execute(
        select(Machine.site_name, func.count(Machine.id).label("count"))
        .group_by(Machine.site_name)
        .order_by(func.count(Machine.id).desc())
    )
    sites = [{"site": r.site_name, "count": r.count} for r in sites_result]

    brands_result = await db.execute(
        select(Machine.brand, func.count(Machine.id).label("count"))
        .where(Machine.brand.isnot(None))
        .group_by(Machine.brand)
        .order_by(func.count(Machine.id).desc())
        .limit(50)
    )
    brands = [{"brand": r.brand, "count": r.count} for r in brands_result]

    price_result = await db.execute(
        select(
            func.min(Machine.price).label("min"),
            func.max(Machine.price).label("max"),
        ).where(Machine.price.isnot(None))
    )
    price_row = price_result.one()

    total = await db.scalar(select(func.count(Machine.id)))

    return {
        "total_machines": total,
        "sites": sites,
        "brands": brands,
        "price_range": {"min": price_row.min, "max": price_row.max},
    }


@router.get("/machine/{machine_id}")
async def get_machine(machine_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve a single machine by UUID and increment view count."""
    try:
        uid = _uuid.UUID(machine_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid machine ID: {machine_id}")

    machine = await db.scalar(select(Machine).where(Machine.id == uid))
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    await db.execute(
        update(Machine).where(Machine.id == uid).values(view_count=Machine.view_count + 1)
    )
    await db.commit()

    return {
        "id": str(machine.id),
        "name": machine.name,
        "brand": machine.brand,
        "price": machine.price,
        "currency": machine.currency,
        "location": machine.location,
        "image_url": machine.image_url,
        "description": machine.description,
        "specs": machine.specs or {},
        "source_url": machine.source_url,
        "site_name": machine.site_name,
        "language": machine.language,
        "view_count": machine.view_count,
        "click_count": machine.click_count,
        "created_at": machine.created_at.isoformat() if machine.created_at else None,
    }


@router.post("/track-click")
async def track_click(body: dict, db: AsyncSession = Depends(get_db)):
    """Record a click event and return the machine's source URL."""
    machine_id = body.get("machine_id")
    if not machine_id:
        raise HTTPException(status_code=400, detail="machine_id required")

    try:
        uid = _uuid.UUID(str(machine_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid machine_id")

    machine = await db.scalar(select(Machine).where(Machine.id == uid))
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    await db.execute(
        update(Machine).where(Machine.id == uid).values(click_count=Machine.click_count + 1)
    )
    db.add(ClickEvent(machine_id=uid))
    await db.commit()

    return {"redirect_url": machine.source_url}
