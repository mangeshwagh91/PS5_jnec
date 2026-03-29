from __future__ import annotations

import argparse
import json
import queue
import random
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from urllib import error, request

# Allow running as a script without manual PYTHONPATH setup.
REPO_SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_SERVER_ROOT))

from app.services.vision_pipeline import RawDetection, VisionRuleEngine


@dataclass
class WorkerConfig:
    api_base_url: str
    api_key: str
    mode: str
    weights: str
    device: str
    inference_imgsz: int
    yolo_confidence: float
    min_confidence: float
    profile: str
    label_map_path: str
    preview_dir: str
    draw_boxes: bool
    preview_write_every_n_frames: int
    smoke_confidence_threshold: float
    fire_confidence_threshold: float
    weapon_confidence_threshold: float
    smoke_confirmation_frames: int


@dataclass
class CameraConfig:
    camera_id: str
    stream_url: str
    location: str
    source: str = "cctv"
    sample_every_n_frames: int = 2


@dataclass
class FramePacket:
    camera_id: str
    location: str
    source: str
    frame_w: int
    frame_h: int
    frame: object


class MockDetector:
    LABEL_POOL = ["person", "weapon", "trash_bag", "smoke", "fire"]

    def detect(self, frame_w: int, frame_h: int) -> list[RawDetection]:
        count = random.randint(0, 3)
        detections: list[RawDetection] = []
        for _ in range(count):
            label = random.choice(self.LABEL_POOL)
            conf = round(random.uniform(0.5, 0.98), 2)
            x1 = random.uniform(0, frame_w * 0.8)
            y1 = random.uniform(0, frame_h * 0.8)
            x2 = min(x1 + random.uniform(20, frame_w * 0.2), frame_w)
            y2 = min(y1 + random.uniform(20, frame_h * 0.2), frame_h)
            detections.append(
                RawDetection(
                    label=label,
                    confidence=conf,
                    bbox_xyxy=(x1, y1, x2, y2),
                    track_id=str(random.randint(1, 20)),
                )
            )
        return detections


class SharedYoloDetector:
    """Single YOLO model instance shared by all cameras in this worker process."""

    def __init__(self, weights_path: str, device: str, inference_imgsz: int, yolo_confidence: float) -> None:
        try:
            from ultralytics import YOLO  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "ultralytics is not installed. Install optional vision dependencies first."
            ) from exc

        effective_weights = weights_path.strip() or "yolo11n.pt"
        self._model = YOLO(effective_weights)
        self._device = device.strip() if device else ""
        self._imgsz = max(inference_imgsz, 160)
        self._conf = max(min(yolo_confidence, 1.0), 0.0)

    def detect(self, frame) -> list[RawDetection]:
        kwargs = {"verbose": False, "imgsz": self._imgsz, "conf": self._conf}
        if self._device:
            kwargs["device"] = self._device

        results = self._model(frame, **kwargs)
        if not results:
            return []

        detections: list[RawDetection] = []
        names = results[0].names
        boxes = results[0].boxes
        for i in range(len(boxes)):
            cls_idx = int(boxes.cls[i].item())
            conf = float(boxes.conf[i].item())
            x1, y1, x2, y2 = [float(v) for v in boxes.xyxy[i].tolist()]
            label = str(names.get(cls_idx, "unknown")).lower()
            detections.append(
                RawDetection(
                    label=label,
                    confidence=conf,
                    bbox_xyxy=(x1, y1, x2, y2),
                    track_id=None,
                )
            )
        return detections


def _load_label_map(path_str: str) -> dict[str, str]:
    if not path_str.strip():
        return {}

    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"Label map file not found: {path}")

    content = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(content, dict):
        raise ValueError("Label map file must be a JSON object")

    normalized: dict[str, str] = {}
    for key, value in content.items():
        normalized[str(key).strip().lower()] = str(value).strip().lower()
    return normalized


def _profile_from_weights(weights_path: str) -> str:
    name = Path(weights_path).name.lower()
    if any(token in name for token in ["smoke", "fire", "hazard"]):
        return "fire-smoke"
    if any(token in name for token in ["weapon", "gun", "knife", "firing", "firearm"]):
        return "weapon"
    return "generic"


