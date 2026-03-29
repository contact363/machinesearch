"""
Import machine type + brand intelligence from Google Sheet into DB.

Sheet: https://docs.google.com/spreadsheets/d/1-JEUXjkjvEIET8LVNa-hYJBpJoa-6-7m_1WFOjEyReI
Columns: Type | Brand | Models

Run from backend/:
    python seed_machine_intelligence.py
"""

import asyncio, os, sys, csv, io, logging
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
os.chdir(os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("seed_intelligence")

SHEET_CSV = "https://docs.google.com/spreadsheets/d/1-JEUXjkjvEIET8LVNa-hYJBpJoa-6-7m_1WFOjEyReI/export?format=csv"


async def main():
    import httpx
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy import select
    from database.models import MachineType, MachineBrand

    db_url = os.getenv("DATABASE_URL", "")
    for prefix in ("postgres://", "postgresql://"):
        if db_url.startswith(prefix):
            db_url = "postgresql+asyncpg://" + db_url[len(prefix):]

    engine = create_async_engine(db_url, echo=False, pool_pre_ping=True, pool_size=2)
    Session = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    # ── Step 1: fetch CSV ─────────────────────────────────────────────────────
    logger.info("Fetching Google Sheet CSV...")
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        resp = await client.get(SHEET_CSV)
        resp.raise_for_status()

    reader = csv.reader(io.StringIO(resp.text))
    next(reader)  # skip header row

    # ── Step 2: parse — collect unique types and brands ───────────────────────
    # type_brands[type_name] = set of brand names
    type_brands: dict[str, set[str]] = defaultdict(set)

    for row in reader:
        if len(row) < 2:
            continue
        machine_type = row[0].strip()
        brand        = row[1].strip()
        if not machine_type or machine_type.lower() in ("unknown", "na", "n/a", ""):
            continue
        if brand and brand.lower() not in ("unknown", "na", "n/a", ""):
            type_brands[machine_type].add(brand)
        else:
            # still register the type even if brand is unknown
            type_brands.setdefault(machine_type, set())

    all_types  = sorted(type_brands.keys())
    all_brands = sorted({b for brands in type_brands.values() for b in brands})

    logger.info("Unique machine types : %d", len(all_types))
    logger.info("Unique brands        : %d", len(all_brands))

    # ── Step 3: upsert machine_types ─────────────────────────────────────────
    logger.info("Upserting machine types...")
    types_added = 0
    async with Session() as session:
        for type_name in all_types:
            stmt = (
                pg_insert(MachineType)
                .values(name=type_name, aliases=[])
                .on_conflict_do_nothing(index_elements=["name"])
            )
            result = await session.execute(stmt)
            if result.rowcount > 0:
                types_added += 1
        await session.commit()
    logger.info("  Types added: %d (skipped existing)", types_added)

    # ── Step 4: upsert machine_brands ─────────────────────────────────────────
    logger.info("Upserting machine brands...")
    brands_added = 0
    async with Session() as session:
        for brand_name in all_brands:
            stmt = (
                pg_insert(MachineBrand)
                .values(name=brand_name, aliases=[])
                .on_conflict_do_nothing(index_elements=["name"])
            )
            result = await session.execute(stmt)
            if result.rowcount > 0:
                brands_added += 1
        await session.commit()
    logger.info("  Brands added: %d (skipped existing)", brands_added)

    # ── Step 5: update machines table — link brand_id and type_id ────────────
    logger.info("Linking existing machines to brands and types...")
    from sqlalchemy import update, select
    from database.models import Machine

    async with Session() as session:
        # Load all types and brands into dicts for fast lookup
        type_rows  = (await session.execute(select(MachineType.id, MachineType.name))).all()
        brand_rows = (await session.execute(select(MachineBrand.id, MachineBrand.name))).all()

        type_map  = {r.name.lower(): r.id for r in type_rows}
        brand_map = {r.name.lower(): r.id for r in brand_rows}

        # Get all machines with no type_id or brand_id
        machines = (await session.execute(
            select(Machine.id, Machine.brand, Machine.machine_type)
        )).all()

        linked = 0
        for m in machines:
            updates = {}
            if m.brand and m.brand.lower() in brand_map:
                updates["brand_id"] = brand_map[m.brand.lower()]
            if m.machine_type and m.machine_type.lower() in type_map:
                updates["type_id"] = type_map[m.machine_type.lower()]
            if updates:
                await session.execute(
                    update(Machine).where(Machine.id == m.id).values(**updates)
                )
                linked += 1

        await session.commit()
        logger.info("  Machines linked: %d", linked)

    logger.info("=" * 60)
    logger.info("DONE")
    logger.info("  Types  in DB : %d", len(all_types))
    logger.info("  Brands in DB : %d", len(all_brands))
    logger.info("  Machines linked: %d", linked)
    logger.info("=" * 60)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
