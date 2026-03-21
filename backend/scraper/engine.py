"""
Adaptive scrape engine for MachineSearch.

Detects whether a site requires static or dynamic (JS-rendered) scraping,
handles all three pagination strategies, visits detail pages when configured,
and returns a clean list of parsed item dicts ready for database upsert.
"""

import asyncio
import logging
import os
import random
import re
from urllib.parse import urljoin, urlencode, urlparse, parse_qs, urlunsplit

import httpx
from bs4 import BeautifulSoup

from scraper.anti_block import DelayManager, ProxyManager, RetryHandler, UserAgentRotator
from scraper.parser import DataParser

logger = logging.getLogger(__name__)

_PLAYWRIGHT_ENABLED: bool = os.getenv("PLAYWRIGHT_ENABLED", "false").lower() == "true"

# Patterns that indicate heavy client-side rendering
_JS_FRAMEWORK_PATTERNS: list[str] = [
    "react",
    "__next_data__",
    "reactroot",
    "vue",
    "ng-app",
    "ng-version",
    "angular",
    "ember",
    "__nuxt",
    "window.__initialstate__",
    "window.initial_data",
]

_CLOUDFLARE_PATTERNS: list[str] = [
    "checking your browser",
    "cloudflare",
    "cf-browser-verification",
    "just a moment",
    "enable javascript and cookies",
]


