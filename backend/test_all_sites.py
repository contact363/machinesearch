"""
test_all_sites.py — smoke-test all 9 site configs against live sites.

For each site that returns 0 items the script:
  1. Fetches the start_url with httpx
  2. Prints the 10 most-repeated element tags+classes with counts
  3. Prints the first 800 chars of the most-repeated element
  4. Updates the listing_container selector in the JSON config
  5. Re-runs that site — up to 2 fix attempts total

Usage (from backend/ with venv active):
    python test_all_sites.py
"""

import asyncio
import json
import sys
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from scraper.engine import AdaptiveEngine
from scraper.anti_block import UserAgentRotator

CONFIGS_DIR = Path(__file__).parent / "site_configs"
SITE_CONFIG_FILES = [
    "vib_kg.json",
    "bidspotter.json",
    "exapro.json",
    "used_machines.json",
    "fm_machines.json",
    "ucy_machines.json",
    "lrtt.json",
    "cnc_toerner.json",
    "reble_machinery.json",
]

_ua = UserAgentRotator()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _element_signature(tag) -> str:
    """Return 'tagname.class1.class2' for a BS4 tag."""
    classes = tag.get("class", [])
    if classes:
        return tag.name + "." + ".".join(classes[:3])
    return tag.name


async def _probe_url(url: str) -> str | None:
    """Fetch url and return response text, or None on error."""
    try:
        async with httpx.AsyncClient(
            headers=_ua.get_headers(url),
            timeout=30,
            follow_redirects=True,
        ) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.text
    except Exception as exc:
        print(f"  [probe] ERROR fetching {url}: {exc}")
        return None


def _analyse_html(html: str) -> list[tuple[str, int, str]]:
    """
    Return list of (signature, count, first_800_chars) sorted by count desc.
    Only tags that appear >= 2 times are included (skip top-level scaffolding).
    """
    soup = BeautifulSoup(html, "lxml")
    # Remove scripts / styles
    for tag in soup(["script", "style", "head", "meta", "link"]):
        tag.decompose()

    counter: Counter = Counter()
    first_html: dict[str, str] = {}

    for tag in soup.find_all(True):
        sig = _element_signature(tag)
        counter[sig] += 1
        if sig not in first_html:
            first_html[sig] = str(tag)[:800]

    # Return top-10 that appear >= 2 times
    top = [(sig, cnt, first_html[sig]) for sig, cnt in counter.most_common(30) if cnt >= 2]
    return top[:10]


def _css_selector_from_sig(sig: str) -> str:
    """Convert 'div.listing__wrapper.col-md-4' → 'div.listing__wrapper'."""
    parts = sig.split(".")
    if len(parts) == 1:
        return parts[0]
    # Use tag + first two classes only
    return parts[0] + "." + ".".join(parts[1:3])


def _pick_container_candidate(top: list[tuple[str, int, str]]) -> str | None:
    """
    Pick the best listing container from the top-10 analysis.
    Prefers: article, div, li over generic tags.
    Skips navigation / layout noise (nav, header, footer, ul, body, html).
    """
    skip_tags = {"nav", "header", "footer", "ul", "ol", "body", "html",
                 "main", "section", "span", "p", "a", "img", "form",
                 "button", "input", "label", "select", "option"}
    for sig, cnt, _ in top:
        tag = sig.split(".")[0]
        if tag in skip_tags:
            continue
        if "." not in sig:
            continue  # bare tag with no class — too generic
        return _css_selector_from_sig(sig)
    return None


# ---------------------------------------------------------------------------
# Core test + auto-fix
# ---------------------------------------------------------------------------

async def test_site(config: dict) -> dict:
    test_cfg = {**config, "max_pages": 1, "detail_page": False}
    engine = AdaptiveEngine()
    try:
        items = await engine.run(test_cfg)
    except Exception as exc:
        return {"status": "FAILED", "items": 0, "error": str(exc), "sample": None}
    first = items[0] if items else None
    return {
        "status": "OK" if items else "FAILED",
        "items": len(items),
        "error": None,
        "sample": first.get("name") if first else None,
        "sample_url": first.get("source_url") if first else None,
    }


async def auto_fix_and_retest(config_path: Path, config: dict, attempt: int) -> tuple[dict, dict]:
    """
    Probe the site, print diagnosis, update listing_container in the JSON,
    return (updated_config, test_result).
    """
    site_name = config.get("name", "?")
    start_url = config.get("start_url", "")
    print(f"\n  [auto-fix attempt {attempt}] Probing {start_url} ...")

    html = await _probe_url(start_url)
    if html is None:
        return config, {"status": "FAILED", "items": 0, "error": "probe failed", "sample": None}

    top = _analyse_html(html)

    print(f"\n  Top 10 most-repeated elements on {site_name}:")
    print(f"  {'#':>3}  {'count':>5}  selector")
    print(f"  {'-'*3}  {'-'*5}  {'-'*40}")
    for i, (sig, cnt, _) in enumerate(top, 1):
        print(f"  {i:>3}  {cnt:>5}  {_css_selector_from_sig(sig)}")

    if top:
        best_sig, best_cnt, best_html = top[0]
        print(f"\n  First 800 chars of most-repeated element ({_css_selector_from_sig(best_sig)}, x{best_cnt}):")
        print("  " + best_html[:800].replace("\n", "\n  "))

    # Pick candidate container
    candidate = _pick_container_candidate(top)
    if candidate is None and top:
        candidate = _css_selector_from_sig(top[0][0])

    if not candidate:
        print(f"\n  [auto-fix] Could not determine a container selector.")
        return config, {"status": "FAILED", "items": 0, "error": "no candidate selector found", "sample": None}

    print(f"\n  [auto-fix] Updating listing_container: {config['selectors']['listing_container']!r} -> {candidate!r}")

    # Update config in-memory and on disk
    config["selectors"]["listing_container"] = candidate
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"  [auto-fix] Config saved. Re-running scrape...")
    await asyncio.sleep(2)
    result = await test_site(config)
    return config, result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    results = []

    for filename in SITE_CONFIG_FILES:
        config_path = CONFIGS_DIR / filename
        if not config_path.exists():
            print(f"\n[SKIP] Config not found: {config_path}")
            results.append({"name": filename, "status": "SKIPPED", "items": 0})
            continue

        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        site_name = config.get("name", filename)
        display  = config.get("display_name", site_name)

        print(f"\n{'='*60}")
        print(f"SITE : {display}")
        print(f"URL  : {config.get('start_url')}")
        print(f"{'='*60}")

        result = await test_site(config)

        # Auto-fix loop — up to 2 attempts
        for fix_attempt in range(1, 3):
            if result["status"] == "OK":
                break
            config, result = await auto_fix_and_retest(config_path, config, fix_attempt)

        if result["status"] == "OK":
            print(f"OK     {site_name}: {result['items']} items | {result['sample']}")
        else:
            err = f" | {result['error']}" if result.get("error") else ""
            print(f"FAILED {site_name}: 0 items{err}")

        results.append({"name": site_name, **result})
        await asyncio.sleep(2)

    # Summary
    total   = len(SITE_CONFIG_FILES)
    working = sum(1 for r in results if r["status"] == "OK")
    failed  = sum(1 for r in results if r["status"] == "FAILED")
    skipped = sum(1 for r in results if r.get("status") == "SKIPPED")

    print(f"\n{'*'*60}")
    print(f"TOTAL: {total} | WORKING: {working} | FAILED: {failed}" + (f" | SKIPPED: {skipped}" if skipped else ""))
    print(f"{'*'*60}")


if __name__ == "__main__":
    asyncio.run(main())
