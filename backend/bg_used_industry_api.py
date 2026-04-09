"""
BG Used Industry — Standalone API Server

Runs as a completely separate FastAPI app on its own port.
Only serves data scraped from bg-used-industry.com.

Run:
    cd backend
    uvicorn bg_used_industry_api:app --host 0.0.0.0 --port 8001 --reload

Or directly:
    python bg_used_industry_api.py
"""

import os
import uuid as _uuid
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------
_db_url = os.getenv("DATABASE_URL", "")
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif _db_url.startswith("postgresql://") and "+asyncpg" not in _db_url:
    _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

_engine = create_async_engine(_db_url, echo=False, pool_pre_ping=True, pool_size=3, max_overflow=5)
_Session = async_sessionmaker(bind=_engine, expire_on_commit=False, autoflush=False)

SITE = "bg-used-industry"


async def _get_db() -> AsyncSession:
    async with _Session() as session:
        yield session


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("BG Used Industry API starting...")
    yield
    await _engine.dispose()
    print("BG Used Industry API stopped.")


app = FastAPI(
    title="BG Used Industry API",
    description=(
        "REST API for all used industrial machines scraped from bg-used-industry.com. "
        "~1,400+ machines: CNC machining centres, lathes, milling machines, grinders, and more."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _to_dict(m) -> dict:
    specs = m.specs or {}
    primary = m.image_url
    extras = m.extra_images or []
    all_images = []
    if primary:
        all_images.append(primary)
    for img in extras:
        if img and img not in all_images:
            all_images.append(img)

    return {
        "id": str(m.id),
        "catalog_id": m.catalog_id,
        "source_url": m.source_url,
        "name": m.name,
        "brand": m.brand,
        "model": specs.get("Model") or specs.get("model"),
        "machine_type": m.machine_type,
        "condition": m.condition,
        "year_of_manufacture": m.year_of_manufacture,
        "location": m.location,
        "country_of_origin": m.country_of_origin,
        "price": m.price,
        "currency": m.currency or "EUR",
        "image_url": primary,
        "extra_images": extras,
        "all_images": all_images,
        "specs": specs,
        "description": m.description,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Import Machine model lazily to avoid circular import issues
# ---------------------------------------------------------------------------
def _machine_model():
    from database.models import Machine
    return Machine


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", tags=["info"])
async def root():
    """API info."""
    return {
        "api": "BG Used Industry API",
        "source": "https://www.bg-used-industry.com",
        "version": "1.0.0",
        "endpoints": {
            "list_machines": "GET /machines",
            "get_machine":   "GET /machines/{id}",
            "filters":       "GET /filters",
            "health":        "GET /health",
            "docs":          "GET /docs",
        },
    }


@app.get("/health", tags=["info"])
async def health():
    return {"status": "ok", "source": SITE}


@app.get("/machines", tags=["machines"])
async def list_machines(
    q: Optional[str] = Query(None, description="Search in name, brand, type, description"),
    brand: Optional[str] = Query(None, description="Filter by brand (partial match, case-insensitive)"),
    machine_type: Optional[str] = Query(None, description="Filter by machine type (partial match)"),
    condition: Optional[str] = Query(None, description="Filter by condition (e.g. 'used')"),
    location: Optional[str] = Query(None, description="Filter by location (partial match)"),
    year_min: Optional[int] = Query(None, description="Minimum year of manufacture"),
    year_max: Optional[int] = Query(None, description="Maximum year of manufacture"),
    has_price: Optional[bool] = Query(None, description="true = only machines with a price listed"),
    has_image: Optional[bool] = Query(None, description="true = only machines with an image"),
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    limit: int = Query(20, ge=1, le=100, description="Results per page (max 100)"),
):
    """
    List all BG Used Industry machines with optional filters and pagination.

    All filters are optional and can be combined freely.
    Results are ordered newest-first (by date added to database).
    """
    Machine = _machine_model()
    async with _Session() as db:
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
        "total_pages": -(-total // limit),  # ceiling division
        "results": [_to_dict(m) for m in machines],
    }


@app.get("/machines/{machine_id}", tags=["machines"])
async def get_machine(machine_id: str):
    """Get a single machine by its UUID (from the `id` field in list results)."""
    try:
        uid = _uuid.UUID(machine_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid machine ID — must be a UUID")

    Machine = _machine_model()
    async with _Session() as db:
        machine = await db.scalar(
            select(Machine).where(Machine.id == uid, Machine.site_name == SITE)
        )

    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    return _to_dict(machine)


@app.get("/filters", tags=["filters"])
async def get_filters():
    """
    Returns all available filter values — use this to build dropdown menus.

    Includes: brands, machine types, locations, year range,
    and counts of machines with image / with price.
    """
    Machine = _machine_model()
    async with _Session() as db:
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


# ---------------------------------------------------------------------------
# Run directly
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("bg_used_industry_api:app", host="0.0.0.0", port=8001, reload=True)
