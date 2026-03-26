# PS5 Integrated Multi-Threat Surveillance Dashboard

This project is already built as a hackathon-ready simulation of a smart city command center.

Important: you do NOT need to build any video AI pipeline for the demo.
The backend already simulates detections (weapon, garbage, hazard, intrusion, fire) and streams live alerts to the dashboard.

## What This Project Demonstrates

- Unified command center UI for multiple threat types
- Real-time alert stream through WebSocket
- Alert lifecycle: active -> acknowledged -> resolved
- Threat map, camera status, and timeline analytics
- Role-aware API filtering (admin, police, municipal, fire)

## Architecture (Simple)

- Frontend: React + Vite + Tailwind (port 8080)
- Backend: FastAPI (port 8000)
- Realtime: WebSocket endpoint at /ws/alerts
- Data source for demo: in-memory simulator (no external AI required)

## 1) Start Backend

Open terminal in project root:

```powershell
cd server
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Optional (recommended for deployment):

```powershell
cd server
Copy-Item .env.example .env
```

Check:
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

## 2) Start Frontend

Open a second terminal in project root:

```powershell
cd client
npm install
npm run dev
```

Optional frontend env setup:

```powershell
cd client
Copy-Item .env.example .env
```

Open dashboard:
- http://localhost:8080

## 3) Demo Without Video Models

Once both apps are running, the simulator automatically creates random alerts every few seconds.
You can show:
- New alerts appearing in feed
- Stats and chart updates
- Threat map updates in real time

You can also inject your own event from Swagger UI:
- Open http://localhost:8000/docs
- Use POST /api/v1/events with this example payload:

```json
{
  "camera_id": "CAM-012",
  "location": "North Entrance",
  "threat_type": "weapon",
  "confidence": 0.92,
  "coordinates": { "x": 35, "y": 22 },
  "source": "cctv",
  "context_signals": ["person", "running"]
}
```

## 4) What To Say In Your Presentation

- This system unifies multiple threat channels into one operational command center.
- AI detections are treated as events and normalized into a common schema.
- A scoring and dedup layer prioritizes alerts and avoids noise.
- The command center receives updates in real time and supports response workflow.
- This MVP architecture is ready to replace simulator input with real model outputs.

## 5) If You Need To Explain "Video Tech"

Use this line:

"For hackathon speed, we decoupled detection from monitoring. The dashboard consumes standardized detection events, so any future CV model can plug in through the same event API."

## 6) Next Upgrade Path (Post-Hackathon)

- Replace in-memory store with PostgreSQL
- Add Redis for high-throughput event buffering
- Add auth with JWT and role-based policies
- Connect real CV models to POST /api/v1/events
- Add incident assignment and SLA tracking

## 7) High-Performance Starter Pack Included

- API key protection for event ingestion (set INGESTION_API_KEY in server/.env)
- Stats endpoint TTL cache via STATS_CACHE_TTL_SECONDS
- WebSocket reconnect with exponential backoff + heartbeat ping/pong
- Concurrent backend load-test script:

```powershell
cd server
python scripts/load_test_events.py --base-url http://localhost:8000/api/v1 --requests 500 --concurrency 30
```

## 8) Build Camera Detection Pipeline (Starter)

The project now includes a vision worker that can read camera/video frames and emit
weapon, garbage, and hazard events into the existing backend API.

From server folder:

```powershell
pip install -r requirements-vision.txt
python scripts/run_vision_worker.py --mode mock --stream-url 0 --camera-id CAM-012 --location "North Entrance"
```

When backend and frontend are running, these events will appear live in the dashboard.
