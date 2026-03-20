import httpx
from bs4 import BeautifulSoup
from collections import Counter
import re, json

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

url = "https://www.zatpatmachines.com"

print(f"Fetching: {url}")
try:
    r = httpx.get(url, headers=headers, timeout=20, follow_redirects=True)
    print(f"Status: {r.status_code}")
    print(f"Final URL: {r.url}")
    print(f"Size: {len(r.text)} chars")

    html = r.text

    # Framework detection
    signals = {
        "Next.js":    "__NEXT_DATA__",
        "_next":      "_next/static",
        "React":      "data-reactroot",
        "Vue":        "__nuxt",
        "WordPress":  "wp-content",
        "Angular":    "ng-version",
    }
    print("\nFramework:")
    for name, signal in signals.items():
        if signal in html:
            print(f"  {name} detected")

    soup = BeautifulSoup(html, "lxml")

    # Repeated elements
    counts = Counter()
    for tag in soup.find_all(["div","article","li","section"], class_=True):
        cls = " ".join(tag.get("class",[]))[:60]
        counts[cls] += 1

    print("\nTop repeated elements:")
    for cls, c in counts.most_common(10):
        if c >= 3:
            print(f"  x{c}  {cls}")

    # All navigation links
    print("\nNavigation links:")
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]
        if text and len(text) > 2 and len(text) < 40:
            print(f"  {text[:35]:35} --> {href[:60]}")

    # Check NEXT_DATA
    match = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            print("\nNEXT_DATA found:")
            print(json.dumps(data, indent=2)[:1000])
        except:
            print("\nNEXT_DATA found but could not parse")

except Exception as e:
    print(f"ERROR: {e}")
