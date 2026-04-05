from __future__ import annotations

import json
from typing import List, Dict, Any

from fastapi.concurrency import run_in_threadpool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from graph import graph
from state import State


def to_lc_message(m: Dict[str, Any]):
    role = (m.get("role") or "").lower()
    content = m.get("content") or ""

    if role == "system":
        return SystemMessage(content=content)
    if role == "assistant":
        return AIMessage(content=content)

    return HumanMessage(content=content)


def safe_parse_ai_json(raw: str) -> dict:
    try:
        data = json.loads(raw)
        return {
            "message": data.get("message", ""),
            "candidateItem": data.get("candidateItem"),
        }
    except Exception:
        return {
            "message": raw,
            "candidateItem": None,
        }


async def run_chat(
    message: str,
    history: List[Dict[str, Any]] | None = None,
    state: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    history = history or []
    state = state or {}
    user_text = (message or "").strip()

    if user_text.lower() in {"exit", "quit"}:
        new_history = history + [
            {"role": "user", "content": user_text},
            {"role": "assistant", "content": "Bye! 👋"},
        ]
        return {
            "message": {
                "response": "Bye! 👋",
                "candidateItem": None,
                "chat_history": new_history,
                "state_delta": state,
            }
        }

    msgs = [to_lc_message(m) for m in history]
    msgs.append(HumanMessage(content=user_text))

    initial_state: State = {
        "messages": msgs,
        "tool_loops": state.get("tool_loops", 1),
        "route": state.get("route", ""),
        "state": state.get("state", {}),
    }

    result = await run_in_threadpool(graph.invoke, initial_state)
    out_msgs = result.get("messages", [])
    last_ai = ""
    for m in reversed(out_msgs):
        if isinstance(m, AIMessage):
            last_ai = m.content or ""
            break

    parsed = safe_parse_ai_json(last_ai)
    new_history = history + [{"role": "user", "content": user_text}]
    if parsed.get("message"):
        new_history.append({"role": "assistant", "content": parsed["message"]})

    updated_state = {
        "tool_loops": result.get("tool_loops", 0),
        "route": result.get("route", ""),
        "state": result.get("state", {}),
    }
    print("checking message")
    print(parsed.get("message", ""))
    return {
        "message": {
            "response": parsed.get("message", ""),
            "candidateItem": parsed.get("candidateItem"),
            "chat_history": new_history,
            "state_delta": updated_state,
        }
    }