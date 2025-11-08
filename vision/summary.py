from __future__ import annotations

from typing import List

try:
    from .schemas import CenterDistanceSummary, DetectedObject, Quadrant
except ImportError:  # pragma: no cover - script execution
    from schemas import CenterDistanceSummary, DetectedObject, Quadrant


def describe_quadrant(quadrant: Quadrant) -> str:
    return quadrant.value.replace("_", " ")


def summarize_scene(objects: List[DetectedObject], center: CenterDistanceSummary) -> str:
    if not objects:
        object_sentence = "No obstacles detected in the current frame."
    else:
        parts = []
        for obj in objects[:10]:
            depth = f"{obj.relative_depth_m:.2f}" if obj.relative_depth_m is not None else "unknown depth"
            parts.append(
                f"{obj.label} in the {describe_quadrant(obj.quadrant)} quadrant (confidence {obj.confidence:.2f}, depth {depth})."
            )
        object_sentence = " ".join(parts)

    if center.distance_m is None:
        center_sentence = "Center clearance is unknown."
    else:
        center_sentence = (
            f"Center clearance sits at relative depth {center.distance_m:.2f} "
            f"(confidence {center.confidence or 0.0:.2f})."
        )

    return f"{object_sentence} {center_sentence}"