def _parse_camera_config(config_path: str) -> list[CameraConfig]:
    raw = json.loads(Path(config_path).read_text(encoding="utf-8-sig"))
    if not isinstance(raw, list):
        raise ValueError("Camera config must be a JSON array")

    cameras: list[CameraConfig] = []
    for idx, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(f"Camera config entry #{idx + 1} must be an object")

        camera_id = str(entry.get("camera_id", "")).strip()
        stream_url = str(entry.get("stream_url", "")).strip()
        location = str(entry.get("location", camera_id)).strip() or camera_id
        source = str(entry.get("source", "cctv")).strip() or "cctv"

        sample_every = entry.get("sample_every_n_frames", 2)
        try:
            sample_every_n_frames = max(int(sample_every), 1)
        except Exception:
            sample_every_n_frames = 2

        if not camera_id or not stream_url:
            raise ValueError(
                f"Camera config entry #{idx + 1} must include non-empty camera_id and stream_url"
            )

        cameras.append(
            CameraConfig(
                camera_id=camera_id,
                stream_url=stream_url,
                location=location,
                source=source,
                sample_every_n_frames=sample_every_n_frames,
            )
        )

    if not cameras:
        raise ValueError("Camera config has no valid camera entries")

    return cameras


def _parse_args() -> tuple[WorkerConfig, str]:
    parser = argparse.ArgumentParser(
        description="Shared multi-camera vision worker (single model instance per worker process)"
    )
    parser.add_argument("--config", required=True, help="JSON file listing cameras for this worker")
    parser.add_argument("--api-base-url", default="http://localhost:8001/api/v1")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--mode", choices=["mock", "yolo"], default="yolo")
    parser.add_argument("--weights", required=True, help="Path to YOLO weights (.pt)")
    parser.add_argument("--device", default="", help="Inference device, e.g. cpu, 0, cuda:0")
    parser.add_argument("--inference-imgsz", type=int, default=416)
    parser.add_argument(
        "--yolo-conf",
        type=float,
        default=-1.0,
        help="YOLO confidence cutoff; if negative, auto-selected from weights filename",
    )
    parser.add_argument("--min-confidence", type=float, default=0.55)
    parser.add_argument("--label-map", default="")
    parser.add_argument("--preview-dir", default="")
    parser.add_argument(
        "--draw-boxes",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Draw detection boxes onto preview frames",
    )
    parser.add_argument(
        "--preview-write-every-n-frames",
        type=int,
        default=1,
        help="Write preview JPEG every N processed frames",
    )
    parser.add_argument("--smoke-confidence-threshold", type=float, default=0.15)
    parser.add_argument("--fire-confidence-threshold", type=float, default=0.25)
    parser.add_argument("--weapon-confidence-threshold", type=float, default=0.25)
    parser.add_argument("--smoke-confirmation-frames", type=int, default=5)

    args = parser.parse_args()

    profile = _profile_from_weights(args.weights)
    if args.yolo_conf < 0:
        if profile == "fire-smoke":
            yolo_conf = 0.01
        elif profile == "weapon":
            yolo_conf = 0.2
        else:
            yolo_conf = 0.2
    else:
        yolo_conf = max(min(args.yolo_conf, 1.0), 0.0)

    min_confidence = max(min(args.min_confidence, 1.0), 0.0)
    inference_imgsz = max(int(args.inference_imgsz), 160)

    if profile == "fire-smoke":
        min_confidence = min(min_confidence, 0.15)
        inference_imgsz = max(inference_imgsz, 416)
    elif profile == "weapon":
        min_confidence = min(min_confidence, 0.25)

    cfg = WorkerConfig(
        api_base_url=args.api_base_url.rstrip("/"),
        api_key=args.api_key,
        mode=args.mode,
        weights=args.weights,
        device=args.device,
        inference_imgsz=inference_imgsz,
        yolo_confidence=yolo_conf,
        min_confidence=min_confidence,
        profile=profile,
        label_map_path=args.label_map,
        preview_dir=args.preview_dir,
        draw_boxes=args.draw_boxes,
        preview_write_every_n_frames=max(args.preview_write_every_n_frames, 1),
        smoke_confidence_threshold=max(min(args.smoke_confidence_threshold, 1.0), 0.0),
        fire_confidence_threshold=max(min(args.fire_confidence_threshold, 1.0), 0.0),
        weapon_confidence_threshold=max(min(args.weapon_confidence_threshold, 1.0), 0.0),
        smoke_confirmation_frames=max(args.smoke_confirmation_frames, 1),
    )
    return cfg, args.config


def _passes_label_threshold(det: RawDetection, cfg: WorkerConfig) -> bool:
    label = det.label.lower().strip()
    if label in {"smoke"}:
        return det.confidence >= cfg.smoke_confidence_threshold
    if label in {"fire", "flame"}:
        return det.confidence >= cfg.fire_confidence_threshold
    if label in {"weapon", "gun", "knife", "pistol", "rifle", "firearm"}:
        return det.confidence >= cfg.weapon_confidence_threshold
    return det.confidence >= cfg.min_confidence


