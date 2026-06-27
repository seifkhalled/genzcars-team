import asyncio
import json
from typing import AsyncGenerator
from app.core.llm import GeminiClient
from app.core.embedder import Embedder
from app.core.qdrant_client import QdrantSearch
from app.core.memory import SessionMemory
from app.core.preference_tracker import extract_and_update
import asyncpg

from app.agents import search_agent, advisor_agent, seller_agent, guide_agent, general_agent

CLASSIFIER_PROMPT = """You are an intent classifier for a car marketplace chatbot.
Classify the user message into exactly ONE of these intents:

- search_cars: user wants to find or browse cars (mentions specs, budget, city, type)
- car_advice: user asks about a specific car already in context (questions about the ad)
- seller_pricing: user wants to price their car or get selling advice
- seller_tips: user wants tips on how to write a listing or sell faster
- website_guide: user asks how to use the website (post ad, filter, save, compare)
- car_knowledge: general car questions (reliability, fuel economy, maintenance)
- greeting: hello, hi, how are you
- unclear: cannot determine intent

Respond with ONLY the intent string. No explanation."""


class Orchestrator:
    def __init__(
        self,
        llm: GeminiClient,
        embedder: Embedder,
        qdrant: QdrantSearch,
        memory: SessionMemory,
        pool: asyncpg.Pool,
    ):
        self.llm = llm
        self.embedder = embedder
        self.qdrant = qdrant
        self.memory = memory
        self.pool = pool

    async def handle(
        self,
        session_token: str,
        message: str,
        user_id: str | None = None,
        context_ad_id: str | None = None,
    ) -> AsyncGenerator[str, None]:
        session = self.memory.get_or_create(session_token, user_id, context_ad_id)

        intent_task = self.llm.classify(f"{CLASSIFIER_PROMPT}\n\nUser message: {message}")
        prefs_task = extract_and_update(self.llm, message, session)

        intent, extracted_prefs = await asyncio.gather(intent_task, prefs_task)

        intent = intent.strip().lower()

        self.memory.update_preferences(session_token, extracted_prefs)

        self.memory.add_message(session_token, "user", message, intent)
        try:
            from app.db.queries import insert_chat_message
            asyncio.create_task(
                insert_chat_message(self.pool, session_token, "user", message, intent)
            )
        except Exception:
            pass

        try:
            from app.db.queries import upsert_preferences
            prefs = self.memory._sessions.get(session_token, {}).get("preferences", {})
            prefs["intent_history"] = prefs.get("intent_history", []) + [intent]
            prefs["turn_count"] = session.get("turn_count", 0)
            asyncio.create_task(
                upsert_preferences(self.pool, session_token, prefs)
            )
        except Exception:
            pass

        ad_payload = None
        if context_ad_id and intent == "car_advice":
            try:
                from app.db.queries import get_ad_images_by_ids
                from uuid import UUID
                async with self.pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT * FROM ads WHERE id = $1 AND is_active = TRUE",
                        UUID(context_ad_id),
                    )
                    if row:
                        ad_payload = dict(row)
                        imgs = await get_ad_images_by_ids(self.pool, [UUID(context_ad_id)])
                        ad_payload["images"] = imgs.get(context_ad_id, [])
            except Exception:
                pass

        full_text = ""

        if intent == "search_cars":
            gen = search_agent.handle(message, session, self.llm, self.embedder, self.qdrant, self.pool)
        elif intent == "car_advice" and ad_payload:
            gen = advisor_agent.handle(message, session, self.llm, self.embedder, self.qdrant, self.pool, ad_payload)
        elif intent == "car_advice":
            gen = general_agent.handle(message, session, self.llm, "car_knowledge")
        elif intent in ("seller_pricing", "seller_tips"):
            gen = seller_agent.handle(message, session, self.llm, self.embedder, self.qdrant)
        elif intent == "website_guide":
            gen = guide_agent.handle(message, session, self.llm)
        else:
            gen = general_agent.handle(message, session, self.llm, intent)

        async for event in gen:
            data = json.loads(event)
            if data.get("type") == "token":
                full_text += data.get("content", "")
            yield event

        if full_text:
            self.memory.add_message(session_token, "assistant", full_text, intent)
            try:
                asyncio.create_task(
                    insert_chat_message(self.pool, session_token, "assistant", full_text, intent)
                )
            except Exception:
                pass
