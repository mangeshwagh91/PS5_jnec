from __future__ import annotations

import heapq
import threading
from datetime import datetime, timezone

from app.models.schemas import (
    Alert,
    AlertStatus,
    Camera,
    DashboardStats,
    QueueItem,
    ThreatMapMarker,
    TimelinePoint,
    UserRole,
)


ROLE_THREAT_SCOPE = {
    UserRole.admin: {"weapon", "garbage", "hazard", "intrusion", "fire"},
    UserRole.police: {"weapon", "intrusion"},
    UserRole.municipal: {"garbage", "hazard"},
    UserRole.fire: {"fire", "hazard"},
}

SEVERITY_PRIORITY = {
    "critical": 1,
    "high": 2,
    "medium": 3,
    "low": 4,
}


class InMemoryStore:
    def __init__(self, stats_cache_ttl_seconds: int = 5) -> None:
        self._lock = threading.RLock()
        self._alerts: dict[str, Alert] = {}
        self._cameras: dict[str, Camera] = {}
        self._queue: list[tuple[int, datetime, str]] = []
        self._stats_cache_ttl_seconds = max(stats_cache_ttl_seconds, 0)
        self._stats_cache: tuple[datetime, DashboardStats] | None = None

    def seed(self) -> None:
        cameras = [
            Camera(id="CAM-012", name="Gate B North", location="North Entrance", status="alert", threat_count=1),
            Camera(id="CAM-013", name="Lab Smoke/Fire Demo", location="Safety Wing", status="online", threat_count=0),
            Camera(id="CAM-023", name="Perimeter East", location="East Fence", status="alert", threat_count=1),
            Camera(id="CAM-034", name="Residential 7", location="Block 7", status="online", threat_count=0),
            Camera(id="CAM-045", name="Parking C", location="Lot C", status="alert", threat_count=1),
            Camera(id="CAM-056", name="Transit Hub", location="Platform 2", status="online", threat_count=0),
            Camera(id="CAM-067", name="Construction A", location="Zone Alpha", status="online", threat_count=0),
            Camera(id="CAM-078", name="Chemical Storage", location="Unit 3", status="alert", threat_count=1),
            Camera(id="CAM-091", name="Warehouse B", location="District B", status="alert", threat_count=1),
        ]
        with self._lock:
            self._cameras = {camera.id: camera for camera in cameras}

    def add_alert(self, alert: Alert) -> None:
        with self._lock:
            self._alerts[alert.id] = alert
            heapq.heappush(self._queue, (SEVERITY_PRIORITY[alert.severity.value], alert.created_at, alert.id))
            self._stats_cache = None

            camera = self._cameras.get(alert.camera_id)
            if not camera:
                camera = Camera(
                    id=alert.camera_id,
                    name=alert.camera_id,
                    location=alert.location,
                    status="alert",
                    threat_count=0,
                )
                self._cameras[alert.camera_id] = camera

            camera.status = "alert"
            camera.threat_count += 1

    def list_alerts(
        self,
        role: UserRole,
        status: AlertStatus | None = None,
        severity: str | None = None,
        threat_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[int, list[Alert]]:
        with self._lock:
            alerts = list(self._alerts.values())

        allowed = ROLE_THREAT_SCOPE[role]
        filtered = [alert for alert in alerts if alert.threat_type.value in allowed]

        if status is not None:
            filtered = [alert for alert in filtered if alert.status == status]
        if severity:
            filtered = [alert for alert in filtered if alert.severity.value == severity]
        if threat_type:
            filtered = [alert for alert in filtered if alert.threat_type.value == threat_type]

        filtered.sort(key=lambda item: item.created_at, reverse=True)
        total = len(filtered)
        return total, filtered[offset : offset + limit]

    def update_alert_status(self, alert_id: str, status: AlertStatus) -> Alert | None:
        with self._lock:
            alert = self._alerts.get(alert_id)
            if not alert:
                return None
            alert.status = status
            alert.updated_at = datetime.now(timezone.utc)
            self._stats_cache = None
            return alert

    def get_cameras(self) -> list[Camera]:
        with self._lock:
            active_by_camera: dict[str, int] = {}
            for alert in self._alerts.values():
                if alert.status == AlertStatus.active:
                    active_by_camera[alert.camera_id] = active_by_camera.get(alert.camera_id, 0) + 1

            cameras: list[Camera] = []
            for camera in self._cameras.values():
                active_count = active_by_camera.get(camera.id, 0)
                computed_status = camera.status
                if camera.status != "offline":
                    computed_status = "alert" if active_count > 0 else "online"

                cameras.append(
                    Camera(
                        id=camera.id,
                        name=camera.name,
                        location=camera.location,
                        status=computed_status,
                        threat_count=active_count,
                    )
                )

            return sorted(cameras, key=lambda cam: cam.id)

    def get_stats(self) -> DashboardStats:
        now = datetime.now(timezone.utc)

        with self._lock:
            if self._stats_cache:
                cached_at, cached = self._stats_cache
                age = (now - cached_at).total_seconds()
                if age <= self._stats_cache_ttl_seconds:
                    return cached

            alerts = list(self._alerts.values())
            cameras = list(self._cameras.values())

        active_alerts = [alert for alert in alerts if alert.status == AlertStatus.active]
        critical_alerts = [alert for alert in active_alerts if alert.severity.value == "critical"]

        today = datetime.now(timezone.utc).date()
        resolved_today = [
            alert
            for alert in alerts
            if alert.status == AlertStatus.resolved and alert.updated_at.date() == today
        ]

        stats = DashboardStats(
            total_cameras=max(len(cameras), 1),
            active_cameras=len([camera for camera in cameras if camera.status != "offline"]),
            total_alerts=len(active_alerts),
            critical_alerts=len(critical_alerts),
            resolved_today=len(resolved_today),
            avg_response_time="2m 31s",
        )

        with self._lock:
            self._stats_cache = (now, stats)

        return stats

    def get_timeline(self, role: UserRole) -> list[TimelinePoint]:
        labels = ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "Now"]
        points: list[TimelinePoint] = [TimelinePoint(hour=label) for label in labels]

        allowed = ROLE_THREAT_SCOPE[role]
        with self._lock:
            alerts = [alert for alert in self._alerts.values() if alert.threat_type.value in allowed]

        for alert in alerts:
            index = min(alert.created_at.hour // 4, 5)
            if alert.created_at.hour >= 20:
                index = 5
            point = points[index]
            setattr(point, alert.threat_type.value, getattr(point, alert.threat_type.value) + 1)

        points[-1] = points[-2]
        points[-1].hour = "Now"
        return points

    def get_markers(self, role: UserRole) -> list[ThreatMapMarker]:
        allowed = ROLE_THREAT_SCOPE[role]
        with self._lock:
            alerts = [
                alert
                for alert in self._alerts.values()
                if alert.status != AlertStatus.resolved and alert.threat_type.value in allowed
            ]

        return [
            ThreatMapMarker(
                alert_id=alert.id,
                threat_type=alert.threat_type,
                severity=alert.severity,
                coordinates=alert.coordinates,
                location=alert.location,
                camera_id=alert.camera_id,
            )
            for alert in sorted(alerts, key=lambda item: item.created_at, reverse=True)
        ]

    def peek_queue(self, limit: int = 20) -> list[QueueItem]:
        with self._lock:
            top = sorted(self._queue)[:limit]

        return [
            QueueItem(priority=priority, alert_id=alert_id, created_at=created_at)
            for priority, created_at, alert_id in top
        ]
