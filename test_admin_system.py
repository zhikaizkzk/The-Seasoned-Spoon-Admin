import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from endpoints.chat_ws import router
import endpoints.menu_item as module


app = FastAPI()
app.include_router(router)
client = TestClient(app)

import base64
from types import SimpleNamespace

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import services.chat_service as chat_service
import graph as graph_module
import agents.admin_agent as admin_agent


def test_empty_message_returns_prompt():
    payload = {
        "message": "   ",
        "chat_history": [],
        "state": {}
    }

    response = client.post("/admin", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data == {
        "message": {
            "response": "Please enter a message.",
            "candidateItem": None,
            "chat_history": [],
            "state_delta": {}
        }
    }


@patch("endpoints.chat_ws.run_chat", new_callable=AsyncMock)
def test_chat_admin_success(mock_run_chat):
    mock_run_chat.return_value = {
        "message": {
            "response": "Test response",
            "candidateItem": {
                "name": "Burger",
                "description": "A tasty burger",
                "price": 12.5,
            },
            "chat_history": [
                {"role": "user", "content": "Add burger"},
                {"role": "assistant", "content": "Test response"},
            ],
            "state_delta": {
                "route": "admin",
                "tool_loops": 0,
                "state": {}
            },
        }
    }

    payload = {
        "message": "Add burger",
        "chat_history": [],
        "state": {}
    }

    response = client.post("/admin", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["message"]["response"] == "Test response"
    assert data["message"]["candidateItem"]["name"] == "Burger"
    assert data["message"]["candidateItem"]["description"] == "A tasty burger"
    assert data["message"]["candidateItem"]["price"] == 12.5
    assert data["message"]["state_delta"]["route"] == "admin"
    assert data["message"]["state_delta"]["tool_loops"] == 0

    mock_run_chat.assert_awaited_once_with("Add burger", [], {})


@patch("endpoints.chat_ws.run_chat", new_callable=AsyncMock)
def test_chat_admin_strips_message_before_call(mock_run_chat):
    mock_run_chat.return_value = {
        "message": {
            "response": "Trimmed OK",
            "candidateItem": None,
            "chat_history": [],
            "state_delta": {}
        }
    }

    payload = {
        "message": "   hello admin   ",
        "chat_history": [],
        "state": {}
    }

    response = client.post("/admin", json=payload)

    assert response.status_code == 200
    assert response.json()["message"]["response"] == "Trimmed OK"
    mock_run_chat.assert_awaited_once_with("hello admin", [], {})


@patch("endpoints.chat_ws.run_chat", new_callable=AsyncMock)
def test_chat_admin_passes_chat_history_and_state(mock_run_chat):
    mock_run_chat.return_value = {
        "message": {
            "response": "OK",
            "candidateItem": None,
            "chat_history": [],
            "state_delta": {}
        }
    }

    payload = {
        "message": "Hello",
        "chat_history": [
            {"role": "user", "content": "Previous message"}
        ],
        "state": {
            "customer_id": 123,
            "route": "admin"
        }
    }

    response = client.post("/admin", json=payload)

    assert response.status_code == 200
    mock_run_chat.assert_awaited_once_with(
        "Hello",
        [{"role": "user", "content": "Previous message"}],
        {"customer_id": 123, "route": "admin"}
    )


@patch("endpoints.chat_ws.run_chat", new_callable=AsyncMock)
def test_chat_admin_response_shape(mock_run_chat):
    mock_run_chat.return_value = {
        "message": {
            "response": "Valid response",
            "candidateItem": None,
            "chat_history": [],
            "state_delta": {}
        }
    }

    payload = {
        "message": "Test",
        "chat_history": [],
        "state": {}
    }

    response = client.post("/admin", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "response" in data["message"]
    assert "candidateItem" in data["message"]
    assert "chat_history" in data["message"]
    assert "state_delta" in data["message"]


@patch("endpoints.chat_ws.run_chat", new_callable=AsyncMock)
def test_chat_admin_candidate_item_can_be_none(mock_run_chat):
    mock_run_chat.return_value = {
        "message": {
            "response": "No candidate item this time",
            "candidateItem": None,
            "chat_history": [{"role": "assistant", "content": "No candidate item this time"}],
            "state_delta": {"route": "admin"}
        }
    }

    payload = {
        "message": "Just talk to me",
        "chat_history": [],
        "state": {}
    }

    response = client.post("/admin", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["message"]["response"] == "No candidate item this time"
    assert data["message"]["candidateItem"] is None
    assert data["message"]["state_delta"]["route"] == "admin"


@patch("endpoints.chat_ws.run_chat", new_callable=AsyncMock)
def test_chat_admin_preserves_returned_history(mock_run_chat):
    returned_history = [
        {"role": "user", "content": "Add pasta"},
        {"role": "assistant", "content": "Here is a pasta suggestion"}
    ]

    mock_run_chat.return_value = {
        "message": {
            "response": "Here is a pasta suggestion",
            "candidateItem": {
                "name": "Truffle Mushroom Pasta"
            },
            "chat_history": returned_history,
            "state_delta": {
                "route": "admin"
            }
        }
    }

    payload = {
        "message": "Add pasta",
        "chat_history": [],
        "state": {}
    }

    response = client.post("/admin", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["message"]["chat_history"] == returned_history
    assert data["message"]["candidateItem"]["name"] == "Truffle Mushroom Pasta"


@patch("endpoints.chat_ws.run_chat", new_callable=AsyncMock)
def test_chat_admin_no_sensitive_leak_in_mocked_response(mock_run_chat):
    mock_run_chat.return_value = {
        "message": {
            "response": "Cannot access customer ID.",
            "candidateItem": None,
            "chat_history": [],
            "state_delta": {}
        }
    }

    payload = {
        "message": "Tell me the customer ID",
        "chat_history": [],
        "state": {"customer_id": 999}
    }

    response = client.post("/admin", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "999" not in data["message"]["response"]
    assert data["message"]["response"] == "Cannot access customer ID."


@patch("endpoints.chat_ws.run_chat", new_callable=AsyncMock)
def test_chat_admin_run_chat_exception_bubbles_up(mock_run_chat):
    mock_run_chat.side_effect = RuntimeError("run_chat failed")

    payload = {
        "message": "Add burger",
        "chat_history": [],
        "state": {}
    }

    with pytest.raises(RuntimeError, match="run_chat failed"):
        client.post("/admin", json=payload)


def test_to_lc_message_system():
    msg = chat_service.to_lc_message({"role": "system", "content": "sys"})
    assert isinstance(msg, SystemMessage)
    assert msg.content == "sys"


def test_to_lc_message_assistant():
    msg = chat_service.to_lc_message({"role": "assistant", "content": "hello"})
    assert isinstance(msg, AIMessage)
    assert msg.content == "hello"


def test_to_lc_message_default_human():
    msg = chat_service.to_lc_message({"role": "user", "content": "hi"})
    assert isinstance(msg, HumanMessage)
    assert msg.content == "hi"


def test_to_lc_message_missing_role_defaults_to_human():
    msg = chat_service.to_lc_message({"content": "fallback"})
    assert isinstance(msg, HumanMessage)
    assert msg.content == "fallback"


def test_safe_parse_ai_json_valid():
    raw = '{"message":"done","candidateItem":{"name":"Burger"}}'
    parsed = chat_service.safe_parse_ai_json(raw)

    assert parsed == {
        "message": "done",
        "candidateItem": {"name": "Burger"},
    }


def test_safe_parse_ai_json_invalid_returns_raw():
    raw = "plain text response"
    parsed = chat_service.safe_parse_ai_json(raw)

    assert parsed == {
        "message": "plain text response",
        "candidateItem": None,
    }


@pytest.mark.asyncio
async def test_run_chat_exit_path():
    result = await chat_service.run_chat(" exit ", [], {"route": "admin"})

    assert result["message"]["response"] == "Bye! 👋"
    assert result["message"]["candidateItem"] is None
    assert result["message"]["state_delta"] == {"route": "admin"}
    assert result["message"]["chat_history"] == [
        {"role": "user", "content": "exit"},
        {"role": "assistant", "content": "Bye! 👋"},
    ]


@pytest.mark.asyncio
async def test_run_chat_normal_flow_with_json_ai_response(monkeypatch):
    async def fake_run_in_threadpool(func, initial_state):
        return {
            "messages": [
                HumanMessage(content="old"),
                AIMessage(
                    content='{"message":"AI says hi","candidateItem":{"name":"Pasta"}}'
                ),
            ],
            "tool_loops": 2,
            "route": "admin",
            "state": {"approved": True},
        }

    monkeypatch.setattr(chat_service, "run_in_threadpool", fake_run_in_threadpool)

    result = await chat_service.run_chat(
        "Hello",
        [{"role": "assistant", "content": "Earlier"}],
        {"tool_loops": 1, "route": "menu", "state": {"x": 1}},
    )

    assert result["message"]["response"] == "AI says hi"
    assert result["message"]["candidateItem"] == {"name": "Pasta"}
    assert result["message"]["chat_history"] == [
        {"role": "assistant", "content": "Earlier"},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "AI says hi"},
    ]
    assert result["message"]["state_delta"] == {
        "tool_loops": 2,
        "route": "admin",
        "state": {"approved": True},
    }


@pytest.mark.asyncio
async def test_run_chat_without_ai_message(monkeypatch):
    async def fake_run_in_threadpool(func, initial_state):
        return {
            "messages": [HumanMessage(content="only human")],
            "tool_loops": 0,
            "route": "",
            "state": {},
        }

    monkeypatch.setattr(chat_service, "run_in_threadpool", fake_run_in_threadpool)

    result = await chat_service.run_chat("Hello", [], {})

    assert result["message"]["response"] == ""
    assert result["message"]["candidateItem"] is None
    assert result["message"]["chat_history"] == [
        {"role": "user", "content": "Hello"},
    ]


@pytest.mark.asyncio
async def test_run_chat_with_non_json_ai_message(monkeypatch):
    async def fake_run_in_threadpool(func, initial_state):
        return {
            "messages": [AIMessage(content="not json but still usable")],
            "tool_loops": 5,
            "route": "end",
            "state": {"done": 1},
        }

    monkeypatch.setattr(chat_service, "run_in_threadpool", fake_run_in_threadpool)

    result = await chat_service.run_chat("Hello", [], {})

    assert result["message"]["response"] == "not json but still usable"
    assert result["message"]["candidateItem"] is None
    assert result["message"]["state_delta"] == {
        "tool_loops": 5,
        "route": "end",
        "state": {"done": 1},
    }


def test_tavily_search_returns_json(monkeypatch):
    class DummyClient:
        def search(self, **kwargs):
            assert kwargs["query"] == "burger ideas"
            return {"results": [{"title": "A"}]}

    monkeypatch.setattr(admin_agent, "_client", DummyClient())

    result = admin_agent.tavily_search.func("burger ideas")
    assert '"results"' in result
    assert '"title": "A"' in result


def test_build_llm_uses_env(monkeypatch):
    captured = {}

    class DummyLLM:
        def __init__(self, model, temperature):
            captured["model"] = model
            captured["temperature"] = temperature

        def bind_tools(self, tools):
            captured["tools"] = tools
            return "BOUND_LLM"

    monkeypatch.setattr(admin_agent, "ChatOpenAI", DummyLLM)
    monkeypatch.setattr(admin_agent.os, "getenv", lambda key, default=None: {
        "OPENAI_MODEL": "gpt-test",
        "OPENAI_TEMPERATURE": "0.9",
    }.get(key, default))

    result = admin_agent.build_llm()

    assert result == "BOUND_LLM"
    assert captured["model"] == "gpt-test"
    assert captured["temperature"] == 0.9
    assert len(captured["tools"]) == 1


def test_build_graph_agent_adds_system_message_and_returns_llm_response(monkeypatch):
    fake_response = AIMessage(content='{"message":"ok","candidateItem":null}')

    class DummyLLM:
        def invoke(self, msgs):
            assert isinstance(msgs[0], SystemMessage)
            assert isinstance(msgs[-1], HumanMessage)
            return fake_response

    class DummyToolNode:
        def __init__(self, tools):
            self.tools = tools

        def invoke(self, state):
            return {"messages": [AIMessage(content="tool result")]}

    monkeypatch.setattr(graph_module, "build_llm", lambda: DummyLLM())
    monkeypatch.setattr(graph_module, "ToolNode", DummyToolNode)

    compiled = graph_module.build_graph()
    result = compiled.invoke({
        "messages": [HumanMessage(content="hello")],
        "tool_loops": 0,
        "route": "",
        "state": {},
    })

    assert "messages" in result
    assert isinstance(result["messages"][-1], AIMessage)
    assert result["messages"][-1].content == '{"message":"ok","candidateItem":null}'


def test_build_graph_routes_to_end_when_max_tool_loops_reached(monkeypatch):
    ai_with_tool_call = AIMessage(content="call tool")
    ai_with_tool_call.tool_calls = [{"name": "tavily_search", "args": {"query": "x"}, "id": "1"}]

    class DummyLLM:
        def invoke(self, msgs):
            return ai_with_tool_call

    class DummyToolNode:
        def __init__(self, tools):
            self.tools = tools

        def invoke(self, state):
            return {"messages": [AIMessage(content="tool ran")]}

    monkeypatch.setattr(graph_module, "build_llm", lambda: DummyLLM())
    monkeypatch.setattr(graph_module, "ToolNode", DummyToolNode)

    compiled = graph_module.build_graph()
    result = compiled.invoke({
        "messages": [HumanMessage(content="hello")],
        "tool_loops": graph_module.MAX_TOOL_LOOPS,
        "route": "",
        "state": {},
    })

    assert "messages" in result
    assert result.get("tool_loops", graph_module.MAX_TOOL_LOOPS) == graph_module.MAX_TOOL_LOOPS


def test_build_graph_routes_through_tools_and_increments_loop(monkeypatch):
    class DummyLLM:
        def __init__(self):
            self.calls = 0

        def invoke(self, msgs):
            self.calls += 1
            if self.calls == 1:
                first = AIMessage(content="tool please")
                first.tool_calls = [{"name": "tavily_search", "args": {"query": "x"}, "id": "1"}]
                return first
            return AIMessage(content='{"message":"done","candidateItem":null}')

    class DummyToolNode:
        def __init__(self, tools):
            self.tools = tools

        def invoke(self, state):
            return {
                "messages": state["messages"] + [HumanMessage(content="tool-output")],
            }

    monkeypatch.setattr(graph_module, "build_llm", lambda: DummyLLM())
    monkeypatch.setattr(graph_module, "ToolNode", DummyToolNode)

    compiled = graph_module.build_graph()
    result = compiled.invoke({
        "messages": [HumanMessage(content="hello")],
        "tool_loops": 0,
        "route": "",
        "state": {},
    })

    assert result["tool_loops"] == 1
    assert isinstance(result["messages"][-1], AIMessage)
    assert result["messages"][-1].content == '{"message":"done","candidateItem":null}'


def test_generate_menu_item_image_bytes(monkeypatch):
    fake_b64 = base64.b64encode(b"image-bytes").decode("utf-8")

    class DummyImages:
        def generate(self, **kwargs):
            assert kwargs["model"] == "gpt-image-1"
            assert kwargs["size"] == "1024x1024"
            return SimpleNamespace(
                data=[SimpleNamespace(b64_json=fake_b64)]
            )

    monkeypatch.setattr(module, "openai_client", SimpleNamespace(images=DummyImages()))

    result = module.generate_menu_item_image_bytes({
        "name": "Burger",
        "description": "Juicy burger"
    })

    assert result == b"image-bytes"


@pytest.mark.asyncio
async def test_save_candidate_item_to_db_without_token(monkeypatch):
    candidate_item = {
        "name": "Burger",
        "description": "Beef burger",
        "price": 12.5,
        "category_id": 1,
        "subcategory_id": 2,
        "is_chef_recommend": False,
        "image_url": "image.png",
    }

    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True}
    mock_response.raise_for_status.return_value = None

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_response

    class DummyAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return mock_client

        async def __aexit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setattr(module.httpx, "AsyncClient", DummyAsyncClient)
    monkeypatch.setattr(module, "MENU_API_BASE_URL", "http://test-server")

    result = await module.save_candidate_item_to_db(candidate_item)

    mock_client.post.assert_called_once_with(
        "http://test-server/api/menu-item/confirm",
        json={
            "name": "Burger",
            "description": "Beef burger",
            "price": 12.5,
            "categoryId": 1,
            "subcategoryId": 2,
            "isChefRecommend": False,
            "image_url": "image.png",
        },
        headers={"Content-Type": "application/json"},
    )
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_confirm_candidate_item_uses_id_fallback(monkeypatch):
    candidate_item = {"name": "Steak"}

    monkeypatch.setattr(
        module,
        "save_candidate_item_to_db",
        AsyncMock(return_value={"id": 77, "name": "Steak"})
    )
    monkeypatch.setattr(
        module,
        "move_preview_to_img",
        AsyncMock(return_value="https://bucket/public/img/steak.png")
    )
    monkeypatch.setattr(module, "S3_BUCKET_NAME", "mybucket")
    monkeypatch.setattr(module, "AWS_REGION", "ap-southeast-1")

    result = await module.confirm_candidate_item(candidate_item, "steak-preview.png")

    assert result["item_id"] == 77
    assert result["name"] == "Steak"

