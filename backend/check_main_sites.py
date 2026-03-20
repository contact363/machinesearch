import httpx
from bs4 import BeautifulSoup
from collections import Counter

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

sites = [
    ("fm_machines",    "https://www.fm-machines.com/"),
    ("cnc_toerner",    "https://cnc-toerner.de/kontakt/"),
    ("mbr_machinery",  "https://www.mbrmachinery.com/second-hand-machines-for-sale"),
    ("lrtt",           "https://www.lrtt.de/"),
    ("ucy_machines",   "https://www.ucymachines.com/en/machine-tools"),
    ("bade_maschinen", "https://www.bade-maschinen.de/"),
    ("reble_machinery","https://reble-machinery.de/"),
]

for name, url in sites:
    print("\n" + "="*55)
    print(f"SITE: {name}")
    print(f"URL:  {url}")
    print("="*55)
    try:
        r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
        html = r.text
        print(f"Status: {r.status_code} | Size: {len(html)} chars | Final: {r.url}")

        js_signals = ["__NEXT_DATA__", "__nuxt", "ng-version",
                      "data-reactroot", "_next/static", "wp-content"]
        framework = "static"
        for s in js_signals:
            if s in html:
                framework = s
                break
        print(f"Framework: {framework}")

        soup = BeautifulSoup(html, "lxml")
        counts = Counter()
        for tag in soup.find_all(["div","article","li","section"], class_=True):
            cls = " ".join(tag.get("class",[]))[:60]
            counts[cls] += 1

        print("Top repeated elements:")
        found_any = False
        for cls, c in counts.most_common(10):
            if c >= 3:
                print(f"  x{c}  {cls}")
                found_any = True
        if not found_any:
            print("  none found")

        # First product-like link
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if any(k in href.lower() for k in
                   ["/machine","/product","/used","/maschine",
                    "/equipment","/stock","/offer","/detail"]):
                if text and len(text) > 3:
                    print(f"Product link: {text[:40]} --> {href[:70]}")
                    break

    except Exception as e:
        print(f"ERROR: {e}")
