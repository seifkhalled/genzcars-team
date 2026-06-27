import json
from langchain_core.messages import SystemMessage, HumanMessage

ANALYZE_SYSTEM = """You are an expert automotive analyst specializing in the Egyptian car market.
Analyze the following car listing using both the listing data and web research
provided. Be objective, data-driven, and specific to the Egyptian market context.

You must return ONLY a valid JSON object — no explanation, no markdown, no extra text.
"""

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

WEB RESEARCH RESULTS:

Reliability & Common Problems:
{reliability_answer}
Sources: {reliability_sources}

Market Price & Resale Value:
{price_answer}
Sources: {price_sources}

Owner Reviews & Reputation:
{reputation_answer}
Sources: {reputation_sources}

{language_instruction}Analyze this car and return this exact JSON structure:
{{
  "ad_id": "{ad_id}",
  "brand": "{brand}",
  "model": "{model}",
  "year": {year},
  "price": {price},
  "cover_image_url": "{cover_image_url}",

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
    sources = research.get("sources", [])
    if not sources:
        return "No sources available."
    lines = []
    for s in sources[:3]:
        title = s.get("title", "Untitled")
        content = s.get("content", "")
        lines.append(f"- {title}: {content[:200]}")
    return "\n".join(lines)


async def analyze_car(ad: dict, research: dict, llm, language: str = "en") -> dict:
    lang_instr = ""
    if language == "ar":
        lang_instr = "Respond in Arabic. All text fields in the JSON must be in Arabic.\n\n"

    reliability_research = research.get("reliability_research", {})
    price_research = research.get("price_research", {})
    reputation_research = research.get("reputation_research", {})

    human_msg = ANALYZE_HUMAN_TEMPLATE.format(
        ad_id=ad.get("id", ""),
        brand=ad.get("brand", ""),
        model=ad.get("model", ""),
        year=ad.get("year", ""),
        price=ad.get("price", 0),
        cover_image_url=ad.get("cover_image_url", ""),
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
        language_instruction=lang_instr,
    )

    return await _parse_llm_json(llm, ANALYZE_SYSTEM, human_msg)


async def _parse_llm_json(llm, system: str, human: str) -> dict:
    response = await llm.ainvoke([
        SystemMessage(content=system),
        HumanMessage(content=human),
    ])
    content = response.content.strip()

    try:
        cleaned = content.removeprefix("```json").removesuffix("```").strip()
        return json.loads(cleaned)
    except (json.JSONDecodeError, AttributeError):
        pass

    retry_response = await llm.ainvoke([
        SystemMessage(content=system + "\nYour previous response was not valid JSON. Return ONLY the JSON object, nothing else."),
        HumanMessage(content=human),
    ])
    retry_content = retry_response.content.strip()
    try:
        cleaned = retry_content.removeprefix("```json").removesuffix("```").strip()
        return json.loads(cleaned)
    except (json.JSONDecodeError, AttributeError):
        raise ValueError("LLM failed to return valid JSON after retry")
