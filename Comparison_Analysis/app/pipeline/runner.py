import asyncio
import hashlib
from typing import AsyncGenerator

from app.schemas.request import CompareRequest
from app.db.queries import fetch_ads_for_comparison
from app.pipeline.analyzer import analyze_car
from app.pipeline.comparator import compare
from app.pipeline.report_builder import build_report
from app.core.ai_metrics import comparison_requests_total, comparison_errors_total, research_calls_total

CACHE_TTL = 3600


def _make_cache_key(request: CompareRequest) -> str:
    ids_key = hashlib.md5("_".join(sorted(request.ad_ids)).encode()).hexdigest()
    return f"compare:{ids_key}:{request.language}"


async def run(request: CompareRequest, app_state) -> AsyncGenerator[dict, None]:
    comparison_requests_total.labels(service="comparison_analysis").inc()
    cache_key = _make_cache_key(request)

    redis = getattr(app_state, "redis", None)
    if redis:
        cached = await redis.get_json(cache_key)
        if cached is not None:
            yield {"type": "report", "content": cached}
            yield {"type": "done", "content": None}
            return

    pool = app_state.pool
    openrouter_llm = app_state.llm
    groq_llm = app_state.groq_llm
    groq_fallback_llm = getattr(app_state, "groq_fallback_llm", groq_llm)
    tavily = app_state.tavily

    yield {"type": "status", "content": "Loading car details..."}
    try:
        ads = await fetch_ads_for_comparison(pool, request.ad_ids)
    except ValueError as e:
        comparison_errors_total.labels(service="comparison_analysis", error_type="invalid_ads").inc()
        yield {"type": "error", "content": str(e)}
        yield {"type": "done", "content": None}
        return

    research_tasks = []
    for ad in ads:
        yield {"type": "status", "content": f"Researching {ad['brand']} {ad['model']}..."}
        research_tasks.append(tavily.research_car(ad))

    research_calls_total.labels(service="comparison_analysis", provider="tavily").inc(len(research_tasks))
    research_results = await asyncio.gather(*research_tasks, return_exceptions=True)
    processed_results = []
    for r in research_results:
        if isinstance(r, Exception):
            processed_results.append({
                "ad_id": "",
                "brand": "",
                "model": "",
                "year": "",
                "reliability_research": {"tavily_answer": "Research unavailable.", "sources": []},
                "price_research": {"tavily_answer": "Research unavailable.", "sources": []},
                "reputation_research": {"tavily_answer": "Research unavailable.", "sources": []},
            })
        else:
            processed_results.append(r)

    yield {"type": "status", "content": f"Analyzing {len(ads)} cars..."}

    async def _analyze_one(ad: dict, research: dict) -> dict | None:
        try:
            return await analyze_car(ad, research, openrouter_llm, groq_llm, groq_fallback_llm, request.language)
        except Exception:
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
        comparison_result = await compare(car_analyses, openrouter_llm, groq_llm, groq_fallback_llm, request.language)
    except Exception:
        comparison_errors_total.labels(service="comparison_analysis", error_type="comparison_failed").inc()
        yield {"type": "error", "content": "Comparison analysis failed. Please try again."}
        yield {"type": "done", "content": None}
        return

    report = build_report(ads, car_analyses, comparison_result, processed_results)

    if redis:
        await redis.set_json(cache_key, report, ttl=CACHE_TTL)

    yield {"type": "report", "content": report}
    yield {"type": "done", "content": None}
