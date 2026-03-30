from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any

from fastapi import APIRouter

from services.chat_service import run_chat

router = APIRouter()


class AdminChatRequest(BaseModel):
    message: str
    chat_history: list[dict[str, Any]] = Field(default_factory=list)
    state: dict[str, Any] = Field(default_factory=dict)


class AdminMessagePayload(BaseModel):
    response: str
    candidateItem: dict[str, Any] | None = None
    chat_history: list[dict[str, Any]] = Field(default_factory=list)
    state_delta: dict[str, Any] = Field(default_factory=dict)


class AdminChatResponse(BaseModel):
    message: AdminMessagePayload


@router.post("/admin", response_model=AdminChatResponse)
async def chat_admin(payload: AdminChatRequest):
    user_message = payload.message.strip()
    history = payload.chat_history
    state = payload.state

    if not user_message:
        return AdminChatResponse(
            message=AdminMessagePayload(
                response="Please enter a message.",
                candidateItem=None,
                chat_history=history,
                state_delta=state,
            )
        )

    result = await run_chat(user_message, history, state)

    return AdminChatResponse(**result)