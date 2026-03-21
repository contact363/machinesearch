import asyncio, sys, io
sys.path.insert(0, ".")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import os
os.environ["PLAYWRIGHT_ENABLED"] = "true"

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from collections import Counter


async def inspect(url, name):
    print(f"\n{'='*60}")
    print(f"INSPECTING: {name}")
    print(f"URL: {url}")
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
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(6000)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(3000)

            html = await page.content()
            soup = BeautifulSoup(html, "lxml")
            print(f"Page size: {len(html)} chars")

            counts = Counter()
            for tag in soup.find_all(["div", "article", "li", "a"], class_=True):
                cls = " ".join(tag.get("class", []))[:80]
                counts[cls] += 1

            print("\nRepeated elements (x5+):")
            for cls, c in counts.most_common(25):
                if c >= 5:
                    print(f"  x{c:3d}  {cls}")

            # Show first 3 machine cards
            print("\n--- MACHINE CARDS (machine-card class) ---")
            cards = soup.find_all(class_="machine-card")
            print(f"Found {len(cards)} machine-card elements")
            for i, card in enumerate(cards[:3]):
                print(f"\n--- Card {i+1} ---")
                # ASCII-safe output
                card_html = card.prettify()
                print(card_html[:3000].encode('ascii', 'replace').decode('ascii'))

        except Exception as e:
            print(f"ERROR: {e}")
            import traceback; traceback.print_exc()
        finally:
            await browser.close()


async def main():
    await inspect("https://zatpatmachines.com/machines", "zatpat /machines")

asyncio.run(main())
