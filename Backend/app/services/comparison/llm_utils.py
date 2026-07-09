import json
import logging
import time

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq

from app.core.ai_metrics import (
    llm_calls_total, llm_tokens_total, llm_latency_seconds, llm_cost_total,
)

logger = logging.getLogger(__name__)


async def parse_llm_json(
    llm: ChatGroq,
    system: str,
    human: str,
    task_type: str = "unknown",
    model_name: str = "",
    provider: str = "groq",
) -> dict:
    start = time.monotonic()
    response = await llm.ainvoke([
        SystemMessage(content=system),
        HumanMessage(content=human),
    ])
    duration = time.monotonic() - start
    content = response.content.strip()

    usage = response.usage_metadata or {}
    prompt_tokens = usage.get("input_tokens", 0) or 0
    completion_tokens = usage.get("output_tokens", 0) or 0

    labels = dict(service="backend", provider=provider, model=model_name, task_type=task_type)
    llm_calls_total.labels(**labels).inc()
    llm_tokens_total.labels(service="backend", provider=provider, type="prompt").inc(prompt_tokens)
    llm_tokens_total.labels(service="backend", provider=provider, type="completion").inc(completion_tokens)
    llm_latency_seconds.labels(**labels).observe(duration)

    result = _try_parse_json(content)
    if result is not None:
        return result

    logger.warning("LLM JSON parse failed on first attempt, retrying with stricter prompt")
    retry_response = await llm.ainvoke([
        SystemMessage(content=system + "\nYour previous response was not valid JSON. Return ONLY the JSON object, nothing else, no markdown formatting."),
        HumanMessage(content=human),
    ])
    retry_content = retry_response.content.strip()
    result = _try_parse_json(retry_content)
    if result is not None:
        return result

    raise ValueError("LLM failed to return valid JSON after retry")


def _try_parse_json(content: str) -> dict | None:
    cleaned = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None
