import asyncio, sys
sys.path.insert(0, ".")
import os
os.environ["PLAYWRIGHT_ENABLED"] = "true"

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from collections import Counter


async def inspect_card(url, name, target_class, num_cards=3):
    print(f"\n{'='*60}")
    print(f"INSPECTING: {name}")
    print(f"URL: {url}")
    print(f"Looking for class containing: {target_class!r}")
    print(f"{'='*60}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox",
                  "--disable-dev-shm-usage", "--disable-gpu"]
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        )
        await context.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)

            html = await page.content()
            soup = BeautifulSoup(html, "lxml")
            print(f"Page size: {len(html)} chars")

            # Find elements with target class
            found = soup.find_all(class_=lambda c: c and target_class in ' '.join(c) if isinstance(c, list) else False)
            if not found:
                # try substring search
                found = [el for el in soup.find_all(True) if target_class in ' '.join(el.get('class', []))]
            print(f"Found {len(found)} elements matching '{target_class}'")

            for i, el in enumerate(found[:num_cards]):
                print(f"\n--- Card {i+1} ---")
                print(el.prettify()[:2500])

            # Count all repeated classes again
            counts = Counter()
            for tag in soup.find_all(["div", "article", "li", "a"], class_=True):
                cls = " ".join(tag.get("class", []))[:80]
                counts[cls] += 1
            print("\nAll repeated classes (x4+):")
            for cls, c in counts.most_common(30):
                if c >= 4:
                    print(f"  x{c:3d}  {cls}")

        except Exception as e:
            print(f"ERROR: {e}")
            import traceback; traceback.print_exc()
        finally:
            await browser.close()


async def main():
    # Corel: inspect machine cards on category page
    await inspect_card(
        "https://www.corelmachines.com/usedmachinestocklist/cnc-turning-centers",
        "corelmachines - machine cards",
        "card"
    )

    # Zatpat: inspect /machines page
    await inspect_card(
        "https://zatpatmachines.com/machines",
        "zatpatmachines - /machines",
        "bg-card"
    )

asyncio.run(main())
