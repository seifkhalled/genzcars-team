import json
from typing import AsyncGenerator
from app.core.llm import GeminiClient

GENERAL_SYSTEM = (
    "You are a helpful car expert assistant for an Egyptian car marketplace. "
    "Help users with: reliability, maintenance, fuel economy, common issues, insurance, "
    "and buying advice specific to the Egyptian market. "
    "Always respond in the same language the user writes in (Arabic or English). "
    "Keep answers to 3-5 sentences unless the user asks for detail. "
    "Never make up statistics or prices. If you don't know, say so."
)


async def handle(
    message: str,
    session: dict,
    llm: GeminiClient,
    intent: str = "car_knowledge",
) -> AsyncGenerator[str, None]:
    if intent == "unclear":
        yield json.dumps({
            "type": "token",
            "content": "I'd be happy to help! Are you looking to buy a car, sell one, or do you have a general car question?",
        })
        yield json.dumps({"type": "done", "content": None})
        return

    if intent == "greeting":
        system = "Respond with a friendly greeting. Ask how you can help with cars today."
        async for chunk in llm.stream(system, [], message):
            yield json.dumps({"type": "token", "content": chunk})
        yield json.dumps({"type": "done", "content": None})
        return

    async for chunk in llm.stream(GENERAL_SYSTEM, session.get("history", []), message):
        yield json.dumps({"type": "token", "content": chunk})

    yield json.dumps({"type": "done", "content": None})
