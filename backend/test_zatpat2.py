import httpx

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

r = httpx.get("https://zatpatmachines.com", headers=headers, timeout=20, follow_redirects=True)

print("Status:", r.status_code)
print("Size:", len(r.text))
print()
print("=== FULL PAGE HTML ===")
print(r.text)
