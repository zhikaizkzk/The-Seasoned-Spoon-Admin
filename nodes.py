from typing import Literal
from langchain_core.messages import AIMessage, BaseMessage
from state import State
from agents import admin_agent_run

def human_node(state: State) -> State:
    print("[RUNNING NODE] → human_node")
    return state

def should_end(state: State) -> Literal["admin", "end"]:
    messages = state.get("messages", [])
    loop_count = state.get("loop_count", 0)
    print(loop_count)
    print("check loop")
    # ✅ STOP CONDITION
    if loop_count >= 3:
        print("[should_end] Max loop reached")
        return "end"

    if not messages:
        return "admin"

    last = (messages[-1].content or "").strip().lower()

    if last in {"exit", "quit"}:
        return "end"

    return "admin"

def admin_node(state: State) -> State:
    print("[RUNNING NODE] → admin_node")

    messages = state.get("messages", [])
    loop_count = state.get("loop_count", 0)

    last_user = (messages[-1].content or "").strip() if messages else ""
    print(f"[admin_node] user said: {last_user}")
    print(f"[admin_node] loop_count: {loop_count}")

    reply = admin_agent_run(last_user)

    new_messages = messages.copy()
    new_messages.append(AIMessage(content=reply))

    return {
        **state,
        "messages": new_messages,
        "loop_count": loop_count + 1,  # 👈 increment
    }