import asyncio, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, ".")
from database.db import AsyncSessionLocal
from database.models import Machine, SiteConfig
from sqlalchemy import delete, select, func

async def main():
    async with AsyncSessionLocal() as session:
        for site in ["bade_maschinen", "mbrmachinery"]:
            count = await session.scalar(
                select(func.count(Machine.id)).where(Machine.site_name == site)
            )
            await session.execute(delete(Machine).where(Machine.site_name == site))
            await session.execute(delete(SiteConfig).where(SiteConfig.name == site))
            print(f"Deleted {site}: {count} machines")
        await session.commit()
        print("Done")

asyncio.run(main())
