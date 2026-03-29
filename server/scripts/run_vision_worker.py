from __future__ import annotations

import argparse
import json
import queue
import random
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib import error, request

# Allow running as a script (python scripts/run_vision_worker.py) without manual PYTHONPATH export.
REPO_SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_SERVER_ROOT))

from app.services.vision_pipeline import RawDetection, VisionRuleEngine


@dataclass
class WorkerConfig:
    api_base_url: str
    api_key: str
    stream_url: str
    camera_id: str
    location: str
    source: str
    sample_every_n_frames: int
    min_confidence: float
    mode: str
    yolo_weights: str
    yolo_confidence: float
    label_map_path: str
    show_overlay: bool
    device: str
    inference_imgsz: int
    preview_output_path: str
    camera_fps: float
    camera_width: int
    camera_height: int
    profile: str
    smoke_confidence_threshold: float
    fire_confidence_threshold: float
    weapon_confidence_threshold: float
    smoke_confirmation_frames: int
    draw_boxes: bool
    preview_write_every_n_frames: int


@dataclass
class _SharedState:
    detections: list[RawDetection] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def update(self, detections: list[RawDetection]) -> None:
        with self.lock:
            self.detections = detections

    def get(self) -> list[RawDetection]:
        with self.lock:
            return list(self.detections)


class _MockDetector:
    LABEL_POOL = [
        "person",
        "weapon",
        "trash_bag",
        "smoke",
        "fire",
    ]

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
                RawDetection(label=label, confidence=conf, bbox_xyxy=(x1, y1, x2, y2), track_id=str(random.randint(1, 20)))
            )
        return detections


class _YoloDetector:
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
            detections.append(RawDetection(label=label, confidence=conf, bbox_xyxy=(x1, y1, x2, y2), track_id=None))
        return detections


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


def _load_label_map(path_str: str) -> dict[str, str]:
    if not path_str.strip():
        return {}

    path = Path(path_str)
    if not path.exists():
        raise FileNotFoundError(f"Label map file not found: {path}")

    content = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(content, dict):
        raise ValueError("Label map file must be a JSON object")

    normalized: dict[str, str] = {}
    for key, value in content.items():
        normalized[str(key).strip().lower()] = str(value).strip().lower()
    return normalized


def _parse_args() -> WorkerConfig:
    parser = argparse.ArgumentParser(description="Vision worker that turns camera detections into dashboard events")
    parser.add_argument("--api-base-url", "--base-url", dest="api_base_url", default="http://localhost:8001/api/v1")
    parser.add_argument("--api-key", "--ingestion-api-key", dest="api_key", default="")
    parser.add_argument("--stream-url", default="0", help="RTSP URL, video file path, or webcam index")
    parser.add_argument("--camera-id", default="CAM-012")
    parser.add_argument("--location", default="North Entrance")
    parser.add_argument("--source", default="cctv")
    parser.add_argument("--sample-every-n-frames", type=int, default=2)
    parser.add_argument("--min-confidence", type=float, default=0.55)
    parser.add_argument("--mode", choices=["mock", "yolo"], default="mock")
    parser.add_argument(
        "--yolo-weights",
        "--weights",
        dest="yolo_weights",
        default="",
        help="Path to YOLO weights (.pt). Defaults to yolo11n.pt when empty",
    )
    parser.add_argument(
        "--yolo-conf",
        type=float,
        default=-1.0,
        help="YOLO internal confidence cutoff before post-processing. Auto-selected per profile when negative.",
    )
    parser.add_argument(
        "--label-map",
        default="",
        help="Optional JSON file mapping raw model labels to canonical labels (weapon/trash_bag/fire/smoke/person/etc)",
    )
    parser.add_argument("--show-overlay", action="store_true", help="Show realtime detections in an OpenCV window")
    parser.add_argument("--device", default="", help="Inference device, e.g. cpu, 0, cuda:0")
    parser.add_argument("--inference-imgsz", type=int, default=416, help="Inference image size for speed/accuracy tradeoff")
    parser.add_argument("--preview-output-path", default="", help="Optional path to write latest processed frame as JPEG")
    parser.add_argument("--camera-fps", type=float, default=60.0, help="Requested FPS for webcam sources")
    parser.add_argument("--camera-width", type=int, default=1280, help="Requested webcam capture width")
    parser.add_argument("--camera-height", type=int, default=720, help="Requested webcam capture height")
    parser.add_argument(
        "--profile",
        choices=["auto", "fire-smoke", "weapon", "generic"],
        default="auto",
        help="Runtime tuning profile for model-specific thresholds and confirmation rules",
    )
    parser.add_argument("--smoke-confidence-threshold", type=float, default=0.15)
    parser.add_argument("--fire-confidence-threshold", type=float, default=0.25)
    parser.add_argument("--weapon-confidence-threshold", type=float, default=0.25)
    parser.add_argument("--smoke-confirmation-frames", type=int, default=5)
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
        help="Write preview JPEG every N processed frames to reduce disk and CPU load",
    )
    args = parser.parse_args()

    effective_profile = args.profile
    if effective_profile == "auto":
        joined = f"{args.yolo_weights} {args.camera_id} {args.location}".lower()
        if any(token in joined for token in ["smoke", "fire"]):
            effective_profile = "fire-smoke"
        elif any(token in joined for token in ["weapon", "gun", "knife"]):
            effective_profile = "weapon"
        else:
            effective_profile = "generic"

    inference_imgsz = max(args.inference_imgsz, 160)
    min_confidence = max(min(args.min_confidence, 1.0), 0.0)
    if effective_profile == "fire-smoke":
        min_confidence = min(min_confidence, 0.15)
        # 416 improves throughput substantially for smoother preview updates.
        inference_imgsz = max(inference_imgsz, 416)
    elif effective_profile == "weapon":
        min_confidence = min(min_confidence, 0.25)

    if args.yolo_conf < 0:
        if effective_profile == "fire-smoke":
            yolo_confidence = 0.01
        elif effective_profile == "weapon":
            yolo_confidence = 0.2
        else:
            yolo_confidence = 0.2
    else:
        yolo_confidence = max(min(args.yolo_conf, 1.0), 0.0)

    cfg = WorkerConfig(
        api_base_url=args.api_base_url.rstrip("/"),
        api_key=args.api_key,
        stream_url=args.stream_url,
        camera_id=args.camera_id,
        location=args.location,
        source=args.source,
        sample_every_n_frames=max(args.sample_every_n_frames, 1),
        min_confidence=min_confidence,
        mode=args.mode,
        yolo_weights=args.yolo_weights,
        yolo_confidence=yolo_confidence,
        label_map_path=args.label_map,
        show_overlay=args.show_overlay,
        device=args.device,
        inference_imgsz=inference_imgsz,
        preview_output_path=args.preview_output_path,
        camera_fps=max(args.camera_fps, 1.0),
        camera_width=max(args.camera_width, 160),
        camera_height=max(args.camera_height, 120),
        profile=effective_profile,
        smoke_confidence_threshold=max(min(args.smoke_confidence_threshold, 1.0), 0.0),
        fire_confidence_threshold=max(min(args.fire_confidence_threshold, 1.0), 0.0),
        weapon_confidence_threshold=max(min(args.weapon_confidence_threshold, 1.0), 0.0),
        smoke_confirmation_frames=max(args.smoke_confirmation_frames, 1),
        draw_boxes=args.draw_boxes,
        preview_write_every_n_frames=max(args.preview_write_every_n_frames, 1),
    )
    return cfg


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


