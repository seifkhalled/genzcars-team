import asyncio
import hashlib
import logging
from typing import Any, Optional
from langchain_groq import ChatGroq
from app.config import settings
from app.enums import TaskType
from app.core.openrouter import OpenRouterChat
from app.core.cache import llm_response_cache
from app.core.key_rotator import KeyRotator

logger = logging.getLogger(__name__)

SIMPLE_TASKS = {TaskType.ROUTER, TaskType.PREFERENCE_EXTRACTOR, TaskType.GUIDE_TOPIC, TaskType.SEARCH_DECISION, TaskType.CATALOGUE_CHECK}
COMPLEX_TASKS = {TaskType.ADVISOR, TaskType.SELLER, TaskType.SEARCH, TaskType.RECOMMENDATION, TaskType.GENERAL, TaskType.COMPARISON, TaskType.GUIDE}

_CACHEABLE_SIMPLE = {TaskType.ROUTER, TaskType.GUIDE_TOPIC, TaskType.SEARCH_DECISION}


def _build_groq_pool(keys: list[str], model: str, temperature: float, streaming: bool, max_tokens: int) -> list[ChatGroq]:
    """Build a list of ChatGroq instances, one per API key."""
    pool = []
    for key in keys:
        if not key:
            continue
        pool.append(ChatGroq(
            model=model,
            api_key=key,
            temperature=temperature,
            streaming=streaming,
            max_tokens=max_tokens,
        ))
    return pool


class MultiLLM:
    """Multi-provider LLM with task-based routing, round-robin key rotation, and automatic fallback.

    - Simple tasks (routing, extraction): cheap/fast Groq model, low tokens, no stream
    - Complex tasks (advisor, seller, analysis): powerful model with streaming, higher tokens

    All available Groq keys are distributed via round-robin rotation so that
    successive calls hit different keys, avoiding 429 rate limits.
    """

    def __init__(self):
        all_groq_keys = [
            settings.groq_api_key,
            settings.groq_api_key_fallback,
            settings.groq_api_key_fallback2,
            settings.groq_api_key_fallback3,
        ]

        fast_model = settings.groq_model
        powerful_model = settings.groq_model_fallback or settings.groq_model

        # Fast pool: all keys with fast config (for simple tasks)
        self._fast_pool = _build_groq_pool(
            all_groq_keys, fast_model,
            temperature=0, streaming=False, max_tokens=1024,
        )
        self._fast_rotator: KeyRotator[ChatGroq] = KeyRotator(self._fast_pool)

        # Powerful pool: all keys with powerful config (for complex tasks)
        self._powerful_pool = _build_groq_pool(
            all_groq_keys, powerful_model,
            temperature=0.3, streaming=True, max_tokens=4096,
        )
        self._powerful_rotator: KeyRotator[ChatGroq] = KeyRotator(self._powerful_pool) if self._powerful_pool else None

        # OpenRouter fallback for complex tasks
        self._powerful_openrouter: OpenRouterChat | None = None

        logger.info(
            "MultiLLM initialized: fast pool=%d keys, powerful pool=%d keys",
            self._fast_rotator.size,
            self._powerful_rotator.size if self._powerful_rotator else 0,
        )

    # ── Backward-compatible properties ──
    # These return the next instance via round-robin so that direct callers
    # (e.g. chat.py passing llm_fast / llm_stream to config) also benefit.

    @property
    def fast(self) -> ChatGroq:
        return self._fast_rotator.next()

    @property
    def powerful(self) -> ChatGroq | None:
        if self._powerful_rotator is None:
            return None
        return self._powerful_rotator.next()

    @property
    def powerful_alt(self) -> OpenRouterChat | None:
        if self._powerful_openrouter is None and settings.openrouter_api_key:
            self._powerful_openrouter = OpenRouterChat(
                model=settings.openrouter_model,
                api_key=settings.openrouter_api_key,
                temperature=0.3,
                max_tokens=4096,
            )
        return self._powerful_openrouter

    # ── Task-based routing ──

    def get_for_task(self, task_type: str, streaming: bool = False):
        if task_type in SIMPLE_TASKS:
            return self.fast
        return self.powerful or self.fast

    # ── Non-streaming invocation with automatic fallback ──

    async def ainvoke_task(
        self,
        task_type: str,
        messages,
        **kwargs,
    ):
        if task_type in _CACHEABLE_SIMPLE:
            prompt_text = "||".join(m.content if hasattr(m, "content") else str(m) for m in messages)
            cache_key = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
            cached = llm_response_cache.get(cache_key)
            if cached is not None:
                logger.info("LLM cache hit for '%s'", task_type)
                return cached

        if task_type in SIMPLE_TASKS:
            providers = list(self._fast_pool)
        else:
            providers = list(self._powerful_pool)
            if self.powerful_alt:
                providers.append(self.powerful_alt)
            if self._fast_pool:
                providers.append(self._fast_pool[0])

        errors = []
        for i, provider in enumerate(providers):
            try:
                result = await asyncio.wait_for(
                    provider.ainvoke(messages, **kwargs),
                    timeout=25.0,
                )
                if task_type in _CACHEABLE_SIMPLE:
                    prompt_text = "||".join(m.content if hasattr(m, "content") else str(m) for m in messages)
                    cache_key = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
                    llm_response_cache.set(cache_key, result, ttl=120)
                return result
            except asyncio.TimeoutError:
                logger.warning("%s (attempt %d/%d) timed out", task_type, i + 1, len(providers))
                errors.append("timeout")
            except Exception as e:
                logger.warning("%s (attempt %d/%d) failed: %s", task_type, i + 1, len(providers), str(e)[:200])
                errors.append(str(e)[:100])

        logger.error("All %d LLM providers failed for '%s': %s", len(providers), task_type, "; ".join(errors))
        raise RuntimeError(f"Service temporarily unavailable. Please try again later.")

    # ── Streaming invocation with automatic fallback ──

    async def astream_task(
        self,
        task_type: str,
        messages,
        **kwargs,
    ):
        if task_type in SIMPLE_TASKS:
            providers = list(self._fast_pool)
        else:
            providers = list(self._powerful_pool)
            if self.powerful_alt:
                providers.append(self.powerful_alt)
            if self._fast_pool:
                providers.append(self._fast_pool[0])

        errors = []
        for i, provider in enumerate(providers):
            if provider is None:
                continue
            try:
                async with asyncio.timeout(60):
                    async for chunk in provider.astream(messages, **kwargs):
                        yield chunk
                return
            except asyncio.TimeoutError:
                logger.warning("%s stream (attempt %d/%d) timed out", task_type, i + 1, len(providers))
                errors.append("timeout")
            except Exception as e:
                logger.warning("%s stream (attempt %d/%d) failed: %s", task_type, i + 1, len(providers), str(e)[:200])
                errors.append(str(e)[:100])

        logger.error("All %d LLM providers failed for '%s' streaming", len(providers), task_type)
        raise RuntimeError(f"Service temporarily unavailable. Please try again later.")


# Singleton
llm_router = MultiLLM()
