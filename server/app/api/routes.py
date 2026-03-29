from __future__ import annotations

from datetime import datetime, timedelta, timezone
import shutil
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.api.deps import get_engine, get_role, get_store, get_ws_manager, verify_ingestion_api_key
from app.models.schemas import (
    AlertActionResponse,
    AlertListResponse,
    AlertStatus,
    DetectionEventIn,
    UserRole,
)
from app.services.event_engine import EventEngine
from app.services.store import InMemoryStore
from app.services.websocket_manager import WebSocketManager

router = APIRouter(prefix="/api/v1", tags=["surveillance"])
REPO_ROOT = Path(__file__).resolve().parents[3]
VIDEO_DIR = REPO_ROOT / "videos"
LIVE_PREVIEW_DIR = REPO_ROOT / "client" / "public" / "live"
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v", ".avi", ".mkv"}
LIVE_FRAME_STALE_SECONDS = 20


def _format_video_label(file_name: str) -> str:
    stem = Path(file_name).stem.replace("_", " ").replace("-", " ").strip()
    return " ".join(part.capitalize() for part in stem.split()) or "Video Feed"


@router.get("")
@router.get("/")
def api_index() -> dict[str, object]:
    return {
        "service": "surveillance-api",
        "status": "ok",
        "version": "v1",
        "docs": "/docs",
        "health": "/api/v1/health",
        "endpoints": [
            "/api/v1/alerts",
            "/api/v1/events",
            "/api/v1/stats",
            "/api/v1/cameras",
            "/api/v1/analytics/timeline",
            "/api/v1/threat-map",
            "/api/v1/queue",
            "/api/v1/live-cameras",
            "/api/v1/videos",
            "/api/v1/videos/upload",
        ],
    }


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "surveillance-api"}


@router.get("/alerts", response_model=AlertListResponse)
def list_alerts(
    status: AlertStatus | None = None,
    severity: str | None = None,
    threat_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    role: UserRole = Depends(get_role),
    store: InMemoryStore = Depends(get_store),
) -> AlertListResponse:
    total, items = store.list_alerts(
        role=role,
        status=status,
        severity=severity,
        threat_type=threat_type,
        limit=min(max(limit, 1), 200),
        offset=max(offset, 0),
    )
    return AlertListResponse(total=total, items=items)


@router.post("/events", response_model=AlertActionResponse)
async def ingest_event(
    event: DetectionEventIn,
    _auth: None = Depends(verify_ingestion_api_key),
    engine: EventEngine = Depends(get_engine),
    store: InMemoryStore = Depends(get_store),
    ws_manager: WebSocketManager = Depends(get_ws_manager),
) -> AlertActionResponse:
    if not engine.should_process(event):
        raise HTTPException(status_code=202, detail="Event ignored: below confidence threshold")

    dedup_key = engine.build_dedup_key(event)
    if engine.is_deduplicated(dedup_key):
        raise HTTPException(status_code=202, detail="Event deduplicated")

    alert = engine.create_alert(event)
    store.add_alert(alert)

    await ws_manager.broadcast(
        {
            "type": "alert.created",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": alert.model_dump(mode="json"),
        }
    )
    return AlertActionResponse(ok=True, alert=alert)


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertActionResponse)
async def acknowledge_alert(
    alert_id: str,
    store: InMemoryStore = Depends(get_store),
    ws_manager: WebSocketManager = Depends(get_ws_manager),
) -> AlertActionResponse:
    alert = store.update_alert_status(alert_id, AlertStatus.acknowledged)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    await ws_manager.broadcast(
        {
            "type": "alert.acknowledged",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": alert.model_dump(mode="json"),
        }
    )
    return AlertActionResponse(ok=True, alert=alert)


@router.post("/alerts/{alert_id}/resolve", response_model=AlertActionResponse)
async def resolve_alert(
    alert_id: str,
    store: InMemoryStore = Depends(get_store),
    ws_manager: WebSocketManager = Depends(get_ws_manager),
) -> AlertActionResponse:
    alert = store.update_alert_status(alert_id, AlertStatus.resolved)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    await ws_manager.broadcast(
        {
            "type": "alert.resolved",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": alert.model_dump(mode="json"),
        }
    )
    return AlertActionResponse(ok=True, alert=alert)


@router.get("/stats")
def get_stats(
    role: UserRole = Depends(get_role),
    store: InMemoryStore = Depends(get_store),
):
    _ = role
    return store.get_stats()


@router.get("/cameras")
def get_cameras(
    role: UserRole = Depends(get_role),
    store: InMemoryStore = Depends(get_store),
):
    _ = role
    return store.get_cameras()


@router.get("/analytics/timeline")
def timeline(
    role: UserRole = Depends(get_role),
    store: InMemoryStore = Depends(get_store),
):
    return store.get_timeline(role)


@router.get("/threat-map")
def threat_map(
    role: UserRole = Depends(get_role),
    store: InMemoryStore = Depends(get_store),
):
    return store.get_markers(role)


@router.get("/queue")
def queue(
    store: InMemoryStore = Depends(get_store),
):
    return store.peek_queue()


@router.get("/live-cameras")
def list_live_cameras() -> dict[str, list[str]]:
    if not LIVE_PREVIEW_DIR.exists():
        return {"items": []}

    freshness_cutoff = datetime.now(timezone.utc) - timedelta(seconds=LIVE_FRAME_STALE_SECONDS)
    camera_ids: list[str] = []
    for path in sorted(LIVE_PREVIEW_DIR.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_file() or path.suffix.lower() not in {".jpg", ".jpeg"}:
            continue

        modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
        if modified_at < freshness_cutoff:
            continue

        camera_id = path.stem.strip()
        if camera_id:
            camera_ids.append(camera_id)

    return {"items": camera_ids}


@router.get("/videos")
def list_videos() -> dict[str, list[dict[str, str]]]:
    if not VIDEO_DIR.exists():
        return {"items": []}

    videos: list[dict[str, str]] = []
    for path in sorted(VIDEO_DIR.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_file() or path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue

        videos.append(
            {
                "filename": path.name,
                "label": _format_video_label(path.name),
                "url": f"/media/videos/{quote(path.name)}",
            }
        )

    return {"items": videos}


@router.post("/videos/upload")
async def upload_video(file: UploadFile = File(...)) -> dict[str, dict[str, str]]:
    raw_name = Path(file.filename or "uploaded-video.mp4").name
    extension = Path(raw_name).suffix.lower()
    if extension not in VIDEO_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {extension or 'unknown'}")

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)

    target_name = raw_name
    destination = VIDEO_DIR / target_name
    if destination.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        target_name = f"{Path(raw_name).stem}_{stamp}{extension}"
        destination = VIDEO_DIR / target_name

    with destination.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    await file.close()

    return {
        "item": {
            "filename": target_name,
            "label": _format_video_label(target_name),
            "url": f"/media/videos/{quote(target_name)}",
        }
    }
