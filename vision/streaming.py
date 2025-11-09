"""Utilities for streaming vision detections to WebSocket clients."""

from __future__ import annotations

import asyncio
import base64
import threading
import time
from datetime import datetime
from typing import Any, Coroutine, Optional, Tuple

import cv2
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .schemas import Environment, FrameAnalysisResponse


def encode_frame_jpeg(frame) -> str:
    """Encode an OpenCV frame as base64 JPEG."""

    ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        raise RuntimeError("Unable to encode frame for transmission.")
    return base64.b64encode(encoded.tobytes()).decode("utf-8")


def serialize_detection(
    response: FrameAnalysisResponse,
    dimensions: Tuple[int, int],
    *,
    frame_base64: Optional[str] = None,
) -> dict:
    """Convert a ``FrameAnalysisResponse`` into a JSON-serializable payload."""

    width, height = dimensions
    objects = []
    for obj in response.objects:
        bbox = obj.bounding_box
        objects.append(
            {
                "label": obj.label,
                "confidence": obj.confidence,
                "bbox": [
                    float(bbox.x_min * width),
                    float(bbox.y_min * height),
                    float(bbox.x_max * width),
                    float(bbox.y_max * height),
                ],
                "distance": obj.relative_depth_m,
                "quadrant": obj.quadrant.value,
            }
        )

    payload = {
        "type": "detection",
        "frame_id": response.frame_id,
        "objects": objects,
        "center_distance": response.center_distance.model_dump(),
        "message": response.vision_summary,
        "notes": response.notes,
        "llm_response": response.llm_response,
        "user_transcript": response.user_transcript,
        "dimensions": {"width": width, "height": height},
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    if response.audio_response_base64:
        payload["audio_response_base64"] = response.audio_response_base64

    if frame_base64:
        if frame_base64.startswith("data:"):
            payload["frame"] = frame_base64
        else:
            payload["frame"] = f"data:image/jpeg;base64,{frame_base64}"

    return payload


class DetectionBroadcast:
    """Tracks the latest detections and streams them to WebSocket clients."""

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._latest_detection: Optional[dict] = None
        self._status_message: Optional[dict] = {"type": "status", "message": "Vision stream idle."}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._environment = Environment.INDOOR
        self._environment_lock = threading.Lock()

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Record the asyncio loop used for scheduling broadcast tasks."""

        if self._loop is None:
            self._loop = loop

    @property
    def environment(self) -> Environment:
        with self._environment_lock:
            return self._environment

    def set_environment(self, environment: Environment) -> None:
        with self._environment_lock:
            self._environment = environment

    def update_environment(self, value: str) -> Environment:
        try:
            environment = Environment(value)
        except ValueError:
            environment = Environment.INDOOR
        self.set_environment(environment)
        return environment

    async def register(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.add(websocket)

        await self.send_latest(websocket)

    async def unregister(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    async def send_latest(self, websocket: WebSocket) -> None:
        if self._latest_detection is not None:
            await websocket.send_json(self._latest_detection)
        elif self._status_message is not None:
            await websocket.send_json(self._status_message)
        else:
            await websocket.send_json({"type": "status", "message": "Waiting for vision data."})

    async def _broadcast(self, message: dict) -> None:
        clients: list[WebSocket]
        async with self._lock:
            clients = list(self._clients)

        for websocket in clients:
            try:
                await websocket.send_json(message)
            except Exception:
                await self.unregister(websocket)

    def _submit(self, coro: Coroutine[Any, Any, None]) -> None:
        loop = self._loop
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, loop)

    def send_status(self, message: str) -> None:
        payload = {"type": "status", "message": message}
        self._status_message = payload
        self._submit(self._broadcast(payload))

    def publish_detection(
        self,
        response: FrameAnalysisResponse,
        dimensions: Tuple[int, int],
        *,
        frame_base64: Optional[str] = None,
    ) -> None:
        payload = serialize_detection(response, dimensions, frame_base64=frame_base64)
        self._latest_detection = payload
        self._status_message = None
        self._submit(self._broadcast(payload))


def create_app(broadcast: DetectionBroadcast) -> FastAPI:
    """Create a FastAPI application wired to the detection broadcast."""

    app = FastAPI(
        title="AI-ATL Blind Assistance",
        version="1.0.0",
        description="Streams processed vision frames and detections to connected clients.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        broadcast.bind_loop(asyncio.get_running_loop())
        await websocket.send_json({"type": "status", "message": "Connected to Kora vision service."})
        await broadcast.register(websocket)

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
                    await broadcast.send_latest(websocket)
                elif message_type == "set_environment":
                    env_value = payload.get("environment", Environment.INDOOR.value)
                    environment = broadcast.update_environment(env_value)
                    await websocket.send_json(
                        {
                            "type": "status",
                            "message": f"Environment set to {environment.value}.",
                        }
                    )
                elif message_type in {"ping", "keepalive"}:
                    await websocket.send_json(
                        {
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                        }
                    )
                else:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": f"Unknown message type: {message_type}",
                        }
                    )
        finally:
            await broadcast.unregister(websocket)

    return app


class StreamServer:
    """Run the FastAPI broadcast app in a background thread."""

    def __init__(
        self,
        *,
        host: str = "0.0.0.0",
        port: int = 8000,
        log_level: str = "info",
    ) -> None:
        self.broadcast = DetectionBroadcast()
        self.app = create_app(self.broadcast)
        self._host = host
        self._port = port
        self._log_level = log_level
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None
        self._startup_event = threading.Event()

    def start(self, *, timeout: float = 5.0) -> None:
        if self._thread and self._thread.is_alive():
            return

        config = uvicorn.Config(
            self.app,
            host=self._host,
            port=self._port,
            log_level=self._log_level,
        )
        self._server = uvicorn.Server(config)
        self._server.install_signal_handlers = False

        def _run() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.broadcast.bind_loop(loop)
            self._startup_event.set()
            loop.run_until_complete(self._server.serve())

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        self._startup_event.wait(timeout)
        # Wait until the server reports as started to ensure the socket is ready.
        if self._server is not None:
            while not self._server.started:
                time.sleep(0.05)

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._server = None
