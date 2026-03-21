"""
MachineSearch API — main application entry point.

Initialises the FastAPI application, registers all routers, configures CORS,
and manages the application lifespan (startup / shutdown hooks).
"""

import asyncio
import os
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from api.routes import admin, analytics, auth, configs, machines, scraper, search
from database.db import init_db

scheduler = AsyncIOScheduler(timezone="UTC")


async def _auto_scrape_all():
    """Triggered every 2 hours: launches a background scrape for every active site."""
    from sqlalchemy import select
    from database.db import AsyncSessionLocal
    from database.models import SiteConfig
    from api.routes.admin import _run_scrape_background

    db_url = os.getenv("DATABASE_URL", "")
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(SiteConfig).where(SiteConfig.is_active == True)
        )
        sites = list(result.scalars().all())

    print(f"[auto-scrape] Starting scheduled scrape for {len(sites)} active sites")
    for sc in sites:
        cfg = {**(sc.config_json or {}), "name": sc.name}
        job_id = str(uuid.uuid4())
        asyncio.create_task(_run_scrape_background(sc.name, cfg, job_id, db_url))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: runs startup logic before yield, shutdown logic after."""
    print("MachineSearch API starting...")
    await init_db()
    scheduler.add_job(
        _auto_scrape_all,
        IntervalTrigger(hours=2),
        id="auto_scrape_all",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    print("Auto-scrape scheduler started (every 2 hours)")
    yield
    scheduler.shutdown(wait=False)
    print("MachineSearch API shutting down.")


app = FastAPI(
    title="MachineSearch API",
    description="Aggregated industrial-machine search platform",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(machines.router, prefix="/api/v1/machines", tags=["machines"])
app.include_router(scraper.router, prefix="/api/v1/scraper", tags=["scraper"])
app.include_router(configs.router, prefix="/api/v1/configs", tags=["configs"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])


@app.get("/health", tags=["health"])
async def health_check():
    """Simple liveness probe."""
    return {"status": "ok", "service": "machinesearch-api"}
