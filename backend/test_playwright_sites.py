import asyncio, json, sys, os, io
sys.path.insert(0, ".")
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
os.environ["PLAYWRIGHT_ENABLED"] = "true"

from scraper.engine import AdaptiveEngine


async def test(config_file):
    with open(f"site_configs/{config_file}") as f:
        config = json.load(f)
    config["max_pages"] = 1
    config["detail_page"] = False
    engine = AdaptiveEngine()
    items = await engine.run(config)
    print(f"\n[{config['name']}]")
    print(f"  Items found: {len(items)}")
    if items:
        for i, item in enumerate(items[:5]):
            print(f"  Machine {i+1}: {str(item.get('name','?'))[:60]}")
            print(f"    Price:    {item.get('price')}")
            print(f"    Location: {item.get('location')}")
            print(f"    Image:    {str(item.get('image_url',''))[:70]}")
            print(f"    URL:      {str(item.get('source_url',''))[:80]}")
    else:
        print("  0 items — selectors need updating")


async def main():
    await test("corel_machines.json")
    await test("zatpat_machines.json")


asyncio.run(main())
