# AI-ATL Blind Assistance

FastAPI backend that fuses MiDaS depth estimation, YOLO-based detection, ElevenLabs speech services, and Snowflake Cortex ("SnowFlake") into a single pipeline for blind navigation. The server accepts frames from the frontend, produces structured object/center-distance data, and?when audio is supplied?routes the conversation through the transcription + LLM branch before handing the result back to the UI.

## Components
- `vision/pipeline.py` - MiDaS depth + YOLO detectors (indoor/general + outdoor navigation stack, including crosswalk/pole/curb detection).
- `vision/integrations/elevenlabs_bridge.py` - ElevenLabs TTS plus the teammate's speech-recognition workflow, adapted to accept base64 audio clips.
- `vision/integrations/snowflake_client.py` - Wrapper around `SNOWFLAKE.CORTEX.COMPLETE` for LLM responses.
- `vision/main.py` - FastAPI entrypoint orchestrating the entire flow and branching into transcription/LLM/TTS as needed.
- `vision/demo.py` - Multi-window OpenCV demo (YOLO boxes, MiDaS depth map, assistive overlay) with camera + environment switches.
- `full_demo.py` - Full-stack webcam + microphone demo that replicates the API lifecycle (vision + ElevenLabs + SnowFlake).

## Environment variables
Set these before launching the server (a `.env` file works too):

| Variable | Purpose |
| --- | --- |
| `ELEVENLABS_API_KEY` | Required for transcription + optional TTS branch |
| `SNOWFLAKE_ACCOUNT` | Snowflake account name (e.g., `xy12345.us-east-1`) |
| `SNOWFLAKE_USER` | Snowflake username |
| `SNOWFLAKE_PASSWORD` | Password for the above user |
| `SNOWFLAKE_ROLE` | (Optional) Role to assume |
| `SNOWFLAKE_WAREHOUSE` | (Optional) Warehouse for Cortex calls |
| `SNOWFLAKE_DATABASE` / `SNOWFLAKE_SCHEMA` | (Optional) Context for the session |
| `SNOWFLAKE_MODEL` | (Optional) Model name, defaults to `mistral-7b` |

> Audio decoding relies on `pydub`, which in turn requires FFmpeg on your PATH.

## Installation
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn vision.main:app --reload
```

## Request ? Response contract
POST `/analyze` with JSON:
```json
{
  "frame_id": "sample-0001",
  "timestamp": "2025-11-08T18:00:00Z",
  "frame_metadata": {"width": 1280, "height": 720, "focal_length_px": 900},
  "image_base64": "<RGB frame encoded via base64>",
  "environment": "indoor",
  "audio_base64": "<optional: wav/mp3/m4a clip>",
  "prompt_instructions": "<optional system prompt override>",
  "synthesize_voice": false
}
```

- `environment`: `"indoor"` (default) for general obstacle detection, `"outdoor"` for the road-aware stack (YOLO street agents + crosswalk/pole/curb detectors).
- `audio_base64`: attach when the user speaks; the backend runs the ElevenLabs speech-recognition workflow. Leave null to skip the conversational branch.
- `prompt_instructions`: optional string injected as the system message for SnowFlake. Defaults to a concise mobility assistant prompt.
- `synthesize_voice`: set `true` to receive an ElevenLabs MP3 (base64) of the Snowflake response.

Response payload:
```json
{
  "frame_id": "sample-0001",
  "objects": [
    {
      "label": "chair",
      "confidence": 0.88,
      "bounding_box": {"x_min": 0.12, "y_min": 0.35, "x_max": 0.32, "y_max": 0.78},
      "quadrant": "middle_left",
      "relative_depth_m": 0.42
    }
  ],
  "center_distance": {
    "distance_m": 0.51,
    "confidence": 0.80,
    "advisory": "Median relative depth (0-1 scale) derived from MiDaS center region."
  },
  "vision_summary": "chair in the middle left quadrant ...",
  "user_transcript": "Can I move forward?",
  "llm_response": "Front path is moderately clear; veer slightly right to avoid the chair ...",
  "audio_response_base64": "<optional ElevenLabs MP3>",
  "notes": "Indoor pipeline: YOLO (general objects) + MiDaS depth normalized 0-1. Convert to metric units downstream if needed."
}
```
- Depth values are MiDaS? 0-1 relative scale. Calibrate downstream if you need meters.
- `user_transcript`, `llm_response`, and `audio_response_base64` only appear when audio is provided *and* speech was recognized.

## Runtime flow
1. **Frame ingestion** - Frontend sends a base64 JPEG plus metadata (and optional audio clip).
2. **Vision pipeline** - YOLO detections + MiDaS depth produce the structured object package and center-distance summary, along with a natural-language `vision_summary`.
3. **Optional branch** - When audio is present, ElevenLabs transcription (via the supplied speech-recognition flow) produces user text. The summary + transcript (plus instructions) feed SnowFlake, and the LLM response is returned. If `synthesize_voice=true`, ElevenLabs also generates an MP3 in base64 for playback on the frontend.
4. **Frontend consumption** - The UI decides whether to simply read the object package or to present the conversational SnowFlake response/audio.

## Vision-only demo
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python vision/demo.py --camera 0 --environment outdoor
```
Displays three OpenCV windows (YOLO detections, MiDaS depth map, assistive overlay) and logs object/center packages every ~1.5s. Use `--environment indoor|outdoor` to flip models and `--camera N` for different webcams. Quit with `q`/`Esc`.

## Full-stack conversational demo
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python full_demo.py --camera 0 --environment indoor --voice
```
This script mimics a real frontend: it captures video, lets you press `T` to speak via the laptop mic, funnels frames + audio through the same path as the FastAPI endpoint (vision summary ? optional ElevenLabs transcription ? SnowFlake LLM ? optional ElevenLabs TTS), and renders the three OpenCV windows. Flags:
- `--camera N` ? select webcam index
- `--environment indoor|outdoor` ? toggle perception stack
- `--voice` ? play SnowFlake replies via ElevenLabs (also returned as text)
- `--prompt "..."` ? override the default SnowFlake system prompt
- `--interval 2.0` ? seconds between automatic frame submissions (press `T` to capture speech immediately)

Requirements: set `ELEVENLABS_API_KEY` and the `SNOWFLAKE_*` variables, ensure FFmpeg is on PATH for `pydub`, and have a working microphone (`PyAudio` backs the speech recognizer). The assistant only replies after it hears a full spoken request. Quit with `q`/`Esc`.

## Production to-do
1. **Depth calibration** - Map MiDaS values to real meters using your camera intrinsics and known distances.
2. **Performance** - Profile MiDaS_small + YOLOv8n, swap in other weights or TensorRT engines, and run on GPUs when available.
3. **Streaming glue** - Build a frame/audio ingestion loop (or WebRTC bridge) that throttles requests so the backend finishes each inference before the next one arrives.
4. **Observability** - Add metrics/logging for frame latency, Snowflake latency, transcription errors, and ElevenLabs synthesis time so ops can spot regressions quickly.



