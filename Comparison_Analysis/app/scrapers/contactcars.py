import re
import json
import logging
from bs4 import BeautifulSoup
from .base import BaseScraper, MIN_CAR_PRICE, MAX_CAR_PRICE

logger = logging.getLogger(__name__)


class ContactCarsScraper(BaseScraper):
    source = "contactcars.com"

    def _build_url(self, make: str, model: str, year: int) -> str:
        make_slug = make.lower().replace(" ", "-")
        model_slug = model.lower().replace(" ", "-")
        return f"https://www.contactcars.com/en/new-cars/{make_slug}-{model_slug}"

    async def _parse_structured(self, html: str, make: str, model: str, year: int) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        items = []

        for script in soup.select("script[type='application/ld+json']"):
            try:
                data = json.loads(script.string)
                if isinstance(data, list):
                    for entry in data:
                        if isinstance(entry, dict) and entry.get("@type") == "Vehicle":
                            data = entry
                            break
                if not isinstance(data, dict) or data.get("@type") != "Vehicle":
                    continue

                name = data.get("name", "")
                offers = data.get("offers", {})
                if isinstance(offers, list):
                    offers = offers[0] if offers else {}
                price_val = offers.get("price")
                if not price_val:
                    continue
                price_val = float(price_val)
                if not (MIN_CAR_PRICE <= price_val <= MAX_CAR_PRICE):
                    continue

                item_year = year
                year_match = re.search(r"\b(19\d{2}|20\d{2})\b", name)
                if year_match:
                    item_year = int(year_match.group(1))

                if item_year != year:
                    continue

                items.append({
                    "source": self.source,
                    "title": name,
                    "price": price_val,
                    "year": item_year,
                    "mileage": 0,
                    "condition": "new",
                    "url": data.get("url", ""),
                    "make": make,
                    "model": model,
                })
            except Exception as e:
                logger.debug("ContactCars JSON-LD parse error: %s", e)
                continue

        for table in soup.select("table"):
            rows = table.select("tbody tr")
            for row in rows:
                cells = row.select("td")
                if len(cells) < 2:
                    continue

                model_text = cells[0].get_text(strip=True)
                official_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                market_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""

                year_match = re.search(r"\b(19\d{2}|20\d{2})\b", model_text)
                item_year = int(year_match.group(1)) if year_match else year

                if item_year != year:
                    continue

                for price_text in (official_text, market_text):
                    price = self._clean_price(price_text)
                    if price:
                        items.append({
                            "source": self.source,
                            "title": f"{make.title()} {model.title()} {item_year} - {model_text}",
                            "price": price,
                            "year": item_year,
                            "mileage": 0,
                            "condition": "new",
                            "url": "",
                            "make": make,
                            "model": model,
                        })

        return items
