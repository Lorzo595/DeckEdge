"""Keep shipped resources separate from per-user / portable state."""
import os
from pathlib import Path

RESOURCE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("DECKEDGE_DATA_DIR", RESOURCE_DIR)).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)


def _port_from_environment() -> int:
    try:
        port = int(os.environ.get("DECKEDGE_PORT", "5000"))
    except (TypeError, ValueError):
        return 5000
    return port if 1 <= port <= 65535 else 5000


PORT = _port_from_environment()
