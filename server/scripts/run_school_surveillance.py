from __future__ import annotations

import argparse
import json
import os
import queue
import random
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from urllib import error, request

# Allow running as a script (python scripts/run_school_surveillance.py)
REPO_SERVER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = REPO_SERVER_ROOT.parent
if str(REPO_SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_SERVER_ROOT))

from app.services.vision_pipeline import RawDetection, VisionRuleEngine


@dataclass
class RuntimeConfig:
    config_path: str
    api_base_url: str
    api_key: str
    mode: str
    fire_weights: str
    weapon_weights: str
    device: str
    inference_imgsz: int
    fire_yolo_conf: float
    weapon_yolo_conf: float
    smoke_confidence_threshold: float
    fire_confidence_threshold: float
    weapon_confidence_threshold: float
    smoke_confirmation_frames: int
    preview_dir: str
    draw_boxes: bool
    preview_write_every_n_frames: int


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


class MockFireSmokeDetector:
    LABEL_POOL = ["fire", "smoke", "person"]

    def detect(self, frame_w: int, frame_h: int) -> list[RawDetection]:
        detections: list[RawDetection] = []
        for _ in range(random.randint(0, 2)):
            label = random.choice(self.LABEL_POOL)
            conf = round(random.uniform(0.2, 0.95), 2)
            x1 = random.uniform(0, frame_w * 0.8)
            y1 = random.uniform(0, frame_h * 0.8)
            x2 = min(x1 + random.uniform(20, frame_w * 0.25), frame_w)
            y2 = min(y1 + random.uniform(20, frame_h * 0.25), frame_h)
            detections.append(
                RawDetection(
                    label=label,
                    confidence=conf,
                    bbox_xyxy=(x1, y1, x2, y2),
                    track_id=None,
                )
            )
        return detections


class MockWeaponDetector:
    LABEL_POOL = ["weapon", "gun", "knife", "person"]

    def detect(self, frame_w: int, frame_h: int) -> list[RawDetection]:
        detections: list[RawDetection] = []
        for _ in range(random.randint(0, 1)):
            label = random.choice(self.LABEL_POOL)
            conf = round(random.uniform(0.25, 0.98), 2)
            x1 = random.uniform(0, frame_w * 0.85)
            y1 = random.uniform(0, frame_h * 0.85)
            x2 = min(x1 + random.uniform(20, frame_w * 0.2), frame_w)
            y2 = min(y1 + random.uniform(20, frame_h * 0.2), frame_h)
            detections.append(
                RawDetection(
                    label=label,
                    confidence=conf,
                    bbox_xyxy=(x1, y1, x2, y2),
                    track_id=None,
                )
            )
        return detections


class YoloDetector:
    def __init__(self, weights_path: str, device: str, inference_imgsz: int, yolo_conf: float) -> None:
        try:
            from ultralytics import YOLO  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "ultralytics is not installed. Install vision dependencies first."
            ) from exc

        self._model = YOLO(weights_path)
        self._device = device.strip()
        self._imgsz = max(inference_imgsz, 160)
        self._conf = max(min(yolo_conf, 1.0), 0.0)

    def detect(self, frame) -> list[RawDetection]:
        kwargs = {
            "verbose": False,
            "imgsz": self._imgsz,
            "conf": self._conf,
        }
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


def _resolve_existing_path(path_str: str, *, base_dir: Path) -> str:
    raw = path_str.strip()
    if not raw:
        return raw

    path = Path(raw)
    if path.is_absolute():
        return str(path)

    candidates = [
        Path.cwd() / path,
        base_dir / path,
        REPO_ROOT / path,
        REPO_SERVER_ROOT / path,
        REPO_ROOT / "server" / path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate.resolve())

    return raw


def _normalize_label(label: str) -> str:
    lower = label.lower().strip()

    if lower in {"fire", "flame"}:
        return "fire"
    if lower in {"smoke", "haze"}:
        return "smoke"
    if lower in {"weapon", "gun", "knife", "pistol", "rifle", "firearm", "firing"}:
        return "weapon"

    if "fire" in lower and lower != "fireproof":
        return "fire"
    if "smoke" in lower:
        return "smoke"
    if any(token in lower for token in ["weapon", "gun", "knife", "rifle", "pistol", "firearm"]):
        return "weapon"

    return lower


