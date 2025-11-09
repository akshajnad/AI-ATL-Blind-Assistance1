from __future__ import annotations

import asyncio
import base64
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect

from config import get_settings
from ElevenLabs.main import get_assistant

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent))
    from integrations.snowflake_client import SnowflakeLLM
    from pipeline import VisionPipeline
    from schemas import (
        Environment,
        FrameAnalysisRequest,
        FrameAnalysisResponse,
        FrameMetadata,
    )
else:  # pragma: no cover
    from .integrations.snowflake_client import SnowflakeLLM
    from .pipeline import VisionPipeline
    from .schemas import (
        Environment,
        FrameAnalysisRequest,
        FrameAnalysisResponse,
        FrameMetadata,
    )


settings = get_settings()
assistant = get_assistant()
pipeline = VisionPipeline()
_snowflake_llm: Optional[SnowflakeLLM] = None

app = FastAPI(
    title="AI-ATL Blind Assistance",
    version="1.0.0",
    description="Receives vision frames + optional audio, runs MiDaS/YOLO, and enriches the payload with Snowflake responses.",
)


def _extract_base64(data_url: str) -> str:
    if "," in data_url:
        _, _, base64_data = data_url.partition(",")
        return base64_data
    return data_url


def _build_detection_payload(
    response: FrameAnalysisResponse,
    frame_dimensions: tuple[int, int],
    environment: Environment,
) -> dict[str, object]:
    width, height = frame_dimensions
    objects: list[dict[str, object]] = []
    min_depth: Optional[float] = None
    for obj in response.objects:
        bbox = obj.bounding_box
        x1 = bbox.x_min * width
        y1 = bbox.y_min * height
        x2 = bbox.x_max * width
        y2 = bbox.y_max * height
        if obj.relative_depth_m is not None:
            min_depth = obj.relative_depth_m if min_depth is None else min(min_depth, obj.relative_depth_m)
        objects.append(
            {
                "label": obj.label,
                "confidence": obj.confidence,
                "bbox": [x1, y1, x2, y2],
                "distance": obj.relative_depth_m,
                "quadrant": obj.quadrant.value,
            }
        )

    center_distance = response.center_distance.distance_m
    alert: Optional[str] = None
    if center_distance is not None:
        if center_distance < 0.2:
            alert = "Stop! Immediate obstacle detected ahead."
        elif center_distance < 0.4:
            alert = "Caution. Obstacle detected in front."

    if alert is None and min_depth is not None:
        if min_depth < 0.2:
            alert = "Stop! Object extremely close."
        elif min_depth < 0.4:
            alert = "Caution. Nearby object detected."

    message = alert or response.vision_summary

    return {
        "type": "detection",
        "frameId": response.frame_id,
        "timestamp": datetime.utcnow().isoformat(),
        "objects": objects,
        "message": message,
        "visionSummary": response.vision_summary,
        "centerDistance": {
            "distance": center_distance,
            "confidence": response.center_distance.confidence,
            "advisory": response.center_distance.advisory,
        },
        "environment": environment.value,
        "dimensions": {"width": width, "height": height},
        "alert": alert,
    }


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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


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
    return response


@app.websocket("/ws")
async def vision_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    last_payload: Optional[dict[str, object]] = None
    processing_lock = asyncio.Lock()

    async def process_frame_message(message: dict[str, object]) -> None:
        nonlocal last_payload
        image_data = message.get("data")
        if not isinstance(image_data, str):
            await websocket.send_text(json.dumps({"type": "error", "message": "Missing frame data"}))
            return

        base64_image = _extract_base64(image_data)

        frame_id = message.get("frameId")
        if not isinstance(frame_id, str):
            frame_id = str(uuid.uuid4())

        environment_value = message.get("environment")
        try:
            if isinstance(environment_value, str):
                environment = Environment(environment_value.lower())
            else:
                environment = Environment.INDOOR
        except ValueError:
            environment = Environment.INDOOR

        def run_pipeline() -> tuple[FrameAnalysisResponse, tuple[int, int]]:
            frame = pipeline._decode_frame(base64_image)
            height, width = frame.shape[:2]
            metadata = FrameMetadata(width=width, height=height)
            request = FrameAnalysisRequest(
                frame_id=frame_id,
                timestamp=datetime.utcnow(),
                frame_metadata=metadata,
                image_base64=base64_image,
                environment=environment,
            )
            result = pipeline.process(request, frame=frame)
            return result, (width, height)

        try:
            response, dimensions = await asyncio.to_thread(run_pipeline)
        except Exception as exc:  # pragma: no cover - runtime guard for model failures
            await websocket.send_text(json.dumps({"type": "error", "message": f"Vision processing failed: {exc}"}))
            return

        payload = _build_detection_payload(response, dimensions, environment)
        last_payload = payload
        await websocket.send_text(json.dumps(payload))

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "message": "Invalid JSON payload"}))
                continue

            message_type = message.get("type")

            if message_type == "frame":
                if processing_lock.locked():
                    continue
                async with processing_lock:
                    await process_frame_message(message)
            elif message_type == "describe":
                if last_payload is not None:
                    describe_payload = dict(last_payload)
                    describe_payload["type"] = "detection"
                    describe_payload["trigger"] = "describe"
                    await websocket.send_text(json.dumps(describe_payload))
                else:
                    await websocket.send_text(json.dumps({"type": "info", "message": "Vision system warming up."}))
            else:
                await websocket.send_text(json.dumps({"type": "error", "message": "Unsupported message type"}))
    except WebSocketDisconnect:
        return
