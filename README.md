# Sentinel AI

Integrated real-time school/control-room surveillance system with:

- React + Vite frontend dashboard
- FastAPI backend with alert lifecycle APIs and live WebSocket push
- Optional YOLO vision workers for multi-camera detection ingestion

This repository is set up for local demos, presentation mode, and hackathon-style iteration.

## What this project does

- Ingests detections from camera workers into `POST /api/v1/events`
- Deduplicates and scores alerts server-side
- Broadcasts live alert updates over WebSocket (`/ws/alerts`)
- Provides dashboard APIs for alerts, stats, cameras, timeline, and threat map
- Supports multi-camera workers grouped by model weights

## Repository layout

- `client/`: React dashboard (Vite + TypeScript)
- `server/`: FastAPI backend and worker scripts
- `scripts/`: top-level local orchestration scripts (`dev-up.ps1`, `dev-down.ps1`)
- `configs/`: optional camera matrix for grouped workers
- `videos/`: local sample video files
- `runs/detect/multi_camera_configs/`: generated worker config files

## Runtime topology (default local)

- Frontend: `http://localhost:8000`
- Backend API base: `http://localhost:8001/api/v1`
- Backend docs: `http://localhost:8001/docs`
- Backend WS: `ws://localhost:8001/ws/alerts`

## Prerequisites

- Windows PowerShell
- Python 3.10+ (recommended)
- Node.js 18+ and npm
- Optional GPU setup (for YOLO acceleration)

## One-time setup

### 1) Create Python virtual environment

From repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r server/requirements.txt
pip install -r server/requirements-vision.txt
```

### 2) Install frontend dependencies

```powershell
cd client
npm install
cd ..
```

### 3) Create backend environment file

Create `server/.env` manually (there is no `.env.example` checked in).

Recommended starter:

```dotenv
INGESTION_API_KEY=change-me
SIMULATION_ENABLED=false
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
```

Notes:

- If `INGESTION_API_KEY` is set, workers must send `X-API-Key`.
- Set `SIMULATION_ENABLED=false` when using live worker ingestion.

## Quick start (recommended)

### Start frontend + backend

```powershell
.\scripts\dev-up.ps1
```

### Start frontend + backend + grouped workers

```powershell
.\scripts\dev-up.ps1 -WithWorkers
```

## Deployment

This project is optimized for hybrid deployment:
- **Frontend**: Deploy to **Vercel** or **Netlify**.
- **Backend (API)**: Deploy to **Render**, **Railway**, or **Fly.io** (requires a Python environment).
- **Vision Workers**: Should remain on **Local machines/Edge devices** with GPUs to process RTSP/Webcam streams, pushing detections to the cloud API.

### 1) Push to GitHub
```powershell
git init
git add .
git commit -m "Initial commit"
# Create repo on GitHub then:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git branch -M main
git push -u origin main
```

### 2) Deploy Frontend (Vercel)
- Connect your GitHub repo to Vercel.
- Set **Build Command**: `cd client && npm run build`
- Set **Output Directory**: `client/dist`
- Set **Environment Variable**: `VITE_API_BASE_URL=https://your-backend-url.onrender.com/api/v1`

### 3) Deploy Backend (Render)
- Connect your GitHub repo to Render as a **Web Service**.
- Set **Build Command**: `pip install -r server/requirements.txt`
- Set **Start Command**: `cd server && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Set **Environment Variables**:
  - `PYTHON_VERSION=3.10.0`
  - `CORS_ORIGINS=https://your-frontend-url.vercel.app`

### 4) Testing without Local Setup
If you only want to test the UI/API without running YOLO workers:
- Open the **Cameras** page in the dashboard.
- Toggle **WEBCAM TEST** to view your own camera feed inside the dashboard.
- Use **Upload Video** to ingest a video file for server-side processing and alert simulation.

### Stop local stack

```powershell
.\scripts\dev-down.ps1
```

## Presentation mode

Use for demos/judging sessions:

```powershell
start_presentation.bat
```

This launches:

- backend on port `8001`
- unified school worker (`run_school_surveillance.py`)
- frontend on port `8000`
- optional `ngrok` tunnel if installed and available in `PATH`

## Manual run commands

### Backend only

```powershell
cd server
..\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### Frontend only

```powershell
cd client
npm run dev -- --host 0.0.0.0 --port 8000
```

### Worker: shared multi-camera model (`run_multi_camera_worker.py`)

```powershell
cd server
..\.venv\Scripts\Activate.ps1
python scripts/run_multi_camera_worker.py `
	--config ..\runs\detect\multi_camera_configs\my_worker_config.json `
	--api-base-url http://localhost:8001/api/v1 `
	--api-key <INGESTION_API_KEY> `
	--mode yolo `
	--weights models/weights/firing_1.pt
```

Example camera config format:

```json
[
	{
		"camera_id": "CAM-012",
		"location": "Gate B North",
		"stream_url": "..\\videos\\Firing.mp4",
		"sample_every_n_frames": 2
	},
	{
		"camera_id": "CAM-013",
		"location": "Parking Lot C",
		"stream_url": "..\\videos\\smoke_fire.mp4",
		"sample_every_n_frames": 2
	}
]
```

### Worker: school unified pipeline (`run_school_surveillance.py`)

```powershell
cd server
..\.venv\Scripts\Activate.ps1
python scripts/run_school_surveillance.py `
	--config scripts/cameras.json `
	--mode yolo `
	--fire-weights models/weights/fire_smoke_2.pt `
	--weapon-weights models/weights/firing_1.pt `
	--api-base-url http://localhost:8001/api/v1 `
	--api-key <INGESTION_API_KEY>
```

## API surface (primary)

- `GET /api/v1/health`
- `GET /api/v1/alerts`
- `POST /api/v1/events`
- `POST /api/v1/alerts/{alert_id}/acknowledge`
- `POST /api/v1/alerts/{alert_id}/resolve`
- `GET /api/v1/stats`
- `GET /api/v1/cameras`
- `GET /api/v1/analytics/timeline`
- `GET /api/v1/threat-map`
- `GET /api/v1/queue`
- `GET /api/v1/videos`
- `WS /ws/alerts`

## Useful verification checks

After startup, verify:

```text
Frontend: http://localhost:8000
Backend docs: http://localhost:8001/docs
Health: GET http://localhost:8001/api/v1/health
```

If workers are running, you should see alert activity in dashboard feeds and API responses.

## Troubleshooting

### `INGESTION_API_KEY is empty in server/.env`

- Set a non-empty `INGESTION_API_KEY` in `server/.env`
- Re-run `.\scripts\dev-up.ps1 -WithWorkers`

### No alerts appearing with workers running

- Confirm worker API URL points to `http://localhost:8001/api/v1`
- Confirm API key in worker command matches `server/.env`
- Check backend logs for `202` responses (below threshold or deduplicated)

### Port already in use

- Run `.\scripts\dev-down.ps1`
- Restart stack with `.\scripts\dev-up.ps1`

### Frontend cannot reach backend

- Ensure frontend is on port `8000`
- Ensure backend is on port `8001`
- Ensure `CORS_ORIGINS` includes `http://localhost:8000`

## Development notes

- Backend store is in-memory by default (suitable for demos/local use)
- Vision dependencies are optional unless running YOLO workers
- Generated worker config JSON files under `runs/detect/multi_camera_configs/` are expected runtime artifacts

## License

This project is released under the repository `LICENSE` file.
