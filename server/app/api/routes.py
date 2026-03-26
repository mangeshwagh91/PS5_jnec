from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

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
