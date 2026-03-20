import httpx
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

sites = [
    ("used_machines", "https://www.used-machines.com/en/machine-tools/"),
    ("bidspotter",    "https://www.bidspotter.com/en-us/for-sale/metalworking/machine-tools-and-tools"),
    ("exapro",        "https://www.exapro.com/metal-working-machinery/"),
    ("machinio",      "https://www.machinio.com/search?q=machine"),
]

for name, url in sites:
    print("\n" + "="*55)
    print("SITE:", name)
    print("="*55)
    try:
        r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
        soup = BeautifulSoup(r.text, "lxml")

        # used_machines
        if name == "used_machines":
            cards = soup.select("div.d-block.mb-4")
            print(f"Cards found: {len(cards)}")
            if cards:
                print(cards[0].prettify()[:1000])

        # bidspotter
        elif name == "bidspotter":
            cards = soup.select("div.thumb")
            print(f"Cards found: {len(cards)}")
            if cards:
                print(cards[0].prettify()[:1000])

        # exapro
        elif name == "exapro":
            cards = soup.select("div.ps-block__item, article, div.product")
            print(f"Cards found: {len(cards)}")
            if cards:
                print(cards[0].prettify()[:1000])
            else:
                # show all repeated divs
                from collections import Counter
                counts = Counter()
                for tag in soup.find_all(["div","article"], class_=True):
                    cls = " ".join(tag.get("class",[]))[:50]
                    counts[cls] += 1
                for cls, c in counts.most_common(10):
                    if c >= 3:
                        print(f"  x{c}  {cls}")

        # machinio
        elif name == "machinio":
            from collections import Counter
            counts = Counter()
            for tag in soup.find_all(["div","article","li"], class_=True):
                cls = " ".join(tag.get("class",[]))[:60]
                counts[cls] += 1
            print("Top repeated elements:")
            for cls, c in counts.most_common(10):
                if c >= 3:
                    print(f"  x{c}  {cls}")
            # first link
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if any(k in href for k in ["/machine","/listing","/equipment","/used"]):
                    print("First machine link:", href[:80])
                    break

    except Exception as e:
        print("ERROR:", e)
