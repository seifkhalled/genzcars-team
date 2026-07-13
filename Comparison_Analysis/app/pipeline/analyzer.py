import asyncio
import json
import logging
import time
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.ai_metrics import (
    llm_calls_total, llm_tokens_total, llm_latency_seconds, llm_cost_total,
    llm_fallback_total,
    add_tokens,
)

logger = logging.getLogger(__name__)

ANALYZE_SYSTEM = """You are an expert automotive analyst specializing in the Egyptian car market.
Analyze the following car listing using both the listing data and web research
provided. Be objective, data-driven, and specific to the Egyptian market context.

CRITICAL RULES:
1. If live market price data is provided, use it to assess whether this car is overpriced, fair, or a bargain. A car priced above the market average should have a lower value_for_money score.
2. Be honest about cons — do not sugarcoat issues. If research mentions problems, list them as cons.
IMPORTANT - REASONING SUPPRESSION: Do NOT include any reasoning, explanation, or thinking text. Output ONLY the raw JSON object.
You must return ONLY a valid JSON object — no explanation, no markdown, no extra text.
"""

VISION_ONLY_SYSTEM = """You are an expert automotive visual inspector.
Analyze the provided car images and assess the vehicle's visible condition.

For EACH image, examine:
1. EXTERIOR: Paint condition (scratches, dents, rust, panel gaps, accident indicators)
2. WHEELS & TIRES: Condition, curb rash, tire tread depth appearance
3. LIGHTS: Headlights, tail lights for cracks or fogging
4. INTERIOR: Seat condition, dashboard wear, steering wheel wear, cleanliness
5. GLASS: Windshield cracks or chips

Return ONLY valid JSON using this schema:
{
  "photo_analysis": "2-3 sentences describing the exterior condition, visible damage, tire wear, cleanliness, any visual red flags",
  "visual_issues": ["specific visible issue"],
  "overall_visual_condition": "excellent | good | fair | poor | unknown"
}

HARD RULES:
- If no images are visible or image quality is insufficient, set overall_visual_condition to "unknown" and explain why.
- Never guess about mechanical condition from images alone.
- Return ONLY valid JSON — no explanation, no markdown, no extra text."""

VISION_ONLY_HUMAN = """Analyze these images of a {brand} {model} {year}.
Focus on visible cosmetic condition, potential accident damage, interior wear, and overall care."""

ANALYZE_HUMAN_TEMPLATE = """CAR LISTING DATA:
Brand: {brand}
Model: {model}
Year: {year}
Price: {price} EGP
Condition: {condition}
KM Driven: {km_driven}
Fuel Type: {fuel_type}
Transmission: {transmission}
Body Type: {body_type}
City: {city}
CC Range: {cc_range}
Special Conditions: {special_conditions}
Description: {description}

TAVILY WEB RESEARCH:

Reliability & Common Problems:
{reliability_answer}
Sources: {reliability_sources}

Market Price & Resale Value:
{price_answer}
Sources: {price_sources}

Owner Reviews & Reputation:
{reputation_answer}
Sources: {reputation_sources}

DUCKDUCKGO RESEARCH (Egypt car sites):

Reliability & Common Problems:
{duckduckgo_reliability}

Market Price Listings:
{duckduckgo_price}

Owner Reviews:
{duckduckgo_reputation}

LIVE MARKET PRICE DATA:
{market_price_data}

{language_instruction}Analyze this car and return this exact JSON structure:
{{
  "ad_id": "{ad_id}",
  "brand": "{brand}",
  "model": "{model}",
  "year": {year},
  "price": {price},
  "condition": "{condition}",
  "pros": [
    "specific pro based on data",
    "specific pro based on data",
    "specific pro based on data"
  ],
  "cons": [
    "specific con based on data",
    "specific con based on data",
    "specific con based on data"
  ],

  "scores": {{
    "value_for_money": 0-10,
    "reliability": 0-10,
    "running_cost": 0-10,
    "resale_value": 0-10,
    "overall": 0-10
  }},

  "market_context": "2-3 sentences on how this car's price compares to market, whether it's overpriced/fair/bargain",
  "reliability_summary": "2-3 sentences on known issues and reliability track record for this model/year",
  "best_for": "1 sentence — who is this car ideal for (family, single, business, daily commute, etc.)",
  "red_flags": ["any serious issues to watch out for based on research, or empty array if none"],
  "spare_parts_availability": "good | fair | poor",
  "service_centers_egypt": "good | fair | poor"
}}
"""


