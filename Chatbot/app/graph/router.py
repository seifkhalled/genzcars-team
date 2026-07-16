import json
import logging
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from app.enums import NodeName, TaskType, ROUTABLE_NODES
from app.graph.state import CarsChatState

logger = logging.getLogger(__name__)


ROUTER_SYSTEM = """You are the routing brain of a car marketplace AI assistant.
Based on the FULL conversation history and the latest user message, decide which
specialist agent should handle this request. Use the conversation history to
determine the user's true intent — not just the literal words in the latest message.

Available agents and when to use each:
- catalogue_node: user wants to FIND, BROWSE, or GET LISTINGS for cars.
  This includes: asking for recommendations, mentioning a brand/model/budget,
  wanting to see cars, or any request that implies "show me cars" based on
  conversation context. If the user previously asked about BMWs and now says
  "send me one" or "show me", the intent is still catalogue_node — they want
  to see BMW listings.
  CRITICAL: Questions about what brands we HAVE/STOCK/OFFER/SELL — including
  nationality-based questions like "what American brands do you have?",
  "what German cars are available?", "do you have Japanese cars?" — are
  ALWAYS catalogue_node. The user wants to see available listings, not
  learn general car knowledge. Also route here when the user asks to
  recommend a car of any kind (by origin, budget, body type, etc.).
- advisor_node: user is asking about a SPECIFIC car already in the conversation
  or on the current page. Questions like "is this a good deal?", "what are the
  problems with this car?", "should I buy it?" when a car is in context.
- seller_node: user wants to SELL their car, price their car, or get listing
  advice. Only route here if the user's intent is clearly about selling or
  has stated "I want to sell". If they ask "offer me" or "send me offers" in
  a context where they've been asking about buying, route to catalogue_node.
- guide_node: user needs HELP USING the website itself — "how to" questions
  about website features (posting, filtering, comparing, contacting sellers).
  KEY DISTINCTION: If the user says "send me an ad" / "show me an ad" but the
  conversation history shows they are a BUYER (asking about cars, brands,
  recommendations), this is catalogue_node — they want to see a listing, not
  learn how to post one. Only route to guide_node for explicit "how to" questions
  about website mechanics.
- general_node: general car knowledge, reliability questions, maintenance advice,
  insurance, market trends, news, greetings, unclear intent, or anything that
  doesn't fit the above.

EXAMPLES:
- "recommend me an american car" → catalogue_node (wants to see listings)
- "what german brands do you have?" → catalogue_node (wants to browse available brands)
- "do you have any Japanese cars?" → catalogue_node (wants to see listings)
- "what's the best SUV under 500k?" → catalogue_node (wants to find cars)
- "show me Toyota Corolla" → catalogue_node (wants specific listing)
- "is the BMW 318 a reliable car?" → advisor_node (evaluating a specific car)
- "I want to sell my Honda Civic" → seller_node (selling intent)
- "how do I post an ad on the website?" → guide_node (website help)
- "what's the difference between gasoline and diesel?" → general_node (general knowledge)
- "hello" → general_node (greeting)

Conversation so far:
{message_history}

Current context:
- User has a car page open: {has_context}

Latest user message: "{latest_message}"

Respond with ONLY one of these exact strings:
catalogue_node | advisor_node | seller_node | guide_node | general_node
"""


async def router_node(state: CarsChatState, config: RunnableConfig) -> dict:
    multi_llm = config["configurable"].get("multi_llm")

    last_message = state["messages"][-1].content if state.get("messages") else ""

    # Build message history
    history_msgs = []
    for m in state.get("messages", []):
        role = "user" if m.type == "human" else "assistant"
        history_msgs.append(f"{role}: {m.content}")
    message_history = "\n".join(history_msgs) if history_msgs else "No prior conversation."

    if multi_llm:
        response = await multi_llm.ainvoke_task(TaskType.ROUTER, [
            SystemMessage(content=ROUTER_SYSTEM.format(
                message_history=message_history,
                has_context="yes" if state.get("context_ad_id") else "no",
                latest_message=last_message,
            )),
            HumanMessage(content=last_message),
        ])
    else:
        response = await config["configurable"]["llm_fast"].ainvoke([
            SystemMessage(content=ROUTER_SYSTEM.format(
                message_history=message_history,
                has_context="yes" if state.get("context_ad_id") else "no",
                latest_message=last_message,
            )),
            HumanMessage(content=last_message),
        ])

    raw = (response.content or "").strip()

    # Try parsing as JSON (some LLMs return {"next_node": "catalogue_node"})
    node_name = None
    if raw.startswith("{"):
        try:
            parsed = json.loads(raw)
            candidate = parsed.get("next_node", "")
            if isinstance(candidate, str):
                cand = candidate.strip().lower()
                if any(n.value == cand for n in ROUTABLE_NODES):
                    node_name = cand
        except json.JSONDecodeError:
            pass

    # Fallback: search for a routable node name anywhere in the response
    if not node_name:
        raw_lower = raw.lower()
        for n in ROUTABLE_NODES:
            if n.value in raw_lower:
                node_name = n.value
                break

    if not node_name:
        if raw:
            logger.warning(
                "Router LLM returned no routable intent (output=%r); defaulting to general_node",
                raw[:200],
            )
        node_name = NodeName.GENERAL

    intent_history = state.get("intent_history", []) + [node_name]

    result = {
        "next_node": node_name,
        "intent": node_name,
        "intent_history": intent_history,
        "node_response": "",
    }

    if node_name == NodeName.CATALOGUE:
        result["retrieved_ads"] = []
        result["similar_ads"] = []
        result["price_analysis"] = None
        result["catalogue_check"] = None
        result["recommendations"] = []

    return result
