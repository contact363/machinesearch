import asyncio, sys
sys.path.insert(0, ".")
import os
os.environ["PLAYWRIGHT_ENABLED"] = "true"

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from collections import Counter


async def inspect(url, name):
    print(f"\n{'='*55}")
    print(f"INSPECTING: {name}")
    print(f"URL: {url}")
    print(f"{'='*55}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        )
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
        )
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)

            # Scroll to load lazy content
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)

            html = await page.content()
            soup = BeautifulSoup(html, "lxml")

            print(f"Page size after JS: {len(html)} chars")

            # Find repeated elements
            counts = Counter()
            for tag in soup.find_all(
                ["div", "article", "li", "section", "a"], class_=True
            ):
                cls = " ".join(tag.get("class", []))[:70]
                counts[cls] += 1

            print("\nTop repeated elements (likely machine cards):")
            for cls, c in counts.most_common(20):
                if c >= 3:
                    print(f"  x{c}  {cls}")

            # Find product links
            print("\nProduct-like links (first 8):")
            shown = 0
            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(strip=True)
                if text and len(text) > 3 and shown < 8:
                    print(f"  {text[:50]} --> {href[:80]}")
                    shown += 1

            # Show first promising card
            print("\nFirst promising card HTML (top candidate):")
            for cls, c in counts.most_common(30):
                if c >= 4:
                    first_cls = cls.split()[0]
                    first = soup.find(class_=first_cls)
                    if first and len(first.get_text(strip=True)) > 10:
                        print(f"  Selector class: {cls[:60]}  (x{c})")
                        print(first.prettify()[:2000])
                        print("  [truncated]")
                        break

        except Exception as e:
            print(f"ERROR: {e}")
        finally:
            await browser.close()


async def main():
    await inspect(
        "https://www.corelmachines.com/usedmachinestocklist",
        "corelmachines"
    )
    await inspect(
        "https://zatpatmachines.com",
        "zatpatmachines"
    )


asyncio.run(main())
