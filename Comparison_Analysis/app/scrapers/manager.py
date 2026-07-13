import asyncio
import logging
from playwright.async_api import Browser

from .base import BaseScraper
from .contactcars import ContactCarsScraper
from .hatla2nee import Hatla2neeScraper
from .dubizzle import DubizzleScraper

logger = logging.getLogger(__name__)

PER_SCRAPER_TIMEOUT = 20


class ScraperManager:
    def __init__(self, browser: Browser):
        self.browser = browser
        self.scrapers: list[BaseScraper] = [
            Hatla2neeScraper(),
            ContactCarsScraper(),
            DubizzleScraper(),
        ]

    async def scrape_car(self, make: str, model: str, year: int) -> list[dict]:
        all_listings = []

        for scraper in self.scrapers:
            context = await self.browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                locale="en-US",
            )
            page = await context.new_page()
            try:
                results = await asyncio.wait_for(
                    scraper.search(page, make, model, year),
                    timeout=PER_SCRAPER_TIMEOUT,
                )
                all_listings.extend(results)
            except asyncio.TimeoutError:
                logger.warning("%s timed out for %s %s %d", scraper.source, make, model, year)
            except Exception as e:
                logger.warning("%s failed for %s %s %d: %s", scraper.source, make, model, year, e)
            finally:
                await page.close()
                await context.close()

        seen = set()
        unique = []
        for ad in all_listings:
            ad_year = ad.get("year", year)
            if ad_year is None or abs(ad_year - year) > 1:
                continue
            key = ad.get("url", "") or f"{ad['source']}:{ad['title']}:{ad['price']}"
            if key not in seen:
                seen.add(key)
                unique.append(ad)

        logger.info(
            "Scraped %d unique listings for %s %s %d (from %d total raw, filtered by year)",
            len(unique), make, model, year, len(all_listings),
        )
        return unique
