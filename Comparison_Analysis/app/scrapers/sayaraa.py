import re
import logging
from bs4 import BeautifulSoup
from .base import BaseScraper

logger = logging.getLogger(__name__)


class SayaraaScraper(BaseScraper):
    source = "sayaraa.com"

    def _build_url(self, make: str, model: str, year: int) -> str:
        q = f"{make} {model} {year}".replace(" ", "+").lower()
        return f"https://sayaraa.com/en/cars/search?q={q}"

    async def _parse_structured(self, html: str, make: str, model: str, year: int) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        items = []

        for card in soup.select("div[class*='listing'], div[class*='card'], article"):
            try:
                title_el = card.select_one("h2, h3, h4, a[class*='title'], div[class*='title']")
                title = title_el.get_text(strip=True) if title_el else ""

                price_el = card.select_one("[class*='price'], [data-price]")
                price_text = price_el.get_text(strip=True) if price_el else ""

                link_el = card.select_one("a[href*='/car'], a[href*='/listing'], a[href]")
                url = ""
                if link_el:
                    url = link_el.get("href", "")
                    if url and not url.startswith("http"):
                        url = "https://sayaraa.com" + url

                price = self._clean_price(price_text)
                if not price:
                    continue

                item_year = year
                year_match = re.search(r"\b(19\d{2}|20\d{2})\b", title)
                if year_match:
                    item_year = int(year_match.group(1))

                mileage = 0
                km_match = re.search(r"(\d[\d,]*)\s*km", title, re.IGNORECASE)
                if km_match:
                    mileage = int(km_match.group(1).replace(",", ""))

                items.append({
                    "source": self.source,
                    "title": title,
                    "price": price,
                    "year": item_year,
                    "mileage": mileage,
                    "condition": "",
                    "url": url,
                    "make": make,
                    "model": model,
                })
            except Exception as e:
                logger.debug("Sayaraa parse error: %s", e)
                continue

        return items
