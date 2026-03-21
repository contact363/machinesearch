import asyncio, sys
sys.path.insert(0, ".")
import os
os.environ["PLAYWRIGHT_ENABLED"] = "true"

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from collections import Counter


async def inspect(url, name, wait_extra=0):
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
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000 + wait_extra)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)

            html = await page.content()
            soup = BeautifulSoup(html, "lxml")
            print(f"Page size: {len(html)} chars")

            # Repeated elements
            counts = Counter()
            for tag in soup.find_all(
                ["div", "article", "li", "section", "a", "tr"], class_=True
            ):
                cls = " ".join(tag.get("class", []))[:80]
                counts[cls] += 1

            print("\nRepeated elements (x4+):")
            for cls, c in counts.most_common(25):
                if c >= 4:
                    print(f"  x{c:3d}  {cls}")

            # All <a href> links that look like detail/listing pages
            print("\nInternal links (href with path, first 20):")
            shown = 0
            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(strip=True)
                if href.startswith("/") and len(text) > 3 and shown < 20:
                    print(f"  {text[:55]:55s}  {href[:70]}")
                    shown += 1

            # Show first 2 promising cards in full
            print("\n--- FIRST CARD HTML (best candidate with x>=4) ---")
            for cls, c in counts.most_common(40):
                if c >= 4:
                    first_cls = cls.split()[0]
                    candidates = soup.find_all(class_=first_cls)
                    for el in candidates[:2]:
                        txt = el.get_text(strip=True)
                        if len(txt) > 15:
                            print(f"\n[class={first_cls!r}, count={c}]")
                            print(el.prettify()[:2500])
                            break
                    break

        except Exception as e:
            print(f"ERROR: {e}")
            import traceback; traceback.print_exc()
        finally:
            await browser.close()


async def main():
    # Corel: inspect a category page for actual machine listings
    await inspect(
        "https://www.corelmachines.com/usedmachinestocklist/cnc-turning-centers",
        "corelmachines - CNC Turning Centers category"
    )

    # Zatpat: inspect /opportunities which might have listings
    await inspect(
        "https://zatpatmachines.com/opportunities",
        "zatpatmachines - /opportunities"
    )


asyncio.run(main())
