"""
Job runner — schedules and executes periodic scrape jobs.

Uses APScheduler (AsyncIOScheduler) to run scrape jobs for each enabled
site configuration on the interval defined by SCRAPE_INTERVAL_HOURS.
Jobs are persisted in the database so they survive application restarts.
"""

import logging
import os
from typing import Any

# TODO: pip install apscheduler
# from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

from scraper.engine import ScraperEngine

logger = logging.getLogger(__name__)

SCRAPE_INTERVAL_HOURS: int = int(os.getenv("SCRAPE_INTERVAL_HOURS", "6"))
MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "10"))

# TODO: configure SQLAlchemy jobstore pointing at DATABASE_URL
# TODO: configure thread/asyncio executor respecting MAX_WORKERS


class JobRunner:
    """Manages the APScheduler lifecycle and job registration."""

    def __init__(self) -> None:
        # TODO: initialise AsyncIOScheduler with jobstore and executor
        self.scheduler = None  # placeholder
        self._jobs: dict[str, Any] = {}

    def start(self) -> None:
        """
        Start the scheduler and register jobs for all enabled site configs.

        TODO: load enabled SiteConfigs from DB.
        TODO: register one interval job per config using add_job().
        TODO: call self.scheduler.start().
        """
        logger.info(
            "JobRunner starting (interval=%dh, max_workers=%d)",
            SCRAPE_INTERVAL_HOURS,
            MAX_WORKERS,
        )
        # TODO: remove stub

    def stop(self) -> None:
        """
        Gracefully shut down the scheduler.

        TODO: call self.scheduler.shutdown(wait=True).
        """
        logger.info("JobRunner stopping.")
        # TODO: remove stub

    async def run_site(self, config: dict[str, Any]) -> None:
        """
        Coroutine executed by APScheduler for a single site scrape.

        TODO: instantiate ScraperEngine(config) and await engine.run().
        TODO: log result summary and persist job history to DB.
        """
        name = config.get("name", "unknown")
        logger.info("Starting scheduled scrape for: %s", name)
        engine = ScraperEngine(config)
        result = await engine.run()
        logger.info("Scrape finished for %s: %s", name, result)

    def add_site(self, config: dict[str, Any]) -> str:
        """
        Dynamically register a new scrape job for a site config at runtime.

        TODO: call scheduler.add_job() and store the returned job ID.
        Returns the APScheduler job ID.
        """
        # TODO: implement
        return ""

    def remove_site(self, site_name: str) -> None:
        """
        Remove a site's scrape job from the scheduler.

        TODO: look up job ID by site_name and call scheduler.remove_job().
        """
        # TODO: implement
        pass
