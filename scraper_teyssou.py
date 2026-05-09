"""
Scraper for teyssou-ra.com/en_GB
- Used Machinery  : 14 categories (~66 machines)
- New Machines    : DENER, LISSMAC, BRETON (~30 machines)
- Total target    : ~96 machines

Fallbacks:
  Brand not found  → "Brand-Unknown"
  Model not found  → "Model-Unknown"
  Type  not found  → "Type-Unknown"
"""

import os
import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from urllib.parse import urljoin

BASE_URL   = "https://www.teyssou-ra.com"
OUTPUT_DIR = "output"
HEADERS    = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    )
}

# ── Used Machinery categories ─────────────────────────────────────────────────
USED_CATEGORIES = [
    ("Machining Center",                    "/en_GB/shop/category/27"),
    ("Milling Machine",                     "/en_GB/shop/category/32"),
    ("Grinding Machine",                    "/en_GB/shop/category/39"),
    ("Saw",                                 "/en_GB/shop/category/42"),
    ("Lathe",                               "/en_GB/shop/category/47"),
    ("Guillotine Shear",                    "/en_GB/shop/category/55"),
    ("Laser Cutting",                       "/en_GB/shop/category/57"),
    ("Deburring Machine",                   "/en_GB/shop/category/58"),
    ("Notching Machine",                    "/en_GB/shop/category/59"),
    ("Punching Machine",                    "/en_GB/shop/category/62"),
    ("CNC Punching Machine",               "/en_GB/shop/category/63"),
    ("Press",                              "/en_GB/shop/category/sheet-metal-presse-64"),
    ("Hydraulic Press",                    "/en_GB/shop/category/sheet-metal-presse-hydraulique-65"),
    ("Press Brake",                         "/en_GB/shop/category/66"),
    ("Rolling Machine",                     "/en_GB/shop/category/67"),
    ("Miscellaneous Equipment",             "/en_GB/shop/category/69"),
]

# ── New Machines brand pages ──────────────────────────────────────────────────
NEW_MACHINE_PAGES = [
    ("DENER",    "/en_GB/dener"),
    ("LISSMAC",  "/en_GB/lissmac"),
    ("BRETON",   "/en_GB/breton"),
]

PRODUCT_RE = re.compile(r"/shop/[^/?#]+-\d+")


def get_soup(url):
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
            return BeautifulSoup(r.text, "lxml")
        except Exception as e:
            if attempt == 2:
                print(f"    [ERROR] {url} -> {e}")
            time.sleep(2)
    return None


def clean(text):
    if not text:
        return ""
    text = text.replace("\xa0", " ").replace("’", "'").replace("&#39;", "'")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def full_image(src):
    src = src.replace("/image_512/", "/image_1024/")
    return src if src.startswith("http") else urljoin(BASE_URL, src)


# ── Collect product URLs from a listing page ──────────────────────────────────

def collect_urls(page_path):
    url  = urljoin(BASE_URL, page_path)
    soup = get_soup(url)
    if not soup:
        return []

    seen, urls = set(), []
    for a in soup.find_all("a", href=True):
        href = a["href"].split("?")[0].split("#")[0]
        if PRODUCT_RE.search(href):
            full = href if href.startswith("http") else urljoin(BASE_URL, href)
            # Normalize: strip /en_GB prefix so /shop/X and /en_GB/shop/X dedup correctly
            norm = full.replace(BASE_URL + "/en_GB", BASE_URL)
            if norm not in seen:
                seen.add(norm)
                urls.append(full)
    return urls


# ── Parse a machine detail page ───────────────────────────────────────────────

def parse_detail(url, default_type="Type-Unknown", is_new=False):
    """
    is_new=False (Used Machines): Type = category name (never override from H1)
    is_new=True  (New Machines) : Type = first part of H1 before ' - '
    """
    soup = get_soup(url)
    if not soup:
        return None

    # ── Brand & Model from #main_caracteristics ───────────────────────────────
    # Used:  <p>Brand: <strong>HURON</strong></p>
    #        <p>Modèle : <strong>MU66</strong></p>
    # New:   <p>Marque : <strong>DENER</strong></p>  (no Modèle row)
    brand = None
    model = None

    main_chars = soup.find("div", id="main_caracteristics")
    if main_chars:
        for p in main_chars.find_all("p"):
            raw    = p.get_text(separator=" ")
            strong = p.find("strong")
            if not strong:
                continue
            val = clean(strong.get_text())
            if not val or val.lower() in ("x", "-", ""):
                continue
            if re.match(r"\s*(Brand|Marque)\s*:", raw, re.IGNORECASE):
                brand = val
            elif re.match(r"\s*Mod[eè]le\s*:", raw, re.IGNORECASE):
                model = val

    # ── H1 ───────────────────────────────────────────────────────────────────
    h1     = soup.find("h1", attrs={"itemprop": "name"}) or soup.find("h1")
    h1_txt = clean(h1.get_text()) if h1 else ""
    description = h1_txt or default_type

    # ── Type ──────────────────────────────────────────────────────────────────
    if is_new and " - " in h1_txt:
        # New machine H1: "Cisaille CNC - type AS" → Type = "Cisaille CNC"
        machine_type = h1_txt.split(" - ")[0].strip() or default_type
    else:
        # Used machine: always use the category name
        machine_type = default_type

    # ── Model from H1 ─────────────────────────────────────────────────────────
    if model is None and " - " in h1_txt:
        # "Type - Model" pattern (new machines)
        parts = h1_txt.split(" - ", 1)
        if len(parts) == 2 and parts[1].strip():
            model = parts[1].strip()

    if model is None and brand and h1_txt:
        # "TYPE BRAND MODEL" pattern (used machines)
        idx = h1_txt.upper().find(brand.upper())
        if idx != -1:
            after = h1_txt[idx + len(brand):].strip(" -–—:")
            if after:
                model = after

    # ── Image ─────────────────────────────────────────────────────────────────
    image_url = ""
    for img in soup.find_all("img", src=True):
        src = img["src"]
        if any(k in src for k in ["product.product", "product.template", "product.image"]):
            image_url = full_image(src)
            break

    return {
        "Type":        machine_type or "Type-Unknown",
        "Brand":       brand        or "Brand-Unknown",
        "Model":       model        or "Model-Unknown",
        "Description": description,
        "Price":       "",
        "Image URL":   image_url,
        "Source URL":  url,
    }


