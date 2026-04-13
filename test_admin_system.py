import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from endpoints.chat_ws import router

# CHANGE THIS import to match your actual file location
# Example:
# from routers.admin import router


app = FastAPI()
app.include_router(router)
client = TestClient(app)


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


@patch("services.chat_service.run_chat", new_callable=AsyncMock)
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


@patch("services.chat_service.run_chat", new_callable=AsyncMock)
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


@patch("services.chat_service.run_chat", new_callable=AsyncMock)
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


@patch("services.chat_service.run_chat", new_callable=AsyncMock)
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


@patch("services.chat_service.run_chat", new_callable=AsyncMock)
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


@patch("services.chat_service.run_chat", new_callable=AsyncMock)
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


@patch("services.chat_service.run_chat", new_callable=AsyncMock)
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


@patch("services.chat_service.run_chat", new_callable=AsyncMock)
def test_chat_admin_run_chat_exception_bubbles_up(mock_run_chat):
    mock_run_chat.side_effect = RuntimeError("run_chat failed")

    payload = {
        "message": "Add burger",
        "chat_history": [],
        "state": {}
    }

    with pytest.raises(RuntimeError, match="run_chat failed"):
        client.post("/admin", json=payload)


def test_chat_admin_validation_error_when_message_missing():
    payload = {
        "chat_history": [],
        "state": {}
    }

    response = client.post("/admin", json=payload)

    assert response.status_code == 422


def test_chat_admin_validation_error_when_message_wrong_type():
    payload = {
        "message": 123,
        "chat_history": [],
        "state": {}
    }

    response = client.post("/admin", json=payload)

    assert response.status_code == 422