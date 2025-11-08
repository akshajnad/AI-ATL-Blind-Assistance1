from __future__ import annotations

import base64
from typing import List, Optional

import cv2
import numpy as np
import torch
from ultralytics import YOLO

try:
    from .schemas import (
        BoundingBox,
        CenterDistanceSummary,
        DetectedObject,
        Environment,
        FrameAnalysisRequest,
        FrameAnalysisResponse,
        Quadrant,
    )
except ImportError:  # pragma: no cover - support script execution
    from schemas import (
        BoundingBox,
        CenterDistanceSummary,
        DetectedObject,
        Environment,
        FrameAnalysisRequest,
        FrameAnalysisResponse,
        Quadrant,
    )
    from summary import summarize_scene
else:
    from .summary import summarize_scene


class MiDaSDepthEstimator:
    """Wraps Intel's MiDaS models via torch.hub."""

    def __init__(self, model_type: str = "MiDaS_small", device: str | None = None) -> None:
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = torch.hub.load("intel-isl/MiDaS", model_type).to(self.device)
        self.model.eval()
        transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
        self.transform = transforms.dpt_transform if "DPT" in model_type else transforms.small_transform

    @torch.inference_mode()
    def predict(self, frame_bgr: np.ndarray) -> np.ndarray:
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        input_batch = self.transform(rgb).to(self.device)
        prediction = self.model(input_batch)
        prediction = torch.nn.functional.interpolate(
            prediction.unsqueeze(1),
            size=rgb.shape[:2],
            mode="bicubic",
            align_corners=False,
        ).squeeze()
        depth = prediction.cpu().numpy()
        depth = (depth - depth.min()) / (depth.max() - depth.min() + 1e-6)
        return depth


OUTDOOR_YOLO_LABELS = {
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "bus",
    "truck",
    "traffic light",
    "stop sign",
    "fire hydrant",
    "bench",
}


