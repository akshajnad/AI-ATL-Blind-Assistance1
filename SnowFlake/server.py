from __future__ import annotations

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import time
import threading

try:
    from vision.schemas import FrameAnalysisResponse, DetectedObject
except Exception:
    # support running as script
    from vision.schemas import FrameAnalysisResponse, DetectedObject

try:
    from ElevenLabs.obstacle_alert import ObstacleAlertSystem
except Exception:
    # Fallback import
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from ElevenLabs.obstacle_alert import ObstacleAlertSystem

app = FastAPI(title="SnowFlake Bridge", version="0.1")

# short-term memory for last frame
_memory: dict[str, any] = {}
# Use enhanced obstacle alert system with deduplication and approach detection
processor = ObstacleAlertSystem(
    min_alert_interval_s=3.0,
    object_memory_s=10.0,
    alert_cooldown_s=30.0,
)


class ConverseRequest(BaseModel):
    text: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/process_frame")
async def process_frame(payload: FrameAnalysisResponse):
    """Accept a FrameAnalysisResponse (from vision) and evaluate risk.

    Returns JSON with 'spoken' and 'message' when an alert was generated.
    """
    try:
        # store latest frame in memory
        _memory["last_frame"] = payload
        # process frame asynchronously so HTTP returns quickly
        def _proc():
            try:
                processor.process_frame(payload)
            except Exception as e:
                print("Processor error:", e)

        threading.Thread(target=_proc, daemon=True).start()
        return JSONResponse({"accepted": True, "frame_id": payload.frame_id})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/converse")
def converse(req: ConverseRequest):
    """Simple conversational endpoint that answers based on last frame.

    It synthesizes audio via ElevenLabs and returns the path to the mp3.
    """
    last: Optional[FrameAnalysisResponse] = _memory.get("last_frame")
    text = req.text.lower()
    resp_text = "I don't have scene information right now."
    if last is None:
        resp_text = "I don't have a recent scene to describe."
    else:
        objs = last.objects or []
        if "how far" in text or "how far" == text.strip():
            if objs:
                top = objs[0]
                dist_label = "unknown distance"
                # use processor's distance description
                dist_label = processor._distance_description(top.relative_depth_m)
                resp_text = f"The nearest object is a {top.label} {dist_label}."
            else:
                resp_text = "I don't see any objects right now."
        elif "where" in text or "where is" in text:
            if objs:
                top = objs[0]
                pos = processor._position_from_quadrant(top.quadrant)
                resp_text = f"The {top.label} is on your {pos}."
            else:
                resp_text = "I don't see any objects to locate."
        elif "what should i do" in text or "what do i do" in text:
            if objs:
                top = objs[0]
                from ElevenLabs.obstacle_alert import DangerLevel
                danger = DangerLevel.from_distance(top.relative_depth_m)
                action = processor._action_for_object(top.label, danger)
                if action:
                    resp_text = f"I suggest you {action.lower()}."
                else:
                    resp_text = "No immediate action needed. Stay aware of your surroundings."
            else:
                resp_text = "No immediate action needed. Stay aware of your surroundings."
        else:
            # default: short scene summary
            if objs:
                summary = ", ".join(f"{o.label}({o.quadrant})" for o in objs[:3])
                resp_text = f"I see: {summary}. Ask me 'how far' or 'where' for details."
            else:
                resp_text = "I don't see anything noteworthy right now."

    # synthesize via ElevenLabs and return path (and also speak if desired)
    try:
        # ElevenLabs TTS helper produces a file 'Audio.mp3'
        from ElevenLabs.main import text_to_speech_file

        out_path = text_to_speech_file(resp_text, play_audio=False)
        return FileResponse(out_path, media_type="audio/mpeg", filename="response.mp3")
    except Exception as exc:
        # fall back to JSON
        return {"text": resp_text, "error": str(exc)}
