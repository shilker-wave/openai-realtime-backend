import asyncio
import base64
import json
import logging
import struct
from contextlib import asynccontextmanager
from typing import Any, assert_never

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from agents import function_tool
from agents.realtime import RealtimeAgent, RealtimeRunner, RealtimeSession, RealtimeSessionEvent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@function_tool
def get_weather(city: str) -> str:
    """Gibt das Wetter für eine Stadt zurück, wenn der Benutzer danach fragt."""
    return f"Das Wetter in {city} ist sonnig."


@function_tool
def get_secret_number() -> int:
    """Gibt die geheime Zahl zurück, wenn der Benutzer danach fragt."""
    return 42


programming_agent = RealtimeAgent(
    name="Programming Agent",
    instructions=(
        "Du bist ein Experte aller Programmiersprachen."
        "Beantworte alle Fragen zu Programmierung, Code und Softwareentwicklung."
    ),
    handoff_description="Experte für Programmierung und Softwareentwicklung",
)


haiku_agent = RealtimeAgent(
    name="Haiku Agent",
    instructions=(
        "Du bist ein Haiku-Dichter."
        "Du darfst NUR in traditioneller Haikuform (5-7-5 Silben) antworten."
        "Jede Antwort muss ein Haiku sein."
        "Bleibe immer in dieser Form."
    ),
    handoff_description="Erstellt ein Haiku zu einem beliebigen Thema",
)


agent = RealtimeAgent(
    name="Assistant",
    instructions=(
        "Du bist ein Dozent im IT-Bereich."
        "Wenn der Benutzer Poesie oder Haikus anfordert, leite an den Haiku-Agenten weiter."
        "Bei Fragen zu Programmierthemen, leite an den 'Programming Agent' weiter."
        "Ansonsten antworte auf alle anderen Fragen."
    ),
    tools=[
        get_weather,
        get_secret_number,
    ],
    handoffs=[programming_agent, haiku_agent],
)


class RealtimeWebSocketManager:
    def __init__(self):
        self.active_sessions: dict[str, RealtimeSession] = {}
        self.session_contexts: dict[str, Any] = {}
        self.websockets: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.websockets[session_id] = websocket

        runner = RealtimeRunner(
            starting_agent=agent,
            config={
            "model_settings": {
                "model_name": "gpt-4o-mini-realtime-preview-2024-12-17",
                "voice": "alloy",
                "modalities": ["text", "audio"],
                "input_audio_transcription": {
                    "model": "whisper-1",
                    "language": "de",
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 200
                }
            }
        })
        session_context = await runner.run()
        session = await session_context.__aenter__()
        self.active_sessions[session_id] = session
        self.session_contexts[session_id] = session_context

        # Start event processing task
        asyncio.create_task(self._process_events(session_id))

    async def disconnect(self, session_id: str):
        if session_id in self.session_contexts:
            await self.session_contexts[session_id].__aexit__(None, None, None)
            del self.session_contexts[session_id]
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        if session_id in self.websockets:
            del self.websockets[session_id]

    async def send_audio(self, session_id: str, audio_bytes: bytes):
        if session_id in self.active_sessions:
            await self.active_sessions[session_id].send_audio(audio_bytes)

    async def _process_events(self, session_id: str):
        try:
            session = self.active_sessions[session_id]
            websocket = self.websockets[session_id]

            async for event in session:
                event_data = await self._serialize_event(event)
                await websocket.send_text(json.dumps(event_data))
        except Exception as e:
            logger.error(f"Error processing events for session {session_id}: {e}")

    async def _serialize_event(self, event: RealtimeSessionEvent) -> dict[str, Any]:
        base_event: dict[str, Any] = {
            "type": event.type,
        }

        if event.type == "agent_start":
            base_event["agent"] = event.agent.name
        elif event.type == "agent_end":
            base_event["agent"] = event.agent.name
        elif event.type == "handoff":
            base_event["from"] = event.from_agent.name
            base_event["to"] = event.to_agent.name
        elif event.type == "tool_start":
            base_event["tool"] = event.tool.name
        elif event.type == "tool_end":
            base_event["tool"] = event.tool.name
            base_event["output"] = str(event.output)
        elif event.type == "audio":
            base_event["audio"] = base64.b64encode(event.audio.data).decode("utf-8")
        elif event.type == "audio_interrupted":
            pass
        elif event.type == "audio_end":
            pass
        elif event.type == "history_updated":
            base_event["history"] = [item.model_dump(mode="json") for item in event.history]
        elif event.type == "history_added":
            pass
        elif event.type == "guardrail_tripped":
            base_event["guardrail_results"] = [
                {"name": result.guardrail.name} for result in event.guardrail_results
            ]
        elif event.type == "raw_model_event":
            base_event["raw_model_event"] = {
                "type": event.data.type,
            }
        elif event.type == "error":
            base_event["error"] = str(event.error) if hasattr(event, "error") else "Unknown error"
        else:
            assert_never(event)

        return base_event


manager = RealtimeWebSocketManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message["type"] == "audio":
                # Convert int16 array to bytes
                int16_data = message["data"]
                audio_bytes = struct.pack(f"{len(int16_data)}h", *int16_data)
                await manager.send_audio(session_id, audio_bytes)

    except WebSocketDisconnect:
        await manager.disconnect(session_id)


app.mount("/", StaticFiles(directory="static", html=True), name="static")


@app.get("/")
async def read_index():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
