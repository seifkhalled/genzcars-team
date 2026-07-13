import asyncio
import hashlib
import logging
import time
from typing import AsyncGenerator

from app.schemas.request import CompareRequest
from app.db.queries import fetch_ads_for_comparison
from app.pipeline.analyzer import analyze_car
from app.pipeline.comparator import compare
from app.pipeline.report_builder import build_report
from app.core.ai_metrics import comparison_requests_total, comparison_errors_total, research_calls_total, get_and_reset_tokens
from app.routers.price_analysis import _compute_stats_from_listings, _generate_ai_summary

logger = logging.getLogger(__name__)
CACHE_TTL = 3600


def _make_cache_key(request: CompareRequest) -> str:
    ids_key = hashlib.md5("_".join(sorted(request.ad_ids)).encode()).hexdigest()
    return f"compare:{ids_key}:{request.language}"


async def run(request: CompareRequest, app_state) -> AsyncGenerator[dict, None]:
    comparison_requests_total.labels(service="comparison_analysis").inc()
    cache_key = _make_cache_key(request)
    _start_time = time.monotonic()

    redis = getattr(app_state, "redis", None)
    if redis:
        cached = await redis.get_json(cache_key)
        if cached is not None:
            yield {"type": "report", "content": cached}
            yield {"type": "done", "content": None}
            return

    pool = app_state.pool
    openrouter_llm = app_state.llm
    vision_llm = getattr(app_state, "vision_llm", None)
    vision_fallback_llm = getattr(app_state, "vision_fallback_llm", None)
    groq_llm = app_state.groq_llm
    groq_fallback_llm = getattr(app_state, "groq_fallback_llm", groq_llm)
    groq_fallback_llm2 = getattr(app_state, "groq_fallback_llm2", groq_fallback_llm)
    groq_fallback_llm3 = getattr(app_state, "groq_fallback_llm3", groq_fallback_llm2)
    tavily = app_state.tavily
    duckduckgo = getattr(app_state, "duckduckgo", None)

    yield {"type": "status", "content": "Loading car details..."}
    try:
        ads = await fetch_ads_for_comparison(pool, request.ad_ids)
    except ValueError as e:
        comparison_errors_total.labels(service="comparison_analysis", error_type="invalid_ads").inc()
        yield {"type": "error", "content": str(e)}
        yield {"type": "done", "content": None}
        return

    yield {"type": "status", "content": f"Researching {len(ads)} cars..."}

    async def _research_one(ad: dict) -> dict:
        tavily_result = None
        duckduckgo_result = None

        try:
            tavily_result = await tavily.research_car(ad)
        except Exception as e:
            logger.warning("Tavily research failed for %s %s: %s", ad.get("brand"), ad.get("model"), e)

        if duckduckgo:
            try:
                duckduckgo_result = await duckduckgo.research_car(ad)
            except Exception as e:
                logger.warning("DuckDuckGo research failed for %s %s: %s", ad.get("brand"), ad.get("model"), e)

        result = {
            "ad_id": str(ad.get("id", "")),
            "brand": ad.get("brand", ""),
            "model": ad.get("model", ""),
            "year": ad.get("year", ""),
            "reliability_research": {"tavily_answer": "Research unavailable.", "sources": []},
            "price_research": {"tavily_answer": "Research unavailable.", "sources": []},
            "reputation_research": {"tavily_answer": "Research unavailable.", "sources": []},
            "duckduckgo": {
                "reliability_snippets": "",
                "price_snippets": "",
                "reputation_snippets": "",
            },
        }

        if tavily_result and not isinstance(tavily_result, Exception):
            result["reliability_research"] = tavily_result.get("reliability_research", result["reliability_research"])
            result["price_research"] = tavily_result.get("price_research", result["price_research"])
            result["reputation_research"] = tavily_result.get("reputation_research", result["reputation_research"])

        if duckduckgo_result and not isinstance(duckduckgo_result, Exception):
            result["duckduckgo"] = {
                "reliability_snippets": duckduckgo_result.get("reliability_snippets", ""),
                "price_snippets": duckduckgo_result.get("price_snippets", ""),
                "reputation_snippets": duckduckgo_result.get("reputation_snippets", ""),
            }

        return result

    research_calls_total.labels(service="comparison_analysis", provider="tavily+duckduckgo").inc(len(ads))
    research_results = await asyncio.gather(*[_research_one(ad) for ad in ads], return_exceptions=True)

    processed_results = []
    for i, r in enumerate(research_results):
        if isinstance(r, Exception):
            ad = ads[i] if i < len(ads) else {}
            logger.error("Research failed for %s %s: %s", ad.get("brand"), ad.get("model"), r)
            processed_results.append({
                "ad_id": str(ad.get("id", "")),
                "brand": ad.get("brand", ""),
                "model": ad.get("model", ""),
                "year": ad.get("year", ""),
                "reliability_research": {"tavily_answer": "Research unavailable.", "sources": []},
                "price_research": {"tavily_answer": "Research unavailable.", "sources": []},
                "reputation_research": {"tavily_answer": "Research unavailable.", "sources": []},
                "duckduckgo": {
                    "reliability_snippets": "",
                    "price_snippets": "",
                    "reputation_snippets": "",
                },
            })
        else:
            processed_results.append(r)

    yield {"type": "status", "content": f"Fetching market prices for {len(ads)} cars..."}

    scraper = getattr(app_state, "scraper", None)
    market_prices = {}
    if scraper:
        async def _fetch_market_price(ad: dict) -> tuple[str, dict]:
            make = ad.get("brand", "").strip().lower()
            model = ad.get("model", "").strip().lower()
            year = ad.get("year", 0)
            key = f"{make}:{model}:{year}"
            try:
                listings = await scraper.scrape_car(make, model, year)
                if listings:
                    stats = _compute_stats_from_listings(listings)
                    if stats:
                        return key, stats
            except Exception as e:
                logger.warning("Market price fetch failed for %s %s %d: %s", make, model, year, e)
            return key, {}

        price_tasks = [_fetch_market_price(ad) for ad in ads]
        price_results = await asyncio.gather(*price_tasks)
        for key, stats in price_results:
            market_prices[key] = stats

    for r in processed_results:
        make = r.get("brand", "").strip().lower()
        model = r.get("model", "").strip().lower()
        year = r.get("year", 0)
        key = f"{make}:{model}:{year}"
        mp = market_prices.get(key, {})
        if mp and mp.get("estimated_range", {}).get("high", 0) > 0 and groq_llm:
            try:
                mp["summary"] = await _generate_ai_summary(groq_llm, mp, make, model, year)
            except Exception as e:
                logger.warning("AI price summary failed for %s %s: %s", make, model, e)
        r["market_price"] = mp

    yield {"type": "status", "content": f"Analyzing {len(ads)} cars..."}

    async def _analyze_one(ad: dict, research: dict) -> dict | None:
        try:
            return await analyze_car(
                ad, research,
                primary_llm=openrouter_llm,
                fallback_llm=groq_llm,
                fallback_llm2=groq_fallback_llm,
                fallback_llm3=groq_fallback_llm2,
                vision_llm=vision_llm,
                vision_fallback_llm=vision_fallback_llm,
                language=request.language,
                market_price=research.get("market_price", {}),
            )
        except Exception as e:
            logger.exception("Analysis failed for %s %s", ad.get("brand"), ad.get("model"))
            return None

    analysis_tasks = [_analyze_one(ad, research) for ad, research in zip(ads, processed_results)]
    results = await asyncio.gather(*analysis_tasks)

    car_analyses = []
    for i, (ad, result) in enumerate(zip(ads, results)):
        if result is None:
            comparison_errors_total.labels(service="comparison_analysis", error_type="analysis_failed").inc()
            yield {"type": "error", "content": f"Analysis failed for {ad['brand']} {ad['model']}."}
            yield {"type": "done", "content": None}
            return
        car_analyses.append(result)
        yield {
            "type": "progress",
            "content": {
                "current": i + 1,
                "total": len(ads),
                "label": f"{ad['brand']} {ad['model']} analyzed",
            },
        }

    yield {"type": "status", "content": "Writing final verdict..."}
    try:
        comparison_result = await compare(car_analyses, openrouter_llm, groq_llm, groq_fallback_llm, groq_fallback_llm2, language=request.language)
    except Exception as e:
        logger.exception("Comparison verdict failed: %s", e)
        comparison_errors_total.labels(service="comparison_analysis", error_type="comparison_failed").inc()
        yield {"type": "error", "content": "Comparison analysis failed. Please try again."}
        yield {"type": "done", "content": None}
        return

    report = build_report(ads, car_analyses, comparison_result, processed_results)

    tokens = get_and_reset_tokens()
    duration = time.monotonic() - _start_time
    logger.info(
        "Comparison completed — prompt_tokens=%d completion_tokens=%d total=%d duration=%.1fs",
        tokens["prompt"], tokens["completion"], tokens["prompt"] + tokens["completion"], duration,
    )

    if redis:
        await redis.set_json(cache_key, report, ttl=CACHE_TTL)

    yield {"type": "report", "content": report}
    yield {"type": "done", "content": None}