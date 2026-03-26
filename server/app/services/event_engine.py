from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.models.schemas import Alert, AlertStatus, DetectionEventIn, Severity, ThreatType


class EventEngine:
    def __init__(self, confidence_threshold: float, dedup_window_seconds: int) -> None:
        self.confidence_threshold = confidence_threshold
        self.dedup_window_seconds = dedup_window_seconds
        self._last_seen: dict[str, datetime] = {}

    def build_dedup_key(self, event: DetectionEventIn) -> str:
        x = round(event.coordinates.x / 5)
        y = round(event.coordinates.y / 5)
        return f"{event.camera_id}:{event.threat_type}:{event.location}:{x}:{y}"

    def _threat_weight(self, threat: ThreatType) -> float:
        return {
            ThreatType.weapon: 1.0,
            ThreatType.fire: 0.95,
            ThreatType.intrusion: 0.8,
            ThreatType.hazard: 0.7,
            ThreatType.garbage: 0.45,
        }[threat]

    def _context_bonus(self, context_signals: list[str]) -> float:
        signals = {signal.lower() for signal in context_signals}
        bonus = 0.0
        if "running" in signals:
            bonus += 0.15
        if "crowd" in signals:
            bonus += 0.1
        if "smoke" in signals:
            bonus += 0.2
        if "person" in signals:
            bonus += 0.05
        return min(bonus, 0.3)

    def _severity(self, score: float) -> Severity:
        if score >= 0.85:
            return Severity.critical
        if score >= 0.65:
            return Severity.high
        if score >= 0.45:
            return Severity.medium
        return Severity.low

    def should_process(self, event: DetectionEventIn) -> bool:
        return event.confidence >= self.confidence_threshold

    def is_deduplicated(self, dedup_key: str) -> bool:
        now = datetime.now(timezone.utc)
        previous = self._last_seen.get(dedup_key)
        if previous and now - previous < timedelta(seconds=self.dedup_window_seconds):
            return True
        self._last_seen[dedup_key] = now
        return False

    def create_alert(self, event: DetectionEventIn) -> Alert:
        now = datetime.now(timezone.utc)
        dedup_key = self.build_dedup_key(event)
        score = min((event.confidence * self._threat_weight(event.threat_type)) + self._context_bonus(event.context_signals), 1.0)
        severity = self._severity(score)

        return Alert(
            id=f"ALT-{uuid4().hex[:8].upper()}",
            camera_id=event.camera_id,
            location=event.location,
            threat_type=event.threat_type,
            confidence=event.confidence,
            severity=severity,
            status=AlertStatus.active,
            coordinates=event.coordinates,
            source=event.source,
            score=round(score, 3),
            dedup_key=dedup_key,
            created_at=now,
            updated_at=now,
        )
