from __future__ import annotations

import base64
import time
import uuid
from datetime import datetime

import cv2

import sys
from pathlib import Path

if __package__ in (None, ""):
    # allow running this file directly (python vision/run_camera.py)
    # by adding the vision package dir and repo root to sys.path so
    # imports for sibling packages work.
    repo_dir = str(Path(__file__).resolve().parent.parent)
    vision_dir = str(Path(__file__).resolve().parent)
    sys.path.insert(0, repo_dir)
    sys.path.insert(0, vision_dir)
    from pipeline import VisionPipeline
    from schemas import FrameAnalysisRequest, FrameMetadata, Environment
else:
    from .pipeline import VisionPipeline
    from .schemas import FrameAnalysisRequest, FrameMetadata, Environment

try:
    from ElevenLabs.obstacle_alert import ObstacleAlertSystem
except Exception:
    # fallback: ensure repo root is on path and import
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from ElevenLabs.obstacle_alert import ObstacleAlertSystem


def frame_to_base64(frame) -> str:
    ret, buf = cv2.imencode('.jpg', frame)
    if not ret:
        raise RuntimeError('Failed to encode frame')
    return base64.b64encode(buf.tobytes()).decode('ascii')


def run_camera_loop(device_index: int = 0, fps_limit: float = 1.0) -> None:
    def _try_open(idx: int):
        # Try a few common backends on macOS to improve camera compatibility.
        backends = [None]
        # Add AVFoundation if available (macOS)
        if hasattr(cv2, "CAP_AVFOUNDATION"):
            backends.append(cv2.CAP_AVFOUNDATION)
        # Generic any
        if hasattr(cv2, "CAP_ANY"):
            backends.append(cv2.CAP_ANY)

        last_exc = None
        for b in backends:
            try:
                if b is None:
                    cap_try = cv2.VideoCapture(idx)
                else:
                    cap_try = cv2.VideoCapture(idx, b)
                print(f"Tried VideoCapture(idx={idx}, backend={b}) -> isOpened={cap_try.isOpened()}")
                if cap_try.isOpened():
                    return cap_try
                cap_try.release()
            except Exception as exc:
                last_exc = exc
                print(f"VideoCapture attempt failed for backend={b}: {exc}")
        if last_exc:
            raise last_exc
        return None

    cap = _try_open(device_index)
    if cap is None or not cap.isOpened():
        raise RuntimeError(f"Unable to open camera device {device_index}. Check macOS camera permissions and that no other app is using the camera.")

    print(f"Camera opened: isOpened={cap.isOpened()}")

    pipeline = VisionPipeline()
    # if SnowFlake HTTP server is running, post frames to it; otherwise fall back to local processor
    import os
    SERVER_URL = os.environ.get("SNOWFLAKE_SERVER_URL", "http://127.0.0.1:8001")
    use_http = True
    try:
        import requests
    except Exception:
        requests = None
        use_http = False

    if use_http and requests is not None:
        # a quick check
        try:
            requests.get(f"{SERVER_URL}/health", timeout=1.0)
        except Exception:
            use_http = False

    processor = ObstacleAlertSystem(min_alert_interval_s=5.0, object_memory_s=10.0, alert_cooldown_s=30.0) if not use_http else None

    print("Starting camera loop. Press Ctrl+C to stop.")
    last_time = 0.0
    try:
        while True:
            now = time.time()
            if now - last_time < 1.0 / fps_limit:
                time.sleep(0.01)
                continue
            last_time = now

            ret, frame = cap.read()
            print(f"cap.read() returned: {ret}, frame is None: {frame is None}")
            if not ret or frame is None:
                print("Failed to read frame from camera. Will retry after short delay.")
                time.sleep(0.5)
                # continue instead of breaking so we can tolerate transient read failures
                continue

            h, w = frame.shape[:2]
            img_b64 = frame_to_base64(frame)
            payload = FrameAnalysisRequest(
                frame_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                frame_metadata=FrameMetadata(width=w, height=h),
                image_base64=img_b64,
                environment=Environment.OUTDOOR,
            )

            try:
                response = pipeline.process(payload)
                # Debug: print detection summary so user can see what's happening
                obj_count = len(response.objects) if response.objects is not None else 0
                print(f"Processed frame {payload.frame_id}: detected {obj_count} objects")
                if obj_count:
                    top = response.objects[0]
                    print(
                        f" Top object: label={top.label}, conf={top.confidence:.2f}, quadrant={top.quadrant}, depth_rel={top.relative_depth_m}"
                    )
                # Send to SnowFlake server if available, otherwise use local processor
                if use_http and requests is not None:
                    try:
                        j = response.model_dump()
                        r = requests.post(f"{SERVER_URL}/process_frame", json=j, timeout=2.0)
                        if r.ok:
                            print(f"Posted frame {payload.frame_id} to SnowFlake server")
                        else:
                            print("SnowFlake server returned error:", r.text)
                    except Exception as e:
                        print("Error posting to SnowFlake server:", e)
                        # fallback to local
                        msg = processor.process_frame(response) if processor is not None else None
                        if msg:
                            print(f"Spoken alert: {msg}")
                else:
                    msg = processor.process_frame(response)
                    if msg:
                        print(f"Spoken alert: {msg}")
                # Draw simple overlays and show the frame so you can visually confirm detections
                try:
                    for obj in response.objects:
                        bb = obj.bounding_box
                        h, w = frame.shape[:2]
                        x1 = int(bb.x_min * w)
                        y1 = int(bb.y_min * h)
                        x2 = int(bb.x_max * w)
                        y2 = int(bb.y_max * h)
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(
                            frame,
                            f"{obj.label} {obj.confidence:.2f}",
                            (x1, max(10, y1 - 6)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (0, 255, 0),
                            1,
                        )
                    cv2.imshow("Vision - press q to quit", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        print("Exiting by user keypress.")
                        break
                except Exception:
                    # If GUI not available, ignore display errors
                    pass
            except Exception as exc:
                print(f"Error processing frame: {exc}")

    except KeyboardInterrupt:
        print("Camera loop interrupted by user.")
    finally:
        cap.release()


if __name__ == "__main__":
    run_camera_loop()
