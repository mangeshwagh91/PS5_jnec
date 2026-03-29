from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Iterable

from app.models.schemas import Coordinates, DetectionEventIn, ThreatType


@dataclass
class RawDetection:
    label: str
    confidence: float
    bbox_xyxy: tuple[float, float, float, float]
    track_id: str | None = None


@dataclass
class _RuleState:
    hits: deque[datetime] = field(default_factory=deque)
    first_seen: datetime | None = None
    last_fired: datetime | None = None


class VisionRuleEngine:
    """Transforms frame-level detections into stable threat events.

    The logic is temporal to reduce noisy single-frame false positives:
    - weapon: requires consecutive confirmations
    - garbage: requires dwell time in frame
    - hazard: requires short consecutive confirmations
    """

    WEAPON_LABELS = {"weapon", "gun", "knife", "pistol", "rifle", "firearm"}
    GARBAGE_LABELS = {"garbage", "trash", "trash_bag", "dumping"}
    FIRE_LABELS = {"fire", "flame"}
    HAZARD_LABELS = {"hazard", "smoke", "spill", "leak"}
    CONTEXT_LABELS = {"person", "running", "crowd", "smoke"}

    def __init__(
        self,
        weapon_consecutive_frames: int = 3,
        weapon_window_seconds: int = 2,
        garbage_dwell_seconds: int = 20,
        hazard_consecutive_frames: int = 2,
        smoke_consecutive_frames: int = 5,
        hazard_window_seconds: int = 2,
        cooldown_seconds: int = 30,
    ) -> None:
        self.weapon_consecutive_frames = max(weapon_consecutive_frames, 1)
        self.weapon_window_seconds = max(weapon_window_seconds, 1)
        self.garbage_dwell_seconds = max(garbage_dwell_seconds, 1)
        self.hazard_consecutive_frames = max(hazard_consecutive_frames, 1)
        self.smoke_consecutive_frames = max(smoke_consecutive_frames, 1)
        self.hazard_window_seconds = max(hazard_window_seconds, 1)
        self.cooldown_seconds = max(cooldown_seconds, 1)

        self._states: dict[str, _RuleState] = {}

    def _key(self, threat: ThreatType, det: RawDetection, zone: str) -> str:
        track = det.track_id or "no-track"
        return f"{threat.value}:{zone}:{track}"

    def _get_state(self, key: str) -> _RuleState:
        if key not in self._states:
            self._states[key] = _RuleState()
        return self._states[key]

    @staticmethod
    def _to_coordinates(det: RawDetection, frame_w: int, frame_h: int) -> Coordinates:
        x1, y1, x2, y2 = det.bbox_xyxy
        center_x = ((x1 + x2) / 2.0) / max(frame_w, 1)
        center_y = ((y1 + y2) / 2.0) / max(frame_h, 1)
        return Coordinates(x=max(min(center_x * 100.0, 100.0), 0.0), y=max(min(center_y * 100.0, 100.0), 0.0))

    def _cooldown_ready(self, state: _RuleState, now: datetime) -> bool:
        if state.last_fired is None:
            return True
        return (now - state.last_fired) >= timedelta(seconds=self.cooldown_seconds)

    @staticmethod
    def _trim_hits(state: _RuleState, now: datetime, window_seconds: int) -> None:
        while state.hits and (now - state.hits[0]).total_seconds() > window_seconds:
            state.hits.popleft()

    def _maybe_event(
        self,
        threat_type: ThreatType,
        det: RawDetection,
        now: datetime,
        frame_w: int,
        frame_h: int,
        camera_id: str,
        location: str,
        source: str,
        context_signals: list[str],
        hazard_confirmation_frames: int | None = None,
    ) -> DetectionEventIn | None:
        key = self._key(threat_type, det, location)
        state = self._get_state(key)

        if threat_type == ThreatType.weapon:
            state.hits.append(now)
            self._trim_hits(state, now, self.weapon_window_seconds)
            if len(state.hits) < self.weapon_consecutive_frames or not self._cooldown_ready(state, now):
                return None

        elif threat_type == ThreatType.hazard:
            state.hits.append(now)
            self._trim_hits(state, now, self.hazard_window_seconds)
            required_hazard_frames = hazard_confirmation_frames or self.hazard_consecutive_frames
            if len(state.hits) < required_hazard_frames or not self._cooldown_ready(state, now):
                return None

        elif threat_type == ThreatType.garbage:
            if state.first_seen is None:
                state.first_seen = now
                return None
            dwell = (now - state.first_seen).total_seconds()
            if dwell < self.garbage_dwell_seconds or not self._cooldown_ready(state, now):
                return None

        state.last_fired = now
        coords = self._to_coordinates(det, frame_w, frame_h)

        return DetectionEventIn(
            camera_id=camera_id,
            location=location,
            threat_type=threat_type,
            confidence=det.confidence,
            coordinates=coords,
            source=source,
            context_signals=context_signals,
        )

    def evaluate(
        self,
        detections: Iterable[RawDetection],
        frame_w: int,
        frame_h: int,
        camera_id: str,
        location: str,
        source: str = "cctv",
    ) -> list[DetectionEventIn]:
        now = datetime.now(timezone.utc)
        events: list[DetectionEventIn] = []

        detections_list = list(detections)
        context_signals = [d.label for d in detections_list if d.label in self.CONTEXT_LABELS]

        for det in detections_list:
            label = det.label.lower().strip()

            threat_type: ThreatType | None = None
            if label in self.WEAPON_LABELS:
                threat_type = ThreatType.weapon
            elif label in self.FIRE_LABELS:
                threat_type = ThreatType.fire
            elif label in self.GARBAGE_LABELS:
                threat_type = ThreatType.garbage
            elif label in self.HAZARD_LABELS:
                threat_type = ThreatType.hazard

            if threat_type is None:
                continue

            event = self._maybe_event(
                threat_type=threat_type,
                det=det,
                now=now,
                frame_w=frame_w,
                frame_h=frame_h,
                camera_id=camera_id,
                location=location,
                source=source,
                context_signals=context_signals,
                hazard_confirmation_frames=self.smoke_consecutive_frames if label == "smoke" else self.hazard_consecutive_frames,
            )
            if event is not None:
                events.append(event)

        self._cleanup_old_states(now)
        return events

    def _cleanup_old_states(self, now: datetime) -> None:
        ttl = timedelta(minutes=10)
        stale_keys: list[str] = []
        for key, state in self._states.items():
            last_touch = state.last_fired or state.first_seen or (state.hits[-1] if state.hits else None)
            if last_touch and now - last_touch > ttl:
                stale_keys.append(key)

        for key in stale_keys:
            del self._states[key]
