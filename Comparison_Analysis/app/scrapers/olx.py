import re
import logging
from bs4 import BeautifulSoup
from .base import BaseScraper

logger = logging.getLogger(__name__)


class OLXScraper(BaseScraper):
    source = "olx.com.eg"

    def _build_url(self, make: str, model: str, year: int) -> str:
        q = f"{make} {model} {year}".replace(" ", "-").lower()
        return f"https://www.olx.com.eg/cars/q-{q}/"

    async def _parse_structured(self, html: str, make: str, model: str, year: int) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        items = []

        for card in soup.select("li[data-testid='listing-card'], div[data-testid='listing-card']"):
            try:
                title_el = card.select_one("h6, h2, a h6, div[data-testid='ad-title']")
                title = title_el.get_text(strip=True) if title_el else ""

                price_el = card.select_one("[data-testid='price'], span[data-testid='price'], div[data-testid='price']")
                price_text = price_el.get_text(strip=True) if price_el else ""

                link_el = card.select_one("a[href]")
                url = ""
                if link_el:
                    url = link_el.get("href", "")
                    if url and not url.startswith("http"):
                        url = "https://www.olx.com.eg" + url

                price = self._clean_price(price_text)
                if not price:
                    continue

                item_year = year
                year_match = re.search(r"\b(19\d{2}|20\d{2})\b", title)
                if year_match:
                    item_year = int(year_match.group(1))

                items.append({
                    "source": self.source,
                    "title": title,
                    "price": price,
                    "year": item_year,
                    "mileage": 0,
                    "condition": "",
                    "url": url,
                    "make": make,
                    "model": model,
                })
            except Exception as e:
                logger.debug("OLX parse error: %s", e)
                continue

        return items
