import asyncio
from typing import AsyncGenerator

from app.schemas.request import CompareRequest
from app.db.queries import fetch_ads_for_comparison
from app.pipeline.analyzer import analyze_car
from app.pipeline.comparator import compare
from app.pipeline.report_builder import build_report


async def run(request: CompareRequest, app_state) -> AsyncGenerator[dict, None]:
    cache_key = frozenset(request.ad_ids)
    if cache_key in app_state.report_cache:
        cached = app_state.report_cache[cache_key]
        yield {"type": "report", "content": cached}
        yield {"type": "done", "content": None}
        return

    pool = app_state.pool
    llm = app_state.llm
    tavily = app_state.tavily

    # Stage 1: Fetch ads
    yield {"type": "status", "content": "Loading car details..."}
    try:
        ads = await fetch_ads_for_comparison(pool, request.ad_ids)
    except ValueError as e:
        yield {"type": "error", "content": str(e)}
        yield {"type": "done", "content": None}
        return

    # Stage 2: Concurrent Tavily research
    research_tasks = []
    for ad in ads:
        yield {"type": "status", "content": f"Researching {ad['brand']} {ad['model']}..."}
        research_tasks.append(tavily.research_car(ad))

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

    # Stage 3: Sequential LLM analysis per car
    car_analyses = []
    for i, (ad, research) in enumerate(zip(ads, processed_results)):
        yield {"type": "status", "content": f"Analyzing {ad['brand']} {ad['model']}..."}
        try:
            analysis = await analyze_car(ad, research, llm, request.language)
            car_analyses.append(analysis)
        except ValueError:
            yield {"type": "error", "content": f"Analysis failed for {ad['brand']} {ad['model']}. Please try again."}
            yield {"type": "done", "content": None}
            return

        yield {
            "type": "progress",
            "content": {
                "current": i + 1,
                "total": len(ads),
                "label": f"{ad['brand']} {ad['model']} analyzed",
            },
        }

    # Stage 4: Single LLM comparison call
    yield {"type": "status", "content": "Writing final verdict..."}
    try:
        comparison_result = await compare(car_analyses, llm, request.language)
    except ValueError:
        yield {"type": "error", "content": "Comparison analysis failed. Please try again."}
        yield {"type": "done", "content": None}
        return

    # Stage 5: Assemble report
    report = build_report(ads, car_analyses, comparison_result, processed_results)

    # Cache the report
    app_state.report_cache[cache_key] = report
    if len(app_state.report_cache) >= 50:
        oldest_key = next(iter(app_state.report_cache))
        del app_state.report_cache[oldest_key]

    yield {"type": "report", "content": report}
    yield {"type": "done", "content": None}
