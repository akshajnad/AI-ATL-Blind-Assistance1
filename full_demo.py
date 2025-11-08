from __future__ import annotations

import argparse
import base64
import io
import queue
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import speech_recognition as sr
from pydub import AudioSegment
from pydub.playback import play

PROJECT_ROOT = Path(__file__).resolve().parent
VISION_DIR = PROJECT_ROOT / "vision"

if str(VISION_DIR) not in sys.path:
    sys.path.append(str(VISION_DIR))

from config import get_settings
from ElevenLabs.main import get_assistant
from vision.integrations.snowflake_client import SnowflakeLLM
from vision.pipeline import VisionPipeline
from vision.schemas import Environment, FrameAnalysisRequest, FrameAnalysisResponse, FrameMetadata

WINDOW_VISION = "Assistive Overlay"
WINDOW_YOLO = "YOLO Detections"
WINDOW_DEPTH = "MiDaS Depth"

INACTIVITY_TIMEOUT = 15.0  # seconds of silence before ending the convo


class SpeechListener:
    """Continuously captures phrases and stores them as base64 wav strings."""

    def __init__(
        self,
        recognizer: sr.Recognizer,
        microphone: sr.Microphone,
        *,
        phrase_time_limit: float,
    ) -> None:
        self._queue: "queue.Queue[str]" = queue.Queue()
        self._stopper = recognizer.listen_in_background(
            microphone,
            self._callback,
            phrase_time_limit=phrase_time_limit,
        )

    def _callback(self, recognizer: sr.Recognizer, audio: sr.AudioData) -> None:  # pylint: disable=unused-argument
        try:
            wav_bytes = audio.get_wav_data()
            audio_b64 = base64.b64encode(wav_bytes).decode("utf-8")
            self._queue.put(audio_b64)
            print(f"\n[VOICE] Captured user speech chunk ({len(wav_bytes)} bytes).")
        except Exception as exc:  # pragma: no cover
            print(f"[VOICE] Error capturing audio: {exc}")

    def get_audio(self) -> Optional[str]:
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def stop(self) -> None:
        if self._stopper:
            self._stopper(wait_for_stop=False)


def frame_to_base64(frame: np.ndarray) -> str:
    success, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not success:
        raise RuntimeError("Failed to encode frame as JPEG")
    return base64.b64encode(encoded.tobytes()).decode("utf-8")


