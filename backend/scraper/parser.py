"""
Data parser for MachineSearch scraper.

Cleans and normalises raw scraped item dicts into the schema expected
by the database models.  Handles multi-locale price strings, HTML
stripping, spec normalisation, deduplication keys, and language detection.
"""

import hashlib
import logging
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Price parsing helpers
# ---------------------------------------------------------------------------

# Tokens that unambiguously mean "no price"
_NO_PRICE_TOKENS: tuple[str, ...] = (
    "price on request",
    "по запросу",
    "договорная",
    "договорная цена",
    "по договору",
    "contact for price",
    "call for price",
    "auf anfrage",
    "n/a",
    "—",
    "-",
)

# Map of currency symbols / codes → ISO code
_CURRENCY_MAP: dict[str, str] = {
    "$": "USD",
    "usd": "USD",
    "€": "EUR",
    "eur": "EUR",
    "£": "GBP",
    "gbp": "GBP",
    "¥": "JPY",
    "jpy": "JPY",
    "сом": "KGS",
    "kgs": "KGS",
    "kgz": "KGS",
    "₽": "RUB",
    "руб": "RUB",
    "rub": "RUB",
    "₸": "KZT",
    "тнг": "KZT",
    "kzt": "KZT",
    "₴": "UAH",
    "uah": "UAH",
}

# Finds numeric value(s) inside a price string
_PRICE_RE = re.compile(
    r"[\d\s\u00a0\u202f\.,]+",  # digits, spaces (incl. NBSP / NNBSP), dots, commas
)

