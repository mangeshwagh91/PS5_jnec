from __future__ import annotations

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class ThreatType(str, Enum):
    weapon = "weapon"
    garbage = "garbage"
    hazard = "hazard"
    intrusion = "intrusion"
    fire = "fire"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class AlertStatus(str, Enum):
    active = "active"
    acknowledged = "acknowledged"
    resolved = "resolved"


class UserRole(str, Enum):
    admin = "admin"
    police = "police"
    municipal = "municipal"
    fire = "fire"


class Coordinates(BaseModel):
    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)


class Camera(BaseModel):
    id: str
    name: str
    location: str
    status: str
    threat_count: int = 0


class DetectionEventIn(BaseModel):
    camera_id: str
    location: str
    threat_type: ThreatType
    confidence: float = Field(ge=0, le=1)
    coordinates: Coordinates
    source: str = "cctv"
    context_signals: list[str] = Field(default_factory=list)


class Alert(BaseModel):
    id: str
    camera_id: str
    location: str
    threat_type: ThreatType
    confidence: float
    severity: Severity
    status: AlertStatus
    coordinates: Coordinates
    source: str
    score: float
    dedup_key: str
    created_at: datetime
    updated_at: datetime


class AlertListResponse(BaseModel):
    total: int
    items: list[Alert]


class TimelinePoint(BaseModel):
    hour: str
    weapon: int = 0
    garbage: int = 0
    hazard: int = 0
    intrusion: int = 0
    fire: int = 0


class DashboardStats(BaseModel):
    total_cameras: int
    active_cameras: int
    total_alerts: int
    critical_alerts: int
    resolved_today: int
    avg_response_time: str


class ThreatMapMarker(BaseModel):
    alert_id: str
    threat_type: ThreatType
    severity: Severity
    coordinates: Coordinates
    location: str
    camera_id: str


class AlertActionResponse(BaseModel):
    ok: bool
    alert: Alert


class QueueItem(BaseModel):
    priority: int
    alert_id: str
    created_at: datetime
