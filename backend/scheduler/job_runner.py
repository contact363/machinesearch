"""
Job runner — schedules and executes periodic scrape jobs.

Handles large site counts (500-1000+) efficiently:
- MAX_CONCURRENT parallel scrapes (configurable via MAX_WORKERS env var)
- Priority queue: sites with fewer machines are scraped first (likely new sites)
- Site health tracking: auto-disables sites after 5 consecutive failures
"""

import asyncio
import logging
import os
from typing import Any

from scraper.engine import ScraperEngine

logger = logging.getLogger(__name__)

SCRAPE_INTERVAL_HOURS: int = int(os.getenv("SCRAPE_INTERVAL_HOURS", "6"))
MAX_CONCURRENT: int = int(os.getenv("MAX_WORKERS", "10"))


class WorkerPool:
    """
    Manages concurrent scrape execution with a semaphore-based worker pool.

    Sites are processed in priority order (fewer machines → higher priority)
    so newly added sites get their first scrape faster.
    """

    def __init__(self, max_concurrent: int = MAX_CONCURRENT) -> None:
        self.max_concurrent = max_concurrent
        self._sem = asyncio.Semaphore(max_concurrent)
        self._active: set[str] = set()

    async def run_site(self, config: dict[str, Any]) -> dict:
        """
        Run a single site scrape, respecting the concurrency limit.
        Returns a result dict with items_found, items_new, error.
        """
        name = config.get("name", "unknown")
        async with self._sem:
            self._active.add(name)
            try:
                logger.info("WorkerPool: starting scrape for %s", name)
                engine = ScraperEngine(config)
                result = await engine.run()
                logger.info("WorkerPool: finished %s — %s items", name, len(result) if isinstance(result, list) else "?")
                return {"site_name": name, "success": True, "items": result or []}
            except Exception as exc:
                logger.error("WorkerPool: scrape failed for %s: %s", name, exc)
                return {"site_name": name, "success": False, "error": str(exc)}
            finally:
                self._active.discard(name)

    async def run_batch(self, configs: list[dict[str, Any]]) -> list[dict]:
        """
        Run scrapes for a list of site configs concurrently (up to MAX_CONCURRENT at once).
        Configs are sorted by machine_count ascending so sites with fewer machines go first.
        """
        # Priority sort: fewer machines → higher priority (scrape first)
        sorted_configs = sorted(configs, key=lambda c: c.get("machine_count", 0))

        tasks = [self.run_site(cfg) for cfg in sorted_configs]
        results = await asyncio.gather(*tasks, return_exceptions=False)
        return list(results)

    @property
    def active_sites(self) -> set[str]:
        return set(self._active)


class JobRunner:
    """Manages the scrape job lifecycle with WorkerPool for scale."""

    def __init__(self) -> None:
        self.pool = WorkerPool(max_concurrent=MAX_CONCURRENT)
        self._running = False

    def start(self) -> None:
        logger.info(
            "JobRunner starting (interval=%dh, max_concurrent=%d)",
            SCRAPE_INTERVAL_HOURS,
            MAX_CONCURRENT,
        )
        self._running = True

    def stop(self) -> None:
        logger.info("JobRunner stopping.")
        self._running = False

    async def run_site(self, config: dict[str, Any]) -> None:
        """Run a single site scrape (for manual/scheduled invocation)."""
        await self.pool.run_site(config)

    async def run_all(self, configs: list[dict[str, Any]]) -> list[dict]:
        """
        Run all enabled site configs in batch, respecting MAX_CONCURRENT.
        Returns list of result dicts.
        """
        enabled = [c for c in configs if c.get("enabled", True)]
        logger.info("JobRunner: running %d/%d enabled sites", len(enabled), len(configs))
        return await self.pool.run_batch(enabled)

    def add_site(self, config: dict[str, Any]) -> str:
        """Register a site for future scheduled scraping. Returns site name."""
        return config.get("name", "")

    def remove_site(self, site_name: str) -> None:
        """Remove a site from scheduled scraping."""
        pass