def _sources_text(research: dict) -> str:
    sources = research.get("results", [])
    if not sources:
        return "No sources available."
    lines = []
    for s in sources[:2]:
        title = s.get("title", "Untitled")
        content = s.get("content", "")
        lines.append(f"- {title}: {content[:120]}")
    return "\n".join(lines)


def _build_prompt(ad: dict, research: dict, language: str, market_price: dict = None) -> str:
    lang_instr = ""
    if language == "ar":
        lang_instr = "Respond in Arabic. All text fields in the JSON must be in Arabic.\n\n"

    reliability_research = research.get("reliability_research", {})
    price_research = research.get("price_research", {})
    reputation_research = research.get("reputation_research", {})
    duckduckgo = research.get("duckduckgo", {})

    mp = market_price or {}
    if mp and mp.get("estimated_range", {}).get("high", 0) > 0:
        market_price_data = (
            f"Market range: {mp['estimated_range']['low']:,.0f} - {mp['estimated_range']['high']:,.0f} EGP\n"
            f"Average: {mp['estimated_range']['average']:,.0f} EGP\n"
            f"Median: {mp.get('median', 0):,.0f} EGP\n"
            f"Sample size: {mp.get('sample_count', 0)} listings\n"
            f"Confidence: {mp.get('confidence', 'unknown')}\n"
            f"This car is listed at {ad.get('price', 0):,.0f} EGP."
        )
    else:
        market_price_data = "No live market price data available for this car."

    return ANALYZE_HUMAN_TEMPLATE.format(
        ad_id=ad.get("id", ""),
        brand=ad.get("brand", ""),
        model=ad.get("model", ""),
        year=ad.get("year", ""),
        price=ad.get("price", 0),
        condition=ad.get("condition", ""),
        km_driven=ad.get("km_driven", ""),
        fuel_type=ad.get("fuel_type", ""),
        transmission=ad.get("transmission", ""),
        body_type=ad.get("body_type", ""),
        city=ad.get("city", ""),
        cc_range=ad.get("cc_range", ""),
        special_conditions=ad.get("special_conditions", ""),
        description=ad.get("description", ""),
        reliability_answer=reliability_research.get("tavily_answer", "Research unavailable."),
        reliability_sources=_sources_text(reliability_research),
        price_answer=price_research.get("tavily_answer", "Research unavailable."),
        price_sources=_sources_text(price_research),
        reputation_answer=reputation_research.get("tavily_answer", "Research unavailable."),
        reputation_sources=_sources_text(reputation_research),
        duckduckgo_reliability=duckduckgo.get("reliability_snippets", "No DuckDuckGo results."),
        duckduckgo_price=duckduckgo.get("price_snippets", "No DuckDuckGo results."),
        duckduckgo_reputation=duckduckgo.get("reputation_snippets", "No DuckDuckGo results."),
        market_price_data=market_price_data,
        language_instruction=lang_instr,
    )


def _build_vision_prompt(ad: dict) -> str:
    return VISION_ONLY_HUMAN.format(
        brand=ad.get("brand", "Unknown"),
        model=ad.get("model", "Unknown"),
        year=ad.get("year", ""),
    )


def _get_llm_provider(llm) -> str:
    return getattr(llm, "_llm_type", None) or llm.__class__.__name__.lower().replace("chat", "").replace("groq", "groq")


async def _parse_llm_json(llm, system: str, human: str, task_type: str = "unknown") -> dict:
    def _ensure_dict(result):
        if isinstance(result, dict):
            return result
        if isinstance(result, list) and len(result) == 1 and isinstance(result[0], dict):
            return result[0]
        raise ValueError(f"Expected dict, got {type(result).__name__}")

    provider = _get_llm_provider(llm)

    start = time.monotonic()
    response = await llm.ainvoke([
        SystemMessage(content=system),
        HumanMessage(content=human),
    ])
    duration = time.monotonic() - start
    content = response.content.strip()

    usage = getattr(response, "usage_metadata", None) or {}
    prompt_tokens = usage.get("input_tokens", 0) or 0
    completion_tokens = usage.get("output_tokens", 0) or 0

    llm_calls_total.labels(service="comparison_analysis", provider=provider, model="", task_type=task_type).inc()
    llm_tokens_total.labels(service="comparison_analysis", provider=provider, type="prompt").inc(prompt_tokens)
    llm_tokens_total.labels(service="comparison_analysis", provider=provider, type="completion").inc(completion_tokens)
    llm_latency_seconds.labels(service="comparison_analysis", provider=provider, model="", task_type=task_type).observe(duration)
    add_tokens(prompt_tokens, completion_tokens)

    try:
        cleaned = _clean_json(content)
        return _ensure_dict(json.loads(cleaned))
    except (json.JSONDecodeError, ValueError, AttributeError) as e:
        logger.warning("First LLM attempt failed: %s | preview: %s", e, content[:200])

    retry_response = await llm.ainvoke([
        SystemMessage(content=system + "\nCRITICAL: Your previous response contained NO JSON at all. You MUST output ONLY a raw JSON object. Start with { and end with }. NO reasoning, NO explanation, NO markdown, NO text before or after."),
        HumanMessage(content=human),
    ])
    retry_content = retry_response.content.strip()
    retry_usage = getattr(retry_response, "usage_metadata", None) or {}
    retry_prompt = retry_usage.get("input_tokens", 0) or 0
    retry_completion = retry_usage.get("output_tokens", 0) or 0
    add_tokens(retry_prompt, retry_completion)
    try:
        cleaned = _clean_json(retry_content)
        return _ensure_dict(json.loads(cleaned))
    except (json.JSONDecodeError, ValueError, AttributeError) as e:
        logger.error("Second LLM attempt also failed: %s | content: %s", e, retry_content[:500])
        raise ValueError("LLM failed to return valid JSON after retry")


