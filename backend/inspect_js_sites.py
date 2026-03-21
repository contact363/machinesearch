import asyncio, sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, ".")
os.environ["PLAYWRIGHT_ENABLED"] = "true"
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def inspect(url, name, card_sel):
    print(f"\n{'='*55}")
    print(f"SITE: {name}")
    print(f"URL: {url}")
    print(f"{'='*55}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox","--disable-setuid-sandbox",
                  "--disable-dev-shm-usage","--disable-gpu"]
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        await context.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

        api_calls = []
        async def on_request(req):
            u = req.url
            if any(k in u.lower() for k in ["api","machine","product","listing","item","stock","data","search","catalog","inventory","graphql","json"]):
                api_calls.append(f"{req.method} {u}")

        context.on("request", on_request)
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)

        html = await page.content()
        soup = BeautifulSoup(html, "lxml")
        count_before = len(soup.select(card_sel))
        print(f"Items on initial load: {count_before}")

        # Look for pagination buttons/links
        print("\nPagination elements:")
        for sel in ["[class*='pagination']","[class*='pager']","[aria-label='pagination']","nav a","button[class*='page']","a[href*='page']"]:
            try:
                els = await page.query_selector_all(sel)
                if els:
                    for el in els[:5]:
                        txt = await el.inner_text()
                        href = await el.get_attribute("href") or ""
                        if txt.strip():
                            print(f"  [{sel}] text='{txt.strip()[:40]}' href='{href[:60]}'")
            except:
                pass

        # Check for Load More button
        print("\nLoad more buttons:")
        for text in ["Load More","Show More","Next","See More","View More","More machines","Load more"]:
            try:
                btn = await page.query_selector(f"button:has-text('{text}')")
                if btn:
                    vis = await btn.is_visible()
                    inner = await btn.inner_html()
                    print(f"  Found '{text}': visible={vis} html={inner[:150]}")
            except:
                pass

        # Scroll test
        print("\nScroll test:")
        prev = count_before
        for i in range(6):
            await page.evaluate("window.scrollTo(0,document.body.scrollHeight)")
            await page.wait_for_timeout(3000)
            html = await page.content()
            soup = BeautifulSoup(html, "lxml")
            curr = len(soup.select(card_sel))
            print(f"  After scroll {i+1}: {curr} items (+{curr-prev} new)")
            prev = curr
            if curr - count_before > 50:
                print("  INFINITE SCROLL DETECTED")
                break

        # API calls
        print(f"\nIntercepted API/data calls ({len(api_calls)}):")
        seen = set()
        for u in api_calls:
            if u not in seen:
                seen.add(u)
                print(f"  {u[:150]}")

        # Show what the page structure looks like
        print("\nTop repeated elements:")
        counts = {}
        for tag in soup.find_all(["div","article","a","li"], class_=True):
            cls = " ".join(tag.get("class",[]))[:60]
            counts[cls] = counts.get(cls, 0) + 1
        for cls, c in sorted(counts.items(), key=lambda x: -x[1])[:15]:
            if c >= 3:
                print(f"  x{c}  {cls}")

        await browser.close()

async def main():
    await inspect(
        "https://www.corelmachines.com/usedmachinestocklist",
        "corelmachines",
        "a.card"
    )
    await inspect(
        "https://zatpatmachines.com/machines",
        "zatpatmachines",
        "a.machine-card"
    )

asyncio.run(main())
