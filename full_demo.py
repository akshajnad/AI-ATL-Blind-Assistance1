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
import pygame
import speech_recognition as sr
from pydub import AudioSegment
from pydub.playback import play

PROJECT_ROOT = Path(__file__).resolve().parent
VISION_DIR = PROJECT_ROOT / "vision"

if str(VISION_DIR) not in sys.path:
    sys.path.append(str(VISION_DIR))

from config import get_settings
from main import get_assistant
from vision.integrations.snowflake_client import SnowflakeLLM
from vision.pipeline import VisionPipeline
from vision.schemas import Environment, FrameAnalysisRequest, FrameAnalysisResponse, FrameMetadata, Quadrant

WINDOW_VISION = "Assistive Overlay"
WINDOW_YOLO = "YOLO Detections"
WINDOW_DEPTH = "MiDaS Depth"

INACTIVITY_TIMEOUT = 45.0  # seconds of silence before ending the convo
PROXIMITY_THRESHOLD = 1.0  # meters - play alert if object is closer than this


class ProximityAlert:
    """Handles proximity alert sounds."""
    
    def __init__(self):
        """Initialize pygame mixer for playing alert sounds."""
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        self._alert_sound = None
        self._last_alert_time = 0.0
        self._alert_cooldown = 2.0  # seconds between alerts to avoid spam
        
    def create_alert_sound(self):
        """Create a simple beep sound programmatically."""
        sample_rate = 22050
        duration = 0.3  # seconds
        frequency = 800  # Hz
        
        # Generate a sine wave beep
        samples = int(sample_rate * duration)
        wave = np.sin(2 * np.pi * frequency * np.linspace(0, duration, samples))
        
        # Apply envelope to avoid clicks
        envelope = np.ones(samples)
        fade_samples = int(sample_rate * 0.05)
        envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
        envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
        wave = wave * envelope
        
        # Convert to 16-bit PCM
        wave = (wave * 32767).astype(np.int16)
        
        # Create stereo sound
        stereo_wave = np.column_stack((wave, wave))
        
        # Create pygame Sound object
        sound = pygame.sndarray.make_sound(stereo_wave)
        return sound
    
    def initialize(self):
        """Initialize the alert sound."""
        try:
            self._alert_sound = self.create_alert_sound()
            print("[ALERT] Proximity alert system initialized")
        except Exception as exc:
            print(f"[ALERT] Warning: Could not initialize alert sound: {exc}")
    
    def check_and_alert(self, response: FrameAnalysisResponse) -> bool:
        """
        Check if any objects are within proximity threshold and play alert.
        
        Returns:
            True if alert was played, False otherwise
        """
        if self._alert_sound is None:
            return False
        
        now = time.time()
        
        # Check cooldown
        if now - self._last_alert_time < self._alert_cooldown:
            return False
        
        # Find closest object
        closest_distance = float('inf')
        closest_object = None
        
        for obj in response.objects:
            if obj.relative_depth_m is not None and obj.relative_depth_m < closest_distance:
                closest_distance = obj.relative_depth_m
                closest_object = obj
        
        # Trigger alert if within threshold
        if closest_distance <= PROXIMITY_THRESHOLD:
            try:
                self._alert_sound.play()
                self._last_alert_time = now
                print(f"[ALERT] ⚠️  {closest_object.label} detected at {closest_distance:.2f}m!")
                return True
            except Exception as exc:
                print(f"[ALERT] Error playing sound: {exc}")
        
        return False


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
        self._recognizer = recognizer
        self._microphone = microphone
        self._phrase_time_limit = phrase_time_limit
        self._stopper = None
        self._accepting_audio = True

    def _callback(self, recognizer: sr.Recognizer, audio: sr.AudioData) -> None:  # pylint: disable=unused-argument
        if not self._accepting_audio:
            return  # Silently ignore
            
        try:
            wav_bytes = audio.get_wav_data()
            audio_b64 = base64.b64encode(wav_bytes).decode("utf-8")
            self._queue.put(audio_b64)
            timestamp = datetime.now().strftime("%H:%M:%S")
            #print(f"\n[{timestamp}] [VOICE] ✓ CAPTURED: {len(wav_bytes)} bytes")
        except Exception as exc:  # pragma: no cover
            print(f"[VOICE] Error: {exc}")

    def start(self) -> None:
        """Start the background listener."""
        if self._stopper is None:
            self._stopper = self._recognizer.listen_in_background(
                self._microphone,
                self._callback,
                phrase_time_limit=self._phrase_time_limit,
            )
            self._accepting_audio = True
            #print("[VOICE] Listener started")

    def pause_acceptance(self) -> None:
        """Stop accepting new audio (but keep listener running)."""
        self._accepting_audio = False

    def resume_acceptance(self) -> None:
        """Resume accepting audio."""
        self._accepting_audio = True

    def get_audio(self) -> Optional[str]:
        """Get one audio chunk from queue."""
        try:
            return self._queue.get_nowait()
        except queue.Empty:
            return None

    def clear_queue(self) -> None:
        """Clear all pending audio."""
        count = 0
        while True:
            try:
                self._queue.get_nowait()
                count += 1
            except queue.Empty:
                break

    def stop(self) -> None:
        if self._stopper:
            self._stopper(wait_for_stop=False)
            self._stopper = None


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
        
        # Use red color for proximity alerts
        color = (0, 0, 255) if (obj.relative_depth_m and obj.relative_depth_m <= PROXIMITY_THRESHOLD) else (0, 255, 0)
        cv2.rectangle(view, (x_min, y_min), (x_max, y_max), color, 2, cv2.LINE_AA)
        
        label = f"{obj.label} ({obj.confidence:.2f})"
        cv2.putText(view, label, (x_min, max(18, y_min - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
    cv2.putText(view, "YOLO detections", (16, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    return view


def draw_overlay(frame: np.ndarray, response: FrameAnalysisResponse, environment: Environment, llm_text: Optional[str], status: str) -> np.ndarray:
    annotated = frame.copy()
    h, w = annotated.shape[:2]
    grid_color = (80, 80, 80)
    for i in range(1, 3):
        cv2.line(annotated, (i * w // 3, 0), (i * w // 3, h), grid_color, 1, cv2.LINE_AA)
        cv2.line(annotated, (0, i * h // 3), (w, i * h // 3), grid_color, 1, cv2.LINE_AA)

    # Check for proximity alerts
    has_proximity_alert = any(
        obj.relative_depth_m and obj.relative_depth_m <= PROXIMITY_THRESHOLD 
        for obj in response.objects
    )

    for obj in response.objects:
        x_min = int(obj.bounding_box.x_min * w)
        y_min = int(obj.bounding_box.y_min * h)
        x_max = int(obj.bounding_box.x_max * w)
        y_max = int(obj.bounding_box.y_max * h)
        
        # Use red for proximity alerts, orange for center, green otherwise
        if obj.relative_depth_m and obj.relative_depth_m <= PROXIMITY_THRESHOLD:
            color = (0, 0, 255)  # Red for close objects
        elif obj.quadrant.value == "center":
            color = (0, 200, 255)  # Orange for center
        else:
            color = (0, 200, 0)  # Green for normal
            
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

    # Show status
    status_color = (0, 255, 255) if "PROCESSING" in status else (0, 255, 0)
    cv2.putText(annotated, status, (18, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2, cv2.LINE_AA)
    
    # Show proximity warning
    if has_proximity_alert:
        warning_text = f"⚠️  PROXIMITY ALERT - Object within {PROXIMITY_THRESHOLD}m"
        cv2.putText(annotated, warning_text, (18, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)

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
    try:
        #print(f"[TTS] Playing {len(audio_bytes)} bytes...")
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
        #print(f"[TTS] Duration: {len(audio_segment)}ms")
        play(audio_segment)
        #print("[TTS] ✓✓✓ PLAYBACK COMPLETE ✓✓✓")
    except Exception as exc:
        #print(f"[TTS] ✗ PLAYBACK ERROR: {exc}")
        import traceback
        traceback.print_exc()


def build_detailed_vision_summary(response: FrameAnalysisResponse) -> str:
    """Build a detailed vision summary for the LLM."""
    parts = []
    
    # Overall scene
    if response.objects:
        parts.append(f"I can see {len(response.objects)} objects in your environment:")
        
        # Group by quadrant
        by_quadrant = {}
        for obj in response.objects:
            quad = obj.quadrant.value
            if quad not in by_quadrant:
                by_quadrant[quad] = []
            by_quadrant[quad].append(obj)
        
        # Describe each quadrant
        for quadrant, objects in by_quadrant.items():
            obj_descriptions = []
            for obj in objects:
                depth_str = f"{obj.relative_depth_m:.1f} meters away" if obj.relative_depth_m else "unknown distance"
                # Add proximity warning to description
                if obj.relative_depth_m and obj.relative_depth_m <= PROXIMITY_THRESHOLD:
                    depth_str += " ⚠️ VERY CLOSE"
                obj_descriptions.append(f"{obj.label} ({depth_str})")
            
            parts.append(f"- In the {quadrant.replace('_', ' ')}: {', '.join(obj_descriptions)}")
    else:
        parts.append("I don't see any specific objects detected in the current view.")
    
    # Center depth information
    if response.center_distance and response.center_distance.distance_m is not None:
        parts.append(f"\nDirectly ahead of you, the distance is approximately {response.center_distance.distance_m:.1f} meters.")
        if response.center_distance.advisory:
            parts.append(f"Advisory: {response.center_distance.advisory}")
    
    # Vision summary from pipeline
    if response.vision_summary:
        parts.append(f"\nAdditional context: {response.vision_summary}")
    
    return "\n".join(parts)


def run_cycle(
    frame: np.ndarray,
    metadata: FrameMetadata,
    environment: Environment,
    prompt_instructions: Optional[str],
    audio_base64: str,
    pipeline: VisionPipeline,
    assistant,
    snowflake: SnowflakeLLM,
    synthesize_voice: bool,
    proximity_alert: ProximityAlert,
) -> FrameAnalysisResponse:
    #print("\n" + "="*80)
    #print("[CYCLE] START")
    #print("="*80)
    
    # Vision processing
    request = FrameAnalysisRequest(
        frame_id=f"demo-{int(time.time() * 1000)}",
        timestamp=datetime.utcnow(),
        frame_metadata=metadata,
        image_base64=frame_to_base64(frame),
        environment=environment,
        audio_base64=None,
        prompt_instructions=prompt_instructions,
        synthesize_voice=False,
    )
    
    #print("[1/5] Vision pipeline...")
    response = pipeline.process(request)
    #print(f"[1/5] ✓ Found {len(response.objects)} objects")
    
    # Check for proximity alerts
    proximity_alert.check_and_alert(response)
    
    # Log what we detected
    for obj in response.objects:
        depth_str = f"{obj.relative_depth_m:.1f}m" if obj.relative_depth_m else "n/a"
        #print(f"      - {obj.label} @ {obj.quadrant.value} ({depth_str})")

    update: dict[str, Optional[str]] = {}
    
    # Transcribe user audio
    #print("[2/5] Transcribing...")
    try:
        user_transcript = assistant.transcribe_base64(audio_base64)
        #print(f"[2/5] ✓ '{user_transcript}'")
    except Exception as exc:
        #print(f"[2/5] ✗ ERROR: {exc}")
        user_transcript = None
    
    # Process if we got valid transcript
    if user_transcript and user_transcript.strip():
        #print(f"\n[USER]: {user_transcript}\n")
        
        update["user_transcript"] = user_transcript
        assistant.append_history("User", user_transcript)
        
        # Build detailed vision summary
        detailed_vision = build_detailed_vision_summary(response)
        #print("[VISION CONTEXT]:")
        #print(detailed_vision)
        #print()
        
        # Build prompt
        #print("[3/5] Building prompt with vision data...")
        prompt = assistant.build_prompt(
            vision_summary=detailed_vision,
            user_text=user_transcript,
            instructions=prompt_instructions,
        )
        #print(f"[3/5] ✓ Prompt ready ({len(prompt)} chars)")
        
        # Get LLM response
        #print("[4/5] Calling Snowflake...")
        try:
            llm_text = snowflake.complete(prompt)
            #print(f"[4/5] ✓ Got response ({len(llm_text)} chars)")
            #print(f"\n[ASSISTANT]: {llm_text}\n")
            
            assistant.append_history("Assistant", llm_text)
            update["llm_response"] = llm_text
            
            # Synthesize and play
            if synthesize_voice and llm_text and llm_text.strip():
                #print("[5/5] Synthesizing speech...")
                try:
                    audio_bytes = assistant.synthesize(llm_text)
                    #print(f"[5/5] ✓ Got audio ({len(audio_bytes)} bytes)")
                    update["audio_response_base64"] = base64.b64encode(audio_bytes).decode("utf-8")
                    
                    play_audio_bytes(audio_bytes)
                    
                except Exception as exc:
                    #print(f"[5/5] ✗ TTS ERROR: {exc}")
                    import traceback
                    traceback.print_exc()
            else:
                if not synthesize_voice:
                    print("[5/5] ⚠ Voice disabled")
                #print("[5/5] Done (no TTS)")
                    
        except Exception as exc:
            #rint(f"[4/5] ✗ LLM ERROR: {exc}")
            import traceback
            traceback.print_exc()
    
    if update:
        response = response.model_copy(update=update)
    
    #print("="*80)
    #print("[CYCLE] COMPLETE")
    #print("="*80 + "\n")
    return response


def main() -> None:
    parser = argparse.ArgumentParser(description="Full-stack demo (vision + ElevenLabs + SnowFlake)")
    parser.add_argument("--camera", type=int, default=0, help="Webcam index (default 0)")
    parser.add_argument(
        "--environment",
        choices=[Environment.INDOOR.value, Environment.OUTDOOR.value],
        default=Environment.INDOOR.value,
    )
    parser.add_argument("--interval", type=float, default=5.0, help="Seconds between automatic vision refreshes")
    parser.add_argument("--prompt", type=str, default=None, help="Optional custom system instructions")
    parser.add_argument("--voice", action="store_true", help="Enable voice synthesis")
    parser.add_argument("--listen-time", type=float, default=8.0, help="Max seconds per utterance")
    parser.add_argument("--no-alert", action="store_true", help="Disable proximity alert sounds")
    args = parser.parse_args()

    from config import ELEVENLABS_API_KEY, SNOWFLAKE_USER, SNOWFLAKE_ACCOUNT, SNOWFLAKE_MODEL, SNOWFLAKE_PASSWORD

    #print("\n" + "="*80)
    #print("INITIALIZING SYSTEM")
    #print("="*80)
    
    pipeline = VisionPipeline()
    assistant = get_assistant()
    snowflake = SnowflakeLLM(
        account=SNOWFLAKE_ACCOUNT,
        user=SNOWFLAKE_USER,
        password=SNOWFLAKE_PASSWORD,
        role="ACCOUNTADMIN",
        model=SNOWFLAKE_MODEL,
    )
    
    # Initialize proximity alert system
    proximity_alert = ProximityAlert()
    if not args.no_alert:
        proximity_alert.initialize()

    cap = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open webcam {args.camera}")

    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    microphone = sr.Microphone()
    listener = SpeechListener(recognizer, microphone, phrase_time_limit=args.listen_time)
    listener.start()
    
    #print(f"\nVOICE: {'ENABLED' if args.voice else 'DISABLED'}")
    #print(f"PROXIMITY ALERT: {'ENABLED' if not args.no_alert else 'DISABLED'}")
    #print(f"Say wake phrase to start\n")

    environment = Environment(args.environment)
    cv2.namedWindow(WINDOW_VISION, cv2.WINDOW_NORMAL)
    cv2.namedWindow(WINDOW_YOLO, cv2.WINDOW_NORMAL)
    cv2.namedWindow(WINDOW_DEPTH, cv2.WINDOW_NORMAL)

    metadata: Optional[FrameMetadata] = None
    last_run = 0.0
    last_response: Optional[FrameAnalysisResponse] = None
    conversation_active = False
    last_user_activity = 0.0
    status = "Waiting for wake phrase..."

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if metadata is None:
                height, width = frame.shape[:2]
                metadata = FrameMetadata(width=width, height=height, focal_length_px=None)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break

            now = time.time()
            speech_audio = listener.get_audio()

            if speech_audio:
                listener.pause_acceptance()
                listener.clear_queue()
                
                # Quick check for wake/goodbye
                try:
                    transcript = assistant.transcribe_base64(speech_audio) or ""
                    #print(f"\n[HEARD]: '{transcript}'")
                except Exception:
                    transcript = ""

                # Wake detection
                if not conversation_active:
                    if transcript and assistant.should_wake(transcript):
                        conversation_active = True
                        last_user_activity = now
                        assistant.reset_history()
                        #print("\n*** CONVERSATION STARTED ***\n")
                        status = "Active - listening"
                    else:
                        #print("(Not wake phrase)")
                        listener.resume_acceptance()
                        speech_audio = None

                # Goodbye detection
                if conversation_active and transcript and assistant.should_end(transcript):
                    #print("\n*** CONVERSATION ENDED ***\n")
                    conversation_active = False
                    assistant.reset_history()
                    status = "Waiting for wake phrase..."
                    listener.resume_acceptance()
                    continue

                # Process in conversation
                if conversation_active and speech_audio and metadata is not None:
                    status = "PROCESSING..."
                    last_user_activity = now
                    
                    try:
                        response = run_cycle(
                            frame=frame,
                            metadata=metadata,
                            environment=environment,
                            prompt_instructions=args.prompt,
                            audio_base64=speech_audio,
                            pipeline=pipeline,
                            assistant=assistant,
                            snowflake=snowflake,
                            synthesize_voice=args.voice,
                            proximity_alert=proximity_alert,
                        )
                        last_response = response
                        last_run = now
                        
                        if response.user_transcript:
                            last_user_activity = now
                            
                    except Exception as exc:
                        #print(f"ERROR in cycle: {exc}")
                        import traceback
                    finally:
                        status = "Active - listening"
                        listener.resume_acceptance()
                        #print("Ready for next input\n")
                    
            # Periodic vision refresh
            if now - last_run >= args.interval and metadata and not conversation_active:
                request = FrameAnalysisRequest(
                    frame_id=f"demo-{int(time.time() * 1000)}",
                    timestamp=datetime.utcnow(),
                    frame_metadata=metadata,
                    image_base64=frame_to_base64(frame),
                    environment=environment,
                    audio_base64=None,
                    prompt_instructions=args.prompt,
                    synthesize_voice=False,
                )
                response = pipeline.process(request)
                last_response = response
                last_run = now
                
                # Check for proximity alerts during periodic refresh too
                if not args.no_alert:
                    proximity_alert.check_and_alert(response)

            # Timeout
            if conversation_active and now - last_user_activity > INACTIVITY_TIMEOUT:
                #print(f"\nTimeout after {INACTIVITY_TIMEOUT}s\n")
                conversation_active = False
                assistant.reset_history()
                status = "Waiting for wake phrase..."

            # Update display
            if last_response is not None:
                annotated = draw_overlay(frame, last_response, environment, last_response.llm_response, status)
                yolo_view = draw_yolo_view(frame, last_response)
                depth_view = render_depth(pipeline.last_depth_map, frame.shape[:2])
                cv2.imshow(WINDOW_VISION, annotated)
                cv2.imshow(WINDOW_YOLO, yolo_view)
                cv2.imshow(WINDOW_DEPTH, depth_view)
                
    finally:
        cap.release()
        cv2.destroyAllWindows()
        listener.stop()
        pygame.mixer.quit()


if __name__ == "__main__":
    main()