class AdaptiveEngine:
    """
    Orchestrates a full scrape run for one site configuration.

    Selects static / dynamic / stealth fetch mode automatically,
    paginates through all listing pages, optionally follows detail links,
    and returns a deduplicated list of parsed item dicts.
    """

    _PLAYWRIGHT_SEMAPHORE_LIMIT: int = 3

    def __init__(self) -> None:
        self._browser_pool = None  # future: shared browser context pool
        self._playwright_sem = asyncio.Semaphore(self._PLAYWRIGHT_SEMAPHORE_LIMIT)
        self._ua = UserAgentRotator()
        self._proxy_mgr = ProxyManager()
        self._delay = DelayManager()
        self._retry = RetryHandler()
        self._parser = DataParser()

    # ------------------------------------------------------------------
    # Mode detection
    # ------------------------------------------------------------------

    async def detect_mode(self, url: str, config: dict) -> str:
        """
        Determine the optimal fetch mode for a site.

        If config["mode"] is not "auto", return it directly.
        Otherwise probe the URL with a lightweight httpx GET and inspect
        the response to choose: "static" | "dynamic" | "stealth".
        """
        configured_mode: str = config.get("mode", "auto")
        if configured_mode != "auto":
            logger.info("[%s] Using configured mode: %s", config.get("name"), configured_mode)
            return configured_mode

        logger.info("[%s] Auto-detecting fetch mode for %s", config.get("name"), url)
        try:
            async with httpx.AsyncClient(
                headers=self._ua.get_headers(url),
                timeout=10,
                follow_redirects=True,
            ) as client:
                response = await client.get(url)
        except Exception as exc:
            logger.warning("[%s] Mode probe failed (%s), defaulting to static.", config.get("name"), exc)
            return "static"

        # Blocked by Cloudflare / WAF
        if response.status_code in (403, 429):
            logger.info("[%s] Received %d — switching to stealth.", config.get("name"), response.status_code)
            return "stealth"

        html_lower = response.text.lower()

        for pattern in _CLOUDFLARE_PATTERNS:
            if pattern in html_lower:
                logger.info("[%s] Cloudflare detected — switching to stealth.", config.get("name"))
                return "stealth"

        # Check for heavy JS frameworks
        for pattern in _JS_FRAMEWORK_PATTERNS:
            if pattern in html_lower:
                logger.info("[%s] JS framework detected (%r) — switching to dynamic.", config.get("name"), pattern)
                return "dynamic"

        # Check for <noscript> with meaningful content (JS-gated sites)
        soup = BeautifulSoup(response.text, "html.parser")
        noscript_tags = soup.find_all("noscript")
        for tag in noscript_tags:
            if len(tag.get_text(strip=True)) > 50:
                logger.info("[%s] Heavy <noscript> content — switching to dynamic.", config.get("name"))
                return "dynamic"

        logger.info("[%s] No JS indicators — using static mode.", config.get("name"))
        return "static"

    # ------------------------------------------------------------------
    # Page scrapers
    # ------------------------------------------------------------------

    async def scrape_page(self, url: str, mode: str, config: dict) -> list[dict]:
        """Dispatch to the correct scraper based on mode."""
        if mode == "static":
            return await self.scrape_static(url, config)
        elif mode == "dynamic":
            return await self.scrape_dynamic(url, config)
        elif mode == "stealth":
            return await self.scrape_stealth(url, config)
        else:
            logger.warning("[%s] Unknown mode %r, falling back to static.", config.get("name"), mode)
            return await self.scrape_static(url, config)

    async def scrape_static(self, url: str, config: dict) -> list[dict]:
        """
        Fetch a listing page with httpx and extract items.

        Uses CSS selectors from config["selectors"] for generic sites.
        Applies vib-kg-aware field extraction (background-url images,
        slug-based name fallback, price text search, etc.) so the same
        method works correctly for vib-kg.com without any special-casing
        at the call site.
        """
        proxy = self._proxy_mgr.get_proxy(config.get("proxy_tier", "none"))
        headers = self._ua.get_headers(url)

        try:
            async with httpx.AsyncClient(
                headers=headers,
                proxy=proxy,
                timeout=30,
                follow_redirects=True,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if proxy and exc.response.status_code in (403, 429, 407):
                self._proxy_mgr.mark_failed(proxy)
            raise

        site_name: str = config.get("name", "")
        base_url: str = config.get("base_url", "") or config.get("start_url", "")
        selectors: dict = config.get("selectors", {})
        container_sel: str = selectors.get("listing_container", "")

        soup = BeautifulSoup(response.text, "lxml")

        if not container_sel:
            logger.warning("[%s] listing_container selector is empty.", site_name)
            return []

        containers = soup.select(container_sel)
        if not containers:
            logger.debug("[%s] No containers matched %r on %s", site_name, container_sel, url)
            return []

        items: list[dict] = []

        for el in containers:
            try:
                raw: dict = {"site_name": site_name}

                # ── Detail link ───────────────────────────────────────────
                detail_href = ""
                link_sel = selectors.get("detail_link", "")
                if link_sel:
                    link_node = el.select_one(link_sel)
                    if link_node:
                        detail_href = link_node.get("href", "")
                # Fallback: any first <a href> in the element
                if not detail_href:
                    any_a = el.find("a", href=True)
                    if any_a:
                        detail_href = any_a["href"]
                if detail_href:
                    raw["source_url"] = (
                        urljoin(base_url, detail_href)
                        if detail_href.startswith("/")
                        else detail_href
                    )
                else:
                    raw["source_url"] = url  # fallback to listing page

                # ── Name ──────────────────────────────────────────────────
                name = ""
                name_sel = selectors.get("name", "")
                if name_sel:
                    # selector may be comma-separated; try each in order
                    for sel_part in name_sel.split(","):
                        node = el.select_one(sel_part.strip())
                        if node:
                            name = node.get_text(strip=True)
                            break
                # Fallback: first h2 / h3 / strong in the element
                if not name:
                    for tag in ("h2", "h3", "strong"):
                        node = el.find(tag)
                        if node:
                            name = node.get_text(strip=True)
                            break
                # Fallback: derive from URL slug
                # e.g. "/usedmachines/star_st-20-01-29429" → "Star St 20"
                if not name and detail_href:
                    slug = detail_href.rstrip("/").split("/")[-1]
                    # strip trailing numeric ID segment
                    slug = re.sub(r"-\d{4,}$", "", slug)
                    slug = re.sub(r"_\d{4,}$", "", slug)
                    name = re.sub(r"[-_]", " ", slug).title()
                raw["name"] = name

                # ── Brand ─────────────────────────────────────────────────
                # Explicit selector first; fall back to first word of name
                brand = ""
                brand_sel = selectors.get("brand", "")
                if brand_sel:
                    node = el.select_one(brand_sel)
                    if node:
                        brand = node.get_text(strip=True)
                if not brand and name:
                    brand = name.split()[0].title()
                raw["brand"] = brand

                # ── Price ─────────────────────────────────────────────────
                # Try selector first; fall back to text scan for currency symbols
                price_raw = ""
                price_sel = selectors.get("price", "")
                if price_sel:
                    for sel_part in price_sel.split(","):
                        node = el.select_one(sel_part.strip())
                        if node:
                            price_raw = node.get_text(strip=True)
                            break
                if not price_raw:
                    # Scan all text nodes in the element for currency patterns
                    _currency_re = re.compile(
                        r"[\d\s.,]+\s*(?:EUR|USD|GBP|€|\$|£|сом|KGS|₽|руб)", re.IGNORECASE
                    )
                    for text_node in el.stripped_strings:
                        if _currency_re.search(text_node):
                            price_raw = text_node
                            break
                raw["price"] = price_raw

                # ── Image ─────────────────────────────────────────────────
                image_url = ""
                img_sel = selectors.get("image", "")
                if img_sel:
                    img_node = el.select_one(img_sel)
                    if img_node:
                        # 1. Standard src / data-src / data-lazy-src / data-original attributes
                        image_url = (
                            img_node.get("src")
                            or img_node.get("data-src")
                            or img_node.get("data-lazy-src")
                            or img_node.get("data-original")
                            or ""
                        )
                        # 2. CSS background: url('...') in style attribute
                        if not image_url:
                            style = img_node.get("style", "")
                            bg_match = re.search(r"url\(['\"]?([^'\")\s]+)['\"]?\)", style)
                            if bg_match:
                                image_url = bg_match.group(1)
                        # 3. Nested <img> tag
                        if not image_url:
                            nested_img = img_node.find("img")
                            if nested_img:
                                image_url = nested_img.get("src") or nested_img.get("data-src") or ""
                # Make absolute
                if image_url and image_url.startswith("/"):
                    image_url = urljoin(base_url, image_url)
                raw["image_url"] = image_url or None

                # ── Location ──────────────────────────────────────────────
                location = ""
                loc_sel = selectors.get("location", "")
                if loc_sel:
                    for sel_part in loc_sel.split(","):
                        node = el.select_one(sel_part.strip())
                        if node:
                            location = node.get_text(strip=True)
                            break
                # Scan li.machine-attribute for country/city keywords
                if not location:
                    _GEO_RE = re.compile(
                        r"\b(germany|deutschland|france|spain|italia|italy|"
                        r"poland|netherlands|austria|switzerland|"
                        r"berlin|munich|hamburg|paris|madrid|rome|"
                        r"kyrgyzstan|bishkek|almaty|kazakhstan)\b",
                        re.IGNORECASE,
                    )
                    for attr_el in el.select("li.machine-attribute"):
                        txt = attr_el.get_text(strip=True)
                        if _GEO_RE.search(txt):
                            location = txt
                            break
                # Site-level default location
                if not location:
                    location = config.get("default_location", "")
                raw["location"] = location or None

                # ── Description ───────────────────────────────────────────
                description = ""
                desc_node = el.select_one("div.machine-index-desc")
                if desc_node:
                    description = desc_node.get_text(separator=" ", strip=True)
                if not description:
                    desc_sel = selectors.get("description", "")
                    if desc_sel:
                        node = el.select_one(desc_sel)
                        if node:
                            description = node.get_text(separator=" ", strip=True)
                raw["description"] = description or None

                items.append(raw)

            except Exception as exc:
                logger.warning("[%s] Error extracting item on %s: %s", site_name, url, exc)
                continue

        logger.info("[%s] Found %d items on %s", site_name, len(items), url)
        return items

    async def scrape_dynamic(self, url: str, config: dict) -> list[dict]:
        """
        Playwright scraper for JS-rendered sites.
        Uses stealth mode to avoid bot detection, scrolls to trigger lazy loading.
        """
        self._require_playwright("dynamic")
        import os as _os
        from playwright.async_api import async_playwright

        # Honour PLAYWRIGHT_BROWSERS_PATH so Render can find Chromium
        # in the project directory (no root access required).
        _browser_path = _os.getenv("PLAYWRIGHT_BROWSERS_PATH")
        if _browser_path:
            _os.environ["PLAYWRIGHT_BROWSERS_PATH"] = _browser_path

        async with self._playwright_sem:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--single-process",
                        "--no-zygote",
                        "--disable-blink-features=AutomationControlled",
                        "--window-size=1920,1080",
                    ],
                )
                context = await browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    java_script_enabled=True,
                    ignore_https_errors=True,
                    extra_http_headers={
                        "Accept-Language": "en-US,en;q=0.9",
                        "Accept": (
                            "text/html,application/xhtml+xml,"
                            "application/xml;q=0.9,image/webp,*/*;q=0.8"
                        ),
                    },
                )
                # Stealth: hide automation signals
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    window.chrome = { runtime: {} };
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                """)
                page = await context.new_page()
                try:
                    logger.info("[%s] Playwright loading: %s", config.get("name"), url)
                    # Use domcontentloaded for React/Vite SPAs that never reach networkidle
                    wait_until = config.get("playwright_wait_until", "domcontentloaded")
                    await page.goto(url, wait_until=wait_until, timeout=60_000)

                    # Wait for JS framework to render content
                    await page.wait_for_timeout(5000)

                    # Scroll to trigger lazy loading
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                    await page.wait_for_timeout(1500)
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await page.wait_for_timeout(1500)

                    html = await page.content()
                    logger.info("[%s] Playwright got %d chars of HTML", config.get("name"), len(html))
                finally:
                    await context.close()
                    await browser.close()

        return self._extract_from_html(html, url, config)

    async def scrape_stealth(self, url: str, config: dict) -> list[dict]:
        """
        Fetch with Playwright + proxy + navigator.webdriver masking.
        Random viewport width (1280–1920) to vary fingerprint.
        """
        self._require_playwright("stealth")
        from playwright.async_api import async_playwright

        proxy = self._proxy_mgr.get_proxy(config.get("proxy_tier", "residential"))
        playwright_proxy = None
        if proxy:
            proxy_url = proxy.get("https://") or proxy.get("http://")
            playwright_proxy = {"server": proxy_url} if proxy_url else None

        async with self._playwright_sem:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
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
                # Mask automation signals
                await context.add_init_script(
                    """
                    Object.defineProperty(navigator,'webdriver',{get:()=>false});
                    Object.defineProperty(navigator,'plugins',{get:()=>[1,2,3,4,5]});
                    Object.defineProperty(navigator,'languages',{get:()=>['en-US','en']});
                    window.chrome = {runtime:{}};
                    """
                )
                page = await context.new_page()
                try:
                    await page.goto(url, wait_until="networkidle", timeout=60_000)
                    # Human-like: random short scroll before extraction
                    await page.mouse.wheel(0, random.randint(300, 700))
                    await asyncio.sleep(random.uniform(1, 2))
                    html = await page.content()
                finally:
                    await context.close()
                    await browser.close()

        return self._extract_from_html(html, url, config)

    # ------------------------------------------------------------------
    # HTML extraction
    # ------------------------------------------------------------------

    def _extract_from_html(self, html: str, page_url: str, config: dict) -> list[dict]:
        """
        Use CSS selectors from config["selectors"] to extract raw item dicts.
        Falls back gracefully if a selector is empty or matches nothing.
        """
        selectors = config.get("selectors", {})
        container_sel = selectors.get("listing_container", "")
        if not container_sel:
            logger.warning("[%s] listing_container selector is empty.", config.get("name"))
            return []

        soup = BeautifulSoup(html, "html.parser")
        containers = soup.select(container_sel)
        if not containers:
            logger.debug("[%s] No elements matched selector %r on %s", config.get("name"), container_sel, page_url)
            return []

        items: list[dict] = []
        for el in containers:
            raw: dict = {"source_url": page_url}

            for field in ["name", "price", "location", "brand", "description"]:
                sel = selectors.get(field, "")
                if sel:
                    node = el.select_one(sel)
                    raw[field] = node.get_text(strip=True) if node else ""

            # Image
            img_sel = selectors.get("image", "")
            if img_sel:
                img_node = el.select_one(img_sel)
                if img_node:
                    image_src = (
                        img_node.get("src")
                        or img_node.get("data-src")
                        or img_node.get("data-lazy-src")
                        or ""
                    )
                    if image_src and image_src.startswith("/"):
                        base = page_url.split("/")[0] + "//" + page_url.split("/")[2]
                        image_src = urljoin(base, image_src)
                    raw["image_url"] = image_src or None
            else:
                # Fallback: first img in container
                img_node = el.find("img")
                if img_node:
                    raw["image_url"] = img_node.get("src") or img_node.get("data-src") or None

            # Detail link — three strategies:
            # 1. explicit selector, 2. container is <a>, 3. first <a> inside
            link_sel = selectors.get("detail_link", "")
            if link_sel:
                link_node = el.select_one(link_sel)
                if link_node:
                    href = link_node.get("href", "")
                    raw["source_url"] = urljoin(page_url, href) if href else page_url
            elif el.name == "a" and el.get("href"):
                # Container IS the link (common in React/Next.js sites)
                href = el["href"]
                raw["source_url"] = urljoin(page_url, href) if href.startswith("/") else href
            else:
                # Fallback: first <a> inside the container
                any_a = el.find("a", href=True)
                if any_a:
                    href = any_a.get("href", "")
                    raw["source_url"] = urljoin(page_url, href) if href.startswith("/") else href

            items.append(raw)

        return items

    # ------------------------------------------------------------------
    # Detail page merge
    # ------------------------------------------------------------------

    async def _enrich_from_detail(self, item: dict, mode: str, config: dict) -> dict:
        """
        Visit item["source_url"], scrape additional fields (description, specs),
        and merge them into the item dict. Returns the (possibly enriched) item.
        """
        detail_url = item.get("source_url", "")
        if not detail_url:
            return item

        try:
            await self._delay.human_delay()
            if mode == "static":
                proxy = self._proxy_mgr.get_proxy(config.get("proxy_tier", "none"))
                async with httpx.AsyncClient(
                    headers=self._ua.get_headers(detail_url),
                    proxy=proxy,
                    timeout=30,
                    follow_redirects=True,
                ) as client:
                    response = await client.get(detail_url)
                    response.raise_for_status()
                    html = response.text
            else:
                from scraper.crawler import URLCrawler
                crawler = URLCrawler(config)
                html = await crawler.get_page_content(detail_url, mode)

            soup = BeautifulSoup(html, "html.parser")
            selectors = config.get("selectors", {})

            for field in ["description", "brand", "specs"]:
                if item.get(field):
                    continue  # already populated from listing page
                sel = selectors.get(field, "")
                if sel:
                    node = soup.select_one(sel)
                    if node:
                        item[field] = node.get_text(separator="\n", strip=True)

            if not item.get("image_url"):
                img_sel = selectors.get("image", "")
                if img_sel:
                    img_node = soup.select_one(img_sel)
                    if img_node:
                        item["image_url"] = (
                            img_node.get("src") or img_node.get("data-src") or ""
                        )

        except Exception as exc:
            logger.warning("[%s] Failed to enrich detail page %s: %s", config.get("name"), detail_url, exc)

        return item

    # ------------------------------------------------------------------
    # Pagination helpers
    # ------------------------------------------------------------------

    def _build_page_url(self, base_url: str, config: dict, page_num: int) -> str:
        """
        Construct the URL for a given page number using page_param strategy.
        Page 1 always returns the clean start_url (no param added) because
        many sites return errors or redirect when ?page=1 is present.
        e.g. page 2 -> https://example.com/machines?page=2
        """
        param = config.get("pagination_param", "page")
        parsed = urlparse(base_url)
        qs = parse_qs(parsed.query, keep_blank_values=True)
        if page_num <= 1:
            # Page 1 = clean URL, remove any stale page param
            qs.pop(param, None)
        else:
            qs[param] = [str(page_num)]
        new_query = urlencode({k: v[0] for k, v in qs.items()})
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, new_query, ""))

    async def _scroll_infinite(self, page, config: dict) -> str:
        """
        Scroll a Playwright page until no new content loads (max 30 scrolls).
        Returns final page HTML.
        """
        prev_height: int = 0
        for scroll_idx in range(30):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(1.5, 3.0))
            curr_height = await page.evaluate("document.body.scrollHeight")
            if curr_height == prev_height:
                logger.debug("[scroll] No new content after scroll %d, stopping.", scroll_idx + 1)
                break
            prev_height = curr_height
        return await page.content()

    # ------------------------------------------------------------------
    # Main entry
    # ------------------------------------------------------------------

    async def run(self, config: dict) -> list[dict]:
        """
        Full scrape run for one site config.

        1. Detect fetch mode.
        2. Paginate through all listing pages.
        3. Optionally enrich items from detail pages.
        4. Parse and deduplicate all items.
        5. Return list of clean item dicts.
        """
        site_name: str = config.get("name", "unknown")
        start_url: str = config.get("start_url", "")
        max_pages: int = config.get("max_pages", 50)
        pagination_type: str = config.get("pagination_type", "page_param")
        has_detail_page: bool = config.get("detail_page", False)

        mode = await self.detect_mode(start_url, config)

        all_raw: list[dict] = []
        seen_keys: set[str] = set()

        # ----------------------------------------------------------------
        # page_param pagination
        # Appends ?{pagination_param}=1, ?{pagination_param}=2 … to
        # config["start_url"] and stops as soon as a page yields 0 items.
        # ----------------------------------------------------------------
        if pagination_type == "page_param":
            for page_num in range(1, max_pages + 1):
                page_url = self._build_page_url(start_url, config, page_num)
                logger.info("[%s] Scraping page %d: %s", site_name, page_num, page_url)

                raw_items = await self._retry.execute(
                    lambda: self.scrape_page(page_url, mode, config),
                    max_attempts=3,
                    site_name=site_name,
                )

                # None means all retries failed; [] means page had no items
                if not raw_items:
                    logger.info(
                        "[%s] Page %d returned 0 items — stopping pagination.",
                        site_name, page_num,
                    )
                    break

                logger.info("[%s] Page %d | %d items found", site_name, page_num, len(raw_items))
                all_raw.extend(raw_items)
                await self._delay.page_delay()

        # ----------------------------------------------------------------
        # next_button pagination (Playwright only)
        # ----------------------------------------------------------------
        elif pagination_type == "next_button":
            self._require_playwright("next_button pagination")
            from playwright.async_api import async_playwright

            next_sel = config.get("selectors", {}).get("next_page", "")
            page_num = 0

            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
                context = await browser.new_context(user_agent=self._ua.get_random())
                page = await context.new_page()
                await page.goto(start_url, wait_until="networkidle", timeout=45_000)

                while page_num < max_pages:
                    page_num += 1
                    html = await page.content()
                    raw_items = self._extract_from_html(html, page.url, config)
                    logger.info("[%s] Page %d | %d items found", site_name, page_num, len(raw_items))

                    if not raw_items:
                        break

                    all_raw.extend(raw_items)

                    # Try to click next
                    if not next_sel:
                        break
                    next_btn = await page.query_selector(next_sel)
                    if not next_btn:
                        logger.info("[%s] No next button found, pagination complete.", site_name)
                        break
                    is_disabled = await next_btn.get_attribute("disabled")
                    if is_disabled is not None:
                        logger.info("[%s] Next button disabled, pagination complete.", site_name)
                        break

                    await next_btn.click()
                    await page.wait_for_load_state("networkidle", timeout=30_000)
                    await self._delay.page_delay()

                await context.close()
                await browser.close()

        # ----------------------------------------------------------------
        # infinite_scroll pagination (Playwright only)
        # ----------------------------------------------------------------
        elif pagination_type == "infinite_scroll":
            self._require_playwright("infinite_scroll pagination")
            from playwright.async_api import async_playwright

            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
                context = await browser.new_context(user_agent=self._ua.get_random())
                page = await context.new_page()
                await page.goto(start_url, wait_until="networkidle", timeout=45_000)
                html = await self._scroll_infinite(page, config)
                await context.close()
                await browser.close()

            raw_items = self._extract_from_html(html, start_url, config)
            logger.info("[%s] Infinite scroll | %d items found", site_name, len(raw_items))
            all_raw.extend(raw_items)

        else:
            logger.warning("[%s] Unknown pagination_type %r, scraping start URL only.", site_name, pagination_type)
            raw_items = await self._retry.execute(
                lambda: self.scrape_page(start_url, mode, config),
                max_attempts=3,
                site_name=site_name,
            )
            if raw_items:
                all_raw.extend(raw_items)

        # ----------------------------------------------------------------
        # Detail page enrichment
        # ----------------------------------------------------------------
        if has_detail_page and all_raw:
            logger.info("[%s] Enriching %d items from detail pages...", site_name, len(all_raw))
            enriched: list[dict] = []
            for raw_item in all_raw:
                enriched_item = await self._enrich_from_detail(raw_item, mode, config)
                enriched.append(enriched_item)
            all_raw = enriched

        # ----------------------------------------------------------------
        # Parse, deduplicate, and return
        # ----------------------------------------------------------------
        parsed: list[dict] = []
        for raw_item in all_raw:
            item = self._parser.parse_item(raw_item, config)
            if item is None:
                continue
            dedup_key = self._parser.generate_dedup_key(item)
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)
            parsed.append(item)

        logger.info(
            "[%s] Scrape complete — %d raw items → %d unique parsed items",
            site_name, len(all_raw), len(parsed),
        )
        return parsed

    # ------------------------------------------------------------------
    # Guard
    # ------------------------------------------------------------------

    @staticmethod
    def _require_playwright(feature: str) -> None:
        if not _PLAYWRIGHT_ENABLED:
            raise RuntimeError(
                f"'{feature}' requires Playwright, but PLAYWRIGHT_ENABLED=false in your .env.\n"
                "To enable:\n"
                "  1. Set PLAYWRIGHT_ENABLED=true in backend/.env\n"
                "  2. pip install playwright\n"
                "  3. playwright install chromium"
            )
