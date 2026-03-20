import httpx
from bs4 import BeautifulSoup
from collections import Counter

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

url = "https://www.corelmachines.com/usedmachinestocklist"

print(f"Fetching: {url}")
r = httpx.get(url, headers=headers, timeout=20, follow_redirects=True)
print(f"Status: {r.status_code}")
print(f"Size: {len(r.text)} chars")

html = r.text

# Check framework
signals = {
    "Next.js": "__NEXT_DATA__",
    "React": "data-reactroot",
    "_next static": "_next/static",
    "Vue": "__nuxt",
}
print("\nFramework detection:")
for name, signal in signals.items():
    print(f"  {name}: {signal in html}")

# Try to find machine data
soup = BeautifulSoup(html, "lxml")
counts = Counter()
for tag in soup.find_all(["div","article","li","section"], class_=True):
    cls = " ".join(tag.get("class",[]))[:60]
    counts[cls] += 1

print("\nTop repeated elements:")
for cls, c in counts.most_common(10):
    if c >= 3:
        print(f"  x{c}  {cls}")

# Check for machine-related text
print("\nMachine-related text found:")
for tag in soup.find_all(["h1","h2","h3","p"], string=True):
    text = tag.get_text(strip=True)
    if any(k in text.lower() for k in ["machine","lathe","mill","cnc","press","grind"]):
        print(f"  {text[:80]}")

# Check if data is in a script tag (JSON)
import re, json
scripts = soup.find_all("script", string=True)
print(f"\nScript tags found: {len(scripts)}")
for s in scripts:
    content = s.string or ""
    if any(k in content.lower() for k in ["machine","product","listing"]):
        print(f"  Promising script ({len(content)} chars):")
        print(f"  {content[:300]}")
        break
