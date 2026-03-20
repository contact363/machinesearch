"""
MachineSearch API — main application entry point.

Initialises the FastAPI application, registers all routers, configures CORS,
and manages the application lifespan (startup / shutdown hooks).
"""

from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import admin, analytics, auth, configs, machines, scraper, search
from database.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: runs startup logic before yield, shutdown logic after."""
    print("MachineSearch API starting...")
    await init_db()
    yield
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
