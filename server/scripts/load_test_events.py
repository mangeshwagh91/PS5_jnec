from __future__ import annotations

import argparse
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib import error, request

THREAT_TYPES = ["weapon", "garbage", "hazard", "intrusion", "fire"]
SOURCES = ["cctv", "drone", "iot"]


def build_payload(index: int) -> dict:
    return {
        "camera_id": f"CAM-{12 + (index % 80):03d}",
        "location": random.choice(["North Entrance", "East Fence", "Lot C", "Platform 2", "Zone Alpha"]),
        "threat_type": random.choice(THREAT_TYPES),
        "confidence": round(random.uniform(0.55, 0.99), 2),
        "coordinates": {
            "x": round(random.uniform(10, 95), 2),
            "y": round(random.uniform(10, 90), 2),
        },
        "source": random.choice(SOURCES),
        "context_signals": random.sample(["person", "running", "crowd", "smoke"], k=random.randint(0, 2)),
    }


def post_event(base_url: str, api_key: str | None, payload: dict, timeout: float) -> int:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    req = request.Request(f"{base_url}/events", data=body, headers=headers, method="POST")
    with request.urlopen(req, timeout=timeout) as response:
        return response.status


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple concurrent load test for /api/v1/events")
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1", help="API base URL")
    parser.add_argument("--api-key", default="", help="Optional ingestion API key")
    parser.add_argument("--requests", type=int, default=300, help="Total number of events to send")
    parser.add_argument("--concurrency", type=int, default=20, help="Concurrent worker threads")
    parser.add_argument("--timeout", type=float, default=10.0, help="Per-request timeout seconds")
    args = parser.parse_args()

    total = max(args.requests, 1)
    workers = max(args.concurrency, 1)
    api_key = args.api_key.strip() or None

    start = time.perf_counter()
    success = 0
    accepted = 0
    dedup_or_ignored = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(post_event, args.base_url, api_key, build_payload(i), args.timeout)
            for i in range(total)
        ]

        for future in as_completed(futures):
            try:
                status = future.result()
                success += 1
                if status == 200:
                    accepted += 1
                elif status == 202:
                    dedup_or_ignored += 1
            except error.HTTPError as exc:
                if exc.code == 202:
                    success += 1
                    dedup_or_ignored += 1
                else:
                    failed += 1
            except Exception:
                failed += 1

    elapsed = max(time.perf_counter() - start, 0.001)

    print("Load test complete")
    print(f"  total requests: {total}")
    print(f"  success: {success}")
    print(f"  accepted (200): {accepted}")
    print(f"  dedup/ignored (202): {dedup_or_ignored}")
    print(f"  failed: {failed}")
    print(f"  duration: {elapsed:.2f}s")
    print(f"  throughput: {total / elapsed:.2f} req/s")


if __name__ == "__main__":
    main()
