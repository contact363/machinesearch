"""
URL Crawler for MachineSearch.

Discovers listing URLs from a start page and fetches page content
via either plain httpx (static mode) or Playwright (dynamic mode).
"""

import asyncio
import logging
import os
import re
from urllib.parse import urljoin, urlparse

import httpx

from scraper.anti_block import DelayManager, ProxyManager, UserAgentRotator

logger = logging.getLogger(__name__)

_PLAYWRIGHT_ENABLED: bool = os.getenv("PLAYWRIGHT_ENABLED", "false").lower() == "true"

# Patterns that indicate a URL is a detail/listing page
_LISTING_PATH_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"/product/",
        r"/machine/",
        r"/item/",
        r"/listing/",
        r"/detail/",
        r"/catalog/[^/]+/\d+",  # /catalog/excavators/12345
        r"/tovar/",
        r"/ob/",
        r"/\d{4,}/",            # numeric ID segment ≥ 4 digits
        r"-\d{4,}$",            # slug ending with numeric ID
    ]
]

# Patterns that disqualify a URL (navigation, auth, static assets)
_EXCLUDE_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"/login",
        r"/logout",
        r"/register",
        r"/signup",
        r"/cart",
        r"/checkout",
        r"/admin",
        r"/account",
        r"/profile",
        r"\.(css|js|png|jpg|jpeg|gif|svg|ico|woff|woff2|ttf|pdf|zip)(\?|$)",
        r"^mailto:",
        r"^tel:",
        r"^javascript:",
        r"#",
    ]
]


class URLCrawler:
    """
    Discovers listing page URLs from a site's start URL and fetches HTML.
    Supports static (httpx) and dynamic (Playwright) fetch modes.
    """

    _MAX_DISCOVERED: int = 500

    def __init__(self, config: dict) -> None:
        self.config = config
        self._visited: set[str] = set()
        self._ua = UserAgentRotator()
        self._proxy_mgr = ProxyManager()
        self._delay = DelayManager()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def discover_listing_urls(self, start_url: str, mode: str) -> list[str]:
        """
        Fetch start_url and return deduplicated absolute listing URLs (max 500).
        """
        try:
            html = await self.get_page_content(start_url, mode)
        except Exception as exc:
            logger.error("[%s] Failed to fetch start URL %s: %s", self.config.get("name"), start_url, exc)
            return []

        urls: list[str] = []
        # Extract all <a href="..."> links
        for href in re.findall(r'<a[^>]+href=["\']([^"\']+)["\']', html, re.IGNORECASE):
            absolute = self._normalize_url(href, start_url)
            if not absolute:
                continue
            if absolute in self._visited:
                continue
            if self._is_listing_url(absolute):
                urls.append(absolute)
                self._visited.add(absolute)
            if len(urls) >= self._MAX_DISCOVERED:
                break

        logger.info(
            "[%s] Discovered %d listing URLs from %s",
            self.config.get("name"), len(urls), start_url,
        )
        return urls

    async def get_page_content(self, url: str, mode: str) -> str:
        """
        Fetch a single URL and return raw HTML.

        mode="static"  → httpx GET
        mode="dynamic" → Playwright (headless Chromium)
        mode="stealth" → Playwright + proxy + webdriver masking
        """
        if mode == "static":
            return await self._fetch_static(url)
        elif mode in ("dynamic", "stealth"):
            self._require_playwright(mode)
            return await self._fetch_playwright(url, stealth=(mode == "stealth"))
        else:
            logger.warning("Unknown fetch mode %r, falling back to static.", mode)
            return await self._fetch_static(url)

    # ------------------------------------------------------------------
    # Private: static fetch (httpx)
    # ------------------------------------------------------------------

    async def _fetch_static(self, url: str) -> str:
        proxy = self._proxy_mgr.get_proxy(self.config.get("proxy_tier", "none"))
        headers = self._ua.get_headers(url)

        async with httpx.AsyncClient(
            headers=headers,
            proxy=proxy,
            timeout=30,
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    # ------------------------------------------------------------------
    # Private: dynamic fetch (Playwright)
    # ------------------------------------------------------------------

    async def _fetch_playwright(self, url: str, stealth: bool = False) -> str:
        from playwright.async_api import async_playwright

        proxy = self._proxy_mgr.get_proxy(self.config.get("proxy_tier", "none")) if stealth else None
        playwright_proxy = None
        if proxy:
            # Convert httpx proxy dict to Playwright format
            proxy_url = proxy.get("https://") or proxy.get("http://")
            playwright_proxy = {"server": proxy_url} if proxy_url else None

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--disable-gpu",
                ],
            )
            context = await browser.new_context(
                proxy=playwright_proxy,
                user_agent=self._ua.get_random(),
                viewport={
                    "width": random.randint(1280, 1920),
                    "height": random.randint(800, 1080),
                },
                locale="en-US",
            )

            if stealth:
                await context.add_init_script(
                    "Object.defineProperty(navigator,'webdriver',{get:()=>false});"
                    "Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3]});"
                    "Object.defineProperty(navigator,'languages',{get:()=>['en-US','en']});"
                )

            page = await context.new_page()
            try:
                await page.goto(url, wait_until="networkidle", timeout=45_000)
                html = await page.content()
            finally:
                await context.close()
                await browser.close()

        return html

    # ------------------------------------------------------------------
    # Private: URL utilities
    # ------------------------------------------------------------------

    def _normalize_url(self, href: str, base: str) -> str | None:
        """Resolve href relative to base, return absolute URL or None."""
        href = href.strip()
        if not href or href.startswith(("javascript:", "mailto:", "tel:", "#")):
            return None
        try:
            absolute = urljoin(base, href)
            parsed = urlparse(absolute)
            # Must share the same domain as the base
            base_domain = urlparse(base).netloc
            if parsed.netloc != base_domain:
                return None
            # Strip fragment
            return absolute.split("#")[0]
        except Exception:
            return None

    def _is_listing_url(self, url: str) -> bool:
        """Return True if the URL looks like a machine detail/listing page."""
        path = urlparse(url).path
        for exc_pat in _EXCLUDE_PATTERNS:
            if exc_pat.search(url):
                return False
        for pat in _LISTING_PATH_PATTERNS:
            if pat.search(path):
                return True
        return False

    # ------------------------------------------------------------------
    # Private: guard
    # ------------------------------------------------------------------

    @staticmethod
    def _require_playwright(mode: str) -> None:
        if not _PLAYWRIGHT_ENABLED:
            raise RuntimeError(
                f"Mode '{mode}' requires Playwright, but PLAYWRIGHT_ENABLED=false in your .env. "
                "Set PLAYWRIGHT_ENABLED=true and run: "
                "pip install playwright && playwright install chromium"
            )


# Avoid NameError on Python < 3.12 where `random` might not be imported
import random  # noqa: E402 — must stay after class definition to satisfy linters
