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


import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock

# change this import to your actual module path
# example:
# from routers.menu_item import (
#     _slugify,
#     build_image_prompt,
#     upload_image_bytes_to_s3,
#     save_candidate_item_to_db,
#     preview_candidate_item_image,
#     confirm_candidate_item,
#     move_preview_to_img,
#     confirm_menu_item_with_image,
# )

import endpoints.menu_item as module


class DummyPayload:
    def __init__(self, **kwargs):
        self.name = kwargs.get("name")
        self.description = kwargs.get("description")
        self.price = kwargs.get("price")
        self.category_id = kwargs.get("category_id")
        self.subcategory_id = kwargs.get("subcategory_id")
        self.is_chef_recommend = kwargs.get("is_chef_recommend", False)
        self.preview_image_name = kwargs.get("preview_image_name")

    def dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "category_id": self.category_id,
            "subcategory_id": self.subcategory_id,
            "is_chef_recommend": self.is_chef_recommend,
            "preview_image_name": self.preview_image_name,
        }


def test_slugify_basic():
    assert module._slugify("Chicken Rice") == "chicken-rice"


def test_slugify_special_chars():
    assert module._slugify("  Chef's Special!!  ") == "chef-s-special"


def test_slugify_empty_returns_default():
    assert module._slugify("") == "menu-item"
    assert module._slugify(None) == "menu-item"


def test_build_image_prompt():
    candidate_item = {
        "name": "Truffle Pasta",
        "description": "Creamy mushroom sauce with parmesan"
    }

    prompt = module.build_image_prompt(candidate_item)

    assert "Professional food photography of Truffle Pasta." in prompt
    assert "Creamy mushroom sauce with parmesan" in prompt
    assert "Restaurant menu photo" in prompt


def test_upload_image_bytes_to_s3(monkeypatch):
    mock_s3 = MagicMock()
    monkeypatch.setattr(module, "s3_client", mock_s3)
    monkeypatch.setattr(module, "AWS_REGION", "ap-southeast-1")

    result = module.upload_image_bytes_to_s3(b"fake-bytes", "public/previews/test.png")

    mock_s3.upload_fileobj.assert_called_once()
    assert result == "https://seasonedspoonimages.s3.ap-southeast-1.amazonaws.com/public/previews/test.png"


@pytest.mark.asyncio
async def test_save_candidate_item_to_db(monkeypatch):
    candidate_item = {
        "name": "Burger",
        "description": "Beef burger",
        "price": 12.5,
        "category_id": 1,
        "subcategory_id": 2,
        "is_chef_recommend": True,
        "image_url": "image.png",
    }

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "itemId": 123,
        "name": "Burger",
        "imageUrl": "https://example.com/image.png",
    }
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

    result = await module.save_candidate_item_to_db(candidate_item, token="abc123")

    mock_client.post.assert_called_once_with(
        "http://test-server/api/menu-item/confirm",
        json={
            "name": "Burger",
            "description": "Beef burger",
            "price": 12.5,
            "categoryId": 1,
            "subcategoryId": 2,
            "isChefRecommend": True,
            "image_url": "image.png",
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer abc123",
        },
    )

    assert result["itemId"] == 123


@pytest.mark.asyncio
async def test_preview_candidate_item_image(monkeypatch):
    monkeypatch.setattr(module, "generate_menu_item_image_bytes", lambda candidate_item: b"img-bytes")
    monkeypatch.setattr(
        module,
        "upload_image_bytes_to_s3",
        lambda image_bytes, key: f"https://example.com/{key}"
    )

    class DummyUuid:
        hex = "abc123"

    monkeypatch.setattr(module.uuid, "uuid4", lambda: DummyUuid())

    candidate_item = {
        "name": "Fried Rice",
        "description": "Wok-fried rice"
    }

    result = await module.preview_candidate_item_image(candidate_item)

    assert result["message"] == "Preview generated. Confirm if you want to save this menu item."
    assert result["type"] == "candidate_preview"
    assert result["preview_id"] == "abc123"
    assert result["preview_image_name"] == "fried-rice-preview-abc123.png"
    assert result["preview_image_url"] == "https://example.com/public/previews/fried-rice-preview-abc123.png"
    assert result["candidate_item"] == candidate_item


