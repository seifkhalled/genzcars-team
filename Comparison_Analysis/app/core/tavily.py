import asyncio
from tavily import TavilyClient


class TavilyWrapper:
    def __init__(self, api_key: str):
        self.client = TavilyClient(api_key=api_key)

    async def search(self, query: str) -> dict:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.client.search(
                query=query,
                search_depth="basic",
                max_results=3,
                include_answer=True,
                include_raw_content=False,
            )
        )
        return result

    async def research_car(self, ad: dict) -> dict:
        reliability_q = f"{ad['brand']} {ad['model']} {ad['year']} reliability common problems Egypt"
        price_q = f"{ad['brand']} {ad['model']} {ad['year']} price Egypt market EGP used"
        reputation_q = f"{ad['brand']} {ad['model']} owner review Egypt مصر"

        try:
            reliability, price, reputation = await asyncio.gather(
                self.search(reliability_q),
                self.search(price_q),
                self.search(reputation_q),
            )
        except Exception:
            return {
                "ad_id": str(ad.get("id", "")),
                "brand": ad.get("brand", ""),
                "model": ad.get("model", ""),
                "year": ad.get("year", ""),
                "reliability_research": {"tavily_answer": "Research unavailable.", "sources": []},
                "price_research": {"tavily_answer": "Research unavailable.", "sources": []},
                "reputation_research": {"tavily_answer": "Research unavailable.", "sources": []},
            }

        return {
            "ad_id": str(ad["id"]),
            "brand": ad["brand"],
            "model": ad["model"],
            "year": ad["year"],
            "reliability_research": reliability,
            "price_research": price,
            "reputation_research": reputation,
        }
