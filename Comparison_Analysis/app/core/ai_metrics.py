from __future__ import annotations
import threading
from prometheus_client import Counter, Histogram

SERVICE = "comparison_analysis"

_lock = threading.Lock()
_token_summary: dict[str, int] = {"prompt": 0, "completion": 0}


def add_tokens(prompt: int, completion: int):
    with _lock:
        _token_summary["prompt"] += prompt
        _token_summary["completion"] += completion


def get_and_reset_tokens() -> dict[str, int]:
    with _lock:
        snapshot = dict(_token_summary)
        _token_summary["prompt"] = 0
        _token_summary["completion"] = 0
    return snapshot


llm_calls_total = Counter(
    'llm_calls_total',
    'Total number of LLM calls',
    ['service', 'provider', 'model', 'task_type']
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total tokens used in LLM calls',
    ['service', 'provider', 'type']
)

llm_latency_seconds = Histogram(
    'llm_latency_seconds',
    'Latency of LLM calls in seconds',
    ['service', 'provider', 'model', 'task_type'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
)

llm_cost_total = Counter(
    'llm_cost_total_usd',
    'Total cost of LLM calls in USD',
    ['service', 'provider', 'model']
)

comparison_requests_total = Counter(
    'comparison_requests_total',
    'Total number of comparison requests',
    ['service']
)

comparison_errors_total = Counter(
    'comparison_errors_total',
    'Total number of comparison errors',
    ['service', 'error_type']
)

research_calls_total = Counter(
    'research_calls_total',
    'Total number of web research calls',
    ['service', 'provider']
)

llm_fallback_total = Counter(
    'llm_fallback_total',
    'Total number of LLM fallback events',
    ['service', 'task_type', 'from_provider', 'to_provider']
)