class VisionPipeline:
    def __init__(
        self,
        detector_weights: str = "yolov8n.pt",
        depth_model_type: str = "MiDaS_small",
    ) -> None:
        self.detector = YOLO(detector_weights)
        self.depth_model = MiDaSDepthEstimator(model_type=depth_model_type)
        self._last_depth_map: Optional[np.ndarray] = None

    def process(self, payload: FrameAnalysisRequest) -> FrameAnalysisResponse:
        frame = self._decode_frame(payload.image_base64)
        depth_map = self.depth_model.predict(frame)
        self._last_depth_map = depth_map
        if payload.environment == Environment.OUTDOOR:
            objects = self._run_outdoor_detection(frame, depth_map)
            note = (
                "Outdoor pipeline: YOLO filtered for roadway agents plus classical CV "
                "detectors for crosswalks, poles, and curbs. Depth normalized 0-1."
            )
        else:
            objects = self._run_indoor_detection(frame, depth_map)
            note = (
                "Indoor pipeline: YOLO (general objects) + MiDaS depth normalized 0-1. "
                "Convert to metric units downstream if needed."
            )
        center_summary = self._summarize_center(depth_map, payload.frame_metadata.width, payload.frame_metadata.height)
        summary = summarize_scene(objects, center_summary)
        return FrameAnalysisResponse(
            frame_id=payload.frame_id,
            objects=objects,
            center_distance=center_summary,
            vision_summary=summary,
            notes=note,
        )

    @property
    def last_depth_map(self) -> Optional[np.ndarray]:
        return None if self._last_depth_map is None else self._last_depth_map.copy()

    def _decode_frame(self, image_base64: str) -> np.ndarray:
        buffer = base64.b64decode(image_base64)
        arr = np.frombuffer(buffer, np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Unable to decode provided image_base64")
        return frame

    def _run_indoor_detection(self, frame: np.ndarray, depth_map: np.ndarray) -> List[DetectedObject]:
        return self._detect_with_yolo(frame, depth_map)

    def _run_outdoor_detection(self, frame: np.ndarray, depth_map: np.ndarray) -> List[DetectedObject]:
        objects = self._detect_with_yolo(frame, depth_map, allowed_labels=OUTDOOR_YOLO_LABELS)
        objects.extend(self._detect_crosswalks(frame, depth_map))
        objects.extend(self._detect_poles(frame, depth_map))
        objects.extend(self._detect_curbs(frame, depth_map))
        return objects

    def _detect_with_yolo(
        self,
        frame: np.ndarray,
        depth_map: np.ndarray,
        allowed_labels: Optional[set[str]] = None,
    ) -> List[DetectedObject]:
        results = self.detector.predict(source=frame, verbose=False)[0]
        objects: List[DetectedObject] = []
        height, width = frame.shape[:2]
        for box in results.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            bbox = BoundingBox(
                x_min=max(0.0, x1 / width),
                y_min=max(0.0, y1 / height),
                x_max=min(1.0, x2 / width),
                y_max=min(1.0, y2 / height),
            )
            label = results.names[int(box.cls)]
            if allowed_labels is not None and label not in allowed_labels:
                continue
            confidence = float(box.conf)
            quadrant = self._quadrant_from_bbox(bbox)
            center = bbox.center
            depth_value = depth_map[int(center[1] * height), int(center[0] * width)]
            depth_m = float(depth_value)
            objects.append(
                DetectedObject(
                    label=label,
                    confidence=confidence,
                    bounding_box=bbox,
                    quadrant=quadrant,
                    relative_depth_m=depth_m,
                )
            )
        return objects

    def _detect_crosswalks(self, frame: np.ndarray, depth_map: np.ndarray) -> List[DetectedObject]:
        height, width = frame.shape[:2]
        roi_start = int(height * 0.4)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        roi = gray[roi_start:, :]
        if roi.size == 0:
            return []
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(roi)
        _, thresh = cv2.threshold(enhanced, 200, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (35, 7))
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detections: List[DetectedObject] = []
        frame_area = float(width * height)
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 0.01 * frame_area:
                continue
            x, y, w_box, h_box = cv2.boundingRect(contour)
            aspect = w_box / (h_box + 1e-6)
            if aspect < 3.0:
                continue
            y_abs = y + roi_start
            bbox = (x, y_abs, x + w_box, y_abs + h_box)
            detections.append(
                self._build_detected_object(
                    label="crosswalk",
                    bbox_pixels=bbox,
                    frame_shape=frame.shape,
                    depth_map=depth_map,
                    confidence=0.8,
                )
            )
        return [det for det in detections if det is not None]

    def _detect_poles(self, frame: np.ndarray, depth_map: np.ndarray) -> List[DetectedObject]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 40, 120)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 13))
        vertical = cv2.morphologyEx(edges, cv2.MORPH_DILATE, kernel, iterations=1)
        contours, _ = cv2.findContours(vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detections: List[DetectedObject] = []
        height, width = frame.shape[:2]
        for contour in contours:
            x, y, w_box, h_box = cv2.boundingRect(contour)
            if h_box < height * 0.2 or w_box > width * 0.08:
                continue
            if h_box / (w_box + 1e-6) < 4.0:
                continue
            bbox = (x, y, x + w_box, y + h_box)
            detections.append(
                self._build_detected_object(
                    label="pole",
                    bbox_pixels=bbox,
                    frame_shape=frame.shape,
                    depth_map=depth_map,
                    confidence=0.65,
                )
            )
        return [det for det in detections if det is not None]

    def _detect_curbs(self, frame: np.ndarray, depth_map: np.ndarray) -> List[DetectedObject]:
        height, width = frame.shape[:2]
        roi_start = int(height * 0.65)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        roi = gray[roi_start:, :]
        if roi.size == 0:
            return []
        sobel = cv2.Sobel(roi, cv2.CV_64F, 0, 1, ksize=3)
        abs_sobel = cv2.convertScaleAbs(sobel)
        _, thresh = cv2.threshold(abs_sobel, 60, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 5))
        dilated = cv2.morphologyEx(thresh, cv2.MORPH_DILATE, kernel, iterations=1)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        detections: List[DetectedObject] = []
        for contour in contours:
            x, y, w_box, h_box = cv2.boundingRect(contour)
            if w_box < width * 0.2 or h_box > height * 0.15:
                continue
            y_abs = y + roi_start
            bbox = (x, y_abs, x + w_box, y_abs + h_box)
            detections.append(
                self._build_detected_object(
                    label="curb",
                    bbox_pixels=bbox,
                    frame_shape=frame.shape,
                    depth_map=depth_map,
                    confidence=0.7,
                )
            )
        return [det for det in detections if det is not None]

    def _build_detected_object(
        self,
        label: str,
        bbox_pixels: tuple[int, int, int, int],
        frame_shape: tuple[int, int, int],
        depth_map: np.ndarray,
        confidence: float,
    ) -> Optional[DetectedObject]:
        height, width = frame_shape[:2]
        x_min, y_min, x_max, y_max = bbox_pixels
        x_min = int(np.clip(x_min, 0, width - 1))
        y_min = int(np.clip(y_min, 0, height - 1))
        x_max = int(np.clip(x_max, x_min + 1, width))
        y_max = int(np.clip(y_max, y_min + 1, height))
        bbox = BoundingBox(
            x_min=x_min / width,
            y_min=y_min / height,
            x_max=x_max / width,
            y_max=y_max / height,
        )
        center = bbox.center
        cx = int(np.clip(center[0] * width, 0, width - 1))
        cy = int(np.clip(center[1] * height, 0, height - 1))
        depth_value = float(depth_map[cy, cx])
        if not np.isfinite(depth_value):
            return None
        return DetectedObject(
            label=label,
            confidence=confidence,
            bounding_box=bbox,
            quadrant=self._quadrant_from_bbox(bbox),
            relative_depth_m=depth_value,
        )

    def _quadrant_from_bbox(self, bbox: BoundingBox) -> Quadrant:
        cx, cy = bbox.center
        col = 0 if cx < 1 / 3 else (1 if cx < 2 / 3 else 2)
        row = 0 if cy < 1 / 3 else (1 if cy < 2 / 3 else 2)
        mapping: dict[tuple[int, int], Quadrant] = {
            (0, 0): Quadrant.TOP_LEFT,
            (1, 0): Quadrant.TOP_CENTER,
            (2, 0): Quadrant.TOP_RIGHT,
            (0, 1): Quadrant.MIDDLE_LEFT,
            (1, 1): Quadrant.CENTER,
            (2, 1): Quadrant.MIDDLE_RIGHT,
            (0, 2): Quadrant.BOTTOM_LEFT,
            (1, 2): Quadrant.BOTTOM_CENTER,
            (2, 2): Quadrant.BOTTOM_RIGHT,
        }
        return mapping[(col, row)]

    def _summarize_center(self, depth_map: np.ndarray, width: int, height: int) -> CenterDistanceSummary:
        h, w = depth_map.shape
        x_start = w // 3
        x_end = 2 * w // 3
        y_start = h // 3
        y_end = 2 * h // 3
        center_region = depth_map[y_start:y_end, x_start:x_end]
        valid = center_region[np.isfinite(center_region)]
        if valid.size == 0:
            return CenterDistanceSummary(advisory="No valid depth in center region.")
        median_depth = float(np.median(valid))
        return CenterDistanceSummary(
            distance_m=median_depth,
            confidence=0.8,
            advisory="Median relative depth (0-1 scale) derived from MiDaS center region.",
        )
