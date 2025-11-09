from __future__ import annotations

import base64
import sys
import asyncio
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


def _extract_base64(data_url: str) -> str:
    if "," in data_url:
        return data_url.split(",", 1)[1]
    return data_url


def _serialize_detection(response: FrameAnalysisResponse) -> dict:
    return {
        "type": "detection",
        "frame_id": response.frame_id,
        "vision_summary": response.vision_summary,
        "message": response.vision_summary,
        "center_distance": response.center_distance.model_dump(),
        "objects": [
            {
                "label": obj.label,
                "confidence": obj.confidence,
                "bbox": [
                    obj.bounding_box.x_min,
                    obj.bounding_box.y_min,
                    obj.bounding_box.x_max,
                    obj.bounding_box.y_max,
                ],
                "quadrant": obj.quadrant,
                "distance": obj.relative_depth_m,
            }
            for obj in response.objects
        ],
        "notes": response.notes,
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    last_response: Optional[FrameAnalysisResponse] = None

    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")

            if message_type == "frame":
                image_data = data.get("data")
                if not image_data:
                    await websocket.send_json({"type": "error", "message": "Frame payload missing data"})
                    continue

                width = max(int(data.get("width") or 640), 1)
                height = max(int(data.get("height") or 480), 1)
                environment_raw = data.get("environment") or Environment.INDOOR.value

                try:
                    environment = Environment(environment_raw)
                except ValueError:
                    environment = Environment.INDOOR

                frame_id = data.get("frame_id") or data.get("timestamp") or "frame"
                payload = FrameAnalysisRequest(
                    frame_id=str(frame_id),
                    timestamp=datetime.utcnow(),
                    frame_metadata=FrameMetadata(width=width, height=height),
                    image_base64=_extract_base64(image_data),
                    environment=environment,
                )

                try:
                    response = await asyncio.to_thread(pipeline.process, payload)
                except Exception as exc:  # pragma: no cover - runtime diagnostics
                    await websocket.send_json({"type": "error", "message": f"Processing failed: {exc}"})
                    continue

                last_response = response
                await websocket.send_json(_serialize_detection(response))

            elif message_type == "describe":
                if last_response is not None:
                    await websocket.send_json(_serialize_detection(last_response))
                else:
                    await websocket.send_json(
                        {
                            "type": "detection",
                            "objects": [],
                            "message": "Vision system ready. Awaiting first frame.",
                        }
                    )
            else:
                await websocket.send_json({"type": "error", "message": "Unsupported message type"})
    except WebSocketDisconnect:
        return
