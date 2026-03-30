from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocket, WebSocketDisconnect

from endpoints.chat_ws import router as chat_ws_router
from endpoints.menu_item import router as menu_item_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_ws_router)
app.include_router(menu_item_router)


@app.websocket("/ws/test")
async def ws_test(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("connected")
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"echo: {data}")
    except WebSocketDisconnect:
        pass


@app.get("/health")
def health_check():
    return {"status": "ok"}