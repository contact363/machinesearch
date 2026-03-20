import httpx
from bs4 import BeautifulSoup
from collections import Counter

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

sites = [
    ("cnc_toerner",    "https://cnc-toerner.de/maschinen/"),
    ("lrtt",           "http://lrtt.de/maschinenmarkt.php"),
    ("reble_machinery","https://reble-machinery.de/maschinen/"),
]

for name, url in sites:
    print("\n" + "="*55)
    print(f"SITE: {name} | {url}")
    print("="*55)
    try:
        r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
        html = r.text
        print(f"Status: {r.status_code} | Size: {len(html)} | Final: {r.url}")

        soup = BeautifulSoup(html, "lxml")
        counts = Counter()
        for tag in soup.find_all(["div","article","li","section"], class_=True):
            cls = " ".join(tag.get("class",[]))[:60]
            counts[cls] += 1

        print("Top repeated elements:")
        for cls, c in counts.most_common(8):
            if c >= 3:
                print(f"  x{c}  {cls}")

        # First machine card HTML
        for cls, c in counts.most_common(15):
            if c >= 4:
                tag_name = cls.split()[0] if cls else "div"
                first = soup.find(attrs={"class": cls.split()[0]})
                if first:
                    print(f"\nFirst card ({cls[:40]}):")
                    print(first.prettify()[:800])
                    break

    except Exception as e:
        print(f"ERROR: {e}")
