from __future__ import annotations

from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage, AIMessage

from state import State
from agents import build_llm, tavily_search

MAX_TOOL_LOOPS = 3


def build_graph():
    llm = build_llm()
    tools = [tavily_search]
    tool_node = ToolNode(tools)

    def agent_node(state: State) -> dict:
        print("\n[RUNNING NODE] → agent_node")

        msgs = state.get("messages", [])

        if not msgs or not isinstance(msgs[0], SystemMessage):
            system = SystemMessage(
                content=(
                    "You are an Admin AI assistant for restaurant menu creation.\n"
                    "You may use the tavily_search tool to research ideas.\n"
                    "Rules:\n"
                    "- Use tavily_search only when needed.\n"
                    "- Never call tools more than 3 times in one request.\n"
                    "- Your final output must recommend exactly ONE menu item only.\n"
                    "- Do not output a full menu, course list, shopping list, or prep timeline.\n"
                    "- Summarize your findings into one practical menu item suitable for adding into a restaurant database.\n"
                    "- Keep the user-facing summary short.\n"
                    "- Return valid JSON only.\n"
                    "- Do not wrap JSON in markdown fences.\n"
                    "- JSON format must be exactly:\n"
                    "{\n"
                    '  "message": "short user-facing summary",\n'
                    '  "candidateItem": {\n'
                    '    "name": "string",\n'
                    '    "description": "string",\n'
                    '    "price": number,\n'
                    '    "category_id": number or null,\n'
                    '    "subcategory_id": number or null,\n'
                    '    "is_chef_recommend": true or false,\n'
                    '    "image_url": null\n'
                    "  }\n"
                    "}\n"
                    "- If you already have enough information, do not call tools again.\n"
                    "- When you stop using tools, produce the final JSON immediately.\n"
                )
            )
            msgs = [system] + msgs

        response = llm.invoke(msgs)
        return {"messages": [response]}

    def tools_router(state: State) -> Literal["tools", "end"]:
        print("[RUNNING NODE] → tools_router")

        messages = state.get("messages", [])
        tool_loops = state.get("tool_loops", 0)

        if tool_loops >= MAX_TOOL_LOOPS:
            print(f"[tools_router] Max tool loops reached: {tool_loops}")
            return "end"

        if not messages:
            return "end"

        last = messages[-1]

        if getattr(last, "tool_calls", None):
            print(f"[tools_router] tool_calls found, current count={tool_loops}")
            return "tools"

        return "end"

    def counted_tool_node(state: State) -> dict:
        print("\n[RUNNING NODE] → counted_tool_node")

        current = state.get("tool_loops", 0)
        tool_result = tool_node.invoke(state)

        return {
            **tool_result,
            "tool_loops": current + 1,
        }

    builder = StateGraph(State)

    builder.add_node("agent", agent_node)
    builder.add_node("tools", counted_tool_node)

    builder.add_edge(START, "agent")

    builder.add_conditional_edges(
        "agent",
        tools_router,
        {
            "tools": "tools",
            "end": END,
        },
    )

    builder.add_edge("tools", "agent")

    return builder.compile()


graph = build_graph()