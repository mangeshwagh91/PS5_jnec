from __future__ import annotations

import argparse
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from urllib import error, request

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
    label_map_path: str
    show_overlay: bool
    device: str
    inference_imgsz: int


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
    def __init__(self, weights_path: str, device: str, inference_imgsz: int) -> None:
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

    def detect(self, frame) -> list[RawDetection]:
        kwargs = {"verbose": False, "imgsz": self._imgsz}
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


def _post_event(base_url: str, api_key: str, payload: dict) -> int:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    req = request.Request(url=f"{base_url}/events", data=body, headers=headers, method="POST")
    with request.urlopen(req, timeout=10) as resp:
        return resp.status


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
    parser.add_argument("--api-base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--stream-url", default="0", help="RTSP URL, video file path, or webcam index")
    parser.add_argument("--camera-id", default="CAM-012")
    parser.add_argument("--location", default="North Entrance")
    parser.add_argument("--source", default="cctv")
    parser.add_argument("--sample-every-n-frames", type=int, default=6)
    parser.add_argument("--min-confidence", type=float, default=0.55)
    parser.add_argument("--mode", choices=["mock", "yolo"], default="mock")
    parser.add_argument("--yolo-weights", default="", help="Path to YOLO weights (.pt). Defaults to yolo11n.pt when empty")
    parser.add_argument(
        "--label-map",
        default="",
        help="Optional JSON file mapping raw model labels to canonical labels (weapon/trash_bag/fire/smoke/person/etc)",
    )
    parser.add_argument("--show-overlay", action="store_true", help="Show realtime detections in an OpenCV window")
    parser.add_argument("--device", default="", help="Inference device, e.g. cpu, 0, cuda:0")
    parser.add_argument("--inference-imgsz", type=int, default=416, help="Inference image size for speed/accuracy tradeoff")
    args = parser.parse_args()

    cfg = WorkerConfig(
        api_base_url=args.api_base_url.rstrip("/"),
        api_key=args.api_key,
        stream_url=args.stream_url,
        camera_id=args.camera_id,
        location=args.location,
        source=args.source,
        sample_every_n_frames=max(args.sample_every_n_frames, 1),
        min_confidence=max(min(args.min_confidence, 1.0), 0.0),
        mode=args.mode,
        yolo_weights=args.yolo_weights,
        label_map_path=args.label_map,
        show_overlay=args.show_overlay,
        device=args.device,
        inference_imgsz=args.inference_imgsz,
    )
    return cfg


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


def main() -> None:
    cfg = _parse_args()
    label_map = _load_label_map(cfg.label_map_path)

    rule_engine = VisionRuleEngine()

    if cfg.mode == "mock":
        detector = _MockDetector()
    else:
        detector = _YoloDetector(cfg.yolo_weights, cfg.device, cfg.inference_imgsz)

    try:
        import cv2  # type: ignore
    except Exception as exc:
        raise RuntimeError("opencv-python-headless is required for vision worker") from exc

    source = int(cfg.stream_url) if cfg.stream_url.isdigit() else cfg.stream_url
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open stream source: {cfg.stream_url}")

    frame_idx = 0
    sent = 0
    last_detections: list[RawDetection] = []
    print("Vision worker started. Press Ctrl+C to stop.")
    if cfg.mode == "yolo":
        print("YOLO mode active: detections come from real camera/video frames.")
    if label_map:
        print(f"Label map loaded: {len(label_map)} entries")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.2)
                continue

            frame_idx += 1
            if frame_idx % cfg.sample_every_n_frames != 0:
                if cfg.show_overlay:
                    _draw_overlay(frame, last_detections)
                    cv2.imshow("Vision Worker", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                continue

            h, w = frame.shape[:2]

            if cfg.mode == "mock":
                detections = detector.detect(frame_w=w, frame_h=h)
            else:
                detections = detector.detect(frame)

            detections = _normalize_labels(detections, label_map)
            detections = [d for d in detections if d.confidence >= cfg.min_confidence]
            last_detections = detections

            if cfg.show_overlay:
                _draw_overlay(frame, detections)
                cv2.imshow("Vision Worker", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            events = rule_engine.evaluate(
                detections=detections,
                frame_w=w,
                frame_h=h,
                camera_id=cfg.camera_id,
                location=cfg.location,
                source=cfg.source,
            )

            for event in events:
                payload = event.model_dump(mode="json")
                try:
                    status = _post_event(cfg.api_base_url, cfg.api_key, payload)
                    sent += 1
                    print(f"[{sent}] status={status} type={payload['threat_type']} conf={payload['confidence']}")
                except error.HTTPError as exc:
                    print(f"Event rejected: HTTP {exc.code}")
                except Exception as exc:  # pragma: no cover
                    print(f"Event post failed: {exc}")

    except KeyboardInterrupt:
        print("Stopping vision worker...")
    finally:
        cap.release()
        if cfg.show_overlay:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
