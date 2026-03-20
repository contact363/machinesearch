import httpx

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://zatpatmachines.com"
}

# Try common API patterns
urls = [
    "https://zatpatmachines.com/api/machines",
    "https://zatpatmachines.com/api/products",
    "https://zatpatmachines.com/api/listings",
    "https://zatpatmachines.com/api/v1/machines",
    "https://zatpatmachines.com/api/v1/listings",
    "https://api.zatpatmachines.com/machines",
    "https://api.zatpatmachines.com/listings",
    "https://zatpatmachines.com/~api/machines",
    "https://zatpatmachines.com/~api/listings",
]

print("Checking API endpoints...\n")
for url in urls:
    try:
        r = httpx.get(url, headers=headers, timeout=10, follow_redirects=True)
        size = len(r.text)
        ct = r.headers.get("content-type","")
        print(f"{r.status_code} | {size:7} chars | {ct[:30]:30} | {url}")
        if r.status_code == 200 and "json" in ct:
            print(f"  JSON FOUND: {r.text[:300]}")
    except Exception as e:
        print(f"ERR | {url} | {e}")

# Also check the JS bundle for API URLs
print("\nChecking JS bundle for API URLs...")
r = httpx.get("https://zatpatmachines.com/assets/index-D9r9nocH.js",
              headers=headers, timeout=30)
import re
apis = re.findall(r'["\'](/api/[^"\']{3,50})["\']', r.text)
apis += re.findall(r'["\']https?://[^"\']*api[^"\']{3,50}["\']', r.text)
unique = list(set(apis))[:20]
print(f"API patterns found in JS bundle: {len(unique)}")
for a in unique:
    print(f"  {a}")