def draw_yolo_view(frame: np.ndarray, response: FrameAnalysisResponse) -> np.ndarray:
    view = frame.copy()
    h, w = view.shape[:2]
    for obj in response.objects:
        x_min = int(obj.bounding_box.x_min * w)
        y_min = int(obj.bounding_box.y_min * h)
        x_max = int(obj.bounding_box.x_max * w)
        y_max = int(obj.bounding_box.y_max * h)
        cv2.rectangle(view, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2, cv2.LINE_AA)
        label = f"{obj.label} ({obj.confidence:.2f})"
        cv2.putText(view, label, (x_min, max(18, y_min - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2, cv2.LINE_AA)
    cv2.putText(view, "YOLO detections", (16, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    return view


def draw_overlay(frame: np.ndarray, response: FrameAnalysisResponse, environment: Environment, llm_text: Optional[str]) -> np.ndarray:
    annotated = frame.copy()
    h, w = annotated.shape[:2]
    grid_color = (80, 80, 80)
    for i in range(1, 3):
        cv2.line(annotated, (i * w // 3, 0), (i * w // 3, h), grid_color, 1, cv2.LINE_AA)
        cv2.line(annotated, (0, i * h // 3), (w, i * h // 3), grid_color, 1, cv2.LINE_AA)

    for obj in response.objects:
        x_min = int(obj.bounding_box.x_min * w)
        y_min = int(obj.bounding_box.y_min * h)
        x_max = int(obj.bounding_box.x_max * w)
        y_max = int(obj.bounding_box.y_max * h)
        color = (0, 200, 255) if obj.quadrant.value == "center" else (0, 200, 0)
        cv2.rectangle(annotated, (x_min, y_min), (x_max, y_max), color, 2, cv2.LINE_AA)
        depth_text = f"{obj.relative_depth_m:.2f}" if obj.relative_depth_m is not None else "n/a"
        cv2.putText(
            annotated,
            f"{obj.label} ({depth_text})",
            (x_min, max(18, y_min - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )

    center = response.center_distance
    center_text = (
        f"Center depth (0-1): {center.distance_m:.2f} conf={center.confidence or 0.0:.2f}"
        if center.distance_m is not None
        else "Center depth unavailable"
    )
    cv2.putText(annotated, center_text, (18, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(annotated, f"Mode: {environment.value}", (18, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 255, 180), 2, cv2.LINE_AA)

    if llm_text:
        y = h - 90
        for line in wrap_text(llm_text, width=52):
            cv2.putText(annotated, line, (18, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 2, cv2.LINE_AA)
            y += 22

    cv2.putText(
        annotated,
        "Speak naturally when ready. Press Q/Esc to quit.",
        (18, h - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (200, 200, 200),
        2,
        cv2.LINE_AA,
    )
    return annotated


def render_depth(depth_map: Optional[np.ndarray], shape: tuple[int, int]) -> np.ndarray:
    height, width = shape
    if depth_map is None:
        blank = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.putText(blank, "Depth unavailable", (40, height // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2, cv2.LINE_AA)
        return blank
    normalized = np.clip(depth_map, 0.0, 1.0)
    depth_uint8 = (normalized * 255).astype(np.uint8)
    depth_color = cv2.applyColorMap(depth_uint8, cv2.COLORMAP_TURBO)
    depth_color = cv2.resize(depth_color, (width, height))
    cv2.putText(depth_color, "MiDaS depth (0-1)", (20, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
    return depth_color


def wrap_text(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        test = word if not current else f"{' '.join(current)} {word}"
        if len(test) > width:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def play_audio_bytes(audio_bytes: bytes) -> None:
    audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
    play(audio_segment)


def run_cycle(
    frame: np.ndarray,
    metadata: FrameMetadata,
    environment: Environment,
    prompt_instructions: Optional[str],
    audio_base64: Optional[str],
    transcript_text: Optional[str],
    pipeline: VisionPipeline,
    assistant,
    snowflake: SnowflakeLLM,
    synthesize_voice: bool,
) -> FrameAnalysisResponse:
    print("[PIPELINE] Building request payload.")
    request = FrameAnalysisRequest(
        frame_id=f"demo-{int(time.time() * 1000)}",
        timestamp=datetime.utcnow(),
        frame_metadata=metadata,
        image_base64=frame_to_base64(frame),
        environment=environment,
        audio_base64=audio_base64,
        prompt_instructions=prompt_instructions,
        synthesize_voice=synthesize_voice,
    )
    print("[PIPELINE] Running vision pipeline...")
    response = pipeline.process(request)
    print("[PIPELINE] Vision results ready.")

    update: dict[str, Optional[str]] = {}
    user_transcript = transcript_text
    if audio_base64 and not user_transcript:
        print("[AUDIO] Transcribing captured speech via ElevenLabs workflow...")
        user_transcript = assistant.transcribe_base64(audio_base64)
    if audio_base64:
        update["user_transcript"] = user_transcript
        if user_transcript:
            print(f"[AUDIO] Transcript: {user_transcript}")
            assistant.append_history("User", user_transcript)
            prompt = assistant.build_prompt(
                vision_summary=response.vision_summary,
                user_text=user_transcript,
                instructions=prompt_instructions,
            )
            print("[LLM] Sending prompt to Snowflake Cortex...")
            llm_text = snowflake.complete(prompt)
            print("[LLM] Received response.")
            assistant.append_history("Assistant", llm_text)
            update["llm_response"] = llm_text
            if synthesize_voice:
                print("[TTS] Synthesizing ElevenLabs audio...")
                audio_bytes = assistant.synthesize(llm_text)
                update["audio_response_base64"] = base64.b64encode(audio_bytes).decode("utf-8")
                play_audio_bytes(audio_bytes)
        else:
            print("[AUDIO] Speech detected but transcription returned empty.")
    if update:
        response = response.model_copy(update=update)
    return response


def log_packages(response: FrameAnalysisResponse) -> None:
    print("\n" + "=" * 80)
    print(f"Frame: {response.frame_id}")
    for obj in response.objects:
        depth = f"{obj.relative_depth_m:.2f}" if obj.relative_depth_m is not None else "n/a"
        print(f"- {obj.label:<12} quadrant={obj.quadrant.value:<13} depth={depth:<6} conf={obj.confidence:.2f}")
    center = response.center_distance
    print("Center depth:", center.distance_m, "confidence:", center.confidence, "advisory:", center.advisory)
    if response.user_transcript:
        print("Transcript:", response.user_transcript)
    if response.llm_response:
        print("LLM response:", response.llm_response)


def main() -> None:
    parser = argparse.ArgumentParser(description="Full-stack demo (vision + ElevenLabs + SnowFlake)")
    parser.add_argument("--camera", type=int, default=0, help="Webcam index (default 0)")
    parser.add_argument(
        "--environment",
        choices=[Environment.INDOOR.value, Environment.OUTDOOR.value],
        default=Environment.INDOOR.value,
    )
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds between automatic vision refreshes")
    parser.add_argument("--prompt", type=str, default=None, help="Optional custom system instructions for SnowFlake")
    parser.add_argument("--voice", action="store_true", help="Speak Snowflake responses via ElevenLabs")
    parser.add_argument("--listen-time", type=float, default=7.0, help="Max seconds per utterance")
    args = parser.parse_args()

    settings = get_settings()
    if not settings.elevenlabs_api_key:
        raise RuntimeError("ELEVENLABS_API_KEY must be set for the full demo.")
    if not (settings.snowflake_account and settings.snowflake_user and settings.snowflake_password):
        raise RuntimeError("SNOWFLAKE_* credentials must be configured for the full demo.")

    pipeline = VisionPipeline()
    assistant = get_assistant()
    snowflake = SnowflakeLLM(
        account=settings.snowflake_account,
        user=settings.snowflake_user,
        password=settings.snowflake_password,
        role=settings.snowflake_role,
        warehouse=settings.snowflake_warehouse,
        database=settings.snowflake_database,
        schema=settings.snowflake_schema,
        model=settings.snowflake_model,
    )

    cap = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open webcam index {args.camera}")

    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    listener = SpeechListener(recognizer, microphone, phrase_time_limit=args.listen_time)
    print(f"[VOICE] Background listener ready (phrase limit {args.listen_time}s). Speak any time.")

    environment = Environment(args.environment)
    cv2.namedWindow(WINDOW_VISION, cv2.WINDOW_NORMAL)
    cv2.namedWindow(WINDOW_YOLO, cv2.WINDOW_NORMAL)
    cv2.namedWindow(WINDOW_DEPTH, cv2.WINDOW_NORMAL)

    metadata: Optional[FrameMetadata] = None
    last_run = 0.0
    last_response: Optional[FrameAnalysisResponse] = None
    conversation_active = False
    last_user_activity = 0.0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Failed to capture frame. Exiting.")
                break

            if metadata is None:
                height, width = frame.shape[:2]
                metadata = FrameMetadata(width=width, height=height, focal_length_px=None)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break

            now = time.time()
            speech_audio = listener.get_audio()
            should_refresh = now - last_run >= args.interval

            transcript_for_wake: Optional[str] = None
            if speech_audio:
                try:
                    transcript_for_wake = assistant.transcribe_base64(speech_audio) or ""
                    print(f"[VOICE] Transcript preview: {transcript_for_wake!r}")
                except Exception as exc:
                    print(f"[VOICE] Transcript failed during wake detection: {exc}")
                    transcript_for_wake = ""

            if not conversation_active:
                if assistant.should_wake(transcript_for_wake):
                    conversation_active = True
                    last_user_activity = now
                    assistant.reset_history()
                    print("[WAKE] Wake phrase detected. Conversation started.")
                    # rerun cycle with the same audio to capture the request
                else:
                    transcript_for_wake = None  # ignore this clip

            if conversation_active and transcript_for_wake:
                last_user_activity = now
                if assistant.should_end(transcript_for_wake):
                    print("[WAKE] Goodbye phrase detected, ending conversation.")
                    conversation_active = False
                    assistant.reset_history()
                    continue

            if (
                conversation_active and speech_audio
            ) or should_refresh and metadata is not None:
                print(
                    "[STATE] conversation_active=%s speech=%s refresh=%s"
                    % (conversation_active, bool(speech_audio), should_refresh)
                )
                response = run_cycle(
                    frame=frame,
                    metadata=metadata,
                    environment=environment,
                    prompt_instructions=args.prompt,
                    audio_base64=speech_audio if conversation_active else None,
                    transcript_text=transcript_for_wake if conversation_active else None,
                    pipeline=pipeline,
                    assistant=assistant,
                    snowflake=snowflake,
                    synthesize_voice=args.voice and conversation_active and bool(speech_audio),
                )
                last_response = response
                last_run = now
                log_packages(response)
                if response.user_transcript:
                    last_user_activity = now
                    if assistant.should_end(response.user_transcript):
                        print("[WAKE] Goodbye phrase detected in transcript, ending conversation.")
                        conversation_active = False
                        assistant.reset_history()
            else:
                print("[PIPELINE] Waiting for wake phrase or refresh...", end="\r")

            if (
                conversation_active
                and now - last_user_activity > INACTIVITY_TIMEOUT
            ):
                print("[WAKE] Conversation timed out due to inactivity.")
                conversation_active = False
                assistant.reset_history()

            if last_response is not None:
                annotated = draw_overlay(frame, last_response, environment, last_response.llm_response)
                yolo_view = draw_yolo_view(frame, last_response)
                depth_view = render_depth(pipeline.last_depth_map, frame.shape[:2])
                cv2.imshow(WINDOW_VISION, annotated)
                cv2.imshow(WINDOW_YOLO, yolo_view)
                cv2.imshow(WINDOW_DEPTH, depth_view)
    finally:
        cap.release()
        cv2.destroyAllWindows()
        listener.stop()


if __name__ == "__main__":
    main()