async def _parse_vision_json(ad: dict, llm, fallback_llm=None) -> dict:
    human = _build_vision_prompt(ad)
    image_url = ad.get("cover_image_url") or None

    if not image_url:
        return {
            "photo_analysis": "No images available to analyze.",
            "visual_issues": [],
            "overall_visual_condition": "unknown",
        }

    content = [
        {"type": "text", "text": human},
        {"type": "image_url", "image_url": {"url": image_url, "detail": "high"}},
    ]

    models_to_try = [("primary", llm)]
    if fallback_llm:
        models_to_try.append(("fallback", fallback_llm))

    for label, model in models_to_try:
        try:
            provider = _get_llm_provider(model)

            start = time.monotonic()
            response = await model.ainvoke([
                SystemMessage(content=VISION_ONLY_SYSTEM),
                HumanMessage(content=content),
            ])
            duration = time.monotonic() - start
            raw = response.content.strip()

            usage = getattr(response, "usage_metadata", None) or {}
            prompt_tokens = usage.get("input_tokens", 0) or 0
            completion_tokens = usage.get("output_tokens", 0) or 0

            llm_calls_total.labels(service="comparison_analysis", provider=provider, model="", task_type="vision_analysis").inc()
            llm_tokens_total.labels(service="comparison_analysis", provider=provider, type="prompt").inc(prompt_tokens)
            llm_tokens_total.labels(service="comparison_analysis", provider=provider, type="completion").inc(completion_tokens)
            llm_latency_seconds.labels(service="comparison_analysis", provider=provider, model="", task_type="vision_analysis").observe(duration)
            add_tokens(prompt_tokens, completion_tokens)

            cleaned = _clean_json(raw)
            result = json.loads(cleaned)
            if not isinstance(result, dict):
                raise ValueError(f"Expected dict, got {type(result).__name__}")
            logger.info("Vision analysis complete for %s %s via %s", ad.get("brand"), ad.get("model"), label)
            return result

        except Exception as e:
            logger.warning("%s vision model failed for %s %s (%s: %s)", label, ad.get("brand"), ad.get("model"), type(e).__name__, e)
            if label == "primary" and fallback_llm:
                llm_fallback_total.labels(service="comparison_analysis", task_type="vision_analysis", from_provider=provider, to_provider="vision_fallback").inc()
            continue

    logger.error("All vision models failed for %s %s", ad.get("brand"), ad.get("model"))
    return {
        "photo_analysis": "Vision analysis unavailable.",
        "visual_issues": [],
        "overall_visual_condition": "unknown",
    }


def _combine_analyses(vision_result: dict, text_result: dict, market_price: dict = None) -> dict:
    merged = dict(text_result)
    merged["photo_analysis"] = vision_result.get("photo_analysis", "No photo analysis available.")
    merged["market_price"] = market_price or {}

    visual_condition = vision_result.get("overall_visual_condition", "unknown")
    visual_issues = vision_result.get("visual_issues", [])

    if visual_condition in ("poor", "fair"):
        scores = dict(merged.get("scores", {}))
        current_overall = scores.get("overall", 5)
        penalty = 3 if visual_condition == "poor" else 1
        scores["overall"] = max(1, current_overall - penalty)
        merged["scores"] = scores

        existing_flags = list(merged.get("red_flags", []))
        for issue in visual_issues:
            if issue not in existing_flags:
                existing_flags.append(issue)
        condition_flag = f"Visual inspection: {visual_condition} condition"
        if condition_flag not in existing_flags:
            existing_flags.append(condition_flag)
        merged["red_flags"] = existing_flags

    merged["visual_issues"] = visual_issues
    merged["overall_visual_condition"] = visual_condition
    return merged


