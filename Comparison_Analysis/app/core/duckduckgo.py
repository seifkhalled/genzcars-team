import asyncio
import logging
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)


class DuckDuckGoSearch:

    def search(self, query: str, max_results: int = 5) -> str:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                if not results:
                    return ""
                lines = []
                for r in results:
                    title = r.get("title", "")
                    body = r.get("body", "")
                    url = r.get("href", "")
                    if title and body:
                        lines.append(f"- {title}: {body} ({url})")
                    elif body:
                        lines.append(f"- {body}")
                return "\n".join(lines[:max_results])
        except Exception as e:
            logger.warning("DuckDuckGo search failed for query '%s': %s", query, e)
            return ""

    async def search_prices(self, make: str, model: str, year: int) -> list[dict]:
        queries = [
            f'"{make}" "{model}" "{year}" price EGP Egypt',
            f'{make} {model} {year} سعر مصر جنيه',
            f'"{make} {model} {year}" سيارة للبيع مصر',
            f'site:olx.com.eg "{make}" "{model}" "{year}"',
            f'site:contactcars.com "{make}" "{model}" "{year}"',
            f'site:hatla2ee.com "{make}" "{model}" "{year}"',
            f'site:dubizzle.com.eg "{make}" "{model}" "{year}"',
            f'site:sayaraa.com "{make}" "{model}" "{year}"',
            f'{make} {model} {year} official price Egypt EGP',
            f'{make} {model} {year} average market price Egypt',
            f'site:hatla2ee.com "{make}" "{model}" new price',
        ]

        loop = asyncio.get_running_loop()

        async def _run(q: str) -> dict:
            snippets = await loop.run_in_executor(None, self.search, q, 8)
            return {"query": q, "snippets": snippets}

        results = await asyncio.gather(*[_run(q) for q in queries])
        return results

    async def research_car(self, ad: dict) -> dict:
        brand = ad.get("brand", "")
        model = ad.get("model", "")
        year = ad.get("year", "")

        reliability_queries = [
            f"{brand} {model} {year} reliability common problems Egypt",
            f"{brand} {model} {year} مشاكل شائعة مصر",
            f"{brand} {model} {year} أعطال مصر",
        ]
        price_queries = [
            f"site:olx.com.eg {brand} {model} {year}",
            f"site:contactcars.com {brand} {model} {year}",
            f"site:hatla2ee.com {brand} {model}",
            f"site:dubizzle.com.eg {brand} {model} {year}",
            f"site:sayaraa.com {brand} {model} {year}",
            f"{brand} {model} {year} سعر مستعمل مصر",
        ]
        reputation_queries = [
            f"{brand} {model} owner review Egypt",
            f"{brand} {model} تجربة مالك مصر",
            f"{brand} {model} مراجعة مصر",
        ]

        loop = asyncio.get_running_loop()

        async def _search_all(queries: list[str], max_per_query: int = 5) -> str:
            async def _run(q: str) -> str:
                return await loop.run_in_executor(None, self.search, q, max_per_query)
            results = await asyncio.gather(*[_run(q) for q in queries])
            return "\n".join(r for r in results if r)

        snippets = await asyncio.gather(
            _search_all(reliability_queries),
            _search_all(price_queries),
            _search_all(reputation_queries),
        )

        return {
            "reliability_snippets": snippets[0],
            "price_snippets": snippets[1],
            "reputation_snippets": snippets[2],
        }
