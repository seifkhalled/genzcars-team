from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from app.graph.state import CarsChatState


TOPIC_DETECT_SYSTEM = """Classify the user's website help question into one of these topics:
post_ad | filter_search | save_car | compare | contact_seller |
delete_ad | edit_ad | view_favorites | account_settings | other

Respond with ONLY the topic string.
User message: "{message}"
"""

GUIDE_SYSTEM = """You are a friendly website guide for a car marketplace.
Help the user with their question about how to use the website.

Website features reference:
- Post Ad: top navigation bar → "Post Ad" button → fill car details → upload
  up to 10 photos → click Publish. Goes live immediately.
- Filter/Search: homepage left sidebar has filters (brand, price, city, fuel,
  body type, transmission, year range). Search bar accepts natural language.
- Save/Favorites: heart icon on any car card or ad page. View at Profile → Favorites.
- Compare: "Add to Compare" on up to 3 ads → comparison tray at page bottom →
  "Compare Now" → full AI report with pros/cons and final recommendation.
- Contact seller: phone number shown on every ad page below car details.
- Edit ad: Profile → My Ads → Edit button on the ad.
- Delete ad: Profile → My Ads → three-dot menu → Delete.
- Account settings: Profile → Settings (name, phone, avatar, password).

Detected topic: {detected_topic}
User message: "{message}"

Answer helpfully and concisely. If the question is about a feature not listed
above, be honest that you are not sure and suggest they contact support.
Always respond in the same language as the user (Arabic or English).
"""


async def guide_node(state: CarsChatState, config: RunnableConfig) -> dict:
    llm_fast = config["configurable"]["llm_fast"]
    llm_stream = config["configurable"]["llm_stream"]

    last_message = state["messages"][-1].content if state.get("messages") else ""

    # Step 1: Topic detection
    topic_response = await llm_fast.ainvoke([
        SystemMessage(content=TOPIC_DETECT_SYSTEM.format(message=last_message)),
        HumanMessage(content=last_message),
    ])
    detected_topic = topic_response.content.strip().lower() if topic_response.content else "other"

    # Step 2: Guide response (streaming)
    streamed_text = ""
    async for chunk in llm_stream.astream([
        SystemMessage(content=GUIDE_SYSTEM.format(
            detected_topic=detected_topic,
            message=last_message,
        )),
        HumanMessage(content=last_message),
    ]):
        content = chunk.content if hasattr(chunk, "content") else str(chunk)
        streamed_text += content

    return {
        "node_response": streamed_text,
    }
