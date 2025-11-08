from __future__ import annotations

import base64
import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException

from config import get_settings
from ElevenLabs.main import get_assistant
from ElevenLabs.obstacle_alert import ObstacleAlertSystem

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent))
    from integrations.snowflake_client import SnowflakeLLM
    from pipeline import VisionPipeline
    from schemas import FrameAnalysisRequest, FrameAnalysisResponse
else:  # pragma: no cover
    from .integrations.snowflake_client import SnowflakeLLM
    from .pipeline import VisionPipeline
    from .schemas import FrameAnalysisRequest, FrameAnalysisResponse


settings = get_settings()
assistant = get_assistant()
pipeline = VisionPipeline()
_snowflake_llm: Optional[SnowflakeLLM] = None
# Initialize obstacle alert system with intelligent deduplication and approach detection
obstacle_alert = ObstacleAlertSystem(
    min_alert_interval_s=5.0,   # minimum 5 seconds between any alerts
    object_memory_s=10.0,        # remember objects for 10 seconds
    alert_cooldown_s=30.0,       # don't re-alert same object within 30 seconds
)

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

    # Process frame through obstacle alert system for continuous monitoring
    # This runs in parallel with voice interactions and provides proactive safety alerts
    try:
        alert_message = obstacle_alert.process_frame(response)
        if alert_message:
            print(f"[OBSTACLE ALERT] {alert_message}")
    except Exception as exc:
        # Don't fail the request if obstacle detection has issues
        print(f"[OBSTACLE ALERT] Error processing alerts: {exc}")

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
