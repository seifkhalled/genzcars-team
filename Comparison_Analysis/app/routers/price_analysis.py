import json
import logging
from urllib.parse import urlparse
from fastapi import APIRouter, Request
from pydantic import BaseModel

from langchain_core.messages import SystemMessage, HumanMessage

from app.config import settings
from app.core.duckduckgo import DuckDuckGoSearch

logger = logging.getLogger(__name__)
router = APIRouter(tags=["price-analysis"])

CAR_DOMAINS = {
    "olx.com.eg",
    "contactcars.com",
    "hatla2ee.com",
    "hatla2nee.com",
    "sayaraa.com",
    "dubizzle.com.eg",
    "yallamotor.com",
    "motory.com",
    "elmotor.com",
    "cars.egypt",
}

CAR_KEYWORDS = [
    "car", "cars", "سيارة", "سيارات", "automotive", "used car", "for sale", "معروض للبيع",
    "market price", "سعر السوق", "seller", "dealer", "وكيل", "توكيل",
    "engine", "motor", "محرك", "horsepower", "حصان", "transmission", "ناقل حركة",
    "mileage", "كيلومتر", "km", "condition", "حالة", "showroom", "صالة عرض",
    "warranty", "ضمان", "finance", "تقسيط", "loan", "قرض",
]


def _is_car_url(url: str) -> bool:
    try:
        domain = urlparse(url).hostname or ""
        domain = domain.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        for allowed in CAR_DOMAINS:
            if domain == allowed or domain.endswith("." + allowed):
                return True
        return False
    except Exception:
        return False


def _has_car_keywords(text: str) -> bool:
    text_lower = text.lower()
    for kw in CAR_KEYWORDS:
        if kw in text_lower:
            return True
    return False


def _filter_car_snippets(search_results: list[dict]) -> list[dict]:
    filtered = []
    for r in search_results:
        keep_lines = []
        for line in r.get("snippets", "").split("\n"):
            if not line.strip():
                continue
            url = ""
            if "(" in line and line.endswith(")"):
                url = line[line.rindex("(") + 1 : -1]
            domain_match = url and _is_car_url(url)
            keyword_match = _has_car_keywords(line)
            if domain_match or keyword_match:
                keep_lines.append(line)
        if keep_lines:
            filtered.append({"query": r["query"], "snippets": "\n".join(keep_lines)})
    return filtered


class PriceAnalysisRequest(BaseModel):
    make: str
    model: str
    year: int


PRICE_SYSTEM = """You are an expert automotive analyst for the Egyptian car market.
You will receive REAL scraped market data from Egyptian car listing websites.
Summarize the data in 2-3 sentences. Do NOT make up or estimate any prices.
Only describe what the data shows — price range, number of listings, condition (new/used).
Be concise and factual.
"""

PRICE_HUMAN_TEMPLATE = """Here is real scraped market data for a {year} {make} {model} in Egypt:

Number of listings found: {sample_count}
Price range: {low} to {high} EGP
Average price: {avg} EGP
Median price: {median} EGP

{sources_text}

Write a brief, factual 2-3 sentence summary of this market data."""

SUMMARY_ONLY_SYSTEM = """You are an automotive market analyst for the Egyptian car market.
Given real scraped price data, write a brief 2-3 sentence summary.
Be factual. Only describe what the data shows. Do NOT estimate or invent prices."""


