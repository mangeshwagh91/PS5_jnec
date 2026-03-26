from __future__ import annotations

from fastapi import Header, HTTPException, Request

from app.core.config import get_settings
from app.models.schemas import UserRole
from app.services.event_engine import EventEngine
from app.services.store import InMemoryStore
from app.services.websocket_manager import WebSocketManager


settings = get_settings()


def get_store(request: Request) -> InMemoryStore:
    return request.app.state.store


def get_engine(request: Request) -> EventEngine:
    return request.app.state.engine


def get_ws_manager(request: Request) -> WebSocketManager:
    return request.app.state.ws_manager


def get_role(x_user_role: str = Header(default="admin")) -> UserRole:
    normalized = x_user_role.strip().lower()
    try:
        return UserRole(normalized)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Unsupported role '{x_user_role}'") from exc


def verify_ingestion_api_key(x_api_key: str | None = Header(default=None)) -> None:
    # Allow open ingestion in local/demo mode when key is not configured.
    if not settings.ingestion_api_key:
        return

    if not x_api_key or x_api_key != settings.ingestion_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing ingestion API key")
