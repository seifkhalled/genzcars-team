import re
import logging
from abc import ABC, abstractmethod
from playwright.async_api import Page

logger = logging.getLogger(__name__)


PRICE_PATTERNS = [
    re.compile(r"(\d{1,}(?:[\s,]\d{3})+)(?:[\s]*)(?:EGP|جنيه|ج\.م|LE|جم|ج\.م)", re.IGNORECASE),
    re.compile(r"(?:EGP|جنيه|ج\.م|LE|جم|ج\.م)\s*:?\s*(\d{1,}(?:[\s,]\d{3})+)", re.IGNORECASE),
]

YEAR_PATTERN = re.compile(r"\b(19\d{2}|20\d{2})\b")

MIN_CAR_PRICE = 50_000
MAX_CAR_PRICE = 50_000_000


class BaseScraper(ABC):
    source: str = ""

    async def _fetch(self, page: Page, url: str, timeout: float = 30.0) -> str | None:
        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=int(timeout * 1000))
            if resp and resp.ok:
                return await page.content()
            status = resp.status if resp else 0
            logger.warning("%s returned HTTP %d for %s", self.source, status, url)
            return None
        except Exception as e:
            logger.warning("%s fetch error for %s: %s", self.source, url, e)
            return None

    def _extract_prices_from_text(self, text: str) -> list[float]:
        prices = set()
        for pattern in PRICE_PATTERNS:
            for match in pattern.finditer(text):
                raw = match.group(1).replace(",", "").replace(" ", "")
                try:
                    val = float(raw)
                    if MIN_CAR_PRICE <= val <= MAX_CAR_PRICE:
                        prices.add(val)
                except ValueError:
                    continue
        return sorted(prices)

    def _extract_years_from_text(self, text: str) -> list[int]:
        return [int(m) for m in YEAR_PATTERN.findall(text) if 1990 <= int(m) <= 2030]

    def _clean_price(self, text: str) -> float | None:
        if not text:
            return None
        cleaned = text.replace(",", "").replace(" ", "").strip()
        cleaned = re.sub(r"[^\d.]", "", cleaned)
        match = re.search(r"(\d+(?:\.\d+)?)", cleaned)
        if match:
            try:
                val = float(match.group(1))
                if MIN_CAR_PRICE <= val <= MAX_CAR_PRICE:
                    return val
            except ValueError:
                pass
        return None

    def _extract_listings_from_text(
        self, text: str, make: str, model: str, year: int
    ) -> list[dict]:
        prices = self._extract_prices_from_text(text)
        years = self._extract_years_from_text(text)

        year_counts = {}
        for y in years:
            if 1990 <= y <= 2030:
                year_counts[y] = year_counts.get(y, 0) + 1

        items = []
        for price in prices:
            items.append({
                "source": self.source,
                "title": f"{make} {model} {year}",
                "price": price,
                "year": year,
                "mileage": 0,
                "condition": "",
                "url": "",
                "make": make,
                "model": model,
            })

        if items:
            logger.info(
                "%s extracted %d prices from full-page text for %s %s %d (years found: %s)",
                self.source, len(items), make, model, year, dict(sorted(year_counts.items(), key=lambda x: -x[1])[:5]),
            )

        return items

    @abstractmethod
    def _build_url(self, make: str, model: str, year: int) -> str:
        ...

    async def search(self, page: Page, make: str, model: str, year: int) -> list[dict]:
        url = self._build_url(make, model, year)
        html = await self._fetch(page, url)
        if not html:
            logger.info("%s returned no HTML for %s %s %d", self.source, make, model, year)
            return []

        items = await self._parse_structured(html, make, model, year) or []

        logger.info("%s found %d listings for %s %s %d", self.source, len(items), make, model, year)
        return items

    async def _get_page_text(self, page: Page) -> str | None:
        try:
            return await page.evaluate("() => document.body.innerText")
        except Exception as e:
            logger.debug("%s _get_page_text error: %s", self.source, e)
            return None

    @abstractmethod
    async def _parse_structured(self, html: str, make: str, model: str, year: int) -> list[dict]:
        ...