def _passes_threshold(det: RawDetection, cfg: RuntimeConfig) -> bool:
    label = det.label.lower().strip()
    if label == "smoke":
        return det.confidence >= cfg.smoke_confidence_threshold
    if label == "fire":
        return det.confidence >= cfg.fire_confidence_threshold
    if label == "weapon":
        return det.confidence >= cfg.weapon_confidence_threshold
    return False


def _draw_overlay(frame, detections: list[RawDetection]) -> None:
    import cv2  # type: ignore

    color_map = {
        "fire": (0, 165, 255),
        "smoke": (0, 255, 255),
        "weapon": (0, 0, 255),
    }

    for det in detections:
        label = det.label.lower().strip()
        color = color_map.get(label, (46, 204, 113))
        x1, y1, x2, y2 = [int(v) for v in det.bbox_xyxy]
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        text = f"{label} {det.confidence:.2f}"
        cv2.putText(frame, text, (x1, max(y1 - 8, 18)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)


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


def _parse_camera_config(config_path: str) -> list[CameraConfig]:
    path = Path(config_path)
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
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

        resolved_stream = stream_url
        if not stream_url.isdigit() and "://" not in stream_url:
            resolved_stream = _resolve_existing_path(stream_url, base_dir=REPO_SERVER_ROOT)

        cameras.append(
            CameraConfig(
                camera_id=camera_id,
                stream_url=resolved_stream,
                location=location,
                source=source,
                sample_every_n_frames=sample_every_n_frames,
            )
        )

    if not cameras:
        raise ValueError("Camera config has no valid camera entries")

    return cameras


def _parse_args() -> RuntimeConfig:
    default_config_path = str((Path(__file__).resolve().parent / "cameras.json"))
    parser = argparse.ArgumentParser(
        description=(
            "School surveillance worker: each camera runs fire/smoke model and weapon model "
            "on the same frame, then combines detections into one alert stream."
        )
    )
    parser.add_argument("--config", default=default_config_path, help="Path to cameras JSON config")
    parser.add_argument("--api-base-url", default="http://localhost:8001/api/v1")
    parser.add_argument("--api-key", default=os.getenv("INGESTION_API_KEY", ""))
    parser.add_argument("--mode", choices=["mock", "yolo"], default="yolo")
    parser.add_argument("--fire-weights", default="models/weights/fire_smoke_2.pt")
    parser.add_argument("--weapon-weights", default="models/weights/firing_1.pt")
    parser.add_argument("--device", default="0", help="Inference device, e.g. cpu, 0, cuda:0")
    parser.add_argument("--inference-imgsz", type=int, default=416)
    parser.add_argument("--fire-yolo-conf", type=float, default=0.01)
    parser.add_argument("--weapon-yolo-conf", type=float, default=0.2)
    parser.add_argument("--smoke-confidence-threshold", type=float, default=0.15)
    parser.add_argument("--fire-confidence-threshold", type=float, default=0.25)
    parser.add_argument("--weapon-confidence-threshold", type=float, default=0.25)
    parser.add_argument("--smoke-confirmation-frames", type=int, default=3)
    parser.add_argument("--preview-dir", default="")
    parser.add_argument(
        "--draw-boxes",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Draw detection boxes in preview JPG output",
    )
    parser.add_argument("--preview-write-every-n-frames", type=int, default=1)

    args = parser.parse_args()

    fire_weights = _resolve_existing_path(args.fire_weights, base_dir=REPO_SERVER_ROOT)
    weapon_weights = _resolve_existing_path(args.weapon_weights, base_dir=REPO_SERVER_ROOT)
    config_path = _resolve_existing_path(args.config, base_dir=REPO_SERVER_ROOT)

    return RuntimeConfig(
        config_path=config_path,
        api_base_url=args.api_base_url.rstrip("/"),
        api_key=args.api_key,
        mode=args.mode,
        fire_weights=fire_weights,
        weapon_weights=weapon_weights,
        device=args.device,
        inference_imgsz=max(int(args.inference_imgsz), 160),
        fire_yolo_conf=max(min(args.fire_yolo_conf, 1.0), 0.0),
        weapon_yolo_conf=max(min(args.weapon_yolo_conf, 1.0), 0.0),
        smoke_confidence_threshold=max(min(args.smoke_confidence_threshold, 1.0), 0.0),
        fire_confidence_threshold=max(min(args.fire_confidence_threshold, 1.0), 0.0),
        weapon_confidence_threshold=max(min(args.weapon_confidence_threshold, 1.0), 0.0),
        smoke_confirmation_frames=max(int(args.smoke_confirmation_frames), 1),
        preview_dir=args.preview_dir,
        draw_boxes=args.draw_boxes,
        preview_write_every_n_frames=max(int(args.preview_write_every_n_frames), 1),
    )


def _capture_thread(cam: CameraConfig, infer_queue: queue.Queue, stop_event: threading.Event) -> None:
    import cv2  # type: ignore

    source = int(cam.stream_url) if cam.stream_url.isdigit() else cam.stream_url
    is_local_file_source = isinstance(source, str) and Path(source).exists()

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
    fire_detector,
    weapon_detector,
    rule_engines: dict[str, VisionRuleEngine],
    cfg: RuntimeConfig,
    stop_event: threading.Event,
) -> None:
    processed_by_camera: dict[str, int] = {}

    while not stop_event.is_set():
        try:
            packet: FramePacket = infer_queue.get(timeout=0.1)
        except queue.Empty:
            continue

        if cfg.mode == "mock":
            fire_dets = fire_detector.detect(packet.frame_w, packet.frame_h)
            weapon_dets = weapon_detector.detect(packet.frame_w, packet.frame_h)
        else:
            fire_dets = fire_detector.detect(packet.frame)
            weapon_dets = weapon_detector.detect(packet.frame)

        combined_raw = fire_dets + weapon_dets
        detections: list[RawDetection] = []
        for det in combined_raw:
            mapped = _normalize_label(det.label)
            normalized = RawDetection(
                label=mapped,
                confidence=det.confidence,
                bbox_xyxy=det.bbox_xyxy,
                track_id=det.track_id,
            )
            if _passes_threshold(normalized, cfg):
                detections.append(normalized)

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


