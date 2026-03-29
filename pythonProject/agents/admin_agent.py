from __future__ import annotations

import os
import json
from dotenv import load_dotenv
from tavily import TavilyClient

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

load_dotenv()

TAVILY_MAX_RESULTS = int(os.getenv("TAVILY_MAX_RESULTS", "3"))
TAVILY_SEARCH_DEPTH = os.getenv("TAVILY_SEARCH_DEPTH", "basic")

_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


@tool("tavily_search")
def tavily_search(query: str) -> str:
    """
    Search the web using Tavily and return JSON string of results.
    """
    print(f"[TOOL RUNNING] → tavily_search | query={query!r}")
    res = _client.search(
        query=query,
        search_depth=TAVILY_SEARCH_DEPTH,
        max_results=TAVILY_MAX_RESULTS,
        include_answer=False,
        include_raw_content=False,
    )
    return json.dumps(res, ensure_ascii=False)


def build_llm():
    model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))

    llm = ChatOpenAI(model=model, temperature=temperature)
    llm_with_tools = llm.bind_tools([tavily_search])
    return llm_with_tools