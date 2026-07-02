import asyncio
import logging
import httpx
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.language_models import BaseChatModel
from langchain_core.outputs import ChatResult, ChatGeneration
from app.config import settings

logger = logging.getLogger(__name__)


class OpenRouterChat(BaseChatModel):
    model: str
    api_key: str
    temperature: float = 0.2
    max_tokens: int = 4096

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        raise NotImplementedError("Use async only")

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system" if isinstance(m, SystemMessage) else "user", "content": m.content}
                for m in messages
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        last_error = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    resp = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return ChatResult(generations=[ChatGeneration(message=AIMessage(content=content))])
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429 or 500 <= e.response.status_code < 600:
                    import asyncio
                    await asyncio.sleep(2 ** (attempt + 1))
                    continue
                raise
        raise last_error

    @property
    def _llm_type(self) -> str:
        return "openrouter"


class FallbackLLM:
    def __init__(self, streaming: bool = False):
        self._groq = None
        self._groq_alt = None
        self._groq_alt2 = None
        self._openrouter = None
        self._openrouter_alt = None
        self.streaming = streaming

    @property
    def primary(self):
        if self._groq is None:
            self._groq = ChatGroq(
                model=settings.groq_model,
                api_key=settings.groq_api_key,
                temperature=0 if not self.streaming else 0.3,
                streaming=self.streaming,
                max_tokens=2048,
            )
        return self._groq

    @property
    def secondary(self):
        if self._groq_alt is None and settings.groq_api_key_fallback:
            self._groq_alt = ChatGroq(
                model=settings.groq_model,
                api_key=settings.groq_api_key_fallback,
                temperature=0 if not self.streaming else 0.3,
                streaming=self.streaming,
                max_tokens=2048,
            )
        return self._groq_alt

    @property
    def secondary2(self):
        if self._groq_alt2 is None and settings.groq_api_key_fallback2:
            self._groq_alt2 = ChatGroq(
                model=settings.groq_model_fallback,
                api_key=settings.groq_api_key_fallback2,
                temperature=0 if not self.streaming else 0.3,
                streaming=self.streaming,
                max_tokens=2048,
            )
        return self._groq_alt2

    @property
    def fallback(self):
        if self._openrouter is None:
            self._openrouter = OpenRouterChat(
                model=settings.openrouter_model,
                api_key=settings.openrouter_api_key,
                temperature=0 if not self.streaming else 0.3,
                max_tokens=2048,
            )
        return self._openrouter

    @property
    def fallback_alt(self):
        if self._openrouter_alt is None and settings.openrouter_api_key_fallback:
            self._openrouter_alt = OpenRouterChat(
                model=settings.openrouter_model,
                api_key=settings.openrouter_api_key_fallback,
                temperature=0 if not self.streaming else 0.3,
                max_tokens=2048,
            )
        return self._openrouter_alt

    async def _try_ainvoke(self, provider, name, messages, **kwargs):
        try:
            return await asyncio.wait_for(provider.ainvoke(messages, **kwargs), timeout=15.0)
        except asyncio.TimeoutError:
            logger.warning("%s timed out after 15s", name)
            raise

    async def _try_astream(self, provider, name, messages, **kwargs):
        if "OpenRouter" in name:
            result = await asyncio.wait_for(provider.ainvoke(messages, **kwargs), timeout=20.0)
            content = result.generations[0].message.content if hasattr(result, "generations") else str(result)
            from langchain_core.messages import AIMessageChunk
            return [AIMessageChunk(content=content)]
        else:
            chunks = []
            async for chunk in provider.astream(messages, **kwargs):
                chunks.append(chunk)
            return chunks

    async def ainvoke(self, messages, **kwargs):
        providers = [("OpenRouter (alt key)", self.fallback_alt), ("OpenRouter", self.fallback), ("Groq", self.primary), ("Groq (alt key)", self.secondary), ("Groq (alt key 2)", self.secondary2)]
        for name, provider in providers:
            if provider is None:
                continue
            try:
                return await self._try_ainvoke(provider, name, messages, **kwargs)
            except Exception as e:
                logger.warning("%s failed (%s: %s)", name, type(e).__name__, str(e)[:200])
        raise RuntimeError("All LLM providers unavailable. Please try again later.")

    async def astream(self, messages, **kwargs):
        providers = [("OpenRouter (alt key)", self.fallback_alt), ("OpenRouter", self.fallback), ("Groq", self.primary), ("Groq (alt key)", self.secondary), ("Groq (alt key 2)", self.secondary2)]
        for name, provider in providers:
            if provider is None:
                continue
            try:
                chunks = await asyncio.wait_for(self._try_astream(provider, name, messages, **kwargs), timeout=25.0)
                for chunk in chunks:
                    yield chunk
                return
            except Exception as e:
                logger.warning("%s streaming failed (%s: %s)", name, type(e).__name__, str(e)[:200])
        raise RuntimeError("All LLM providers unavailable. Please try again later.")


def get_llm(streaming: bool = False) -> FallbackLLM:
    return FallbackLLM(streaming=streaming)