@pytest.mark.asyncio
async def test_confirm_candidate_item(monkeypatch):
    candidate_item = {
        "name": "Laksa",
        "description": "Spicy noodle soup"
    }

    mock_save = AsyncMock(return_value={
        "itemId": 88,
        "name": "Laksa",
        "imageUrl": "https://db-image-url.com/laksa.png"
    })
    mock_move = AsyncMock(return_value="https://final-s3-url.com/public/img/laksa.png")

    monkeypatch.setattr(module, "save_candidate_item_to_db", mock_save)
    monkeypatch.setattr(module, "move_preview_to_img", mock_move)

    result = await module.confirm_candidate_item(candidate_item, "laksa-preview.png", token="token123")

    assert candidate_item["image_url"] == "laksa-preview.png"
    mock_save.assert_awaited_once_with(candidate_item, "token123")
    mock_move.assert_awaited_once_with("laksa-preview.png")

    assert result == {
        "db_result": {
            "itemId": 88,
            "name": "Laksa",
            "imageUrl": "https://db-image-url.com/laksa.png"
        },
        "message": "Menu item inserted successfully.",
        "item_id": 88,
        "name": "Laksa",
        "image_url": "https://db-image-url.com/laksa.png",
    }


@pytest.mark.asyncio
async def test_confirm_candidate_item_fallback_image_url(monkeypatch):
    candidate_item = {"name": "Pasta"}

    mock_save = AsyncMock(return_value={
        "item_id": 55,
        "name": "Pasta",
    })
    mock_move = AsyncMock(return_value="https://final-s3-url.com/public/img/pasta.png")

    monkeypatch.setattr(module, "save_candidate_item_to_db", mock_save)
    monkeypatch.setattr(module, "move_preview_to_img", mock_move)
    monkeypatch.setattr(module, "S3_BUCKET_NAME", "mybucket")
    monkeypatch.setattr(module, "AWS_REGION", "ap-southeast-1")

    result = await module.confirm_candidate_item(candidate_item, "pasta-preview.png")

    assert result["item_id"] == 55
    assert result["image_url"] == (
        "https://mybucket.s3.ap-southeast-1.amazonaws.com/public/previews/pasta-preview.png"
    )


@pytest.mark.asyncio
async def test_move_preview_to_img(monkeypatch):
    mock_s3 = MagicMock()
    monkeypatch.setattr(module, "s3_client", mock_s3)
    monkeypatch.setattr(module, "S3_BUCKET_NAME", "mybucket")
    monkeypatch.setattr(module, "AWS_REGION", "ap-southeast-1")

    result = await module.move_preview_to_img("preview.png")

    mock_s3.copy_object.assert_called_once_with(
        Bucket="mybucket",
        CopySource={
            "Bucket": "mybucket",
            "Key": "public/previews/preview.png",
        },
        Key="public/img/preview.png",
    )

    mock_s3.delete_object.assert_called_once_with(
        Bucket="mybucket",
        Key="public/previews/preview.png",
    )

    assert result == "https://mybucket.s3.ap-southeast-1.amazonaws.com/public/img/preview.png"


@pytest.mark.asyncio
async def test_confirm_menu_item_with_image_success(monkeypatch):
    payload = DummyPayload(
        name="Pizza",
        description="Cheesy pizza",
        price=18.0,
        category_id=1,
        subcategory_id=2,
        is_chef_recommend=True,
        preview_image_name="pizza-preview.png",
    )

    mock_confirm = AsyncMock(return_value={
        "db_result": {"itemId": 1},
        "message": "Menu item inserted successfully.",
        "item_id": 1,
        "name": "Pizza",
        "image_url": "https://example.com/pizza.png",
    })

    monkeypatch.setattr(module, "confirm_candidate_item", mock_confirm)

    result = await module.confirm_menu_item_with_image(payload)

    mock_confirm.assert_awaited_once_with(
        {
            "name": "Pizza",
            "description": "Cheesy pizza",
            "price": 18.0,
            "category_id": 1,
            "subcategory_id": 2,
            "is_chef_recommend": True,
        },
        "pizza-preview.png",
    )

    assert result == {
        "db_result": {"itemId": 1},
        "message": "Menu item inserted successfully.",
        "item_id": 1,
        "name": "Pizza",
        "image_url": "https://example.com/pizza.png",
    }


@pytest.mark.asyncio
async def test_confirm_menu_item_with_image_missing_name_returns_500_with_current_code():
    payload = DummyPayload(
        name="   ",
        preview_image_name="test.png",
    )

    with pytest.raises(HTTPException) as exc:
        await module.confirm_menu_item_with_image(payload)

    # current code catches the 400 and rethrows 500
    assert exc.value.status_code == 500
    assert "Item name is required." in str(exc.value.detail)


@pytest.mark.asyncio
async def test_confirm_menu_item_with_image_missing_preview_returns_500_with_current_code():
    payload = DummyPayload(
        name="Valid Name",
        preview_image_name=None,
    )

    with pytest.raises(HTTPException) as exc:
        await module.confirm_menu_item_with_image(payload)

    # current code catches the 400 and rethrows 500
    assert exc.value.status_code == 500
    assert "preview_image_name is required." in str(exc.value.detail)