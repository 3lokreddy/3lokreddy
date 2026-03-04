"""
Web search tool — pluggable implementation.

By default this is a stub that returns simulated results so the system works
without any API keys. Swap in a real provider (Tavily, SerpAPI, Brave, …) by
setting the SEARCH_PROVIDER env var and the matching key.
"""
import os
import json
from typing import Any, Dict, List

# Tool definition consumed by the Anthropic API tool-use feature
web_search_tool: Dict[str, Any] = {
    "name": "web_search",
    "description": (
        "Search the web for up-to-date information on a topic. "
        "Returns a list of relevant results with titles, URLs, and snippets."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query.",
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (default 5, max 10).",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}


def web_search(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    """
    Execute a web search and return structured results.

    Providers checked in order:
      1. Tavily  (TAVILY_API_KEY)
      2. Stub / simulation (always available)
    """
    provider = os.getenv("SEARCH_PROVIDER", "stub").lower()

    if provider == "tavily":
        return _tavily_search(query, num_results)

    # Default: stub results useful for demos / unit tests
    return _stub_search(query, num_results)


# ── Provider implementations ────────────────────────────────────────────────

def _tavily_search(query: str, num_results: int) -> List[Dict[str, str]]:
    try:
        from tavily import TavilyClient  # type: ignore
        client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
        response = client.search(query=query, max_results=num_results)
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", ""),
            }
            for r in response.get("results", [])
        ]
    except Exception as exc:
        return [{"title": "Search error", "url": "", "snippet": str(exc)}]


def _stub_search(query: str, num_results: int) -> List[Dict[str, str]]:
    """Return plausible-looking stub results for demos."""
    results = []
    for i in range(1, min(num_results, 5) + 1):
        results.append({
            "title": f"Result {i}: {query[:50]}",
            "url": f"https://example.com/result-{i}",
            "snippet": (
                f"This is a simulated search result about '{query}'. "
                f"In a production system, connect a real search provider via "
                f"the SEARCH_PROVIDER environment variable."
            ),
        })
    return results