def _clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text[3:]
    if text.startswith("json"):
        text = text[4:]
    text = text.strip()
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    if not text:
        return text

    decoder = json.JSONDecoder()
    candidates = []
    positions = [i for i, ch in enumerate(text) if ch in ("{", "[")]
    for start in positions:
        try:
            obj, end = decoder.raw_decode(text, start)
            priority = 2 if text[start] == "{" else 1
            candidates.append((priority, end - start, text[start:end]))
        except json.JSONDecodeError:
            continue

    if candidates:
        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return candidates[0][2]

    return text.strip()


async def analyze_car(ad: dict, research: dict, primary_llm, fallback_llm, fallback_llm2=None, fallback_llm3=None, vision_llm=None, vision_fallback_llm=None, language: str = "en", market_price: dict = None) -> dict:
    text_task = _analyze_text(ad, research, primary_llm, fallback_llm, fallback_llm2, fallback_llm3, language, market_price)
    vision_task = _analyze_vision(ad, vision_llm, vision_fallback_llm)

    text_result, vision_result = await asyncio.gather(text_task, vision_task, return_exceptions=True)

    if isinstance(text_result, Exception):
        logger.error("Text analysis failed for %s %s: %s", ad.get("brand"), ad.get("model"), text_result)
        raise ValueError(f"Text analysis failed: {text_result}")

    if isinstance(vision_result, Exception):
        logger.warning("Vision analysis failed for %s %s, continuing without photo analysis: %s", ad.get("brand"), ad.get("model"), vision_result)
        vision_result = {
            "photo_analysis": "Vision analysis unavailable.",
            "visual_issues": [],
            "overall_visual_condition": "unknown",
        }

    result = _combine_analyses(vision_result, text_result, market_price)
    result["cover_image_url"] = ad.get("cover_image_url", "")
    return result


async def _analyze_text(ad: dict, research: dict, primary_llm, fallback_llm, fallback_llm2=None, fallback_llm3=None, language: str = "en", market_price: dict = None) -> dict:
    human_msg = _build_prompt(ad, research, language, market_price)

    try:
        logger.info("Attempting OpenRouter text analysis for %s %s", ad.get("brand"), ad.get("model"))
        return await _parse_llm_json(primary_llm, ANALYZE_SYSTEM, human_msg, task_type="car_analysis")
    except Exception as e:
        logger.warning("OpenRouter failed (%s: %s), falling back to Groq for %s %s", type(e).__name__, e, ad.get("brand"), ad.get("model"))
        llm_fallback_total.labels(service="comparison_analysis", task_type="car_analysis", from_provider="openrouter", to_provider="groq").inc()
        try:
            return await _parse_llm_json(fallback_llm, ANALYZE_SYSTEM, human_msg, task_type="car_analysis")
        except Exception as e2:
            if fallback_llm2:
                logger.warning("Primary Groq failed (%s: %s), falling back to secondary Groq for %s %s", type(e2).__name__, e2, ad.get("brand"), ad.get("model"))
                llm_fallback_total.labels(service="comparison_analysis", task_type="car_analysis", from_provider="groq", to_provider="groq_fallback").inc()
                try:
                    return await _parse_llm_json(fallback_llm2, ANALYZE_SYSTEM, human_msg, task_type="car_analysis")
                except Exception as e3:
                    if fallback_llm3:
                        logger.warning("Secondary Groq failed (%s: %s), falling back to tertiary Groq for %s %s", type(e3).__name__, e3, ad.get("brand"), ad.get("model"))
                        llm_fallback_total.labels(service="comparison_analysis", task_type="car_analysis", from_provider="groq_fallback", to_provider="groq_fallback2").inc()
                        return await _parse_llm_json(fallback_llm3, ANALYZE_SYSTEM, human_msg, task_type="car_analysis")
                    raise
            raise


async def _analyze_vision(ad: dict, vision_llm, vision_fallback_llm=None) -> dict:
    if not vision_llm:
        logger.info("No vision LLM configured, skipping vision analysis for %s %s", ad.get("brand"), ad.get("model"))
        return {
            "photo_analysis": "Vision analysis not configured.",
            "visual_issues": [],
            "overall_visual_condition": "unknown",
        }

    logger.info("Running vision analysis for %s %s", ad.get("brand"), ad.get("model"))
    return await _parse_vision_json(ad, vision_llm, vision_fallback_llm)