def _inference_thread(
    infer_queue: queue.Queue,
    preview_queue: queue.Queue,
    event_queue: queue.Queue,
    shared: _SharedState,
    detector,
    cfg: WorkerConfig,
    label_map: dict[str, str],
    rule_engine: VisionRuleEngine,
    stop_event: threading.Event,
) -> None:
    processed_idx = 0

    while not stop_event.is_set():
        try:
            frame, frame_w, frame_h = infer_queue.get(timeout=0.1)
        except queue.Empty:
            continue

        if cfg.mode == "mock":
            detections = detector.detect(frame_w=frame_w, frame_h=frame_h)
        else:
            detections = detector.detect(frame)

        detections = _normalize_labels(detections, label_map)
        detections = [d for d in detections if _passes_label_threshold(d, cfg)]
        shared.update(detections)
        processed_idx += 1

        if processed_idx % cfg.preview_write_every_n_frames == 0:
            frame_for_output = frame.copy()
            if cfg.draw_boxes:
                _draw_overlay(frame_for_output, detections)
            try:
                preview_queue.put_nowait(frame_for_output)
            except queue.Full:
                pass

        events = rule_engine.evaluate(
            detections=detections,
            frame_w=frame_w,
            frame_h=frame_h,
            camera_id=cfg.camera_id,
            location=cfg.location,
            source=cfg.source,
        )
        for event in events:
            try:
                event_queue.put_nowait(event)
            except queue.Full:
                pass


def _preview_writer_thread(
    preview_queue: queue.Queue,
    preview_output_path: Path,
    stop_event: threading.Event,
) -> None:
    try:
        import cv2  # type: ignore
    except Exception:
        return

    while not stop_event.is_set():
        try:
            frame = preview_queue.get(timeout=0.1)
        except queue.Empty:
            continue

        try:
            cv2.imwrite(
                str(preview_output_path),
                frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), 65],
            )
        except Exception:
            pass


def _event_poster_thread(
    event_queue: queue.Queue,
    cfg: WorkerConfig,
    stop_event: threading.Event,
) -> None:
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
                print(f"[{sent}] status={status} type={payload['threat_type']} conf={payload['confidence']} note={note}")
            else:
                print(f"[{sent}] status={status} type={payload['threat_type']} conf={payload['confidence']}")
        except error.HTTPError as exc:
            print(f"Event rejected: HTTP {exc.code}")
        except Exception as exc:  # pragma: no cover
            print(f"Event post failed: {exc}")


