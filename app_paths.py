"""Keep shipped resources separate from per-user / portable state."""
import os
from pathlib import Path

RESOURCE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DECKEDGE_DATA_DIR", RESOURCE_DIR)).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
