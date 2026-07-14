import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from app.enums import TaskType, NodeName
from app.graph.state import CarsChatState
from app.data.brand_origins import format_brand_origins_prompt

logger = logging.getLogger(__name__)

EXTRACT_CATALOGUE_SYSTEM = """You are a catalogue checker for a car marketplace.
Analyze the user's message and accumulated preferences to determine if they
are asking about a specific car (make, model, year) or doing a general search.

If the user names a SPECIFIC brand and/or model and/or year (e.g., "BMW 318",
"Toyota Corolla 2020", "show me BMWs", "Mercedes E-Class 2018"), extract those
as exact metadata filters.

If the user asks BROADLY ("find me cars", "show me some cars",
"cheap automatic"), set exact_request to null — this is a general
semantic search, not a catalogue lookup.

CRITICAL: Use conversation history to resolve pronouns and references.
If the user says "one", "it", "that", "this car", or similar references,
look at the conversation history to determine what they are referring to.
For example, if they previously mentioned "Mercedes" and now say
"recommend one", "one" refers to a Mercedes.

CRITICAL: When the user mentions a car origin/country/nationality
(e.g., "American car", "Japanese car", "German car", "Korean car",
"European car", "Italian car", "British car"), you MUST expand it into
the actual brand names using this mapping:
{brand_origins_prompt}

For example:
- "American car" → brands: ["Ford", "Chevrolet", "Dodge", "Jeep", "GMC", "Cadillac", "Lincoln", "Tesla"]
- "Japanese car" → brands: ["Toyota", "Honda", "Nissan", "Mazda", "Suzuki", "Mitsubishi", "Subaru"]
- "German car" → brands: ["BMW", "Mercedes", "Audi", "Volkswagen", "Porsche", "Opel"]

NEVER leave brands empty when a nationality/origin is mentioned. Always expand
to the full list of brands for that origin.

Return ONLY valid JSON. No explanation, no markdown:
{{
  "exact_request": {{
    "brands": [],
    "model": null,
    "year": null,
    "body_type": null
  }} | null,
  "is_specific": true | false,
  "request_label": "short description of what user asked for"
}}

Conversation history:
{conversation_history}

User message: "{message}" """


def _clean_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.removeprefix("```json").removeprefix("```").strip()
        if text.endswith("```"):
            text = text.removesuffix("```").strip()
    return text


async def catalogue_node(state: CarsChatState, config: RunnableConfig) -> dict:
    multi_llm = config["configurable"].get("multi_llm")
    llm_fast = config["configurable"].get("llm_fast")
    pool = config["configurable"].get("db_pool")
    mcp_registry = config["configurable"].get("mcp_registry")

    last_message = state["messages"][-1].content if state.get("messages") else ""

    # Build conversation history for context
    history_msgs = []
    for m in state.get("messages", [])[-6:-1]:
        role = "user" if m.type == "human" else "assistant"
        history_msgs.append(f"{role}: {m.content}")
    conversation_history = "\n".join(history_msgs) if history_msgs else "No prior conversation."

    # Step 1: LLM extracts exact request
    messages = [
        SystemMessage(content=EXTRACT_CATALOGUE_SYSTEM.format(
            message=last_message,
            brand_origins_prompt=format_brand_origins_prompt(),
            conversation_history=conversation_history,
        )),
        HumanMessage(content=last_message),
    ]
    if multi_llm:
        response = await multi_llm.ainvoke_task(TaskType.CATALOGUE_CHECK, messages)
    else:
        response = await llm_fast.ainvoke(messages)

    try:
        parsed = json.loads(_clean_json(response.content))
    except (json.JSONDecodeError, AttributeError):
        parsed = {"exact_request": None, "is_specific": False, "request_label": ""}

    exact = parsed.get("exact_request")
    is_specific = parsed.get("is_specific", False)
    request_label = parsed.get("request_label", last_message)

    # Fallback: if the LLM didn't expand brands but accumulated preferences
    # already hold preferred_brands (e.g. "American car" was expanded by the
    # preference_extractor), use those so the catalogue check never misses a
    # user intent that the LLM failed to expand on this turn.
    if exact and not exact.get("brands"):
        state_brands = state.get("preferences", {}).get("preferred_brands")
        if state_brands and isinstance(state_brands, list):
            exact["brands"] = state_brands
            if not request_label or request_label == last_message:
                request_label = f"{', '.join(state_brands)} cars"

    # Step 2: If specific request, query via MCP or direct DB
    if is_specific and exact and (pool or mcp_registry):
        brands = exact.get("brands", [])
        model = exact.get("model")
        year = exact.get("year")
        body_type = exact.get("body_type")

        available_brands = []
        for brand in brands:
            result = None
            if mcp_registry:
                try:
                    result = await mcp_registry.call_tool("check_catalogue", {
                        "brand": brand, "model": model, "year": year, "body_type": body_type,
                    })
                except Exception as e:
                    logger.warning("MCP check_catalogue failed for %s, falling back: %s", brand, e)
            if not result and pool:
                from app.db.queries import check_catalogue_availability
                result = await check_catalogue_availability(
                    pool, brand=brand, model=model, year=year, body_type=body_type,
                )
            if result and result.get("count", 0) > 0:
                available_brands.append({
                    "brand": brand,
                    "count": result["count"],
                    "ads": result.get("ads", []),
                })

        if available_brands:
            # Found exact matches — write confirmed brands back to preferences
            # so the brand context survives to subsequent turns even when the
            # preference_extractor's fire-and-forget upsert hasn't completed.
            confirmed_brands = [b["brand"] for b in available_brands]
            updated_prefs = dict(state.get("preferences", {}))
            existing = updated_prefs.get("preferred_brands")
            if existing:
                merged = list(existing)
                for b in confirmed_brands:
                    if b not in merged:
                        merged.append(b)
                updated_prefs["preferred_brands"] = merged
            else:
                updated_prefs["preferred_brands"] = confirmed_brands
            return {
                "catalogue_check": {
                    "available": True,
                    "requested": request_label,
                    "available_brands": available_brands,
                },
                "preferences": updated_prefs,
                "next_node": NodeName.SEARCH,
            }
        else:
            # Not found — route to recommendation
            return {
                "catalogue_check": {
                    "available": False,
                    "requested": request_label,
                    "brands_searched": brands,
                    "model": model,
                    "year": year,
                    "body_type": body_type,
                },
                "next_node": NodeName.RECOMMENDATION,
            }

    # General search — route directly to search_node
    return {
        "catalogue_check": {
            "available": True,
            "requested": request_label,
            "available_brands": [],
        },
        "next_node": NodeName.SEARCH,
    }
