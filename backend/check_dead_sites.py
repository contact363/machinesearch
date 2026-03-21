import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import httpx
from bs4 import BeautifulSoup
from collections import Counter

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

sites = [
    ("bade_maschinen", [
        "https://www.bade-maschinen.de/",
        "https://www.bade-maschinen.de/maschinen/",
        "https://www.bade-maschinen.de/gebrauchtmaschinen/",
    ]),
    ("mbrmachinery", [
        "https://www.mbrmachinery.com/used-machines-for-sale",
        "https://www.mbrmachinery.com/second-hand-machines-for-sale",
    ]),
]

for name, urls in sites:
    print(f"\n{'='*50}")
    print(f"SITE: {name}")
    for url in urls:
        try:
            r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
            soup = BeautifulSoup(r.text, "lxml")
            print(f"\n  URL: {url}")
            print(f"  Status: {r.status_code} | Size: {len(r.text)}")
            counts = Counter()
            for tag in soup.find_all(["div","article","li"], class_=True):
                cls = " ".join(tag.get("class",[]))[:60]
                counts[cls] += 1
            for cls, c in counts.most_common(6):
                if c >= 3:
                    print(f"  x{c}  {cls}")
            for a in soup.find_all("a", href=True)[:5]:
                href = a["href"]
                text = a.get_text(strip=True)
                if text and len(text) > 3:
                    print(f"  Link: {text[:40]} --> {href[:70]}")
        except Exception as e:
            print(f"  ERROR: {e}")