# Valid image extensions
_IMAGE_EXTS: frozenset[str] = frozenset(
    [".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".bmp", ".svg"]
)


class DataParser:
    """
    Transforms raw scraped dicts into clean, schema-compliant item dicts.
    """

    # ------------------------------------------------------------------
    # Main entry
    # ------------------------------------------------------------------

    def parse_item(self, raw: dict, config: dict) -> dict | None:
        """
        Map raw field dict to the Machine model schema.

        Returns None if the item lacks a name or source_url — both are
        required non-nullable columns.
        """
        name = self.clean_text(raw.get("name", ""))
        source_url = (raw.get("source_url") or raw.get("detail_url") or "").strip()

        if not name or not source_url:
            logger.debug("Skipping item — missing name or source_url: %r", raw)
            return None

        raw_price_str = str(raw.get("price", ""))
        price, currency = self._extract_price_and_currency(raw_price_str)

        image_url = self.normalize_image_url(
            raw.get("image_url") or raw.get("image") or "",
            config.get("start_url", ""),
        )

        description = self.clean_text(raw.get("description", ""))

        return {
            "name": name[:500],
            "brand": self.clean_text(raw.get("brand", ""))[:200] or None,
            "price": price,
            "currency": currency,
            "location": self.clean_text(raw.get("location", ""))[:300] or None,
            "image_url": image_url,
            "description": description or None,
            "specs": self.clean_specs(raw.get("specs")),
            "source_url": source_url,
            "site_name": config.get("name", ""),
            "language": self.detect_language(name + " " + (description or "")),
        }

    # ------------------------------------------------------------------
    # Price cleaning
    # ------------------------------------------------------------------

    def clean_price(self, raw: str | None) -> float | None:
        """
        Parse a price string into a float.

        Handles formats: $1,200 / 1.200,00 / 1 200 USD / сом / KGS /
        "Price on request" / "Договорная" / "По запросу".
        Returns None for non-numeric / negotiated prices.
        """
        if not raw:
            return None
        normalised = raw.strip().lower()
        for token in _NO_PRICE_TOKENS:
            if token in normalised:
                return None

        # Pull out first contiguous block of numeric characters
        match = _PRICE_RE.search(normalised)
        if not match:
            return None

        numeric_str = match.group(0).strip()
        # Remove non-breaking spaces, regular spaces
        numeric_str = re.sub(r"[\s\u00a0\u202f]", "", numeric_str)

        # Determine decimal separator heuristic:
        # If last separator is ',' and there are exactly 2 digits after → decimal comma
        if re.search(r",\d{2}$", numeric_str) and "." not in numeric_str:
            numeric_str = numeric_str.replace(".", "").replace(",", ".")
        elif re.search(r"\.\d{2}$", numeric_str) and "," not in numeric_str:
            numeric_str = numeric_str.replace(",", "")
        else:
            # Ambiguous — strip both separators except the last one
            numeric_str = numeric_str.replace(",", "").replace(".", "")

        try:
            return float(numeric_str) if numeric_str else None
        except ValueError:
            logger.debug("Could not parse price from %r", raw)
            return None

    def _extract_price_and_currency(self, raw: str) -> tuple[float | None, str]:
        """Return (price_float, currency_iso_code) from a raw price string."""
        if not raw:
            return None, "USD"

        lower = raw.lower()
        detected_currency = "USD"  # default

        for symbol, iso in _CURRENCY_MAP.items():
            if symbol in lower:
                detected_currency = iso
                break

        return self.clean_price(raw), detected_currency

    # ------------------------------------------------------------------
    # Text cleaning
    # ------------------------------------------------------------------

    def clean_text(self, raw: str | None) -> str:
        """
        Strip HTML tags, collapse whitespace, limit to 1000 chars.
        Returns an empty string (never None) for safe downstream use.
        """
        if not raw:
            return ""
        if "<" in raw and ">" in raw:
            soup = BeautifulSoup(raw, "html.parser")
            raw = soup.get_text(separator=" ")
        # Collapse whitespace
        cleaned = re.sub(r"\s+", " ", raw).strip()
        return cleaned[:1000]

    # ------------------------------------------------------------------
    # Specs cleaning
    # ------------------------------------------------------------------

    def clean_specs(self, raw) -> dict | None:
        """
        Normalise specs into a flat dict.

        Accepts:
        - None / empty → None
        - Existing dict → returned as-is (keys/values truncated)
        - List of strings → each parsed for "Key: Value"
        - String → split on newline/semicolon, each part parsed for "Key: Value"
        """
        if not raw:
            return None

        if isinstance(raw, dict):
            return {str(k)[:100]: str(v)[:500] for k, v in raw.items()} or None

        lines: list[str] = []
        if isinstance(raw, list):
            lines = [str(item) for item in raw]
        elif isinstance(raw, str):
            lines = re.split(r"[\n\r;]+", raw)

        result: dict[str, str] = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip()[:100]
                value = value.strip()[:500]
                if key and value:
                    result[key] = value
            else:
                # No colon — store as a numbered entry
                result[f"spec_{len(result) + 1}"] = line[:500]

        return result if result else None

    # ------------------------------------------------------------------
    # Deduplication key
    # ------------------------------------------------------------------

    def generate_dedup_key(self, item: dict) -> str:
        """
        Return an MD5 hex digest used to detect duplicate listings.

        Prefer the full source_url as the dedup key when available — this is
        exact and works well for API scrapers where every record has a unique
        URL.  Fall back to name+price+domain for HTML scrapers where the URL
        may not reliably differ across duplicate listing cards.
        """
        source_url = (item.get("source_url") or "").strip()
        if source_url:
            return hashlib.md5(source_url.encode("utf-8")).hexdigest()
        name = (item.get("name") or "").lower().strip()
        price = str(item.get("price") or "")
        domain = urlparse(source_url).netloc
        raw = f"{name}|{price}|{domain}"
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Image URL normalisation
    # ------------------------------------------------------------------

    def normalize_image_url(self, url: str | None, base_url: str) -> str | None:
        """
        Resolve a potentially relative image URL to an absolute one.
        Validates that the extension is a known image type.
        Returns None for data-URIs, empty strings, or unknown types.
        """
        if not url:
            return None
        url = url.strip()
        if url.startswith("data:"):
            return None

        # Make absolute
        if not url.startswith(("http://", "https://")):
            url = urljoin(base_url, url)

        # Validate extension (ignore query string)
        path = urlparse(url).path.lower()
        ext = re.search(r"\.\w+$", path)
        if ext and ext.group(0) not in _IMAGE_EXTS:
            return None

        return url

    # ------------------------------------------------------------------
    # Language detection
    # ------------------------------------------------------------------

    def detect_language(self, text: str) -> str:
        """
        Heuristic language detection based on character script ratios.

        - Cyrillic chars > 30 % of alphabetic chars → "ru"
        - CJK block chars > 10 %                   → "zh"
        - Otherwise                                 → "en"
        """
        if not text:
            return "en"

        alpha_chars = [c for c in text if c.isalpha()]
        if not alpha_chars:
            return "en"

        total = len(alpha_chars)

        cyrillic = sum(1 for c in alpha_chars if "\u0400" <= c <= "\u04ff")
        cjk = sum(1 for c in alpha_chars if "\u4e00" <= c <= "\u9fff")

        if cyrillic / total > 0.30:
            return "ru"
        if cjk / total > 0.10:
            return "zh"
        return "en"
