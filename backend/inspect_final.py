import httpx
from bs4 import BeautifulSoup
from collections import Counter

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

# 1. lrtt - get first artikel_self card full HTML
print("="*55)
print("LRTT - first machine card")
print("="*55)
r = httpx.get("https://www.lrtt.de/maschinenmarkt.php", headers=headers, timeout=15, follow_redirects=True)
soup = BeautifulSoup(r.text, "lxml")
card = soup.find(class_="artikel_self")
if card:
    print(card.prettify()[:1500])
else:
    print("Not found")

# 2. reble - find correct machines page from nav links
print("\n" + "="*55)
print("REBLE - finding correct machines URL")
print("="*55)
r2 = httpx.get("https://reble-machinery.de/", headers=headers, timeout=15, follow_redirects=True)
soup2 = BeautifulSoup(r2.text, "lxml")
print("All nav links:")
for a in soup2.find_all("a", href=True):
    href = a["href"]
    text = a.get_text(strip=True)
    if text and len(text) > 2 and "reble-machinery.de" in href:
        print(f"  {text[:40]} --> {href}")

# 3. cnc-toerner - get first wp-block-cover full HTML
print("\n" + "="*55)
print("CNC-TOERNER - first machine card")
print("="*55)
r3 = httpx.get("https://cnc-toerner.de/maschinen/", headers=headers, timeout=15, follow_redirects=True)
soup3 = BeautifulSoup(r3.text, "lxml")
covers = soup3.find_all(class_="wp-block-cover")
print(f"wp-block-cover found: {len(covers)}")
if covers:
    print(covers[0].prettify()[:1500])

# 4. fm-machines - get first listing__wrapper full HTML
print("\n" + "="*55)
print("FM-MACHINES - first machine card")
print("="*55)
r4 = httpx.get("https://www.fm-machines.com/", headers=headers, timeout=15, follow_redirects=True)
soup4 = BeautifulSoup(r4.text, "lxml")
card4 = soup4.find(class_="listing__wrapper")
if card4:
    print(card4.prettify()[:1500])

# 5. ucy-machines - get first listing__wrapper full HTML
print("\n" + "="*55)
print("UCY-MACHINES - first machine card")
print("="*55)
r5 = httpx.get("https://www.ucymachines.com/en/machine-tools", headers=headers, timeout=15, follow_redirects=True)
soup5 = BeautifulSoup(r5.text, "lxml")
card5 = soup5.find(class_="listing__wrapper")
if card5:
    print(card5.prettify()[:1500])
