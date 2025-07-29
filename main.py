import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from utils.manager import RealtimeWebSocketManager
from config import Config

import numpy as np
from scipy.signal import resample

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

            if message["type"] == "sample_rate":
                manager.set_sample_rate(session_id, message["rate"])

            if message["type"] == "audio":
                int16_data = np.array(message["data"], dtype=np.int16)
                # audio_bytes: bytes = struct.pack(f"{len(int16_data)}h", *int16_data)
                audio_bytes: bytes = downsample_audio(int16_data, manager.sample_rates[session_id])
                await manager.send_audio(session_id, audio_bytes)

    except WebSocketDisconnect:
        await manager.disconnect(session_id)


def downsample_audio(audio: np.array, input_rate: int, target_rate: int = 24000) -> bytes:
    """Downsample audio data to the target sample rate that the OpenAI realtime API expects."""

    audio = audio.astype(np.float32) / 32768.0 # Normalize to float32 (-1.0 to 1.0)

    num_target_samples = int(len(audio) * target_rate / input_rate) # Calculate number of samples for target rate

    resampled = resample(audio, num_target_samples) # Resample using scipy

    resampled_int16 = np.clip(resampled * 32768.0, -32768, 32767).astype(np.int16) # Convert back to int16

    return resampled_int16.tobytes()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=Config.PORT)
