import re
import asyncio
import logging
from playwright.async_api import Page
from bs4 import BeautifulSoup
from .base import BaseScraper, MIN_CAR_PRICE, MAX_CAR_PRICE

logger = logging.getLogger(__name__)


class DubizzleScraper(BaseScraper):
    source = "dubizzle.com.eg"

    def _build_url(self, make: str, model: str, year: int) -> str:
        make_slug = make.lower().replace(" ", "-")
        model_slug = model.lower().replace(" ", "-")
        return (
            f"https://www.dubizzle.com.eg/vehicles/cars-for-sale/"
            f"{make_slug}/model-{model_slug}/{year}/"
        )

    async def search(self, page: Page, make: str, model: str, year: int) -> list[dict]:
        url = self._build_url(make, model, year)
        try:
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            if resp and resp.status == 404:
                logger.info("%s returned 404 for %s %s %d", self.source, make, model, year)
                return []
            try:
                await page.wait_for_selector("li[aria-label='Listing']", timeout=8000)
            except Exception:
                pass
            await asyncio.sleep(2)
            html = await page.content()
        except Exception as e:
            logger.warning("%s fetch error for %s: %s", self.source, url, e)
            return []

        if not html:
            return []

        items = await self._parse_structured(html, make, model, year) or []
        logger.info("%s found %d listings for %s %s %d", self.source, len(items), make, model, year)
        return items

    def _clean_price(self, text: str) -> float | None:
        if not text:
            return None
        text = text.split("دفعة")[0].split("قابل")[0]
        text = text.replace("ج.م", "").replace("جنيه", "").replace("EGP", "")
        text = text.replace(",", "").strip()
        text = re.sub(r"[^\d.]", "", text)
        match = re.search(r"(\d+(?:\.\d+)?)", text)
        if match:
            try:
                val = float(match.group(1))
                if MIN_CAR_PRICE <= val <= MAX_CAR_PRICE:
                    return val
            except ValueError:
                pass
        return None

    async def _parse_structured(self, html: str, make: str, model: str, year: int) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        items = []

        for listing in soup.select("li[aria-label='Listing']"):
            try:
                price_el = listing.select_one("[aria-label='Price']")
                if not price_el:
                    continue
                price_text = price_el.get_text(strip=True)
                price = self._clean_price(price_text)
                if not price:
                    continue

                title_el = listing.select_one("[aria-label='Title'] h2")
                title = title_el.get_text(strip=True) if title_el else ""

                link_el = listing.select_one("a[href*='/ad/']")
                url = ""
                if link_el:
                    url = link_el.get("href", "")
                    if url and not url.startswith("http"):
                        url = "https://www.dubizzle.com.eg" + url

                item_year = year
                year_el = listing.select_one("[aria-label='السنة'] span:last-child, [aria-label='Year'] span:last-child")
                if year_el:
                    try:
                        item_year = int(year_el.get_text(strip=True))
                    except ValueError:
                        pass
                if not item_year or item_year < 1990:
                    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", title)
                    if year_match:
                        item_year = int(year_match.group(1))

                mileage = 0
                km_el = listing.select_one("[aria-label='كيلومترات'] span:last-child, [aria-label='Kilometers'] span:last-child")
                if km_el:
                    km_match = re.search(r"([\d,]+)", km_el.get_text())
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
                logger.debug("Dubizzle parse error: %s", e)
                continue

        return items
