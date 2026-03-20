"""
Admin router — unified admin API for the MachineSearch admin dashboard.

Endpoints:
  POST   /admin/auth/login
  GET    /admin/analytics/overview
  GET    /admin/configs
  POST   /admin/configs
  PUT    /admin/configs/{name}
  DELETE /admin/configs/{name}
  POST   /admin/configs/{name}/toggle
  POST   /admin/scraper/start/{site_name}
  POST   /admin/scraper/start-all
  GET    /admin/scraper/status
  GET    /admin/scraper/jobs
  GET    /admin/machines
  DELETE /admin/machines/bulk
  DELETE /admin/machines/{id}
  GET    /admin/analytics/clicks
  GET    /admin/analytics/searches
"""

import asyncio
import json
import os
import re
import uuid
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Any
from urllib.parse import urlparse, urljoin

import bcrypt
import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy import select, func, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.db import get_db
from database.models import AdminUser, ClickEvent, Machine, ScrapeJob, SearchEvent

router = APIRouter()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24
SITE_CONFIGS_DIR = Path(__file__).parent.parent.parent / "site_configs"

# In-memory running jobs registry  {job_id: {site_name, status, started_at, ...}}
_running_jobs: dict[str, dict] = {}

# ---------------------------------------------------------------------------
# Utility classes to skip when building CSS selectors (layout/utility only)
# ---------------------------------------------------------------------------
_SKIP_CLASSES = {
    "container", "wrapper", "inner", "outer", "content", "main", "body",
    "row", "col", "grid", "flex", "block", "section", "page", "wrap",
    "clearfix", "hidden", "visible", "active", "disabled", "open", "show",
    "item", "element", "box", "card",  # too generic — kept unless best option
}
_PRICE_RE = re.compile(
    r"[\d][\d\s.,]*\s*(?:EUR|USD|GBP|CHF|SEK|NOK|DKK|PLN|CZK|HUF|€|\$|£|Fr\.|kr)",
    re.IGNORECASE,
)
_GEO_RE = re.compile(
    r"\b(germany|deutschland|france|frankreich|spain|españa|italy|italia|"
    r"poland|netherlands|austria|switzerland|belgium|czech|denmark|sweden|"
    r"norway|finland|uk|usa|china|turkey|russia|ukraine|"
    r"berlin|munich|münchen|paris|madrid|rome|amsterdam|vienna|wien|zurich|"
    r"hamburg|cologne|frankfurt|stuttgart|düsseldorf)\b",
    re.IGNORECASE,
)


def _best_class_selector(el) -> str:
    """Return the best single-class CSS selector for an element, skipping utility classes."""
    tag = el.name
    classes = el.get("class", [])
    # prefer a class that isn't a generic utility
    for cls in classes:
        if cls and cls not in _SKIP_CLASSES and not re.match(r"^(col|d-|m-|p-|mt-|mb-|pt-|pb-|g-|gap-|text-|bg-|border-|rounded|shadow|flex-|align-|justify-)", cls):
            return f"{tag}.{cls}"
    # fall back to first class if all are utility
    if classes:
        return f"{tag}.{classes[0]}"
    return tag


