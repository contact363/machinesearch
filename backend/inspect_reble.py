import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import httpx
from bs4 import BeautifulSoup
from collections import Counter

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

urls = [
    "https://reble-machinery.de/angebote/",
    "https://reble-machinery.de/angebote/page/2/",
    "https://reble-machinery.de/",
]

for url in urls:
    try:
        r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
        soup = BeautifulSoup(r.text, "lxml")
        print(f"\nURL: {url} | Status: {r.status_code} | Size: {len(r.text)}")
        counts = Counter()
        for tag in soup.find_all(["div","article","li","section"], class_=True):
            cls = " ".join(tag.get("class",[]))[:70]
            counts[cls] += 1
        print("Repeated elements:")
        for cls, c in counts.most_common(15):
            if c >= 3:
                print(f"  x{c}  {cls}")
        # Show first product card
        for cls, c in counts.most_common(20):
            if c >= 4:
                first_cls = cls.split()[0]
                tag = soup.find(class_=first_cls)
                if tag and len(tag.get_text(strip=True)) > 20:
                    print(f"\nFirst element with class '{first_cls}':")
                    print(tag.prettify()[:1500])
                    break
        # Check pagination links
        print("\nPagination links:")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "page" in href or "/p/" in href:
                print(f"  {href[:100]}")
        # Also check for total count text
        for el in soup.find_all(string=True):
            txt = el.strip()
            if any(w in txt.lower() for w in ["machine", "maschinen", "ergebnis", "result", "produkt"]) and any(c.isdigit() for c in txt):
                if len(txt) < 100:
                    print(f"  Count text: {txt}")
    except Exception as e:
        print(f"ERROR: {e}")
