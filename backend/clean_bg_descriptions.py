"""
Clean BG Used Industry descriptions in DB — remove nav lines directly.
Run from: backend/
    python clean_bg_descriptions.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

_db_url = os.getenv("DATABASE_URL", "")
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif _db_url.startswith("postgresql://") and "+asyncpg" not in _db_url:
    _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(_db_url, echo=False, pool_pre_ping=True)
Session = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

SITE = "bg-used-industry"

NAV_LINES = {
    "all machines", "accessories and tooling", "borers", "cleaners",
    "construction machinery", "cutters", "drills", "food processing machinery",
    "forging machinery", "forming machinery", "furnaces, hardeners", "furnaces hardeners",
    "gear machinery", "grinders", "industrial containers", "industrial properties",
    "lathes", "lifting, transport and earthmoving", "lifting transport and earthmoving",
    "machining centres", "machining centers", "manuals",
    "measuring machines and tools", "mining industry", "paper machinery",
    "plastics machinery", "power engineering", "presses", "robots", "shavers",
    "sheet metal machinery", "threading machinery",
    "tube and bar processing machinery", "welders", "wire machinery",
    "edm", "lots", "mills", "inquiry", "sell", "inquire",
}


def clean_description(desc: str | None) -> str | None:
    if not desc:
        return None
    lines = desc.splitlines()
    cleaned = [
        line.strip() for line in lines
        if line.strip() and line.strip().lower() not in NAV_LINES
        and not line.strip().lower().startswith("all machines")
    ]
    return "\n".join(cleaned).strip() or None


async def main():
    from database.models import Machine

    async with Session() as db:
        result = await db.execute(
            select(Machine.id, Machine.description)
            .where(Machine.site_name == SITE, Machine.description.isnot(None))
        )
        rows = result.all()

    print(f"Machines with description: {len(rows)}")

    updated = 0
    for row in rows:
        cleaned = clean_description(row.description)
        if cleaned != row.description:
            async with Session() as db:
                await db.execute(
                    update(Machine)
                    .where(Machine.id == row.id)
                    .values(description=cleaned)
                )
                await db.commit()
            updated += 1

    print(f"Done — {updated} descriptions cleaned in DB")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
