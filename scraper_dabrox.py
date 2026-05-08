"""
Scraper for dabrox.com — all 16 categories, 1,276 machines
Extracts Brand, Model, Type directly from listing cards (no detail page needed).
Usage:
  python scraper_dabrox.py              # scrape all 16 categories
  python scraper_dabrox.py <url>        # scrape one specific category
"""

import os
import re
import sys
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from urllib.parse import urljoin

BASE_URL   = "https://dabrox.com"
OUTPUT_DIR = "output"
NA         = "Not Available"
HEADERS    = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
    )
}

# All 16 machine categories on dabrox.com
ALL_CATEGORIES = [
    ("Sheet Stamping Presses",  "https://dabrox.com/forging-stamping-machines/sheet-stamping-presses/"),
    ("Hot Forging Presses",     "https://dabrox.com/forging-stamping-machines/hot-forging-presses/"),
    ("Cold Forging Presses",    "https://dabrox.com/forging-stamping-machines/cold-forging-presses/"),
    ("Trimming Presses",        "https://dabrox.com/forging-stamping-machines/trimming-presses/"),
    ("Screw Presses",           "https://dabrox.com/forging-stamping-machines/screw-presses/"),
    ("Knuckle Joint Presses",   "https://dabrox.com/forging-stamping-machines/knuckle-joint-presses/"),
    ("Forging Hammers",         "https://dabrox.com/forging-stamping-machines/forging-hammers/"),
    ("Forging Upsetters",       "https://dabrox.com/forging-stamping-machines/forging-upsetters/"),
    ("Forging Rolls",           "https://dabrox.com/forging-stamping-machines/forging-rolls/"),
    ("Ring Rolling Machines",   "https://dabrox.com/forging-stamping-machines/ring-rolling-machines/"),
    ("Open Die Forging",        "https://dabrox.com/forging-stamping-machines/open-die-forging/"),
    ("Hydraulic Presses",       "https://dabrox.com/forging-stamping-machines/hydraulic-presses/"),
    ("C-Type Presses",          "https://dabrox.com/forging-stamping-machines/c-type-presses/"),
    ("Extrusion Presses",       "https://dabrox.com/forging-stamping-machines/extrusion-presses/"),
    ("Forging Manipulators",    "https://dabrox.com/forging-stamping-machines/forging-manipulators/"),
    ("Billet Shear",            "https://dabrox.com/forging-stamping-machines/billet-shear/"),
]


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
    text = text.replace("\xa0", " ").replace("’", "'").replace("—", "-").replace("–", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def full_image(src):
    """Remove WordPress-style size suffix e.g. -400x267 before extension."""
    return re.sub(r"-\d+x\d+(\.(jpg|jpeg|png|webp))$", r"\1", src, flags=re.IGNORECASE)


def scrape_listing_page(url):
    """
    Extract all machine cards from one listing page.
    Card HTML:
      <article class="product-card">
        <a class="product-card__image"><img src="thumbnail.jpg"></a>
        <h3 class="product-card__title"><a href="detail-url">Title</a></h3>
        <div class="product-card__specs">
          <dl>
            <div class="spec-item"><dt>Brand:</dt><dd>Berrenberg</dd></div>
            <div class="spec-item"><dt>Model:</dt><dd>RSPe 230/300</dd></div>
            <div class="spec-item"><dt>Type:</dt><dd>Screw press</dd></div>
            <div class="spec-item--main"><dt>Parameter:</dt><dd>300 ton</dd></div>
          </dl>
        </div>
      </article>
    """
    soup = get_soup(url)
    if not soup:
        return [], None

    machines = []
    for article in soup.find_all("article", class_="product-card"):

        # ── Source URL & Description from title ──────────────────────────────
        title_tag  = article.find("h3", class_="product-card__title")
        source_url = ""
        description = NA
        if title_tag:
            a = title_tag.find("a", href=True)
            if a:
                source_url  = a["href"] if a["href"].startswith("http") else urljoin(BASE_URL, a["href"])
                description = clean(a.get_text())

        # ── Image (full size) ─────────────────────────────────────────────────
        img_tag   = article.find("a", class_="product-card__image")
        image_url = ""
        if img_tag:
            img = img_tag.find("img", src=True)
            if img:
                src       = img["src"]
                full_src  = src if src.startswith("http") else urljoin(BASE_URL, src)
                image_url = full_image(full_src)

        # ── Brand, Model, Type from spec-item dl ─────────────────────────────
        specs = {}
        for item in article.find_all("div", class_=re.compile(r"spec-item")):
            dt = item.find("dt")
            dd = item.find("dd")
            if dt and dd:
                key = clean(dt.get_text()).rstrip(":").lower()
                val = clean(dd.get_text())
                specs[key] = val

        brand        = specs.get("brand", NA) or NA
        model        = specs.get("model", NA) or NA
        machine_type = specs.get("type",  NA) or NA

        machines.append({
            "Type":        machine_type,
            "Brand":       brand,
            "Model":       model,
            "Description": description,
            "Price":       "",
            "Image URL":   image_url,
            "Source URL":  source_url,
        })

    # ── Next page ─────────────────────────────────────────────────────────────
    next_url  = None
    current_n = 1
    m = re.search(r"/page/(\d+)/?$", url.rstrip("/"))
    if m:
        current_n = int(m.group(1))

    page_nums = set()
    for a in soup.find_all("a", href=True):
        pm = re.search(r"/page/(\d+)/?", a["href"])
        if pm:
            page_nums.add(int(pm.group(1)))

    next_n = current_n + 1
    if next_n in page_nums or (page_nums and max(page_nums) >= next_n):
        base    = re.sub(r"/page/\d+/?$", "", url.rstrip("/"))
        next_url = f"{base}/page/{next_n}/"

    return machines, next_url


def scrape_category(label, start_url):
    """Scrape all pages of one category and return machine records."""
    print(f"\n  [{label}]")
    all_machines = []
    page_url     = start_url
    page_num     = 1

    while page_url:
        print(f"    Page {page_num}: {page_url}")
        machines, next_url = scrape_listing_page(page_url)
        print(f"    -> {len(machines)} machines")
        all_machines.extend(machines)
        page_url  = next_url
        page_num += 1
        if next_url:
            time.sleep(0.5)

    return all_machines


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


def run(categories):
    print("Scraper — dabrox.com")
    print("=" * 60)
    print(f"  Categories to scrape: {len(categories)}")
    print("=" * 60)

    all_machines = []
    seen_urls    = set()

    for label, cat_url in categories:
        machines = scrape_category(label, cat_url)
        new = 0
        for m in machines:
            if m["Source URL"] not in seen_urls:
                seen_urls.add(m["Source URL"])
                all_machines.append(m)
                new += 1
        dupes = len(machines) - new
        print(f"    Total: {new} unique" + (f" ({dupes} duplicates skipped)" if dupes else ""))

    if not all_machines:
        print("No data collected.")
        return

    df = pd.DataFrame(all_machines)
    df = df[["Type", "Brand", "Model", "Description", "Price", "Image URL", "Source URL"]]
    df["Brand"]       = df["Brand"].fillna(NA)
    df["Model"]       = df["Model"].fillna(NA)
    df["Description"] = df["Description"].fillna(NA)
    df["Price"]       = df["Price"].fillna("")
    df["Image URL"]   = df["Image URL"].fillna("")

    df.sort_values("Type", inplace=True)
    df.reset_index(drop=True, inplace=True)

    suffix      = "all" if len(categories) > 1 else categories[0][0].lower().replace(" ", "-")
    timestamp   = datetime.now().strftime("%Y%m%d_%H%M")
    output_path = os.path.join(OUTPUT_DIR, f"dabrox_{suffix}_{timestamp}.xlsx")
    save_excel(df, output_path)

    print("\n" + "=" * 60)
    print("  FINAL SUMMARY")
    print("=" * 60)
    print(f"  Total machines   : {len(df)}")
    print(f"  Excel saved at   : {os.path.abspath(output_path)}")
    print("-" * 60)
    print("  By Type:")
    for t, cnt in df["Type"].value_counts().items():
        print(f"    {str(t)[:45]:<45}: {cnt}")
    print("=" * 60)
    print(f"\nDone. Open: {os.path.abspath(output_path)}")


def main():
    if len(sys.argv) > 1:
        url   = sys.argv[1]
        label = url.rstrip("/").split("/")[-1].replace("-", " ").title()
        run([(label, url)])
    else:
        run(ALL_CATEGORIES)


if __name__ == "__main__":
    main()
