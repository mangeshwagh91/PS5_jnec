from __future__ import annotations

import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVER_DIR = ROOT / "server"
TARGET = SERVER_DIR / "scripts" / "run_vision_worker.py"

# Ensure imports like `from app...` resolve the server package root.
sys.path.insert(0, str(SERVER_DIR))

runpy.run_path(str(TARGET), run_name="__main__")