def main() -> None:
    cfg = _parse_args()
    label_map = _load_label_map(cfg.label_map_path)

    rule_engine = VisionRuleEngine(smoke_consecutive_frames=cfg.smoke_confirmation_frames)

    if cfg.mode == "mock":
        detector = _MockDetector()
    else:
        detector = _YoloDetector(cfg.yolo_weights, cfg.device, cfg.inference_imgsz, cfg.yolo_confidence)

    try:
        import cv2  # type: ignore
    except Exception as exc:
        raise RuntimeError("opencv-python-headless is required for vision worker") from exc

    source = int(cfg.stream_url) if cfg.stream_url.isdigit() else cfg.stream_url
    is_local_file_source = isinstance(source, str) and Path(source).exists()

    preview_output = cfg.preview_output_path.strip()
    if not preview_output:
        preview_output = str(Path(__file__).resolve().parents[2] / "client" / "public" / "live" / f"{cfg.camera_id}.jpg")
    preview_output_path = Path(preview_output)
    preview_output_path.parent.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(source)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if isinstance(source, int):
        cap.set(cv2.CAP_PROP_FPS, cfg.camera_fps)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.camera_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.camera_height)

    if not cap.isOpened():
        raise RuntimeError(f"Cannot open stream source: {cfg.stream_url}")

    stream_fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    stream_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0.0
    stream_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0.0
    if isinstance(source, int):
        print(
            f"Webcam request: {cfg.camera_width}x{cfg.camera_height} @ {cfg.camera_fps:.1f} FPS"
            f" | actual: {int(stream_w)}x{int(stream_h)} @ {stream_fps:.2f} FPS"
        )
    if stream_fps > 0:
        effective_interval_ms = (cfg.sample_every_n_frames / stream_fps) * 1000.0
        print(
            f"Sampling every {cfg.sample_every_n_frames} frame(s) at {stream_fps:.2f} FPS"
            f" -> effective interval {effective_interval_ms:.1f} ms"
        )

    # Local files need explicit pacing; live streams/cameras self-throttle.
    frame_delay = 0.0
    if is_local_file_source:
        fps_for_delay = stream_fps if stream_fps > 1.0 else 25.0
        frame_delay = 1.0 / fps_for_delay
        print(
            f"Local file source: throttling playback to {fps_for_delay:.2f} FPS"
            f" ({frame_delay * 1000.0:.1f} ms/frame)"
        )

    frame_idx = 0
    print("Vision worker started. Press Ctrl+C to stop.")
    if cfg.mode == "yolo":
        print("YOLO mode active: detections come from real camera/video frames.")
    print(
        "Profile=%s | imgsz=%s | yolo-conf>=%.2f | conf weapon>=%.2f fire>=%.2f smoke>=%.2f | smoke frames=%s"
        % (
            cfg.profile,
            cfg.inference_imgsz,
            cfg.yolo_confidence,
            cfg.weapon_confidence_threshold,
            cfg.fire_confidence_threshold,
            cfg.smoke_confidence_threshold,
            cfg.smoke_confirmation_frames,
        )
    )
    if label_map:
        print(f"Label map loaded: {len(label_map)} entries")

    infer_queue: queue.Queue = queue.Queue(maxsize=1)
    preview_queue: queue.Queue = queue.Queue(maxsize=2)
    event_queue: queue.Queue = queue.Queue(maxsize=20)
    shared = _SharedState()
    stop_event = threading.Event()

    threads = [
        threading.Thread(
            target=_inference_thread,
            args=(
                infer_queue,
                preview_queue,
                event_queue,
                shared,
                detector,
                cfg,
                label_map,
                rule_engine,
                stop_event,
            ),
            daemon=True,
            name="inference",
        ),
        threading.Thread(
            target=_preview_writer_thread,
            args=(preview_queue, preview_output_path, stop_event),
            daemon=True,
            name="preview-writer",
        ),
        threading.Thread(
            target=_event_poster_thread,
            args=(event_queue, cfg, stop_event),
            daemon=True,
            name="event-poster",
        ),
    ]
    for thread in threads:
        thread.start()

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                # Local video files can reach EOF; rewind so detections continue.
                if is_local_file_source:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                time.sleep(0.05)
                continue

            if frame_delay > 0.0:
                time.sleep(frame_delay)

            frame_idx += 1
            if frame_idx % cfg.sample_every_n_frames == 0:
                h, w = frame.shape[:2]
                try:
                    infer_queue.put_nowait((frame.copy(), w, h))
                except queue.Full:
                    pass

            if cfg.show_overlay:
                overlay_frame = frame.copy()
                _draw_overlay(overlay_frame, shared.get())
                cv2.imshow("Vision Worker", overlay_frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    except KeyboardInterrupt:
        print("Stopping vision worker...")
    finally:
        stop_event.set()
        for thread in threads:
            thread.join(timeout=2.0)

        cap.release()
        if cfg.show_overlay:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
