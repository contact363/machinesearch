import httpx
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

sites = [
    ("machinio",      "https://www.machinio.com/search"),
    ("exapro",        "https://www.exapro.com/used-machines/"),
    ("used_machines", "https://www.used-machines.com/en/machine-tools/"),
    ("bidspotter",    "https://www.bidspotter.com/en-us/for-sale/metalworking/machine-tools-and-tools"),
]

for name, url in sites:
    print("\n" + "="*55)
    print("SITE:", name, "|", url)
    print("="*55)
    try:
        r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
        soup = BeautifulSoup(r.text, "lxml")

        # Count all repeated tags to find machine list
        from collections import Counter
        tag_counts = Counter()
        for tag in soup.find_all(["div","article","li"], class_=True):
            cls = " ".join(tag.get("class",[]))[:60]
            tag_counts[f"{tag.name}|{cls}"] += 1

        print("MOST REPEATED ELEMENTS (likely machine cards):")
        for tag_cls, count in tag_counts.most_common(8):
            if count >= 3:
                print(f"  x{count}  {tag_cls}")

        # First img with a parent link
        print("\nFIRST LINKED IMAGE:")
        for img in soup.find_all("img"):
            parent = img.find_parent("a")
            if parent and parent.get("href"):
                href = parent["href"]
                src = img.get("src","")
                alt = img.get("alt","")
                print(f"  ALT: {alt[:50]}")
                print(f"  SRC: {src[:80]}")
                print(f"  HREF: {href[:80]}")
                break

    except Exception as e:
        print("ERROR:", e)
