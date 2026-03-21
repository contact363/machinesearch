"""
Clean malformed image URLs in the machines table.
Removes: relative URLs, background:url() strings, SVG placeholders, empty/whitespace strings.
Run: python fix_all_images.py   (from backend/ directory)
"""
import asyncio
import os
import re
import sys

from dotenv import load_dotenv
load_dotenv(".env")

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, update

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set in .env")
    sys.exit(1)

# SQLAlchemy wants postgresql+asyncpg://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


def is_bad_url(url: str | None) -> bool:
    if not url:
        return False  # already NULL — skip
    url = url.strip()
    if not url:
        return True
    # relative path (no scheme)
    if url.startswith("/") or url.startswith("./") or url.startswith("../"):
        return True
    # background:url(...) CSS strings
    if "background" in url.lower() or url.lower().startswith("url("):
        return True
    # data: URIs (inline SVG / base64 placeholders)
    if url.startswith("data:"):
        return True
    # must start with http(s)
    if not url.startswith("http://") and not url.startswith("https://"):
        return True
    # SVG placeholder (e.g. placeholder.svg, noimage.svg)
    if re.search(r'placeholder|noimage|no-image|nophoto|no_image|dummy', url, re.IGNORECASE):
        return True
    return False


async def main():
    async with AsyncSessionLocal() as session:
        # Import here so models are loaded after env is set
        from database.models import Machine

        stmt = select(Machine.id, Machine.image_url).where(Machine.image_url.isnot(None))
        result = await session.execute(stmt)
        rows = result.all()

        bad_ids = [r.id for r in rows if is_bad_url(r.image_url)]

        print(f"Total machines with image_url: {len(rows)}")
        print(f"Bad image URLs found:          {len(bad_ids)}")

        if bad_ids:
            # Show sample
            samples = [r for r in rows if r.id in set(bad_ids[:10])]
            print("\nSample bad URLs:")
            for r in samples:
                print(f"  id={r.id}  url={repr(r.image_url[:80])}")

            await session.execute(
                update(Machine).where(Machine.id.in_(bad_ids)).values(image_url=None)
            )
            await session.commit()
            print(f"\n✓ Cleared {len(bad_ids)} bad image_url(s) → NULL")
        else:
            print("\n✓ No bad URLs found — DB is clean")


asyncio.run(main())
