import httpx
from bs4 import BeautifulSoup

sites = [
    ("machinio", "https://www.machinio.com", "machinio.com"),
    ("exapro", "https://www.exapro.com/used-machines/", "exapro.com"),
    ("used_machines", "https://www.used-machines.com", "used-machines.com"),
    ("bidspotter", "https://www.bidspotter.com/en-us", "bidspotter.com"),
]

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

for name, url, domain in sites:
    print(f"\n{'='*60}")
    print(f"SITE: {domain}")
    print(f"{'='*60}")
    try:
        r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
        soup = BeautifulSoup(r.text, "lxml")

        # Find repeated card elements
        candidates = []
        for tag in soup.find_all(["div","article","li","section"], class_=True):
            classes = " ".join(tag.get("class", []))
            if any(k in classes.lower() for k in ["card","item","machine","product","listing","result","offer"]):
                candidates.append(f"{tag.name} | {classes[:70]}")

        # Deduplicate and show top 5
        seen = set()
        count = 0
        for c in candidates:
            if c not in seen:
                seen.add(c)
                print(c)
                count += 1
                if count >= 5:
                    break

        # Show first machine link
        print("\nFIRST PRODUCT LINK:")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if any(k in href.lower() for k in ["/machine","/product","/listing","/used","/item","/equipment","/offer"]):
                if text and len(text) > 3:
                    print(f"  TEXT: {text[:50]}")
                    print(f"  HREF: {href[:80]}")
                    break

    except Exception as e:
        print(f"ERROR: {e}")
