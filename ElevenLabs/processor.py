from __future__ import annotations

import time
from typing import Optional

from vision.schemas import FrameAnalysisResponse, DetectedObject, Quadrant

try:
    # local project ElevenLabs helper
    from ElevenLabs.main import text_to_speech_file
except Exception:  # pragma: no cover - fallback if import path differs
    def text_to_speech_file(text: str, play_audio: bool = True) -> str:  # type: ignore
        print("[TTS MOCK]", text)
        return ""


class SnowflakeRiskProcessor:
    """Simple risk scorer and alerting bridge.

    Responsibilities:
    - Accept a FrameAnalysisResponse from the vision pipeline
    - Score detected objects to find the highest-risk item
    - Throttle spoken alerts and call ElevenLabs TTS to produce audio

    Assumptions:
    - `DetectedObject.relative_depth_m` is a normalized relative depth (0-1).
      We treat smaller values as closer -> more risky. If you have calibrated
      metric depths, the distance buckets and messaging can be updated.
    """

    LABEL_WEIGHTS = {
        "person": 1.0,
        "bicycle": 1.1,
        "motorcycle": 1.2,
        "car": 1.3,
        "bus": 1.4,
        "truck": 1.4,
        "crosswalk": 0.6,
        "curb": 0.7,
        "pole": 0.4,
        "bench": 0.2,
    }

    def __init__(self, min_speak_interval_s: float = 3.0) -> None:
        self.min_speak_interval_s = min_speak_interval_s
        self._last_spoken_at = 0.0

    def _distance_bucket(self, rel: Optional[float]) -> tuple[str, float]:
        """Return a human label and weight for a normalized relative depth.

        We treat smaller values as closer (higher risk). None -> unknown.
        """
        if rel is None:
            return "unknown distance", 0.5
        # closer -> smaller number -> more risky
        if rel <= 0.25:
            return "about two meters", 1.0
        if rel <= 0.5:
            return "about four meters", 0.7
        if rel <= 0.75:
            return "about eight meters", 0.4
        return "more than ten meters", 0.2

    def _position_from_quadrant(self, q: Quadrant) -> str:
        left = {
            Quadrant.TOP_LEFT,
            Quadrant.MIDDLE_LEFT,
            Quadrant.BOTTOM_LEFT,
        }
        right = {Quadrant.TOP_RIGHT, Quadrant.MIDDLE_RIGHT, Quadrant.BOTTOM_RIGHT}
        center = {Quadrant.TOP_CENTER, Quadrant.CENTER, Quadrant.BOTTOM_CENTER}
        if q in left:
            return "left"
        if q in right:
            return "right"
        if q in center:
            return "center"
        return "ahead"

    def _label_text_action(self, label: str) -> str:
        label = label.lower()
        if label in ("bicycle", "motorcycle"):
            return "pause"
        if label in ("person",):
            return "stop and let them pass"
        if label in ("car", "truck", "bus"):
            return "move to the side"
        if label in ("curb", "crosswalk"):
            return "take care"
        return "be cautious"

    def _score_object(self, obj: DetectedObject) -> float:
        label_w = self.LABEL_WEIGHTS.get(obj.label.lower(), 0.5)
        _, dist_w = self._distance_bucket(obj.relative_depth_m)
        return label_w * dist_w * float(obj.confidence)

    def process_frame(self, response: FrameAnalysisResponse) -> Optional[str]:
        """Process the frame response and speak an alert if needed.

        Returns the composed message if spoken, otherwise None.
        """
        objs = response.objects
        if not objs:
            return None

        # find highest score
        best = None
        best_score = 0.0
        for o in objs:
            try:
                s = self._score_object(o)
            except Exception:
                s = 0.0
            if s > best_score:
                best_score = s
                best = o

        # nothing risky enough
        if best is None or best_score < 0.4:
            return None

        # throttle speech
        now = time.time()
        if now - self._last_spoken_at < self.min_speak_interval_s:
            return None

        # build message
        rel_text, _ = self._distance_bucket(best.relative_depth_m)
        pos = self._position_from_quadrant(best.quadrant)
        action = self._label_text_action(best.label)
        # make message concise and actionable
        message = f"{best.label.capitalize()} approaching from your {pos}, {rel_text} — {action}."

        # speak via ElevenLabs helper
        try:
            text_to_speech_file(message)
            self._last_spoken_at = now
        except Exception as exc:
            print(f"Error while speaking alert: {exc}")

        return message


__all__ = ["SnowflakeRiskProcessor"]
