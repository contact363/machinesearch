import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import asyncio, httpx, json
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()
from database.db import AsyncSessionLocal
from database.models import SiteConfig
from sqlalchemy import select

async def get_config():
    async with AsyncSessionLocal() as session:
        cfg = await session.scalar(
            select(SiteConfig).where(SiteConfig.name == "zatpat_machines")
        )
        if cfg:
            return cfg.config_json
    return None

config = asyncio.run(get_config())
print("Zatpat config:")
print(json.dumps(config, indent=2))

if config:
    api_url = config.get("api_url", "")
    api_key = config.get("api_key", "")
    supabase_url = config.get("supabase_url", "https://aqhgorgilxwrhzleztby.supabase.co")
    supabase_key = config.get("supabase_key", "")

    # Use supabase_key/url if api_key/url not set
    if not api_url and supabase_url:
        api_url = f"{supabase_url}/rest/v1/machines_public"
    if not api_key and supabase_key:
        api_key = supabase_key

    if not api_url or not api_key:
        print("ERROR: No api_url or api_key in config!")
    else:
        print(f"\nUsing api_url: {api_url}")
        headers = {
            "apikey": api_key,
            "Authorization": f"Bearer {api_key}",
            "Prefer": "count=exact"
        }

        # Check count for each status
        for status in ["active", "inactive", "sold", "pending", "available"]:
            try:
                r = httpx.get(
                    f"{api_url}?status=eq.{status}&select=id",
                    headers=headers,
                    timeout=15
                )
                cr = r.headers.get("content-range", "?")
                print(f"  status={status}: content-range={cr} status_code={r.status_code}")
            except Exception as e:
                print(f"  status={status}: ERROR {e}")

        # Get total without filter
        try:
            r = httpx.get(
                f"{api_url}?select=id",
                headers=headers,
                timeout=15
            )
            cr = r.headers.get("content-range", "?")
            print(f"  NO filter: content-range={cr} status_code={r.status_code}")
        except Exception as e:
            print(f"  NO filter: ERROR {e}")

        # Test pagination - fetch first 1000, then next 1000
        print("\nPagination test:")
        for offset in [0, 1000, 2000, 3000, 4000, 4500]:
            try:
                r = httpx.get(
                    f"{api_url}?select=id&limit=1000&offset={offset}",
                    headers={"apikey": api_key, "Authorization": f"Bearer {api_key}"},
                    timeout=30
                )
                data = r.json() if r.status_code == 200 else []
                if isinstance(data, list):
                    print(f"  offset={offset}: got {len(data)} items")
                else:
                    print(f"  offset={offset}: got non-list: {str(data)[:100]}")
            except Exception as e:
                print(f"  offset={offset}: ERROR {e}")
