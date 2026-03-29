"""
Search router — full-text and filtered search across machine listings.
"""

import uuid as _uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_db
from database.models import Machine, ClickEvent, MachineType, MachineBrand

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
        # Find type_ids matching the query (e.g. "VMC" → type_id of VMC)
        type_ids_result = await db.execute(
            select(MachineType.id).where(MachineType.name.ilike(f"%{q}%"))
        )
        matched_type_ids = [r[0] for r in type_ids_result]

        # Find brand_ids matching the query
        brand_ids_result = await db.execute(
            select(MachineBrand.id).where(MachineBrand.name.ilike(f"%{q}%"))
        )
        matched_brand_ids = [r[0] for r in brand_ids_result]

        conditions = [
            Machine.name.ilike(f"%{q}%"),
            Machine.brand.ilike(f"%{q}%"),
            Machine.description.ilike(f"%{q}%"),
            Machine.machine_type.ilike(f"%{q}%"),
        ]
        if matched_type_ids:
            conditions.append(Machine.type_id.in_(matched_type_ids))
        if matched_brand_ids:
            conditions.append(Machine.brand_id.in_(matched_brand_ids))

        stmt = stmt.where(or_(*conditions))
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


@router.get("/suggest")
async def suggest(q: str = Query(..., min_length=1), db: AsyncSession = Depends(get_db)):
    """
    Smart autocomplete — returns matching machine types and brands from the
    intelligence sheet so the search box can suggest as user types.
    """
    types_result = await db.execute(
        select(MachineType.name).where(MachineType.name.ilike(f"%{q}%")).limit(10)
    )
    brands_result = await db.execute(
        select(MachineBrand.name).where(MachineBrand.name.ilike(f"%{q}%")).limit(10)
    )
    return {
        "types": [r[0] for r in types_result],
        "brands": [r[0] for r in brands_result],
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


@router.get("/image-proxy")
async def proxy_image(url: str):
    """Proxy images that block direct browser hotlinking."""
    import httpx
    from fastapi.responses import Response

    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid URL")

    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": url,
                    "Accept": "image/*,*/*;q=0.8",
                },
                timeout=8,
                follow_redirects=True,
            )
            if r.status_code != 200:
                raise HTTPException(status_code=404, detail="Image not found")
            content_type = r.headers.get("content-type", "image/jpeg")
            return Response(
                content=r.content,
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "Access-Control-Allow-Origin": "*",
                },
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Image timeout")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
