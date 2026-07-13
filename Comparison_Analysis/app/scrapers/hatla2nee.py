import re
import logging
from bs4 import BeautifulSoup
from .base import BaseScraper, MIN_CAR_PRICE, MAX_CAR_PRICE

logger = logging.getLogger(__name__)


class Hatla2neeScraper(BaseScraper):
    source = "hatla2ee.com"

    def _build_url(self, make: str, model: str, year: int) -> str:
        make_slug = make.lower().replace(" ", "-")
        model_slug = model.lower().replace(" ", "-")
        return f"https://eg.hatla2ee.com/en/new-car/{make_slug}/{model_slug}"

    def _build_make_url(self, make: str) -> str:
        make_slug = make.lower().replace(" ", "-")
        return f"https://eg.hatla2ee.com/en/new-car/{make_slug}/"

    async def _parse_structured(self, html: str, make: str, model: str, year: int) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        items = []

        price_elements = soup.select("div.font-bold.text-primary")
        for price_el in price_elements:
            try:
                price_text = price_el.get_text(strip=True)
                price = self._clean_price(price_text)
                if not price:
                    continue

                card = price_el.find_parent("div", class_=lambda c: c and "flex" in str(c))

                title = ""
                url = ""
                mileage = 0

                if card:
                    link_el = card.select_one("a[href*='/en/car/']")
                    if link_el:
                        title = link_el.get_text(strip=True)
                        url = link_el.get("href", "")
                        if url and not url.startswith("http"):
                            url = "https://eg.hatla2ee.com" + url

                    card_text = card.get_text(" ", strip=True)
                    km_match = re.search(r"([\d,]+)\s*KM", card_text, re.IGNORECASE)
                    if km_match:
                        mileage = int(km_match.group(1).replace(",", ""))

                    if not title:
                        title = f"{make.title()} {model.title()} {year}"

                if not url or not re.search(r"/\d+$", url):
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
                    "mileage": mileage,
                    "condition": "used",
                    "url": url,
                    "make": make,
                    "model": model,
                })
            except Exception as e:
                logger.debug("Hatla2ee parse error: %s", e)
                continue

        return items
