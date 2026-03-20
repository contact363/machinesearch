"""
Scraper control router.

Exposes HTTP endpoints for triggering, monitoring, and cancelling scrape
jobs.  Intended for admin use only — every endpoint should be protected
behind the auth dependency once that is implemented.
"""

from fastapi import APIRouter, BackgroundTasks

router = APIRouter()

# TODO: protect all endpoints with admin auth dependency
# TODO: wire up to scheduler/job_runner.py to dispatch real jobs


@router.post("/run/{site_name}")
async def trigger_scrape(site_name: str, background_tasks: BackgroundTasks):
    """
    Manually trigger a scrape for the given site configuration.

    TODO: validate that site_name maps to an existing JSON config.
    TODO: enqueue job via scheduler and return job_id.
    TODO: prevent duplicate concurrent jobs for the same site.
    """
    return {"status": "queued", "site": site_name, "job_id": None}


@router.get("/status")
async def scrape_status():
    """
    Return the current status of all running and recently completed scrape jobs.

    TODO: read job state from scheduler / Redis / DB.
    """
    return {"jobs": []}


@router.post("/stop/{job_id}")
async def stop_scrape(job_id: str):
    """
    Attempt to cancel a running scrape job by its ID.

    TODO: signal the background task / worker to stop gracefully.
    """
    return {"stopped": job_id}
