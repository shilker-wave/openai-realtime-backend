import asyncio
import base64
import json
import logging

from typing import Any, Dict
from fastapi import WebSocket

from agents.realtime import RealtimeRunner, RealtimeSession, RealtimeSessionEvent

from utils.agents import leitdozent

logging.basicConfig(level=logging.INFO)
logger: logging.Logger = logging.getLogger(__name__)

class RealtimeWebSocketManager:
    def __init__(self) -> None:
        self.active_sessions: Dict[str, RealtimeSession] = {}
        self.session_contexts: Dict[str, Any] = {}
        self.websockets: Dict[str, WebSocket] = {}
        self.sample_rates: Dict[str, int] = {}


    def set_sample_rate(self, session_id: str, sample_rate: int) -> None:
            logger.info(f"Sample rate for session {session_id}: {sample_rate}")
            self.sample_rates[session_id] = sample_rate


    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        await websocket.accept()
        self.websockets[session_id] = websocket

        runner: RealtimeRunner = RealtimeRunner(
            starting_agent=leitdozent,
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
        session_context: Any = await runner.run()
        session: RealtimeSession = await session_context.__aenter__()
        self.active_sessions[session_id] = session
        self.session_contexts[session_id] = session_context

        # Start event processing task
        asyncio.create_task(self._process_events(session_id))


    async def disconnect(self, session_id: str) -> None:
        if session_id in self.session_contexts:
            await self.session_contexts[session_id].__aexit__(None, None, None)
            del self.session_contexts[session_id]
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        if session_id in self.websockets:
            del self.websockets[session_id]


    async def send_audio(self, session_id: str, audio_bytes: bytes) -> None:
        if session_id in self.active_sessions:
            await self.active_sessions[session_id].send_audio(audio_bytes)


    async def _process_events(self, session_id: str) -> None:
        try:
            session: RealtimeSession = self.active_sessions[session_id]
            websocket: WebSocket = self.websockets[session_id]

            async for event in session:
                event_data: Dict[str, Any] = await self._serialize_event(event)

                await websocket.send_text(json.dumps(event_data))

        except Exception as e:
            logger.error(f"Error processing events for session {session_id}: {e}")


    async def _serialize_event(self, event: RealtimeSessionEvent) -> Dict[str, Any]:
        base_event: Dict[str, Any] = {
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
            from typing import assert_never
            assert_never(event)

        return base_event