def _auto_detect_selectors(html: str, base_url: str) -> dict:
    """
    Analyse a machine listing page and return CSS selectors for:
    listing_container, name, price, image, location, detail_link.

    Algorithm:
    1. Strip non-content elements (script, style, nav, footer).
    2. Count (tag, classes) occurrences — repeated elements are candidates.
    3. Score each candidate: +3 has <img>, +2 has <a href>, +2 price text, +1 geo text.
    4. Pick highest-score selector with ≥ 3 occurrences.
    5. Within a sample element find sub-selectors for each field.
    """
    soup = BeautifulSoup(html, "lxml")

    # Strip non-content tags
    for dead in soup(["script", "style", "nav", "footer", "header", "noscript", "aside"]):
        dead.decompose()

    # --- Step 1: count repeated (tag, first-meaningful-class) patterns ---
    pattern_counter: Counter = Counter()
    for el in soup.find_all(["div", "article", "li", "section", "tr"]):
        classes = el.get("class", [])
        if not classes:
            continue
        key = (el.name, classes[0])  # index by first class only for counting
        pattern_counter[key] += 1

    # --- Step 2: score candidates ---
    scored: list[tuple[int, int, str]] = []  # (score, count, selector)

    for (tag, first_cls), count in pattern_counter.most_common(60):
        if count < 3:
            continue

        sel = f"{tag}.{first_cls}"
        try:
            elements = soup.select(sel)
        except Exception:
            continue

        if not elements:
            continue

        # Skip elements that are clearly layout wrappers (too large)
        sample_text_len = len(elements[0].get_text(strip=True))
        if sample_text_len > 8000:
            continue

        score = 0
        for el in elements[:6]:
            text = el.get_text(strip=True)
            if len(text) < 10:
                continue
            if el.find("img"):
                score += 3
            if el.find("a", href=True):
                score += 2
            if _PRICE_RE.search(text):
                score += 2
            if _GEO_RE.search(text):
                score += 1
            if 20 < len(text) < 3000:
                score += 1

        if score >= 5:
            scored.append((score, count, sel))

    if not scored:
        return {}

    scored.sort(key=lambda x: x[0], reverse=True)
    container_sel = scored[0][2]

    selectors: dict = {"listing_container": container_sel}

    # --- Step 3: sub-selectors from a sample element ---
    samples = soup.select(container_sel)
    if not samples:
        return selectors

    sample = samples[0]

    # Name: prefer heading tags, then strong, then prominent anchor text
    for tag in ["h1", "h2", "h3", "h4", "strong"]:
        node = sample.find(tag)
        if node:
            txt = node.get_text(strip=True)
            if len(txt) > 5:
                selectors["name"] = _best_class_selector(node) if node.get("class") else tag
                break
    if "name" not in selectors:
        # fallback: longest anchor text
        for a in sample.find_all("a", href=True):
            if len(a.get_text(strip=True)) > 8:
                selectors["name"] = _best_class_selector(a) if a.get("class") else "a"
                break

    # Price: first element whose text looks like a price
    for el in sample.find_all(True):
        txt = el.get_text(strip=True)
        if _PRICE_RE.search(txt) and len(txt) < 80:
            if not el.find_all(True):  # leaf node preferred
                selectors["price"] = _best_class_selector(el) if el.get("class") else el.name
                break
            elif el.name not in ("div", "section", "article"):
                selectors["price"] = _best_class_selector(el) if el.get("class") else el.name
                break

    # Image: prefer data-src / data-lazy-src attributes too
    img = sample.find("img")
    if img:
        if img.get("class"):
            selectors["image"] = _best_class_selector(img)
        else:
            # Check if parent has bg-image style
            parent = img.parent
            if parent and "background" in parent.get("style", ""):
                selectors["image"] = _best_class_selector(parent) if parent.get("class") else f"{parent.name}"
            else:
                selectors["image"] = "img"

    # Detail link: first <a> with a meaningful href (not # or javascript:)
    for a in sample.find_all("a", href=True):
        href = a.get("href", "")
        if href and not href.startswith("#") and "javascript" not in href:
            selectors["detail_link"] = _best_class_selector(a) if a.get("class") else "a"
            break

    # Location: first element matching geo keywords
    for el in sample.find_all(True):
        txt = el.get_text(strip=True)
        if _GEO_RE.search(txt) and 3 < len(txt) < 120:
            if not el.find("img") and not el.find("a"):
                selectors["location"] = _best_class_selector(el) if el.get("class") else el.name
                break

    return selectors


async def _fetch_html(url: str) -> tuple[str, str]:
    """Fetch URL, return (html, detected_mode). mode='js' if site needs Playwright."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    async with httpx.AsyncClient(headers=headers, timeout=25, follow_redirects=True) as client:
        resp = await client.get(url)
        resp.raise_for_status()
    html = resp.text
    lower = html.lower()
    # Detect if the page is JS-rendered (minimal real content)
    soup_check = BeautifulSoup(html, "lxml")
    visible_text = soup_check.get_text(strip=True)
    js_signals = any(p in lower for p in ["__next_data__", "ng-app", "__nuxt", "reactroot", "vue"])
    mode = "dynamic" if (js_signals or len(visible_text) < 500) else "static"
    return html, mode


def _name_from_url(url: str) -> str:
    """Derive a safe config name from a URL, e.g. https://www.exapro.com/ → exapro"""
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "").split(":")[0]
    name = domain.split(".")[0]
    name = re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-")
    return name or "site"

security = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _create_token(email: str) -> str:
    expires = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": email, "exp": expires},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


async def _get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> AdminUser:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = await db.scalar(select(AdminUser).where(AdminUser.email == email))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str
    password: str


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@router.post("/auth/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(AdminUser).where(AdminUser.email == body.email))
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    try:
        ok = bcrypt.checkpw(body.password.encode(), user.hashed_password.encode())
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not ok:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = _create_token(user.email)
    return {
        "access_token": token,
        "token_type": "bearer",
        "email": user.email,
    }


# ---------------------------------------------------------------------------
# Analytics — overview
# ---------------------------------------------------------------------------

@router.get("/analytics/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(_get_current_admin),
):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_machines = await db.scalar(select(func.count(Machine.id)))

    clicks_today = await db.scalar(
        select(func.count(ClickEvent.id)).where(ClickEvent.clicked_at >= today_start)
    )

    searches_today = await db.scalar(
        select(func.count(SearchEvent.id)).where(SearchEvent.searched_at >= today_start)
    )

    active_jobs = len([j for j in _running_jobs.values() if j.get("status") == "running"])

    # Top 10 sites by machine count
    sites_result = await db.execute(
        select(Machine.site_name, func.count(Machine.id).label("count"))
        .group_by(Machine.site_name)
        .order_by(desc("count"))
        .limit(10)
    )
    top_sites = [{"site": r.site_name, "count": r.count} for r in sites_result]

    # Top 10 clicked machines
    top_clicked_result = await db.execute(
        select(Machine.name, func.count(ClickEvent.id).label("clicks"))
        .join(ClickEvent, ClickEvent.machine_id == Machine.id)
        .group_by(Machine.id, Machine.name)
        .order_by(desc("clicks"))
        .limit(10)
    )
    top_clicked = [{"name": r.name[:40], "clicks": r.clicks} for r in top_clicked_result]

    # Zero-result searches (top 10)
    zero_result = await db.execute(
        select(SearchEvent.query, func.count(SearchEvent.id).label("count"))
        .where(SearchEvent.results_count == 0, SearchEvent.query.isnot(None))
        .group_by(SearchEvent.query)
        .order_by(desc("count"))
        .limit(10)
    )
    zero_searches = [{"query": r.query, "count": r.count} for r in zero_result]

    # Top clicked sites
    top_clicked_sites_result = await db.execute(
        select(Machine.site_name, func.count(ClickEvent.id).label("clicks"))
        .join(ClickEvent, ClickEvent.machine_id == Machine.id)
        .group_by(Machine.site_name)
        .order_by(desc("clicks"))
        .limit(10)
    )
    top_clicked_sites = [{"site": r.site_name, "clicks": r.clicks} for r in top_clicked_sites_result]

    return {
        "total_machines": total_machines or 0,
        "clicks_today": clicks_today or 0,
        "searches_today": searches_today or 0,
        "active_jobs": active_jobs,
        "top_sites": top_sites,
        "top_clicked": top_clicked,
        "zero_result_searches": zero_searches,
        "top_clicked_sites": top_clicked_sites,
    }


# ---------------------------------------------------------------------------
# Site configs  (reads/writes JSON files in site_configs/)
# ---------------------------------------------------------------------------

def _load_all_configs() -> list[dict]:
    configs = []
    if not SITE_CONFIGS_DIR.exists():
        return configs
    for path in sorted(SITE_CONFIGS_DIR.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                cfg = json.load(f)
            cfg["_filename"] = path.name
            configs.append(cfg)
        except Exception:
            pass
    return configs


def _load_config(name: str) -> tuple[dict, Path] | tuple[None, None]:
    path = SITE_CONFIGS_DIR / f"{name}.json"
    if not path.exists():
        return None, None
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg, path


@router.get("/configs")
async def list_configs(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(_get_current_admin),
):
    configs = _load_all_configs()

    # Enrich with machine counts
    counts_result = await db.execute(
        select(Machine.site_name, func.count(Machine.id).label("count"))
        .group_by(Machine.site_name)
    )
    counts = {r.site_name: r.count for r in counts_result}

    # Enrich with last scrape time from ScrapeJob
    last_scrape_result = await db.execute(
        select(ScrapeJob.site_name, func.max(ScrapeJob.finished_at).label("last"))
        .where(ScrapeJob.status == "completed")
        .group_by(ScrapeJob.site_name)
    )
    last_scrape = {r.site_name: r.last for r in last_scrape_result}

    for cfg in configs:
        name = cfg.get("name", "")
        cfg["machine_count"] = counts.get(name, 0)
        last = last_scrape.get(name)
        cfg["last_scraped"] = last.isoformat() if last else None

    return {"configs": configs}


@router.post("/configs/auto-detect")
async def auto_detect_config(
    body: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(_get_current_admin),
):
    """
    Auto-detect CSS selectors for a machine listing site and immediately start scraping.
    Body: { url: str, name: str (optional) }
    """
    url = (body.get("url") or body.get("start_url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="'url' is required")

    # Auto-generate name from domain if not provided
    name = (body.get("name") or "").strip()
    if not name:
        name = _name_from_url(url)

    # Make name unique — append counter if already exists
    base_name = name
    counter = 1
    while (SITE_CONFIGS_DIR / f"{name}.json").exists():
        name = f"{base_name}-{counter}"
        counter += 1

    # Fetch the page
    try:
        html, mode = await _fetch_html(url)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=400, detail=f"HTTP {e.response.status_code} fetching URL")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not fetch URL: {e}")

    # Auto-detect selectors
    selectors = _auto_detect_selectors(html, url)

    if not selectors.get("listing_container"):
        # Site may be JS-rendered — still create config so user can run with dynamic mode
        mode = "dynamic"
        selectors = {
            "listing_container": "",
            "name": "h2, h3",
            "price": "",
            "image": "img",
            "location": "",
            "detail_link": "a",
        }

    # Count how many items were detected on page 1
    detected_count = 0
    if selectors.get("listing_container"):
        soup_tmp = BeautifulSoup(html, "lxml")
        detected_count = len(soup_tmp.select(selectors["listing_container"]))

    # Parse base_url from URL
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    config = {
        "name": name,
        "display_name": name.replace("-", " ").replace("_", " ").title(),
        "start_url": url,
        "base_url": base_url,
        "enabled": True,
        "mode": mode,
        "pagination": True,
        "pagination_type": "page_param",
        "pagination_param": "page",
        "max_pages": 50,
        "detail_page": False,
        "proxy_tier": "none",
        "rate_limit_delay": 2,
        "language": "en",
        "selectors": {
            "listing_container": selectors.get("listing_container", ""),
            "name": selectors.get("name", ""),
            "price": selectors.get("price", ""),
            "image": selectors.get("image", "img"),
            "location": selectors.get("location", ""),
            "detail_link": selectors.get("detail_link", "a"),
            "next_page": "",
        },
    }

    # Save config JSON
    SITE_CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    config_path = SITE_CONFIGS_DIR / f"{name}.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    # Start scrape immediately in background
    job_id = str(uuid.uuid4())
    db_url = os.getenv("DATABASE_URL", "")
    background_tasks.add_task(_run_scrape_background, name, config, job_id, db_url)

    return {
        "created": name,
        "display_name": config["display_name"],
        "job_id": job_id,
        "detected_count": detected_count,
        "mode": mode,
        "selectors": config["selectors"],
        "needs_js": mode == "dynamic",
    }


@router.post("/configs")
async def create_config(
    body: dict,
    _: AdminUser = Depends(_get_current_admin),
):
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Config 'name' is required")

    path = SITE_CONFIGS_DIR / f"{name}.json"
    if path.exists():
        raise HTTPException(status_code=409, detail=f"Config '{name}' already exists")

    SITE_CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(body, f, indent=2, ensure_ascii=False)

    return {"created": name}


@router.put("/configs/{name}")
async def update_config(
    name: str,
    body: dict,
    _: AdminUser = Depends(_get_current_admin),
):
    _, path = _load_config(name)
    if path is None:
        raise HTTPException(status_code=404, detail=f"Config '{name}' not found")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(body, f, indent=2, ensure_ascii=False)

    return {"updated": name}


@router.delete("/configs/{name}")
async def delete_config(
    name: str,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(_get_current_admin),
):
    _, path = _load_config(name)
    if path is None:
        raise HTTPException(status_code=404, detail=f"Config '{name}' not found")

    # Delete all machines belonging to this site from the database
    result = await db.execute(select(func.count(Machine.id)).where(Machine.site_name == name))
    machine_count = result.scalar() or 0
    await db.execute(delete(Machine).where(Machine.site_name == name))

    # Delete all scrape job history for this site
    await db.execute(delete(ScrapeJob).where(ScrapeJob.site_name == name))
    await db.commit()

    # Remove in-memory job entries for this site
    for jid in [k for k, v in _running_jobs.items() if v.get("site_name") == name]:
        _running_jobs.pop(jid, None)

    # Remove the config JSON file
    path.unlink()
    return {"deleted": name, "machines_removed": machine_count}


@router.post("/configs/{name}/toggle")
async def toggle_config(
    name: str,
    _: AdminUser = Depends(_get_current_admin),
):
    cfg, path = _load_config(name)
    if cfg is None:
        raise HTTPException(status_code=404, detail=f"Config '{name}' not found")

    cfg["enabled"] = not cfg.get("enabled", True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

    return {"name": name, "enabled": cfg["enabled"]}


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------

async def _run_scrape_background(site_name: str, config: dict, job_id: str, db_url: str):
    """Background task: runs a scrape and records results in ScrapeJob."""
    from database.db import AsyncSessionLocal
    from scraper.engine import AdaptiveEngine
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    _running_jobs[job_id] = {
        "job_id": job_id,
        "site_name": site_name,
        "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "items_found": 0,
        "items_new": 0,
        "error": None,
    }

    started_at = datetime.now(timezone.utc)

    try:
        engine = AdaptiveEngine()
        cfg = {**config, "max_pages": config.get("max_pages", 50), "detail_page": False}
        items = await engine.run(cfg)

        new_count = 0
        async with AsyncSessionLocal() as session:
            # Record ScrapeJob first
            job = ScrapeJob(
                id=uuid.UUID(job_id),
                site_name=site_name,
                status="completed",
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
                items_found=len(items),
                items_new=0,
                pages_scraped=cfg.get("max_pages", 50),
            )
            session.add(job)
            await session.flush()  # persist job row before machine inserts

            # Deduplicate within this batch first (same source_url appearing twice)
            seen_urls: set[str] = set()
            deduped_items = []
            for item in items:
                url = (item.get("source_url") or "").strip()
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    deduped_items.append(item)

            # Use INSERT ... ON CONFLICT DO NOTHING to avoid unique violations
            for item in deduped_items:
                source_url = (item.get("source_url") or "").strip()
                if not source_url:
                    continue
                stmt = pg_insert(Machine).values(
                    id=uuid.uuid4(),
                    name=(item.get("name") or "Unknown")[:500],
                    brand=(item.get("brand") or None),
                    price=(item.get("price") or None),
                    currency=(item.get("currency") or "USD"),
                    location=(item.get("location") or None),
                    image_url=(item.get("image_url") or None),
                    description=(item.get("description") or None),
                    specs=(item.get("specs") or None),
                    source_url=source_url,
                    site_name=site_name,
                    language=(item.get("language") or "en"),
                    view_count=0,
                    click_count=0,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                ).on_conflict_do_nothing(index_elements=["source_url"])
                result = await session.execute(stmt)
                if result.rowcount > 0:
                    new_count += 1

            job.items_new = new_count
            await session.commit()

        _running_jobs[job_id]["status"] = "completed"
        _running_jobs[job_id]["items_found"] = len(items)
        _running_jobs[job_id]["items_new"] = new_count
        _running_jobs[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()

    except Exception as exc:
        async with AsyncSessionLocal() as session:
            job = ScrapeJob(
                id=uuid.UUID(job_id),
                site_name=site_name,
                status="failed",
                started_at=started_at,
                finished_at=datetime.now(timezone.utc),
                items_found=0,
                items_new=0,
                pages_scraped=0,
                error_message=str(exc)[:500],
            )
            session.add(job)
            await session.commit()

        _running_jobs[job_id]["status"] = "failed"
        _running_jobs[job_id]["error"] = str(exc)[:200]
        _running_jobs[job_id]["finished_at"] = datetime.now(timezone.utc).isoformat()


@router.post("/scraper/start/{site_name}")
async def start_scrape(
    site_name: str,
    background_tasks: BackgroundTasks,
    _: AdminUser = Depends(_get_current_admin),
):
    cfg, _ = _load_config(site_name)
    if cfg is None:
        raise HTTPException(status_code=404, detail=f"Config '{site_name}' not found")

    job_id = str(uuid.uuid4())
    db_url = os.getenv("DATABASE_URL", "")
    background_tasks.add_task(_run_scrape_background, site_name, cfg, job_id, db_url)

    return {"job_id": job_id, "site_name": site_name, "status": "started"}


@router.post("/scraper/start-all")
async def start_all(
    background_tasks: BackgroundTasks,
    _: AdminUser = Depends(_get_current_admin),
):
    configs = _load_all_configs()
    started = []
    for cfg in configs:
        if not cfg.get("enabled", True):
            continue
        job_id = str(uuid.uuid4())
        site_name = cfg.get("name", "")
        db_url = os.getenv("DATABASE_URL", "")
        background_tasks.add_task(_run_scrape_background, site_name, cfg, job_id, db_url)
        started.append({"job_id": job_id, "site_name": site_name})

    return {"started": started}


@router.get("/scraper/status")
async def scraper_status(
    _: AdminUser = Depends(_get_current_admin),
):
    jobs = list(_running_jobs.values())
    # running first, then others sorted by started desc
    running = [j for j in jobs if j.get("status") == "running"]
    recent = [j for j in jobs if j.get("status") != "running"]
    recent.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    return {"jobs": running + recent[:20]}


@router.get("/scraper/jobs")
async def scraper_jobs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    site: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(_get_current_admin),
):
    stmt = select(ScrapeJob).order_by(desc(ScrapeJob.created_at))
    if site:
        stmt = stmt.where(ScrapeJob.site_name == site)
    if status_filter:
        stmt = stmt.where(ScrapeJob.status == status_filter)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    stmt = stmt.offset((page - 1) * limit).limit(limit)
    result = await db.execute(stmt)
    jobs = result.scalars().all()

    def _job_dict(j: ScrapeJob) -> dict:
        duration = None
        if j.started_at and j.finished_at:
            secs = int((j.finished_at - j.started_at).total_seconds())
            duration = f"{secs // 60}m {secs % 60}s"
        return {
            "id": str(j.id),
            "site_name": j.site_name,
            "status": j.status,
            "started_at": j.started_at.isoformat() if j.started_at else None,
            "finished_at": j.finished_at.isoformat() if j.finished_at else None,
            "duration": duration,
            "pages_scraped": j.pages_scraped,
            "items_found": j.items_found,
            "items_new": j.items_new,
            "error_message": j.error_message,
        }

    return {
        "page": page,
        "limit": limit,
        "total": total or 0,
        "jobs": [_job_dict(j) for j in jobs],
    }


# ---------------------------------------------------------------------------
# Machines
# ---------------------------------------------------------------------------

@router.get("/machines")
async def list_machines(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    search: Optional[str] = Query(None),
    site_name: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(_get_current_admin),
):
    from sqlalchemy import or_

    stmt = select(Machine)
    if search:
        stmt = stmt.where(
            or_(Machine.name.ilike(f"%{search}%"), Machine.brand.ilike(f"%{search}%"))
        )
    if site_name:
        stmt = stmt.where(Machine.site_name == site_name)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    stmt = stmt.order_by(desc(Machine.created_at)).offset((page - 1) * limit).limit(limit)
    result = await db.execute(stmt)
    machines = result.scalars().all()

    def _m(m: Machine) -> dict:
        return {
            "id": str(m.id),
            "name": m.name,
            "brand": m.brand,
            "price": m.price,
            "currency": m.currency,
            "location": m.location,
            "image_url": m.image_url,
            "description": m.description,
            "specs": m.specs,
            "source_url": m.source_url,
            "site_name": m.site_name,
            "language": m.language,
            "view_count": m.view_count,
            "click_count": m.click_count,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }

    return {
        "page": page,
        "limit": limit,
        "total": total or 0,
        "machines": [_m(m) for m in machines],
    }


@router.delete("/machines/clear-all")
async def clear_all_machines(
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(_get_current_admin),
):
    """Delete every machine and every scrape job from the database."""
    machine_result = await db.execute(select(func.count(Machine.id)))
    machine_count = machine_result.scalar() or 0

    await db.execute(delete(Machine))
    await db.execute(delete(ScrapeJob))
    await db.commit()

    _running_jobs.clear()

    return {"cleared": True, "machines_removed": machine_count}


@router.delete("/machines/bulk")
async def delete_machines_bulk(
    site_name: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(_get_current_admin),
):
    result = await db.execute(
        select(func.count(Machine.id)).where(Machine.site_name == site_name)
    )
    count = result.scalar()

    await db.execute(delete(Machine).where(Machine.site_name == site_name))
    await db.commit()

    return {"deleted": count, "site_name": site_name}


@router.delete("/machines/{machine_id}")
async def delete_machine(
    machine_id: str,
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(_get_current_admin),
):
    machine = await db.scalar(select(Machine).where(Machine.id == uuid.UUID(machine_id)))
    if not machine:
        raise HTTPException(status_code=404, detail="Machine not found")

    await db.delete(machine)
    await db.commit()
    return {"deleted": machine_id}


# ---------------------------------------------------------------------------
# Analytics — clicks
# ---------------------------------------------------------------------------

@router.get("/analytics/clicks")
async def get_clicks(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    site: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(_get_current_admin),
):
    stmt = (
        select(ClickEvent, Machine.name.label("machine_name"), Machine.site_name)
        .join(Machine, ClickEvent.machine_id == Machine.id, isouter=True)
        .order_by(desc(ClickEvent.clicked_at))
    )
    if site:
        stmt = stmt.where(Machine.site_name == site)
    if date_from:
        stmt = stmt.where(ClickEvent.clicked_at >= datetime.fromisoformat(date_from))
    if date_to:
        stmt = stmt.where(ClickEvent.clicked_at <= datetime.fromisoformat(date_to))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    stmt = stmt.offset((page - 1) * limit).limit(limit)
    result = await db.execute(stmt)
    rows = result.all()

    clicks = [
        {
            "id": str(r.ClickEvent.id),
            "machine_name": r.machine_name,
            "site_name": r.site_name,
            "clicked_at": r.ClickEvent.clicked_at.isoformat() if r.ClickEvent.clicked_at else None,
            "source_url": r.ClickEvent.source_url,
            "user_ip": r.ClickEvent.user_ip,
        }
        for r in rows
    ]
    return {"page": page, "limit": limit, "total": total or 0, "clicks": clicks}


# ---------------------------------------------------------------------------
# Analytics — searches
# ---------------------------------------------------------------------------

@router.get("/analytics/searches")
async def get_searches(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    zero_results_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    _: AdminUser = Depends(_get_current_admin),
):
    stmt = select(SearchEvent).order_by(desc(SearchEvent.searched_at))
    if date_from:
        stmt = stmt.where(SearchEvent.searched_at >= datetime.fromisoformat(date_from))
    if date_to:
        stmt = stmt.where(SearchEvent.searched_at <= datetime.fromisoformat(date_to))
    if zero_results_only:
        stmt = stmt.where(SearchEvent.results_count == 0)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt)

    stmt = stmt.offset((page - 1) * limit).limit(limit)
    result = await db.execute(stmt)
    events = result.scalars().all()

    searches = [
        {
            "id": str(e.id),
            "query": e.query,
            "filters": e.filters,
            "results_count": e.results_count,
            "user_ip": e.user_ip,
            "searched_at": e.searched_at.isoformat() if e.searched_at else None,
        }
        for e in events
    ]
    return {"page": page, "limit": limit, "total": total or 0, "searches": searches}
