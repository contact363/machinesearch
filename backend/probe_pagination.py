"""Probe all 6 sites for pagination HTML and test page 2 URLs."""
import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv()

import httpx
from bs4 import BeautifulSoup
from scraper.anti_block import UserAgentRotator

ua = UserAgentRotator()

SITES = [
    ("vib_kg",       "https://vib-kg.com/usedmachines",
                     "https://vib-kg.com/usedmachines?page=2",
                     "li.list-group-item.p-0"),
    ("bidspotter",   "https://www.bidspotter.com/en-us/for-sale/metalworking/machine-tools-and-tools",
                     "https://www.bidspotter.com/en-us/for-sale/metalworking/machine-tools-and-tools?page=2",
                     "div.lot-single"),
    ("exapro",       "https://www.exapro.com/hot-deals/metal-machine-tools-c1/",
                     "https://www.exapro.com/hot-deals/metal-machine-tools-c1/?page=2",
                     "div.ps-product"),
    ("used_machines","https://www.used-machines.com/k/gmcp-cat-2",
                     "https://www.used-machines.com/k/gmcp-cat-2?page=2",
                     "section.grid-card"),
    ("fm_machines",  "https://www.fm-machines.com/angebote",
                     "https://www.fm-machines.com/angebote?page=2",
                     "div.listing__wrapper"),
    ("ucy_machines", "https://www.ucymachines.com/en/machine-tools",
                     "https://www.ucymachines.com/en/machine-tools?page=2",
                     "div.listing__wrapper"),
]


async def fetch(url):
    async with httpx.AsyncClient(
        headers=ua.get_headers(url), timeout=30, follow_redirects=True
    ) as c:
        r = await c.get(url)
    return r.status_code, r.text


def get_first_item_text(html, container_sel):
    soup = BeautifulSoup(html, "lxml")
    items = soup.select(container_sel)
    if items:
        return items[0].get_text(separator=" ", strip=True)[:120]
    return "(no items)"


def find_pagination(html):
    soup = BeautifulSoup(html, "lxml")
    results = {}

    # Common selectors
    for sel in [
        "a[rel=next]", ".pagination", "nav.pagination",
        "ul.pagination", ".pager", "a[rel=prev]",
        "pagination",  # custom element
    ]:
        nodes = soup.select(sel)
        if nodes:
            results[sel] = str(nodes[0])[:200]

    # Hrefs with page numbers
    page_hrefs = set()
    for a in soup.find_all("a", href=True):
        h = a["href"]
        if re.search(r"page[=/]\d+|start=\d+|offset=\d+|p=\d+|pg=\d+", h, re.I):
            page_hrefs.add(h)
    if page_hrefs:
        results["page_hrefs"] = sorted(page_hrefs)[:8]

    # Check for numbered page links (e.g. ?page=3)
    for pattern in [r"\?page=(\d+)", r"&page=(\d+)", r"/page/(\d+)", r"\?start=(\d+)", r"\?offset=(\d+)"]:
        matches = re.findall(pattern, html)
        if matches:
            results[f"pattern:{pattern}"] = sorted(set(matches), key=int)[:8]

    return results


async def probe_site(name, url1, url2, container_sel):
    print(f"\n{'='*60}")
    print(f"SITE: {name}")

    status1, html1 = await fetch(url1)
    items1 = BeautifulSoup(html1, "lxml").select(container_sel)
    first1 = get_first_item_text(html1, container_sel)
    print(f"  Page 1: status={status1} | {len(items1)} items | first: {first1[:80]}")

    pag = find_pagination(html1)
    for k, v in pag.items():
        print(f"  PAGINATION [{k}]: {str(v)[:200]}")

    status2, html2 = await fetch(url2)
    items2 = BeautifulSoup(html2, "lxml").select(container_sel)
    first2 = get_first_item_text(html2, container_sel)
    print(f"  Page 2: status={status2} | {len(items2)} items | first: {first2[:80]}")

    different = first1[:60] != first2[:60] and len(items2) > 0
    print(f"  >> Different from page 1: {'YES' if different else 'NO'}")
    print(f"  SITE: {name} | page 2 items: {len(items2)} | different from page 1: {'YES' if different else 'NO'}")

    return {
        "name": name,
        "items1": len(items1),
        "items2": len(items2),
        "different": different,
        "pagination": pag,
        "html1": html1,
        "html2": html2,
    }


async def main():
    results = {}
    for name, url1, url2, container in SITES:
        try:
            r = await probe_site(name, url1, url2, container)
            results[name] = r
        except Exception as e:
            print(f"  ERROR probing {name}: {e}")
        await asyncio.sleep(2)

    print("\n" + "="*60)
    print("SUMMARY")
    for name, r in results.items():
        print(f"  {name:20s} p1={r['items1']:3d}  p2={r['items2']:3d}  different={'YES' if r['different'] else 'NO'}")


if __name__ == "__main__":
    asyncio.run(main())
