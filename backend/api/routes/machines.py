"""
Machines router.

CRUD endpoints for individual machine listings stored in the database.
Supports listing, retrieving a single machine by ID, creating, updating,
and soft-deleting records.
"""

from fastapi import APIRouter, HTTPException, Path

router = APIRouter()

# TODO: inject database session via FastAPI dependency
# TODO: define Pydantic request/response schemas in a schemas.py module


@router.get("/")
async def list_machines(page: int = 1, page_size: int = 20):
    """
    Return a paginated list of all machine listings.

    TODO: query DB with pagination, ordering by scraped_at DESC.
    TODO: add filter query params (site, brand, active_only).
    """
    return {"page": page, "results": [], "total": 0}


@router.get("/{machine_id}")
async def get_machine(machine_id: int = Path(..., description="Machine listing ID")):
    """
    Retrieve a single machine listing by its primary key.

    TODO: fetch from DB, raise 404 if not found.
    """
    raise HTTPException(status_code=404, detail="Machine not found")


@router.delete("/{machine_id}")
async def delete_machine(machine_id: int = Path(...)):
    """
    Soft-delete a machine listing.

    TODO: set is_active=False rather than hard-deleting the row.
    """
    return {"deleted": machine_id}
