Integrated Multi-Threat Surveillance Backend

This backend is a FastAPI service for your Smart City Command Center.
It includes:
- Event ingestion API for AI detections
- Alert deduplication and confidence filtering
- Severity scoring with simple fusion logic
- Role-based alert visibility
- Realtime alert WebSocket stream
- Dashboard-ready endpoints for stats, timeline, cameras, map markers

Quick Start

1) Create environment and install dependencies

Windows PowerShell:
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

2) Run API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

3) Open docs
http://localhost:8000/docs

Core Endpoints

- GET /api/v1/health
- GET /api/v1/alerts
- POST /api/v1/events
- POST /api/v1/alerts/{alert_id}/acknowledge
- POST /api/v1/alerts/{alert_id}/resolve
- GET /api/v1/stats
- GET /api/v1/cameras
- GET /api/v1/analytics/timeline
- GET /api/v1/threat-map
- GET /api/v1/queue
- WS /ws/alerts

Environment Options

- STATS_CACHE_TTL_SECONDS (default: 5)
- INGESTION_API_KEY (optional; if set, required on POST /api/v1/events)

Role-based Filtering

Pass role in request header:
X-User-Role: admin | police | municipal | fire

Sample Event Payload

{
  "camera_id": "CAM-012",
  "location": "North Entrance",
  "threat_type": "weapon",
  "confidence": 0.92,
  "coordinates": { "x": 35, "y": 22 },
  "source": "cctv",
  "context_signals": ["person", "running"]
}

Ingestion Authentication

- Local demo mode: leave INGESTION_API_KEY empty.
- Secured mode: set INGESTION_API_KEY and pass request header:
  - X-API-Key: <your_key>

Simple Load Test

Run concurrent event ingestion test:

python scripts/load_test_events.py --base-url http://localhost:8000/api/v1 --requests 500 --concurrency 30

If INGESTION_API_KEY is set:

python scripts/load_test_events.py --api-key <your_key>

Notes

- This implementation is backend-complete for integration and hackathon demos.
- AI model execution is represented by POST /api/v1/events.
- Next production step is replacing in-memory store with PostgreSQL + Redis + Kafka.

Vision Worker (Camera -> Detection -> Event API)

You can now run a separate vision worker process that reads camera/video frames,
applies temporal logic, and posts stable events to POST /api/v1/events.

Files:

- app/services/vision_pipeline.py
- scripts/run_vision_worker.py
- requirements-vision.txt

Install optional vision dependencies:

pip install -r requirements-vision.txt

Run worker in mock mode (works without trained models):

python scripts/run_vision_worker.py --mode mock --stream-url 0 --camera-id CAM-012 --location "North Entrance"

Run worker in YOLO mode (requires weights):

python scripts/run_vision_worker.py --mode yolo --stream-url 0 --yolo-weights path/to/weights.pt

Real Camera / Video Detection Commands

Webcam (real-time):

python scripts/run_vision_worker.py --mode yolo --stream-url 0 --yolo-weights path/to/weights.pt --label-map configs/label_map.example.json --show-overlay

Video file:

python scripts/run_vision_worker.py --mode yolo --stream-url C:/videos/test.mp4 --yolo-weights path/to/weights.pt --label-map configs/label_map.example.json --show-overlay

RTSP camera:

python scripts/run_vision_worker.py --mode yolo --stream-url rtsp://user:pass@ip:554/stream --yolo-weights path/to/weights.pt --label-map configs/label_map.example.json

Notes:

- `--mode yolo` is real frame inference (not synthetic).
- Use model weights that include classes relevant to weapon/garbage/hazard.
- `--label-map` maps your model class names into pipeline labels.

Temporal Detection Logic

- weapon: requires consecutive confirmations in short window
- garbage: requires dwell time before alerting
- hazard: requires short consecutive confirmations

This avoids noisy one-frame false positives and keeps alerts actionable.
