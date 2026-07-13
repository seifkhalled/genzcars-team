import asyncio
import logging
import time
from typing import List
from openai import AsyncOpenAI

from app.config import settings
from app.core.ai_metrics import (
    llm_calls_total, llm_tokens_total, llm_latency_seconds, llm_cost_total,
)

logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

VISION_SYSTEM_PROMPT = """You are an expert automotive visual inspector.
Analyze the provided car images and assess the vehicle's condition.

For EACH image, examine:
1. EXTERIOR: Paint condition (scratches, dents, rust, panel gaps, accident indicators)
2. WHEELS & TIRES: Condition, curb rash, tire tread depth appearance
3. LIGHTS: Headlights, tail lights for cracks or fogging
4. INTERIOR: Seat condition, dashboard wear, steering wheel wear, cleanliness
5. GLASS: Windshield cracks or chips

Return ONLY valid JSON using this schema:
{
  "findings": [
    {
      "area": "exterior | interior | wheels | lights | glass",
      "observation": "description of what you see",
      "severity": "good | fair | poor | unknown",
      "confidence": "high | medium | low"
    }
  ],
  "overall_condition": "excellent | good | fair | poor | unknown",
  "cosmetic_issues": ["specific visible issue"],
  "accident_indicators": "yes | no | unknown",
  "accident_indicators_reason": "explanation or 'No visible signs of accidents'",
  "image_quality": "good | poor | no_images",
  "summary": "1-2 sentence overall visual assessment"
}

HARD RULES:
- If an area is not visible in any image, use "unknown" severity with "low" confidence.
- Never guess about mechanical condition from images alone.
- If image quality is insufficient, note it and use "unknown".
- Return "no_images" for image_quality if no images are provided."""

VISION_USER_TEMPLATE = """Analyze these images of a {brand} {model} {year} ({color}, {body_type}) with {km_driven} km driven.

The car is listed as condition: {condition}.

Focus on visible cosmetic condition, potential accident damage, interior wear, and overall care."""


async def analyze_car_images(
    ad: dict,
) -> dict:
    images: List[dict] = ad.get("images", [])
    cover_url = ad.get("cover_image_url")

    all_image_urls = []
    if cover_url:
        all_image_urls.append(cover_url)
    for img in images:
        url = img.get("url") or img.get("image_url")
        if url and url not in all_image_urls:
            all_image_urls.append(url)

    if not all_image_urls:
        logger.info("No images available for %s %s, skipping vision analysis", ad.get("brand"), ad.get("model"))
        return {
            "findings": [],
            "overall_condition": "unknown",
            "cosmetic_issues": [],
            "accident_indicators": "unknown",
            "accident_indicators_reason": "No images provided",
            "image_quality": "no_images",
            "summary": "No images available to analyze",
        }

    if not settings.openrouter_api_key:
        logger.warning("OpenRouter API key not set, skipping vision analysis")
        return {
            "findings": [],
            "overall_condition": "unknown",
            "cosmetic_issues": [],
            "accident_indicators": "unknown",
            "accident_indicators_reason": "Vision service not configured",
            "image_quality": "poor",
            "summary": "Vision analysis unavailable",
        }

    try:
        return await _call_vision_llm(ad, all_image_urls)
    except Exception as e:
        logger.exception("Vision analysis failed for %s %s", ad.get("brand"), ad.get("model"))
        return {
            "findings": [],
            "overall_condition": "unknown",
            "cosmetic_issues": [],
            "accident_indicators": "unknown",
            "accident_indicators_reason": f"Vision analysis error: {str(e)[:100]}",
            "image_quality": "poor",
            "summary": "Vision analysis encountered an error",
        }


async def _call_single_vision_model(ad: dict, model: str, content_parts: list) -> dict:
    client = AsyncOpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=settings.openrouter_api_key,
    )

    start = time.monotonic()
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": VISION_SYSTEM_PROMPT},
            {"role": "user", "content": content_parts},
        ],
        temperature=0.1,
        max_tokens=2048,
        extra_headers={
            "HTTP-Referer": "https://dealsegypt.com",
            "X-Title": "Deals Egypt",
        },
        extra_body={"reasoning": {"budget_tokens": 2048}},
    )
    duration = time.monotonic() - start

    usage = response.usage or {}
    prompt_tokens = usage.get("prompt_tokens", 0) or 0
    completion_tokens = usage.get("completion_tokens", 0) or 0
    model_used = response.model or model

    llm_calls_total.labels(service="backend", provider="openrouter", model=model_used, task_type="vision_analysis").inc()
    llm_tokens_total.labels(service="backend", provider="openrouter", type="prompt").inc(prompt_tokens)
    llm_tokens_total.labels(service="backend", provider="openrouter", type="completion").inc(completion_tokens)
    llm_latency_seconds.labels(service="backend", provider="openrouter", model=model_used, task_type="vision_analysis").observe(duration)

    content = response.choices[0].message.content.strip()
    cleaned = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    import json
    result = json.loads(cleaned)
    result["confidence"] = _compute_vision_confidence(result)
    logger.info(
        "Vision analysis complete for %s %s via %s (condition=%s, confidence=%.2f)",
        ad.get("brand"), ad.get("model"), model_used,
        result.get("overall_condition", "unknown"),
        result["confidence"],
    )
    return result


async def _call_vision_llm(ad: dict, image_urls: List[str]) -> dict:
    content_parts = [
        {
            "type": "text",
            "text": VISION_USER_TEMPLATE.format(
                brand=ad.get("brand", "Unknown"),
                model=ad.get("model", "Unknown"),
                year=ad.get("year", ""),
                color=ad.get("color", "Unknown"),
                body_type=ad.get("body_type", "Unknown"),
                km_driven=ad.get("km_driven", 0),
                condition=ad.get("condition", "Unknown"),
            ),
        }
    ]

    for url in image_urls[:5]:
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": url, "detail": "high"},
        })

    models_to_try = [
        (settings.openrouter_vision_model, "primary"),
    ]
    if settings.openrouter_vision_model_fallback:
        models_to_try.append((settings.openrouter_vision_model_fallback, "fallback"))

    import json

    for model, label in models_to_try:
        try:
            return await _call_single_vision_model(ad, model, content_parts)
        except json.JSONDecodeError:
            logger.warning("%s model %s returned invalid JSON", label, model)
            continue
        except Exception as e:
            logger.warning("%s model %s failed (%s: %s)", label, model, type(e).__name__, e)
            continue

    logger.error("All vision models failed for %s %s", ad.get("brand"), ad.get("model"))
    return {
        "findings": [],
        "overall_condition": "unknown",
        "cosmetic_issues": [],
        "accident_indicators": "unknown",
        "accident_indicators_reason": "All vision models failed",
        "image_quality": "poor",
        "summary": "Vision analysis unavailable",
        "confidence": 0.0,
    }


def _compute_vision_confidence(result: dict) -> float:
    findings = result.get("findings", [])
    if not findings:
        return 0.0

    confidence_map = {"high": 1.0, "medium": 0.6, "low": 0.2}
    scores = [confidence_map.get(f.get("confidence", "low"), 0.2) for f in findings]
    return round(sum(scores) / len(scores), 2)
