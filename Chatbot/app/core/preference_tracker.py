import json
from app.core.llm import GeminiClient

EXTRACT_PROMPT = """Extract car preference signals from this message. Return ONLY valid JSON, no extra text.
If no signal found for a field, use null. Never invent values not in the message.

Message: "{user_message}"
Current known preferences: {current_prefs_json}

Return JSON with these fields:
{
  "budget_min": null, "budget_max": null,
  "preferred_brands": [], "preferred_body_types": [],
  "preferred_fuel_types": [], "preferred_transmission": null,
  "preferred_cities": [], "max_km_driven": null,
  "year_min": null, "year_max": null, "use_case": null,
  "is_seller": false, "seller_car_brand": null,
  "seller_car_model": null, "seller_car_year": null,
  "seller_asking_price": null
}"""


async def extract_and_update(
    llm: GeminiClient,
    message: str,
    session: dict,
) -> dict:
    current_prefs = session.get("preferences", {})
    prompt = EXTRACT_PROMPT.format(
        user_message=message,
        current_prefs_json=json.dumps(current_prefs, ensure_ascii=False),
    )
    raw = await llm.classify_json(EXTRACT_PROMPT, message, json.dumps(current_prefs, ensure_ascii=False))
    try:
        extracted = json.loads(raw)
    except json.JSONDecodeError:
        return {}

    merged = dict(current_prefs)
    for key, val in extracted.items():
        if val is None:
            continue
        if isinstance(val, list):
            existing = merged.get(key, [])
            for item in val:
                if item not in existing:
                    existing.append(item)
            merged[key] = existing
        else:
            merged[key] = val

    return merged
