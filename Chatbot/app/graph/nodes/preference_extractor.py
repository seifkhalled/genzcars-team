import json
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from app.graph.state import CarsChatState
from app.data.brand_origins import format_brand_origins_prompt


EXTRACT_SYSTEM_PROMPT = """You are a preference extraction engine for a car marketplace.
Extract any car preference signals from the user message.
Merge with existing preferences — never clear a previously set value
unless the user explicitly contradicts it.
Return ONLY a valid JSON object. No explanation, no markdown, no extra text.

CRITICAL: When the user mentions a car origin/country (e.g., "German car",
"Japanese car", "American car", "European car", "Korean car", "Italian car"),
expand it to the actual brand names in preferred_brands using this mapping:
{brand_origins_prompt}

Existing preferences:
{current_preferences_json}

Extract these fields (use null if not mentioned, use existing value if not contradicted):
{{
  "budget_min": null,
  "budget_max": null,
  "preferred_brands": [],
  "preferred_body_types": [],
  "preferred_fuel_types": [],
  "preferred_transmission": null,
  "preferred_cities": [],
  "max_km_driven": null,
  "year_min": null,
  "year_max": null,
  "use_case": null,
  "is_seller": false,
  "seller_car_brand": null,
  "seller_car_model": null,
  "seller_car_year": null,
  "seller_asking_price": null,
  "seller_intent": null
}}"""


async def preference_extractor_node(state: CarsChatState, config: RunnableConfig) -> dict:
    llm_fast = config["configurable"].get("llm_fast")
    pool = config["configurable"].get("db_pool")

    if not state.get("messages"):
        return {}

    last_message = state["messages"][-1].content if state["messages"] else ""

    current_prefs = state.get("preferences", {})
    current_prefs_json = json.dumps(current_prefs, ensure_ascii=False, default=str)

    system_prompt = EXTRACT_SYSTEM_PROMPT.format(
        current_preferences_json=current_prefs_json,
        brand_origins_prompt=format_brand_origins_prompt(),
    )

    response = await llm_fast.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=last_message),
    ])

    try:
        extracted = json.loads(response.content.strip().removeprefix("```json").removesuffix("```").strip())
    except (json.JSONDecodeError, AttributeError):
        extracted = {}

    merged = dict(current_prefs)
    for key, val in extracted.items():
        if val is None:
            continue
        if isinstance(val, list):
            existing = merged.get(key, [])
            if not isinstance(existing, list):
                existing = []
            for item in val:
                if item not in existing:
                    existing.append(item)
            merged[key] = existing
        else:
            if key == "is_seller" and current_prefs.get("is_seller", False) and val is False:
                merged["is_seller"] = False
            elif key == "is_seller":
                merged["is_seller"] = True
            else:
                merged[key] = val

    updates = {
        "preferences": merged,
        "turn_count": state.get("turn_count", 0) + 1,
    }

    if pool:
        import asyncio
        from app.db.queries import upsert_user_preferences
        prefs_for_db = dict(merged)
        prefs_for_db["intent_history"] = state.get("intent_history", [])
        prefs_for_db["turn_count"] = state.get("turn_count", 0) + 1
        asyncio.ensure_future(
            upsert_user_preferences(
                pool,
                state["session_token"],
                state.get("user_id"),
                prefs_for_db,
            )
        )

    return updates
