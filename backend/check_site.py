import httpx, sys

url = sys.argv[1]
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

try:
    r = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
    html = r.text
    js_signals = ["__NEXT_DATA__", "__nuxt", "ng-version", "data-reactroot", "_next/static"]
    is_js = any(s in html for s in js_signals)
    has_content = len(html) > 20000
    print("URL:", r.url)
    print("Status:", r.status_code)
    print("Page size:", len(html), "chars")
    print("JS framework:", is_js)
    print("Has content:", has_content)
    if is_js:
        print("RESULT: DYNAMIC - needs Playwright")
    elif has_content:
        print("RESULT: STATIC - will work immediately")
    else:
        print("RESULT: UNKNOWN - too small, check manually")
except Exception as e:
    print("Error:", e)