def _normalize_labels(detections: list[RawDetection], label_map: dict[str, str]) -> list[RawDetection]:
    if not label_map:
        return detections

    normalized: list[RawDetection] = []
    for det in detections:
        mapped = label_map.get(det.label.lower().strip(), det.label.lower().strip())
        normalized.append(
            RawDetection(
                label=mapped,
                confidence=det.confidence,
                bbox_xyxy=det.bbox_xyxy,
                track_id=det.track_id,
            )
        )
    return normalized


def _draw_overlay(frame, detections: list[RawDetection]) -> None:
    import cv2  # type: ignore

    for det in detections:
        x1, y1, x2, y2 = [int(v) for v in det.bbox_xyxy]
        cv2.rectangle(frame, (x1, y1), (x2, y2), (46, 204, 113), 2)
        text = f"{det.label} {det.confidence:.2f}"
        cv2.putText(frame, text, (x1, max(y1 - 8, 18)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (46, 204, 113), 2)


def _post_event(base_url: str, api_key: str, payload: dict) -> tuple[int, str]:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    req = request.Request(url=f"{base_url}/events", data=body, headers=headers, method="POST")
    with request.urlopen(req, timeout=10) as resp:
        detail = ""
        raw = resp.read().decode("utf-8", errors="ignore")
        if raw:
            try:
                parsed = json.loads(raw)
                detail = str(parsed.get("detail", ""))
            except Exception:
                detail = ""
        return resp.status, detail


def _capture_thread(cam: CameraConfig, infer_queue: queue.Queue, stop_event: threading.Event) -> None:
    import cv2  # type: ignore

    source = int(cam.stream_url) if cam.stream_url.isdigit() else cam.stream_url
    is_local_file_source = isinstance(source, str) and Path(source).exists()

    if isinstance(source, int) and sys.platform == "win32":
        cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    else:
        cap = cv2.VideoCapture(source)
        
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print(f"[{cam.camera_id}] Cannot open stream: {cam.stream_url}")
        return

    stream_fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    frame_delay = 0.0
    if is_local_file_source:
        fps_for_delay = min(stream_fps, 60.0) if stream_fps > 1.0 else 25.0
        frame_delay = 1.0 / fps_for_delay
        print(
            f"[{cam.camera_id}] Local file source: throttling to {fps_for_delay:.2f} FPS"
            f" ({frame_delay * 1000.0:.1f} ms/frame)"
        )

    frame_idx = 0
    print(f"[{cam.camera_id}] Capture started")

    try:
        while not stop_event.is_set():
            ok, frame = cap.read()
            if not ok:
                if is_local_file_source:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                time.sleep(0.05)
                continue

            if frame_delay > 0.0:
                time.sleep(frame_delay)

            frame_idx += 1
            if frame_idx % cam.sample_every_n_frames != 0:
                continue

            if frame.shape[1] > 640:
                new_h = max(int(frame.shape[0] * (640.0 / frame.shape[1])), 1)
                frame = cv2.resize(frame, (640, new_h))

            frame_h, frame_w = frame.shape[:2]
            packet = FramePacket(
                camera_id=cam.camera_id,
                location=cam.location,
                source=cam.source,
                frame_w=frame_w,
                frame_h=frame_h,
                frame=frame,
            )
            try:
                infer_queue.put_nowait(packet)
            except queue.Full:
                pass
    finally:
        cap.release()
        print(f"[{cam.camera_id}] Capture stopped")


def _inference_thread(
    infer_queue: queue.Queue,
    preview_queues: dict[str, queue.Queue],
    event_queue: queue.Queue,
    detector,
    rule_engines: dict[str, VisionRuleEngine],
    label_map: dict[str, str],
    cfg: WorkerConfig,
    stop_event: threading.Event,
) -> None:
    processed_by_camera: dict[str, int] = {}

    while not stop_event.is_set():
        try:
            packet: FramePacket = infer_queue.get(timeout=0.1)
        except queue.Empty:
            continue

        if cfg.mode == "mock":
            detections = detector.detect(frame_w=packet.frame_w, frame_h=packet.frame_h)
        else:
            detections = detector.detect(packet.frame)

        detections = _normalize_labels(detections, label_map)
        detections = [det for det in detections if _passes_label_threshold(det, cfg)]

        events = rule_engines[packet.camera_id].evaluate(
            detections=detections,
            frame_w=packet.frame_w,
            frame_h=packet.frame_h,
            camera_id=packet.camera_id,
            location=packet.location,
            source=packet.source,
        )

        processed = processed_by_camera.get(packet.camera_id, 0) + 1
        processed_by_camera[packet.camera_id] = processed

        if processed % cfg.preview_write_every_n_frames == 0:
            out_frame = packet.frame.copy()
            if cfg.draw_boxes:
                _draw_overlay(out_frame, detections)
            try:
                preview_queues[packet.camera_id].put_nowait(out_frame)
            except queue.Full:
                pass

        for event in events:
            try:
                event_queue.put_nowait(event)
            except queue.Full:
                pass


def _preview_writer_thread(
    camera_id: str,
    preview_queue: queue.Queue,
    output_path: Path,
    stop_event: threading.Event,
) -> None:
    import cv2  # type: ignore

    while not stop_event.is_set():
        try:
            frame = preview_queue.get(timeout=0.1)
        except queue.Empty:
            continue

        try:
            cv2.imwrite(str(output_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 65])
        except Exception:
            pass

    print(f"[{camera_id}] Preview writer stopped")


def _event_poster_thread(event_queue: queue.Queue, cfg: WorkerConfig, stop_event: threading.Event) -> None:
    sent = 0

    while not stop_event.is_set():
        try:
            event = event_queue.get(timeout=0.1)
        except queue.Empty:
            continue

        payload = event.model_dump(mode="json")
        if payload.get("threat_type") == "hazard" and float(payload.get("confidence", 0.0)) < 0.2:
            payload["confidence"] = 0.2

        try:
            status, detail = _post_event(cfg.api_base_url, cfg.api_key, payload)
            sent += 1
            if status == 202:
                note = detail or "ignored/deduplicated by backend"
                print(
                    f"[event:{sent}] status={status}"
                    f" type={payload['threat_type']} cam={payload['camera_id']} note={note}"
                )
            else:
                print(
                    f"[event:{sent}] status={status}"
                    f" type={payload['threat_type']} cam={payload['camera_id']}"
                )
        except error.HTTPError as exc:
            print(f"Event rejected: HTTP {exc.code}")
        except Exception as exc:  # pragma: no cover
            print(f"Event post failed: {exc}")


def main() -> None:
    cfg, config_path = _parse_args()

    try:
        import cv2  # noqa: F401 # type: ignore
    except Exception as exc:
        raise RuntimeError("opencv-python-headless is required for multi-camera vision worker") from exc

    label_map = _load_label_map(cfg.label_map_path)
    cameras = _parse_camera_config(config_path)

    preview_base = Path(cfg.preview_dir.strip()) if cfg.preview_dir.strip() else (
        Path(__file__).resolve().parents[2] / "client" / "public" / "live"
    )
    preview_base.mkdir(parents=True, exist_ok=True)

    if cfg.mode == "mock":
        detector = MockDetector()
    else:
        detector = SharedYoloDetector(cfg.weights, cfg.device, cfg.inference_imgsz, cfg.yolo_confidence)

    rule_engines = {
        cam.camera_id: VisionRuleEngine(smoke_consecutive_frames=cfg.smoke_confirmation_frames)
        for cam in cameras
    }
    preview_queues = {cam.camera_id: queue.Queue(maxsize=2) for cam in cameras}

    infer_queue: queue.Queue = queue.Queue(maxsize=max(len(cameras) * 2, 4))
    event_queue: queue.Queue = queue.Queue(maxsize=50)
    stop_event = threading.Event()

    threads: list[threading.Thread] = []

    for cam in cameras:
        threads.append(
            threading.Thread(
                target=_capture_thread,
                args=(cam, infer_queue, stop_event),
                daemon=True,
                name=f"capture-{cam.camera_id}",
            )
        )

    threads.append(
        threading.Thread(
            target=_inference_thread,
            args=(
                infer_queue,
                preview_queues,
                event_queue,
                detector,
                rule_engines,
                label_map,
                cfg,
                stop_event,
            ),
            daemon=True,
            name=f"inference-{cfg.profile}",
        )
    )

    for cam in cameras:
        output_path = preview_base / f"{cam.camera_id}.jpg"
        threads.append(
            threading.Thread(
                target=_preview_writer_thread,
                args=(cam.camera_id, preview_queues[cam.camera_id], output_path, stop_event),
                daemon=True,
                name=f"preview-{cam.camera_id}",
            )
        )

    threads.append(
        threading.Thread(
            target=_event_poster_thread,
            args=(event_queue, cfg, stop_event),
            daemon=True,
            name="event-poster",
        )
    )

    print(
        f"Worker ready: profile={cfg.profile} mode={cfg.mode}"
        f" cameras={len(cameras)} weights={Path(cfg.weights).name}"
        f" imgsz={cfg.inference_imgsz} yolo-conf={cfg.yolo_confidence:.3f}"
    )
    print(
        f"Threads: {len(cameras)} capture + 1 inference + {len(cameras)} preview + 1 event poster"
    )
    print("Press Ctrl+C to stop.")

    for thread in threads:
        thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        stop_event.set()
        for thread in threads:
            thread.join(timeout=2.0)
        print("Done.")


if __name__ == "__main__":
    main()
