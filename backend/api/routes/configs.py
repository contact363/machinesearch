"""
Site-config management router (public API v1).

All admin config management is handled by /admin/configs endpoints in admin.py.
Site configs are stored exclusively in the site_configs DB table.
"""

from fastapi import APIRouter, HTTPException, Path

router = APIRouter()

# TODO: protect all endpoints with admin auth dependency
# TODO: load/save configs from DB instead of raw JSON files
# TODO: validate incoming config against a Pydantic SiteConfig schema


@router.get("/")
async def list_configs():
    """
    List all registered site configurations.

    TODO: return list of SiteConfig objects from DB / config directory.
    """
    return {"configs": []}


@router.get("/{name}")
async def get_config(name: str = Path(..., description="Config name, e.g. vib_kg")):
    """
    Retrieve a single site configuration by its slug name.

    TODO: fetch from DB; raise 404 if not found.
    """
    raise HTTPException(status_code=404, detail=f"Config '{name}' not found")


@router.post("/")
async def create_config(config: dict):
    """
    Create a new site scraping configuration.

    TODO: validate against SiteConfig Pydantic schema.
    TODO: persist to DB and optionally write JSON file.
    """
    return {"created": config}


@router.put("/{name}")
async def update_config(name: str, config: dict):
    """
    Replace an existing site configuration.

    TODO: validate, update DB record, reload scheduler if enabled changed.
    """
    return {"updated": name}


@router.delete("/{name}")
async def delete_config(name: str):
    """
    Remove a site configuration (disables future scraping for that site).

    TODO: soft-delete or archive rather than hard-delete.
    """
    return {"deleted": name}
