from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone

from app.models.schemas import Coordinates, DetectionEventIn, ThreatType
from app.services.event_engine import EventEngine
from app.services.store import InMemoryStore
from app.services.websocket_manager import WebSocketManager


async def run_simulator(
    store: InMemoryStore,
    engine: EventEngine,
    ws_manager: WebSocketManager,
    stop_event: asyncio.Event,
    interval_seconds: int,
) -> None:
    camera_seed = store.get_cameras()
    if not camera_seed:
        return

    locations = [camera.location for camera in camera_seed]
    camera_ids = [camera.id for camera in camera_seed]

    while not stop_event.is_set():
        await asyncio.sleep(interval_seconds)

        event = DetectionEventIn(
            camera_id=random.choice(camera_ids),
            location=random.choice(locations),
            threat_type=random.choice(list(ThreatType)),
            confidence=round(random.uniform(0.45, 0.99), 2),
            coordinates=Coordinates(x=random.uniform(10, 95), y=random.uniform(10, 90)),
            source=random.choice(["cctv", "drone", "iot"]),
            context_signals=random.sample(["person", "running", "crowd", "smoke"], k=random.randint(0, 2)),
        )

        if not engine.should_process(event):
            continue

        dedup_key = engine.build_dedup_key(event)
        if engine.is_deduplicated(dedup_key):
            continue

        alert = engine.create_alert(event)
        store.add_alert(alert)

        await ws_manager.broadcast(
            {
                "type": "alert.created",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": alert.model_dump(mode="json"),
            }
        )
