"""
Anti-blocking utilities for MachineSearch scraper.

Provides user-agent rotation, proxy management, human-like delays,
and a retry handler to avoid bot detection and handle transient errors.
"""

import asyncio
import logging
import os
import random
import time
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# User-Agent Rotator
# ---------------------------------------------------------------------------

class UserAgentRotator:
    """Rotates through a pool of realistic 2024-2025 browser user agents."""

    # Pool intentionally uses only Windows and Linux desktop UAs.
    # macOS and Safari UAs are excluded: several sites (e.g. Exapro) serve
    # a stripped page variant when a macOS UA is detected, returning zero
    # product cards in the static HTML.
    _USER_AGENTS: list[str] = [
        # Chrome 124 – Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        # Chrome 125 – Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        # Chrome 126 – Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        # Chrome 124 – Windows (alternate build)
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.207 Safari/537.36",
        # Chrome 125 – Windows (alternate build)
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.142 Safari/537.36",
        # Chrome 124 – Linux
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        # Chrome 125 – Linux
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        # Firefox 125 – Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        # Firefox 124 – Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
        # Firefox 126 – Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
        # Firefox 124 – Linux
        "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
        # Firefox 125 – Linux
        "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
        # Edge 124 – Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        # Edge 125 – Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
        # Edge 126 – Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0",
        # Opera 110 – Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 OPR/110.0.0.0",
        # Opera 111 – Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 OPR/111.0.0.0",
        # Brave – Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Brave/1.65",
        # Chrome 124 – Android (kept for variety; does not cause the macOS issue)
        "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        # Chrome 125 – Android
        "Mozilla/5.0 (Linux; Android 14; SM-S921B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36",
    ]

    _ACCEPT_LANGUAGES: list[str] = [
        "en-US,en;q=0.9",
        "ru-RU,ru;q=0.9,en;q=0.8",
        "de-DE,de;q=0.9,en;q=0.8",
        "zh-CN,zh;q=0.9,en;q=0.8",
    ]

    def get_random(self) -> str:
        """Return a random user-agent string."""
        return random.choice(self._USER_AGENTS)

    def get_headers(self, url: str) -> dict[str, str]:
        """
        Return a full set of browser-like HTTP request headers for the given URL.
        Referer is derived from the URL's origin.
        """
        from urllib.parse import urlparse
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"

        ua = self.get_random()
        is_firefox = "Firefox" in ua

        return {
            "User-Agent": ua,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
                if not is_firefox
                else "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": random.choice(self._ACCEPT_LANGUAGES),
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Referer": origin,
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }


# ---------------------------------------------------------------------------
# Proxy Manager
# ---------------------------------------------------------------------------

class ProxyManager:
    """
    Manages Bright Data proxy pools.
    Supports: none | shared | residential proxy tiers.
    Tracks temporarily failed proxies with a 5-minute cooldown.
    """

    _COOLDOWN_SECONDS: int = 300  # 5 minutes

    def __init__(self) -> None:
        self._host: str = os.getenv("BRIGHT_DATA_HOST", "")
        self._port: str = os.getenv("BRIGHT_DATA_PORT", "")
        self._user: str = os.getenv("BRIGHT_DATA_USER", "")
        self._password: str = os.getenv("BRIGHT_DATA_PASS", "")
        # Maps proxy_url → timestamp when cooldown expires
        self._failed: dict[str, float] = {}

    def _is_configured(self) -> bool:
        return all([self._host, self._port, self._user, self._password])

    def _build_proxy(self, username_suffix: str = "") -> dict[str, str]:
        user = f"{self._user}{username_suffix}"
        proxy_url = f"http://{user}:{self._password}@{self._host}:{self._port}"
        return {"http://": proxy_url, "https://": proxy_url}

    def get_proxy(self, tier: str) -> dict[str, str] | None:
        """
        Return an httpx-compatible proxy dict for the given tier, or None.

        tier="none"        → no proxy
        tier="shared"      → Bright Data shared datacenter proxy
        tier="residential" → Bright Data residential proxy with random country
        """
        if tier == "none" or not self._is_configured():
            return None

        if tier == "shared":
            proxy = self._build_proxy()
        elif tier == "residential":
            # Rotate through common target countries
            country = random.choice(["us", "de", "gb", "fr", "ru", "kz"])
            session_id = random.randint(100000, 999999)
            proxy = self._build_proxy(
                username_suffix=f"-country-{country}-session-{session_id}"
            )
        else:
            logger.warning("Unknown proxy tier %r, using no proxy.", tier)
            return None

        proxy_key = list(proxy.values())[0]
        now = time.monotonic()
        if proxy_key in self._failed and self._failed[proxy_key] > now:
            remaining = int(self._failed[proxy_key] - now)
            logger.debug("Proxy on cooldown for %ds, falling back to no proxy.", remaining)
            return None

        return proxy

    def mark_failed(self, proxy: dict[str, str]) -> None:
        """Place a proxy on a 5-minute cooldown after a failure."""
        for proxy_url in proxy.values():
            self._failed[proxy_url] = time.monotonic() + self._COOLDOWN_SECONDS
            logger.warning("Proxy marked failed, cooldown %ds: %s", self._COOLDOWN_SECONDS, proxy_url)