def _compute_stats_from_listings(listings: list[dict]) -> dict:
    prices = []
    for ad in listings:
        p = ad.get("price")
        if p and isinstance(p, (int, float)) and p > 0:
            prices.append(float(p))

    if not prices:
        return {}

    prices.sort()
    count = len(prices)

    if count >= 3:
        median_before = prices[count // 2]
        filtered = [p for p in prices if median_before * 0.4 <= p <= median_before * 2.5]
        if len(filtered) >= 2:
            prices = filtered
            count = len(prices)

    avg = sum(prices) / count
    median = prices[count // 2]
    low = prices[0]
    high = prices[-1]

    if count >= 5:
        confidence = "high"
    elif count >= 2:
        confidence = "medium"
    else:
        confidence = "low"

    sources_list = []
    seen = set()
    for ad in listings:
        url = ad.get("url", "")
        source = ad.get("source", "unknown")
        title = ad.get("title", "") or f"{ad.get('make', '')} {ad.get('model', '')} {ad.get('year', '')}"
        key = url if url else f"{source}:{title}"
        if key not in seen:
            seen.add(key)
            sources_list.append({
                "title": title,
                "url": url,
                "source": source,
            })

    summary_parts = [f"Based on {count} real listing{'s' if count != 1 else ''}"]
    if count >= 2:
        summary_parts.append(f"from {len(sources_list)} source{'s' if len(sources_list) != 1 else ''}")
    summary_parts.append(f"prices range from {low:,.0f} to {high:,.0f} EGP")
    summary_parts.append(f"with an average of {avg:,.0f} EGP and median of {median:,.0f} EGP")

    return {
        "estimated_range": {
            "low": round(low),
            "high": round(high),
            "average": round(avg),
        },
        "median": round(median),
        "confidence": confidence,
        "sample_count": count,
        "summary": ". ".join(summary_parts) + ".",
        "sources": sources_list[:10],
    }


def _extract_sources(search_results: list[dict]) -> list[dict]:
    seen = set()
    sources = []
    for r in search_results:
        for line in r.get("snippets", "").split("\n"):
            if not line.strip():
                continue
            url = ""
            if "(" in line and line.endswith(")"):
                candidate = line[line.rindex("(") + 1 : -1]
                if candidate.startswith("http"):
                    url = candidate
            if url and url not in seen and _is_car_url(url):
                seen.add(url)
                title = line.split(":", 1)[0].lstrip("- ") if ":" in line else "Search result"
                sources.append({"title": title, "url": url})
            elif not url and _has_car_keywords(line):
                title = line.split(":", 1)[0].lstrip("- ") if ":" in line else line[:80]
                if title not in seen:
                    seen.add(title)
                    sources.append({"title": title, "url": ""})
    return sources[:15]


def _format_sources_text(sources: list[dict]) -> str:
    if not sources:
        return "Sources: (none with URLs)"
    lines = []
    for s in sources:
        if s.get("url"):
            lines.append(f"- {s['title']} ({s['source']}): {s['url']}")
        else:
            lines.append(f"- {s['title']} ({s['source']})")
    return "Sources:\n" + "\n".join(lines)


async def _generate_ai_summary(llm, stats: dict, make: str, model: str, year: int) -> str:
    if not llm:
        return stats.get("summary", "")

    sources_text = _format_sources_text(stats.get("sources", []))

    human_msg = PRICE_HUMAN_TEMPLATE.format(
        year=year,
        make=make.title(),
        model=model.title(),
        sample_count=stats["sample_count"],
        low=f"{stats['estimated_range']['low']:,.0f}",
        high=f"{stats['estimated_range']['high']:,.0f}",
        avg=f"{stats['estimated_range']['average']:,.0f}",
        median=f"{stats['median']:,.0f}",
        sources_text=sources_text,
    )

    try:
        response = await llm.ainvoke([
            SystemMessage(content=PRICE_SYSTEM),
            HumanMessage(content=human_msg),
        ])
        return response.content.strip()
    except Exception as e:
        logger.warning("AI summary generation failed: %s", e)
        return stats.get("summary", "")


@router.post("/price-analysis")
async def price_analysis(body: PriceAnalysisRequest, req: Request):
    make = body.make.strip().lower()
    model = body.model.strip().lower()
    year = body.year
    cache_key = f"price:{make}:{model}:{year}"

    redis = getattr(req.app.state, "redis", None)
    if redis:
        cached = await redis.get_json(cache_key)
        if cached is not None:
            return cached

    scraper = getattr(req.app.state, "scraper", None)
    llm = getattr(req.app.state, "groq_llm", None)

    # ── Path A: Live scraped market data (ONLY path) ──
    if scraper:
        try:
            listings = await scraper.scrape_car(make, model, year)
            if listings:
                stats = _compute_stats_from_listings(listings)
                if stats:
                    ai_summary = await _generate_ai_summary(llm, stats, make, model, year)

                    report = {
                        "make": body.make,
                        "model": body.model,
                        "year": year,
                        "estimated_range": stats["estimated_range"],
                        "median": stats["median"],
                        "confidence": stats["confidence"],
                        "summary": ai_summary,
                        "currency": "EGP",
                        "sample_count": stats["sample_count"],
                        "sources": stats["sources"],
                    }
                    if redis:
                        await redis.set_json(cache_key, report, ttl=3600)
                    return report
        except Exception as e:
            logger.warning("Scraper failed for %s %s %d: %s", make, model, year, e)

    # ── No scraper available or no results: return empty response ──
    report = {
        "make": body.make,
        "model": body.model,
        "year": year,
        "estimated_range": {"low": 0, "high": 0, "average": 0},
        "median": 0,
        "confidence": "none",
        "summary": f"No market data could be scraped for {year} {body.make} {body.model}.",
        "currency": "EGP",
        "sample_count": 0,
        "sources": [],
    }

    if redis:
        await redis.set_json(cache_key, report, ttl=300)

    return report
