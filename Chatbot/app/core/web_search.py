from duckduckgo_search import DDGS
from langsmith import traceable
import logging

logger = logging.getLogger(__name__)


class WebSearch:
    @traceable(run_type="tool")
    def search(self, query: str, max_results: int = 5) -> str:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
                if not results:
                    return ""
                lines = []
                for r in results:
                    title = r.get("title", "")
                    body = r.get("body", "")
                    if title and body:
                        lines.append(f"- {title}: {body}")
                    elif body:
                        lines.append(f"- {body}")
                return "\n".join(lines[:max_results])
        except Exception as e:
            logger.warning("Web search failed for query %r: %s: %s", query[:120], type(e).__name__, str(e)[:200])
            return ""