# ---------------------------------------------------------------------------
# Delay Manager
# ---------------------------------------------------------------------------

class DelayManager:
    """Provides human-like async delays between requests."""

    async def human_delay(self) -> None:
        """Short delay mimicking a human reading a page (1.5 – 4 s)."""
        delay = random.uniform(1.5, 4.0)
        logger.debug("Human delay: %.2fs", delay)
        await asyncio.sleep(delay)

    async def page_delay(self) -> None:
        """Longer delay between full page loads (3 – 7 s)."""
        delay = random.uniform(3.0, 7.0)
        logger.debug("Page delay: %.2fs", delay)
        await asyncio.sleep(delay)

    async def retry_delay(self, attempt: int) -> None:
        """Exponential back-off: 2^attempt seconds, capped at 60 s."""
        delay = min(2 ** attempt, 60)
        logger.debug("Retry delay attempt %d: %ds", attempt, delay)
        await asyncio.sleep(delay)


# ---------------------------------------------------------------------------
# Retry Handler
# ---------------------------------------------------------------------------

class RetryHandler:
    """
    Wraps an async coroutine with configurable retry logic.
    Logs each attempt with site context and returns None after exhausting retries.
    """

    def __init__(self) -> None:
        self._delay = DelayManager()

    async def execute(
        self,
        coro_fn,
        max_attempts: int = 3,
        site_name: str = "",
    ):
        """
        Execute a coroutine factory (callable that returns a coroutine) up to
        max_attempts times.  Returns the result on success or None on failure.

        Usage:
            result = await retry.execute(
                lambda: fetch_page(url), max_attempts=3, site_name="vib_kg"
            )
        """
        last_exc: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                logger.info("[%s] Attempt %d/%d", site_name, attempt, max_attempts)
                return await coro_fn()
            except httpx.TimeoutException as exc:
                last_exc = exc
                logger.warning("[%s] Timeout on attempt %d: %s", site_name, attempt, exc)
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                logger.warning(
                    "[%s] HTTP %d on attempt %d: %s",
                    site_name, exc.response.status_code, attempt, exc.request.url,
                )
                # Don't retry client errors except 429
                if exc.response.status_code not in (429, 503, 502, 500):
                    break
            except httpx.RequestError as exc:
                last_exc = exc
                logger.warning("[%s] Request error on attempt %d: %s", site_name, attempt, exc)
            except asyncio.TimeoutError as exc:
                last_exc = exc
                logger.warning("[%s] asyncio.TimeoutError on attempt %d", site_name, attempt)
            except Exception as exc:
                last_exc = exc
                logger.exception("[%s] Unexpected error on attempt %d: %s", site_name, attempt, exc)

            if attempt < max_attempts:
                await self._delay.retry_delay(attempt)
                # Re-create coro from scratch — consumed coroutines can't be re-awaited.
                # Callers must pass a coroutine factory pattern; see engine.py usage.

        logger.error(
            "[%s] All %d attempts failed. Last error: %s",
            site_name, max_attempts, last_exc,
        )
        return None
