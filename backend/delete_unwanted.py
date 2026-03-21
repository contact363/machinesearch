import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import asyncio
sys.path.insert(0, ".")
from database.db import AsyncSessionLocal
from database.models import Machine, SiteConfig
from sqlalchemy import delete, select, func

REMOVE = ["lrtt", "bade_maschinen", "bade-maschinen", "mbrmachinery", "mbr_machinery"]

async def main():
    async with AsyncSessionLocal() as session:
        for site in REMOVE:
            count = await session.scalar(
                select(func.count(Machine.id)).where(Machine.site_name == site)
            )
            await session.execute(delete(Machine).where(Machine.site_name == site))
            await session.execute(delete(SiteConfig).where(SiteConfig.name == site))
            print(f"Deleted {site}: {count} machines")
        await session.commit()

        remaining = await session.execute(select(SiteConfig.name, SiteConfig.is_active))
        print("\nRemaining site configs:")
        for name, active in remaining:
            print(f"  {name} | active={active}")

asyncio.run(main())