def _event_poster_thread(event_queue: queue.Queue, cfg: RuntimeConfig, stop_event: threading.Event) -> None:
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
    cfg = _parse_args()

    try:
        import cv2  # noqa: F401 # type: ignore
    except Exception as exc:
        raise RuntimeError("opencv-python-headless is required for school surveillance worker") from exc

    cameras = _parse_camera_config(cfg.config_path)

    preview_base = Path(cfg.preview_dir.strip()) if cfg.preview_dir.strip() else (
        REPO_ROOT / "client" / "public" / "live"
    )
    preview_base.mkdir(parents=True, exist_ok=True)

    if cfg.mode == "mock":
        fire_detector = MockFireSmokeDetector()
        weapon_detector = MockWeaponDetector()
    else:
        fire_detector = YoloDetector(cfg.fire_weights, cfg.device, cfg.inference_imgsz, cfg.fire_yolo_conf)
        weapon_detector = YoloDetector(cfg.weapon_weights, cfg.device, cfg.inference_imgsz, cfg.weapon_yolo_conf)

    rule_engines = {
        cam.camera_id: VisionRuleEngine(smoke_consecutive_frames=cfg.smoke_confirmation_frames)
        for cam in cameras
    }
    preview_queues = {cam.camera_id: queue.Queue(maxsize=2) for cam in cameras}

    infer_queue: queue.Queue = queue.Queue(maxsize=max(len(cameras) * 2, 6))
    event_queue: queue.Queue = queue.Queue(maxsize=100)
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
                fire_detector,
                weapon_detector,
                rule_engines,
                cfg,
                stop_event,
            ),
            daemon=True,
            name="inference-fire-smoke-weapon",
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

    print("School surveillance worker ready")
    print("Architecture: each frame -> fire model + weapon model -> merge -> preview + alerts")
    print(
        f"Mode={cfg.mode} cameras={len(cameras)} device={cfg.device or 'auto'} "
        f"imgsz={cfg.inference_imgsz}"
    )
    if cfg.mode == "yolo":
        print(f"Fire model: {Path(cfg.fire_weights).name} (conf>={cfg.fire_yolo_conf:.2f})")
        print(f"Weapon model: {Path(cfg.weapon_weights).name} (conf>={cfg.weapon_yolo_conf:.2f})")
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
