import json
import logging
import struct
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from utils.manager import RealtimeWebSocketManager
from config import Config

logging.basicConfig(level=logging.INFO)
logger: logging.Logger = logging.getLogger(__name__)

manager: RealtimeWebSocketManager = RealtimeWebSocketManager()

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    yield

app: FastAPI = FastAPI(lifespan=lifespan)

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    await manager.connect(websocket, session_id)
    try:
        while True:
            data: str = await websocket.receive_text()
            message: dict = json.loads(data)

            if message["type"] == "audio":
                # Convert int16 array to bytes
                int16_data: list[int] = message["data"]
                audio_bytes: bytes = struct.pack(f"{len(int16_data)}h", *int16_data)
                await manager.send_audio(session_id, audio_bytes)

    except WebSocketDisconnect:
        await manager.disconnect(session_id)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=Config.PORT)