# ── Save Excel ────────────────────────────────────────────────────────────────

def save_excel(df, filepath):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df.to_excel(filepath, index=False, engine="openpyxl")

    wb = load_workbook(filepath)
    ws = wb.active

    hdr_font  = Font(bold=True, color="FFFFFF", size=11)
    hdr_fill  = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    hdr_align = Alignment(horizontal="center", vertical="center")

    for cell in ws[1]:
        cell.font      = hdr_font
        cell.fill      = hdr_fill
        cell.alignment = hdr_align

    ws.freeze_panes = "A2"

    for col_idx, col_cells in enumerate(ws.columns, 1):
        col_letter = get_column_letter(col_idx)
        max_len    = max((len(str(c.value)) for c in col_cells if c.value), default=10)
        ws.column_dimensions[col_letter].width = min(max_len + 4, 80)

    wb.save(filepath)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Scraper — teyssou-ra.com (Used + New Machines)")
    print("=" * 60)

    all_machines = []
    seen_urls    = set()

    def norm(u):
        return u.replace(BASE_URL + "/en_GB", BASE_URL).split("?")[0].split("#")[0]

    # ── SECTION 1: New Machines first (so they own their URLs before used cats) ─
    print("\n[ NEW MACHINES ]")
    new_machines_tmp = []
    for brand_label, brand_path in NEW_MACHINE_PAGES:
        urls = collect_urls(brand_path)
        added = [u for u in urls if norm(u) not in seen_urls]
        print(f"  {brand_label:<35}: {len(added)} machines")
        for url in added:
            seen_urls.add(norm(url))
            new_machines_tmp.append({"url": url, "default_type": brand_label, "is_new": True})
        time.sleep(0.4)

    # ── SECTION 2: Used Machinery (new machine URLs already claimed above) ──────
    print("\n[ USED MACHINERY ]")
    for cat_type, cat_path in USED_CATEGORIES:
        urls = collect_urls(cat_path)
        added = [u for u in urls if norm(u) not in seen_urls]
        print(f"  {cat_type:<35}: {len(added)} machines")
        for url in added:
            seen_urls.add(norm(url))
            all_machines.append({"url": url, "default_type": cat_type, "is_new": False})
        time.sleep(0.4)

    # Append new machines after so display order is used first, new second
    all_machines.extend(new_machines_tmp)

    total = len(all_machines)
    print(f"\n  Total unique machines to scrape: {total}")

    # ── Scrape each detail page ───────────────────────────────────────────────
    print("\n[ SCRAPING DETAIL PAGES ]")
    records = []
    for i, item in enumerate(all_machines, 1):
        print(f"  [{i}/{total}] {item['url']}")
        try:
            data = parse_detail(item["url"], item["default_type"], is_new=item.get("is_new", False))
            if data:
                records.append(data)
        except Exception as e:
            print(f"    [SKIP] {e}")
        time.sleep(0.5)

    if not records:
        print("No data collected.")
        return

    df = pd.DataFrame(records)
    df = df[["Type", "Brand", "Model", "Description", "Price", "Image URL", "Source URL"]]
    df.sort_values("Type", inplace=True)
    df.reset_index(drop=True, inplace=True)

    timestamp   = datetime.now().strftime("%Y%m%d_%H%M")
    output_path = os.path.join(OUTPUT_DIR, f"teyssou_output_{timestamp}.xlsx")
    save_excel(df, output_path)

    print("\n" + "=" * 60)
    print("  CRAWL SUMMARY")
    print("=" * 60)
    print(f"  Total machines   : {len(df)}")
    print(f"  Excel saved at   : {os.path.abspath(output_path)}")
    print("-" * 60)
    print("  By Type:")
    for t, cnt in df["Type"].value_counts().items():
        print(f"    {str(t):<40}: {cnt}")
    print("=" * 60)
    print(f"\nDone. Open: {os.path.abspath(output_path)}")


if __name__ == "__main__":
    main()
