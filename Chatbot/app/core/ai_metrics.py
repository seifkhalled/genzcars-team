from prometheus_client import Counter, Histogram

SERVICE = "chatbot"

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

search_quality_total = Counter(
    'search_quality_total',
    'Search quality evaluation results',
    ['service', 'passed']
)
