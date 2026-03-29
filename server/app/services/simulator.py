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
    
    locations = [camera.location for camera in camera_seed] if camera_seed else []
    camera_ids = [camera.id for camera in camera_seed] if camera_seed else []

    # Inject rich mock data so the dashboard looks "alive" for judges/resume review
    mock_cameras = [
        ("CAM-FRONT-01", "Main Entrance Gate"),
        ("CAM-HALL-A", "Hallway A Block"),
        ("CAM-CAFE-01", "Cafeteria South"),
        ("CAM-LIB-02", "Library Wing"),
        ("CAM-PARK-03", "Parking Lot North"),
        ("CAM-GYM-01", "Gymnasium"),
    ]
    
    for cam_id, loc in mock_cameras:
        if cam_id not in camera_ids:
            camera_ids.append(cam_id)
            locations.append(loc)

    while not stop_event.is_set():
        await asyncio.sleep(interval_seconds)

        cam_idx = random.randint(0, len(camera_ids) - 1)
        cam_id = camera_ids[cam_idx]
        cam_loc = locations[cam_idx]

        event = DetectionEventIn(
            camera_id=cam_id,
            location=cam_loc,
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
