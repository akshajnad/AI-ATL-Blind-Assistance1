"""Enhanced obstacle alert system with approach detection and deduplication.

This module provides intelligent obstacle alerting that:
- Tracks objects over time to detect approaching obstacles
- Uses danger levels based on distance (aligned with color coding)
- Prevents spam by deduplicating repeated alerts
- Prioritizes critical alerts over less important ones
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional, Dict, Tuple

from vision.schemas import FrameAnalysisResponse, DetectedObject, Quadrant

try:
    from ElevenLabs.main import get_assistant
except Exception:
    def get_assistant():
        return None


@dataclass
class TrackedObject:
    """Represents an object being tracked over time."""
    label: str
    quadrant: Quadrant
    distance: float  # normalized 0-1 depth value
    confidence: float
    first_seen: float  # timestamp
    last_seen: float  # timestamp
    last_alerted: Optional[float] = None  # when we last alerted about this object
    initial_distance: Optional[float] = None  # to track if approaching

    @property
    def is_approaching(self) -> bool:
        """Check if object is getting closer."""
        if self.initial_distance is None:
            return False
        # Object is approaching if distance decreased by at least 10%
        return self.distance < (self.initial_distance * 0.9)

    @property
    def position_key(self) -> str:
        """Unique key for position and label."""
        return f"{self.label}_{self.quadrant.value}"


class DangerLevel:
    """Danger levels based on distance thresholds."""
    CRITICAL = "critical"  # < 1.0m - red - immediate danger
    HIGH = "high"          # 1.0-2.5m - orange/yellow - caution
    MEDIUM = "medium"      # 2.5-5.0m - yellow - awareness
    LOW = "low"            # > 5.0m - safe

    # Normalized depth thresholds (0-1 scale, smaller = closer)
    # Based on processor.py distance buckets and CameraOverlay.jsx color coding
    CRITICAL_THRESHOLD = 0.25  # ~2m
    HIGH_THRESHOLD = 0.5       # ~4m
    MEDIUM_THRESHOLD = 0.75    # ~8m

    @classmethod
    def from_distance(cls, relative_depth: Optional[float]) -> str:
        """Determine danger level from normalized depth."""
        if relative_depth is None:
            return cls.LOW
        if relative_depth <= cls.CRITICAL_THRESHOLD:
            return cls.CRITICAL
        if relative_depth <= cls.HIGH_THRESHOLD:
            return cls.HIGH
        if relative_depth <= cls.MEDIUM_THRESHOLD:
            return cls.MEDIUM
        return cls.LOW


class ObstacleAlertSystem:
    """Enhanced obstacle detection and alert system.

    Features:
    - Tracks objects over time
    - Detects approaching obstacles
    - Uses danger levels based on distance
    - Prevents spam with smart deduplication
    - Prioritizes critical alerts
    """

    # Object type weights for risk scoring (higher = more dangerous)
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

    def __init__(
        self,
        min_alert_interval_s: float = 5.0,  # min time between alerts
        object_memory_s: float = 10.0,      # how long to remember objects
        alert_cooldown_s: float = 30.0,     # don't re-alert same object within this time
    ):
        self.min_alert_interval_s = min_alert_interval_s
        self.object_memory_s = object_memory_s
        self.alert_cooldown_s = alert_cooldown_s

        self._tracked_objects: Dict[str, TrackedObject] = {}
        self._last_alert_time = 0.0
        self._last_alert_message: Optional[str] = None

        # Try to get the assistant for TTS
        self._assistant = get_assistant()

    def process_frame(self, response: FrameAnalysisResponse) -> Optional[str]:
        """Process a frame and generate alerts if necessary.

        Returns the alert message if one was spoken, otherwise None.
        """
        now = time.time()

        # Update tracked objects
        self._update_tracked_objects(response.objects, now)

        # Clean up old objects
        self._cleanup_old_objects(now)

        # Find the most critical object requiring an alert
        alert_obj = self._find_alert_candidate(now)

        if alert_obj is None:
            return None

        # Check if we should throttle alerts
        if now - self._last_alert_time < self.min_alert_interval_s:
            return None

        # Generate and speak alert
        message = self._generate_alert_message(alert_obj)
        self._speak_alert(message)

        # Update alert tracking
        alert_obj.last_alerted = now
        self._last_alert_time = now
        self._last_alert_message = message

        return message

    def _update_tracked_objects(self, objects: list[DetectedObject], now: float) -> None:
        """Update our tracked objects with new detections."""
        current_keys = set()

        for obj in objects:
            if obj.relative_depth_m is None:
                continue

            key = f"{obj.label}_{obj.quadrant.value}"
            current_keys.add(key)

            if key in self._tracked_objects:
                # Update existing tracked object
                tracked = self._tracked_objects[key]
                tracked.distance = obj.relative_depth_m
                tracked.confidence = obj.confidence
                tracked.last_seen = now
                # Keep initial distance for approach detection
                if tracked.initial_distance is None:
                    tracked.initial_distance = obj.relative_depth_m
            else:
                # New object
                self._tracked_objects[key] = TrackedObject(
                    label=obj.label,
                    quadrant=obj.quadrant,
                    distance=obj.relative_depth_m,
                    confidence=obj.confidence,
                    first_seen=now,
                    last_seen=now,
                    initial_distance=obj.relative_depth_m,
                )

    def _cleanup_old_objects(self, now: float) -> None:
        """Remove objects that haven't been seen recently."""
        to_remove = [
            key for key, obj in self._tracked_objects.items()
            if now - obj.last_seen > self.object_memory_s
        ]
        for key in to_remove:
            del self._tracked_objects[key]

    def _find_alert_candidate(self, now: float) -> Optional[TrackedObject]:
        """Find the object that most needs an alert.

        Priority order:
        1. Critical danger level objects
        2. High danger level objects
        3. Approaching objects at medium danger
        4. Other medium danger objects
        """
        if not self._tracked_objects:
            return None

        candidates = []

        for obj in self._tracked_objects.values():
            # Skip if we alerted about this recently
            if obj.last_alerted and (now - obj.last_alerted < self.alert_cooldown_s):
                continue

            danger = DangerLevel.from_distance(obj.distance)

            # Only alert for critical, high, or medium danger
            if danger == DangerLevel.LOW:
                continue

            # Only alert for medium danger if approaching
            if danger == DangerLevel.MEDIUM and not obj.is_approaching:
                continue

            # Calculate risk score
            label_weight = self.LABEL_WEIGHTS.get(obj.label.lower(), 0.5)

            # Distance weight (closer = higher)
            if danger == DangerLevel.CRITICAL:
                distance_weight = 1.0
            elif danger == DangerLevel.HIGH:
                distance_weight = 0.7
            else:  # MEDIUM
                distance_weight = 0.4

            # Boost score if approaching
            approach_multiplier = 1.3 if obj.is_approaching else 1.0

            risk_score = label_weight * distance_weight * obj.confidence * approach_multiplier

            candidates.append((risk_score, danger, obj))

        if not candidates:
            return None

        # Sort by risk score (highest first)
        candidates.sort(key=lambda x: x[0], reverse=True)

        # Return highest risk object
        return candidates[0][2]

    def _generate_alert_message(self, obj: TrackedObject) -> str:
        """Generate a concise, actionable alert message."""
        danger = DangerLevel.from_distance(obj.distance)

        # Get position description
        pos = self._position_from_quadrant(obj.quadrant)

        # Get distance description
        dist_text = self._distance_description(obj.distance)

        # Get action recommendation
        action = self._action_for_object(obj.label, danger)

        # Build message based on danger level
        if danger == DangerLevel.CRITICAL:
            # Urgent, immediate alert
            if action:
                message = f"Alert! {obj.label.capitalize()} very close on your {pos}. {action}!"
            else:
                message = f"Alert! {obj.label.capitalize()} very close on your {pos}!"
        elif danger == DangerLevel.HIGH:
            # Caution alert
            if action:
                message = f"{obj.label.capitalize()} approaching on your {pos}, {dist_text}. {action}."
            else:
                message = f"Caution: {obj.label.capitalize()} on your {pos}, {dist_text}."
        else:  # MEDIUM (only if approaching)
            message = f"{obj.label.capitalize()} approaching from {pos}, {dist_text}."

        return message

    def _position_from_quadrant(self, q: Quadrant) -> str:
        """Get position description from quadrant."""
        left = {Quadrant.TOP_LEFT, Quadrant.MIDDLE_LEFT, Quadrant.BOTTOM_LEFT}
        right = {Quadrant.TOP_RIGHT, Quadrant.MIDDLE_RIGHT, Quadrant.BOTTOM_RIGHT}
        center = {Quadrant.TOP_CENTER, Quadrant.CENTER, Quadrant.BOTTOM_CENTER}

        if q in left:
            return "left"
        if q in right:
            return "right"
        if q in center:
            return "center"
        return "ahead"

    def _distance_description(self, rel_depth: float) -> str:
        """Get human-readable distance description."""
        if rel_depth <= 0.25:
            return "about two meters"
        if rel_depth <= 0.5:
            return "about four meters"
        if rel_depth <= 0.75:
            return "about eight meters"
        return "more than ten meters"

    def _action_for_object(self, label: str, danger: DangerLevel) -> str:
        """Get recommended action for object type and danger level."""
        label = label.lower()

        if danger == DangerLevel.CRITICAL:
            # Immediate actions
            if label in ("person",):
                return "Stop"
            if label in ("car", "truck", "bus"):
                return "Move aside immediately"
            if label in ("bicycle", "motorcycle"):
                return "Stop"
            if label in ("curb", "pole"):
                return "Stop"
            return "Stop"
        elif danger == DangerLevel.HIGH:
            # Caution actions
            if label in ("person",):
                return "Slow down"
            if label in ("car", "truck", "bus"):
                return "Move to the side"
            if label in ("bicycle", "motorcycle"):
                return "Be careful"
            if label in ("curb", "pole"):
                return "Avoid ahead"
            return "Be cautious"

        # Medium - just awareness, no action needed
        return ""

    def _speak_alert(self, message: str) -> None:
        """Speak the alert message using ElevenLabs TTS."""
        if self._assistant is None:
            # Fallback: just print
            print(f"[OBSTACLE ALERT] {message}")
            return

        try:
            self._assistant.play_text(message)
        except Exception as exc:
            print(f"[OBSTACLE ALERT] TTS failed: {exc}")
            print(f"[OBSTACLE ALERT] {message}")


__all__ = ["ObstacleAlertSystem", "DangerLevel", "TrackedObject"]
