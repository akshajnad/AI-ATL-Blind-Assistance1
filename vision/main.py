from __future__ import annotations

import asyncio
import base64
import sys
from pathlib import Path
from typing import Optional, Tuple

import cv2
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from ElevenLabs.main import get_assistant

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent))
    from integrations.snowflake_client import SnowflakeLLM
    from pipeline import VisionPipeline
    from schemas import FrameAnalysisRequest, FrameAnalysisResponse, FrameMetadata, Environment
    from streaming import DetectionBroadcast, create_app
else:  # pragma: no cover
    from .integrations.snowflake_client import SnowflakeLLM
    from .pipeline import VisionPipeline
    from .schemas import FrameAnalysisRequest, FrameAnalysisResponse, FrameMetadata, Environment
    from .streaming import DetectionBroadcast, create_app


settings = get_settings()
assistant = get_assistant()
pipeline = VisionPipeline()
stream = DetectionBroadcast()
app = create_app(stream)
_snowflake_llm: Optional[SnowflakeLLM] = None
_last_response: Optional[FrameAnalysisResponse] = None
_last_dimensions: Tuple[int, int] = (640, 480)


class VisionStreamManager:
    """Manages a shared webcam loop and streams detections to connected clients."""

    def __init__(self, *, pipeline: VisionPipeline, frame_interval: float = 0.2) -> None:
        self._pipeline = pipeline
        self._frame_interval = max(0.05, frame_interval)
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._task: Optional[asyncio.Task[None]] = None
        self._running = False
        self._camera_index = 0
        self._environment = Environment.INDOOR
        self._latest_payload: Optional[dict] = None

    async def add_client(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.add(websocket)
            if not self._running:
                self._running = True
                self._task = asyncio.create_task(self._run_loop())

        if self._latest_payload is not None:
            await self._safe_send(websocket, self._latest_payload)

    async def remove_client(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)
            if not self._clients and self._running:
                self._running = False

        task: Optional[asyncio.Task[None]]
        async with self._lock:
            task = self._task if not self._clients else None

        if task is not None:
            await task

    async def set_environment(self, environment_value: str) -> None:
        try:
            environment = Environment(environment_value)
        except ValueError:
            environment = Environment.INDOOR
        async with self._lock:
            self._environment = environment

    async def send_latest(self, websocket: WebSocket) -> None:
        if self._latest_payload is not None:
            await self._safe_send(websocket, self._latest_payload)
        else:
            await self._safe_send(websocket, {"type": "status", "message": "Vision stream warming up."})

    async def _safe_send(self, websocket: WebSocket, message: dict) -> None:
        try:
            await websocket.send_json(message)
        except Exception:
            await self.remove_client(websocket)

    async def _broadcast(self, message: dict) -> None:
        clients_snapshot: list[WebSocket]
        async with self._lock:
            clients_snapshot = list(self._clients)

        for client in clients_snapshot:
            await self._safe_send(client, message)

    async def _run_loop(self) -> None:
        try:
            cap = cv2.VideoCapture(self._camera_index)
            if not cap.isOpened():
                await self._broadcast({"type": "error", "message": "Unable to access webcam. Ensure no other application is using it."})
                return

            await self._broadcast({"type": "status", "message": "Vision stream active."})

            while True:
                async with self._lock:
                    running = self._running and bool(self._clients)
                    environment = self._environment

                if not running:
                    break

                ret, frame = cap.read()
                if not ret or frame is None:
                    await asyncio.sleep(0.1)
                    continue

                height, width = frame.shape[:2]
                frame_base64 = frame_to_base64(frame)
                request = FrameAnalysisRequest(
                    frame_id=str(uuid4()),
                    timestamp=datetime.utcnow(),
                    frame_metadata=FrameMetadata(width=width, height=height),
                    image_base64=frame_base64,
                    environment=environment,
                )

                loop = asyncio.get_running_loop()
                try:
                    response = await loop.run_in_executor(None, self._pipeline.process, request)
                except Exception as exc:  # pragma: no cover - runtime diagnostics
                    await self._broadcast({"type": "error", "message": f"Vision pipeline error: {exc}"})
                    await asyncio.sleep(0.3)
                    continue

                global _last_response, _last_dimensions
                _last_response = response
                _last_dimensions = (width, height)

                payload = _serialize_detection(response, (width, height))
                payload["frame"] = f"data:image/jpeg;base64,{frame_base64}"
                self._latest_payload = payload

                await self._broadcast(payload)
                await asyncio.sleep(self._frame_interval)
        finally:
            cap.release()
            async with self._lock:
                self._task = None
                self._running = False


def frame_to_base64(frame) -> str:
    ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        raise RuntimeError("Unable to encode frame for transmission.")
    return base64.b64encode(encoded.tobytes()).decode("utf-8")


stream_manager = VisionStreamManager(pipeline=pipeline)

app = FastAPI(
    title="AI-ATL Blind Assistance",
    version="1.0.0",
    description="Receives vision frames + optional audio, runs MiDaS/YOLO, and enriches the payload with Snowflake responses.",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_snowflake_llm() -> SnowflakeLLM:
    global _snowflake_llm
    if _snowflake_llm is None:
        account = settings.snowflake_account
        user = settings.snowflake_user
        password = settings.snowflake_password
        if not (account and user and password):
            raise RuntimeError("SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, and SNOWFLAKE_PASSWORD must be configured.")
        _snowflake_llm = SnowflakeLLM(
            account=account,
            user=user,
            password=password,
            role=settings.snowflake_role,
            warehouse=settings.snowflake_warehouse,
            database=settings.snowflake_database,
            schema=settings.snowflake_schema,
            model=settings.snowflake_model,
        )
    return _snowflake_llm


def _serialize_detection(response: FrameAnalysisResponse, dimensions: Tuple[int, int]) -> dict:
    width, height = dimensions
    objects = []
    for obj in response.objects:
        bbox = obj.bounding_box
        objects.append({
            'label': obj.label,
            'confidence': obj.confidence,
            'bbox': [
                float(bbox.x_min * width),
                float(bbox.y_min * height),
                float(bbox.x_max * width),
                float(bbox.y_max * height),
            ],
            'distance': obj.relative_depth_m,
            'quadrant': obj.quadrant.value,
        })

    payload = {
        'type': 'detection',
        'frame_id': response.frame_id,
        'objects': objects,
        'center_distance': response.center_distance.model_dump(),
        'message': response.vision_summary,
        'notes': response.notes,
        'llm_response': response.llm_response,
        'user_transcript': response.user_transcript,
        'dimensions': {'width': width, 'height': height},
        'timestamp': datetime.utcnow().isoformat() + 'Z',
    }

    if response.audio_response_base64:
        payload['audio_response_base64'] = response.audio_response_base64

    return payload


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json({"type": "status", "message": "Connected to Kora vision service."})
    await stream_manager.add_client(websocket)

    try:
        while True:
            try:
                payload = await websocket.receive_json()
            except WebSocketDisconnect:
                break
            except Exception as exc:
                await websocket.send_json({"type": "error", "message": f"Invalid message format: {exc}"})
                continue

            message_type = payload.get("type")
            if message_type == "describe":
                await stream_manager.send_latest(websocket)
            elif message_type == "set_environment":
                environment_value = payload.get("environment", Environment.INDOOR.value)
                await stream_manager.set_environment(environment_value)
                await websocket.send_json({"type": "status", "message": f"Environment set to {environment_value}."})
            elif message_type in {"ping", "keepalive"}:
                await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat() + "Z"})
            else:
                await websocket.send_json({"type": "error", "message": f"Unknown message type: {message_type}"})
    finally:
        await stream_manager.remove_client(websocket)


