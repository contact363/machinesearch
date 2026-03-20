import httpx
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

sites = [
    ("vib_kg",       "https://vib-kg.com/usedmachines",                    "page"),
    ("bidspotter",   "https://www.bidspotter.com/en-us/for-sale/metalworking/machine-tools-and-tools", "page"),
    ("exapro",       "https://www.exapro.com/hot-deals/metal-machine-tools-c1/", "page"),
    ("used_machines","https://www.used-machines.com/k/gmcp-cat-2",          "page"),
    ("fm_machines",  "https://www.fm-machines.com/angebote",                "page"),
    ("ucy_machines", "https://www.ucymachines.com/en/machine-tools",        "page"),
]

for name, url, param in sites:
    print(f"\n{'='*50}")
    print(f"SITE: {name}")
    try:
        r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
        soup = BeautifulSoup(r.text, "lxml")

        # Find total count text
        for tag in soup.find_all(["span","div","p","h1","h2","h3"], string=True):
            text = tag.get_text(strip=True)
            if any(k in text.lower() for k in ["result","treffer","angebot","maschine","found","total","listing","item"]):
                if any(c.isdigit() for c in text):
                    print(f"  Count text: {text[:80]}")

        # Find pagination - last page number
        last_page = 1
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if param in href and text.isdigit():
                last_page = max(last_page, int(text))

        # Also check pagination elements
        pag = soup.find(class_=lambda c: c and any(
            k in c.lower() for k in ["pagination","pager","pages"]))
        if pag:
            print(f"  Pagination HTML: {str(pag)[:200]}")

        print(f"  Last page found: {last_page}")
        print(f"  Estimated total: {last_page} pages x ~20 items = {last_page*20}+ machines")

    except Exception as e:
        print(f"  ERROR: {e}")
