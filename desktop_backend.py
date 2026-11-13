"""Processus serveur privé de l'application Windows DeckEdge.

La fermeture du canal stdin (y compris si l'application plante) arrête le serveur.
Aucun endpoint HTTP d'arrêt n'est exposé sur le réseau.
"""
import asyncio
import logging
import json
from pathlib import Path
import sys
import threading
from app_paths import DATA_DIR

BASE_DIR = Path(__file__).resolve().parent


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.FileHandler(DATA_DIR / "deckedge.log", encoding="utf-8")],
    )
    import uvicorn
    from server import app, ensure_default_desktop, telemetry

    if "--check" in sys.argv:
        print("DeckEdge backend OK", flush=True)
        return

    ensure_default_desktop()
    server = uvicorn.Server(uvicorn.Config(
        app, host="0.0.0.0", port=5000, log_config=None,
        access_log=False, loop="asyncio", proxy_headers=False,
    ))

    def wait_for_desktop():
        try:
            for line in sys.stdin.buffer:
                try:
                    telemetry.ingest(json.loads(line))
                except (ValueError, TypeError, AttributeError):
                    logging.getLogger("DeckEdge").warning("Trame de capteurs invalide ignorée.")
        finally:
            server.should_exit = True

    threading.Thread(target=wait_for_desktop, daemon=True).start()
    asyncio.run(server.serve())


if __name__ == "__main__":
    main()