@app.post("/analyze", response_model=FrameAnalysisResponse)
async def analyze(payload: FrameAnalysisRequest) -> FrameAnalysisResponse:
    try:
        response = pipeline.process(payload)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    update_data: dict[str, Optional[str]] = {}
    if payload.audio_base64:
        try:
            transcript = assistant.transcribe_base64(payload.audio_base64)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Audio transcription failed: {exc}") from exc

        update_data["user_transcript"] = transcript
        if transcript:
            prompt = assistant.build_prompt(
                vision_summary=response.vision_summary,
                user_text=transcript,
                instructions=payload.prompt_instructions,
                conversation_history=[],
            )
            try:
                llm_text = get_snowflake_llm().complete(prompt)
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"Snowflake LLM error: {exc}") from exc
            update_data["llm_response"] = llm_text

            if payload.synthesize_voice:
                try:
                    audio_bytes = assistant.synthesize(llm_text)
                except Exception as exc:
                    raise HTTPException(status_code=502, detail=f"ElevenLabs synthesis failed: {exc}") from exc
                update_data["audio_response_base64"] = base64.b64encode(audio_bytes).decode("utf-8")
        else:
            update_data["llm_response"] = None

    if update_data:
        response = response.model_copy(update=update_data)
    global _last_response, _last_dimensions
    metadata = payload.frame_metadata
    _last_response = response
    _last_dimensions = (metadata.width, metadata.height)

    frame_base64 = payload.image_base64
    if frame_base64.startswith("data:"):
        frame_base64 = frame_base64.split(",", 1)[1]

    stream.publish_detection(
        response,
        _last_dimensions,
        frame_base64=frame_base64,
    )

    return response
