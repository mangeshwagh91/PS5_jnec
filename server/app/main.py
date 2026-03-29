from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from contextlib import suppress
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import get_settings
from app.services.event_engine import EventEngine
from app.services.simulator import run_simulator
from app.services.store import InMemoryStore
from app.services.websocket_manager import WebSocketManager

settings = get_settings()
REPO_ROOT = Path(__file__).resolve().parents[2]
VIDEO_DIR = REPO_ROOT / "videos"
PREVIEW_DIR = REPO_ROOT / "client" / "public" / "live"


async def _mjpeg_generator(camera_id: str):
    preview_path = PREVIEW_DIR / f"{camera_id}.jpg"
    last_mtime_ns = -1

    while True:
        try:
            file_stat = preview_path.stat()
            if file_stat.st_size > 0 and file_stat.st_mtime_ns != last_mtime_ns:
                frame_bytes = preview_path.read_bytes()
                last_mtime_ns = file_stat.st_mtime_ns
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: "
                    + str(len(frame_bytes)).encode("ascii")
                    + b"\r\n\r\n"
                    + frame_bytes
                    + b"\r\n"
                )
        except FileNotFoundError:
            pass
        except asyncio.CancelledError:
            break
        except Exception:
            pass

        await asyncio.sleep(0.05)


@asynccontextmanager
async def lifespan(app: FastAPI):
    store = InMemoryStore(stats_cache_ttl_seconds=settings.stats_cache_ttl_seconds)
    store.seed()

    engine = EventEngine(
        confidence_threshold=settings.detection_confidence_threshold,
        dedup_window_seconds=settings.dedup_window_seconds,
        hazard_confidence_threshold=settings.hazard_confidence_threshold,
    )
    ws_manager = WebSocketManager()

    app.state.store = store
    app.state.engine = engine
    app.state.ws_manager = ws_manager

    stop_event = asyncio.Event()
    app.state.stop_event = stop_event
    app.state.simulator_task = None
    if settings.simulation_enabled:
        app.state.simulator_task = asyncio.create_task(
            run_simulator(
                store=store,
                engine=engine,
                ws_manager=ws_manager,
                stop_event=stop_event,
                interval_seconds=settings.simulation_interval_seconds,
            )
        )

    yield

    stop_event.set()
    if app.state.simulator_task:
        app.state.simulator_task.cancel()
        with suppress(asyncio.CancelledError):
            await app.state.simulator_task


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Integrated multi-threat surveillance backend with realtime event streaming",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

if VIDEO_DIR.exists():
    app.mount("/media/videos", StaticFiles(directory=str(VIDEO_DIR)), name="media-videos")


@app.get("/live/{camera_id}/stream")
async def mjpeg_stream(camera_id: str):
    return StreamingResponse(
        _mjpeg_generator(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache"},
    )


@app.get("/")
def root() -> dict[str, str]:
    return {"service": settings.app_name, "status": "running", "docs": "/docs"}


@app.websocket("/ws/alerts")
async def alerts_websocket(websocket: WebSocket):
    ws_manager: WebSocketManager = websocket.app.state.ws_manager
    await ws_manager.connect(websocket)
    try:
        await websocket.send_json({"type": "connection.ready", "payload": {"message": "connected"}})
        while True:
            message = await websocket.receive_text()
            if message.strip().lower() == "ping":
                await websocket.send_json({"type": "connection.pong"})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
