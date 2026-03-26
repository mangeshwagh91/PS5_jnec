# PS5 Integrated Multi-Threat Surveillance Dashboard

A real-time surveillance dashboard with a React frontend, FastAPI backend, and optional YOLO vision workers for live event ingestion.

## Project Structure

- `client/` React + Vite dashboard UI
- `server/` FastAPI API + WebSocket + event/alert services
- `scripts/` helper scripts for local development
- `videos/` local sample videos used by vision workers

## Runtime Topology

- Frontend: `http://localhost:8000`
- Backend API: `http://localhost:8001/api/v1`
- Backend Docs: `http://localhost:8001/docs`
- Backend WS: `ws://localhost:8001/ws/alerts`

## One-Time Setup

### 1) Python environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r server/requirements.txt
pip install -r server/requirements-vision.txt
```

### 2) Frontend dependencies

```powershell
cd client
npm install
cd ..
```

### 3) Environment files

```powershell
Copy-Item server/.env.example server/.env
Copy-Item client/.env.example client/.env
```

Update `server/.env` with a real `INGESTION_API_KEY` value.

## Start and Stop (Recommended)

### Start frontend + backend

```powershell
.\scripts\dev-up.ps1
```

### Start frontend + backend + workers

```powershell
.\scripts\dev-up.ps1 -WithWorkers
```

### Stop services on local dev ports

```powershell
.\scripts\dev-down.ps1
```

## Manual Start Commands

### Backend

```powershell
cd server
..\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Frontend

```powershell
cd client
npm run dev
```

### Weapon worker

```powershell
cd server
..\.venv\Scripts\Activate.ps1
python scripts/run_vision_worker.py --api-base-url http://localhost:8001/api/v1 --api-key <INGESTION_API_KEY> --mode yolo --yolo-weights models/weapon_best.pt --camera-id CAM-012 --location "Gate B North" --stream-url ..\videos\Firing.mp4
```

### Fire/smoke worker

```powershell
cd server
..\.venv\Scripts\Activate.ps1
python scripts/run_vision_worker.py --api-base-url http://localhost:8001/api/v1 --api-key <INGESTION_API_KEY> --mode yolo --yolo-weights models/smoke_fire.pt --camera-id CAM-013 --location "Parking Lot C" --stream-url ..\videos\smoke_fire.mp4
```

## Health Checks

- API health: `GET /api/v1/health`
- Alerts list: `GET /api/v1/alerts`
- Frontend should show live stats and alert updates once workers are running.
