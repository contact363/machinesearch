"""
test_pagination.py — verify multi-page scraping for all 6 sites.

For each site: fetches pages 1-3 individually, reports per-page item counts,
confirms pages are unique, then reports 3-page total.

Usage (from backend/ with venv active):
    python test_pagination.py
"""

import asyncio
import io
import json
import sys
from pathlib import Path
from urllib.parse import urlparse, urlencode, parse_qs, urlunsplit

# Force UTF-8 output on Windows terminals to avoid charmap encoding errors
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv()

import httpx
from bs4 import BeautifulSoup
from scraper.anti_block import UserAgentRotator
from scraper.engine import AdaptiveEngine

ua = UserAgentRotator()
CONFIGS_DIR = Path(__file__).parent / "site_configs"

SITES = [
    "vib_kg.json",
    "bidspotter.json",
    "exapro.json",
    "used_machines.json",
    "fm_machines.json",
    "ucy_machines.json",
]


def build_page_url(base_url: str, param: str, page_num: int) -> str:
    parsed = urlparse(base_url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    if page_num == 1:
        qs.pop(param, None)   # page 1 = no param (clean URL)
    else:
        qs[param] = [str(page_num)]
    new_query = urlencode({k: v[0] for k, v in qs.items()})
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, new_query, ""))


async def fetch_items(url: str, container_sel: str) -> list[str]:
    """Fetch a URL and return list of first-text-line per item."""
    async with httpx.AsyncClient(
        headers=ua.get_headers(url), timeout=30, follow_redirects=True
    ) as c:
        r = await c.get(url)
    soup = BeautifulSoup(r.text, "lxml")
    items = soup.select(container_sel)
    return [el.get_text(separator=" ", strip=True)[:80] for el in items]


async def test_site_pagination(cfg: dict) -> dict:
    name = cfg["name"]
    pagination_type = cfg.get("pagination_type", "none")
    start_url = cfg["start_url"]
    param = cfg.get("pagination_param", "page")
    container = cfg["selectors"]["listing_container"]

    print(f"\n{'='*65}")
    print(f"SITE: {cfg.get('display_name', name)}")
    print(f"URL : {start_url}")
    print(f"TYPE: {pagination_type}")

    if pagination_type == "none":
        # All on one page
        items1 = await fetch_items(start_url, container)
        print(f"  [No pagination] Single page: {len(items1)} items")
        for i, t in enumerate(items1[:3], 1):
            print(f"    #{i}: {t[:70]}")
        print(f"  [{name}] Page 1: {len(items1)} items | Total: {len(items1)} unique")
        return {
            "name": name,
            "page_counts": [len(items1)],
            "total_unique": len(items1),
            "pages_different": True,
        }

    # page_param — fetch pages 1, 2, 3
    pages_data: list[list[str]] = []
    for pg in range(1, 4):
        url = build_page_url(start_url, param, pg)
        items = await fetch_items(url, container)
        pages_data.append(items)
        top3 = " | ".join(f'"{t[:35]}"' for t in items[:3])
        print(f"  Page {pg}: {len(items):3d} items  ->  {top3}")
        if not items:
            print(f"    (no items — stopping at page {pg})")
            break
        await asyncio.sleep(1.5)

    # Check uniqueness across pages
    all_texts = set()
    unique_per_page = []
    for items in pages_data:
        new_items = [t for t in items if t not in all_texts]
        unique_per_page.append(len(new_items))
        all_texts.update(items)

    pages_different = len(pages_data) < 2 or (
        len(pages_data) >= 2 and pages_data[0][:3] != pages_data[1][:3]
    )

    total_unique = len(all_texts)
    counts = [len(p) for p in pages_data]
    print(f"  Unique items new per page: {unique_per_page}")
    print(f"  Pages different: {'YES' if pages_different else 'NO (DUPLICATE PAGES!)'}")
    print(f"  [{name}] " + " | ".join(f"Page {i+1}: {c}" for i, c in enumerate(counts)) +
          f" | Total 3-page unique: {total_unique}")

    return {
        "name": name,
        "page_counts": counts,
        "total_unique": total_unique,
        "pages_different": pages_different,
    }


async def main():
    results = []
    for filename in SITES:
        path = CONFIGS_DIR / filename
        if not path.exists():
            print(f"\n[SKIP] {filename} not found")
            continue
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)

        try:
            r = await test_site_pagination(cfg)
            results.append(r)
        except Exception as e:
            print(f"\n  ERROR testing {filename}: {e}")
            results.append({"name": cfg.get("name", filename), "error": str(e)})
        await asyncio.sleep(2)

    # Final summary
    print(f"\n{'*'*65}")
    print("FINAL SUMMARY — 3-page pagination test")
    print(f"{'*'*65}")
    for r in results:
        name = r["name"]
        if "error" in r:
            print(f"  {name:<20} ERROR: {r['error'][:60]}")
            continue
        counts = r.get("page_counts", [])
        total = r.get("total_unique", 0)
        diff = "YES" if r.get("pages_different") else "NO (BROKEN)"
        pages_str = " + ".join(str(c) for c in counts)
        print(f"  {name:<20} pages [{pages_str}] = {total} unique | pages different: {diff}")

    print()
    print("Now running full AdaptiveEngine scrape (max_pages=3 each) for final count:")
    print("-"*65)

    for filename in SITES:
        path = CONFIGS_DIR / filename
        if not path.exists():
            continue
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)

        name = cfg["name"]
        test_cfg = {**cfg, "max_pages": 3, "detail_page": False}
        try:
            engine = AdaptiveEngine()
            items = await engine.run(test_cfg)
            print(f"  {name:<20} AdaptiveEngine max_pages=3 -> {len(items)} unique parsed items")
        except Exception as e:
            print(f"  {name:<20} ERROR: {e}")
        await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
