"""
DeckEdge - FastAPI backend & WebSocket orchestrator.
Secure architecture with Pydantic v2 validation:
- Multi-page / profile support (Gaming, Stream, Desktop, Music)
- Per-application Windows volume control via pycaw (Discord, Spotify, Master...)
- Toggle buttons with real-time visual state feedback
- Async LHM telemetry and atomic persistence
"""

from __future__ import annotations

import asyncio
from collections import deque
from contextlib import asynccontextmanager
import ctypes
from ctypes import wintypes
import hmac
import json
import logging
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tempfile
import threading
import time
import weakref
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, TypeVar
import sys
from monitoring import MonitoringState, DEFAULT_WIDGETS
from audio_sessions import collect_application_volumes

# Mandatory redirection under pythonw.exe
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import comtypes
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import pyautogui
import psutil
from pydantic import BaseModel, Field, ValidationError, model_validator
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume, IAudioSessionControl2
from pycaw.utils import AudioSession
from discord_rpc import discord_rpc
from app_paths import DATA_DIR, PORT
from network_access import COOKIE, pairing_key, rotate_pairing_key, is_local, allowed_origin, PhoneRegistry
from local_discovery import discovery, HOSTNAME

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("DeckEdge")

# Absolute paths
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = DATA_DIR / "config.json"
CONFIG_BAK_PATH = DATA_DIR / "config.json.bak"
INDEX_HTML_PATH = BASE_DIR / "index.html"
ADMIN_HTML_PATH = BASE_DIR / "admin.html"

MONITORING_POLL_INTERVAL_SEC = 1.0
MAX_WS_MESSAGE_BYTES = 8192
MAX_BUTTON_CLICKS_PER_SECOND = 30
LOG_TAIL_LINES = 80

pyautogui.FAILSAFE = False


# ============================================================================
# 1. VALIDATION MODELS (Pydantic v2)
# ============================================================================

ActionType = Literal["hotkey", "key", "launch", "volume_app", "slider", "sequence"]
StepType = Literal["hotkey", "key", "launch", "volume_app"]
ConditionType = Literal["always", "button_on", "button_off", "app_running", "mic_muted", "mic_unmuted"]

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_BACKUP_NAME_RE = re.compile(r"^deckedge-\d{8}-\d{6}-\d{3}\.json$")


class ActionStep(BaseModel):
    type: StepType = Field(default="hotkey", description="Type de l'étape")
    target: str = Field(default="", max_length=255, description="Touche, application ou cible audio")
    delay: float = Field(default=0.0, ge=0.0, le=5.0, description="Pause après l'étape, en secondes")
    condition: ConditionType = Field(default="always", description="Condition required to run the step")
    condition_target: str = Field(default="", max_length=64, description="Button or application used by the condition")


def _sanitize_identifier(value: Any, prefix: str, index: int, used: set[str]) -> str:
    """Keep legacy configs loadable while guaranteeing safe, unique DOM identifiers."""
    candidate = value.strip() if isinstance(value, str) else ""
    if not _IDENTIFIER_PATTERN.fullmatch(candidate) or candidate in used:
        candidate = f"{prefix}_{index}"
        suffix = 2
        while candidate in used:
            candidate = f"{prefix}_{index}_{suffix}"
            suffix += 1
    used.add(candidate)
    return candidate


class ButtonConfig(BaseModel):
    id: str = Field(..., min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$", description="Identifiant unique du bouton")
    label: str = Field(default="", max_length=50, description="Libellé affiché")
    icon: str = Field(default="⚡", max_length=10, description="Émoji ou symbole")
    type: ActionType = Field(default="hotkey", description="Type d'action")
    target: str = Field(default="", max_length=255, description="Touches, cible volume ou exécutable")
    steps: List[ActionStep] = Field(default_factory=list, max_length=10, description="Étapes d'une séquence")
    width: Literal["auto", "quarter", "third", "half", "full"] = "auto"
    height: Literal["compact", "normal", "tall"] = "normal"
    color: Optional[str] = Field(
        default="#161c2e",
        pattern=r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$",
        description="Couleur hexadécimale de fond (état inactif)"
    )
    # Toggle button
    is_toggle: bool = Field(default=False, description="Activer le mode bascule ON/OFF")
    state: bool = Field(default=False, description="État actif (True) ou inactif (False)")
    active_label: Optional[str] = Field(default="", max_length=50, description="Libellé affiché si actif")
    active_icon: Optional[str] = Field(default="", max_length=10, description="Icône si actif")
    active_color: Optional[str] = Field(
        default="#991b1b",
        pattern=r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$",
        description="Couleur hexadécimale de fond si actif"
    )

    @model_validator(mode="after")
    def validate_sequence(self):
        if self.type == "sequence" and not self.steps:
            raise ValueError("Une séquence doit contenir au moins une étape.")
        return self

class PageConfig(BaseModel):
    id: str = Field(..., min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$", description="Identifiant unique de la page")
    name: str = Field(..., min_length=1, max_length=50, description="Nom affiché de la page")
    icon: str = Field(default="📄", max_length=10, description="Icône de l'onglet")
    buttons: List[ButtonConfig] = Field(default_factory=list, max_length=500, description="Liste ordonnée des boutons")
    parent_id: Optional[str] = Field(default=None, max_length=64, description="Optional parent folder")
    is_folder: bool = Field(default=False, description="Navigation folder without buttons")

class MonitoringWidget(BaseModel):
    label: str = Field(default="Indicateur", min_length=1, max_length=24)
    sensor_id: str = Field(..., min_length=1, max_length=256)
    secondary_sensor_id: str = Field(default="", max_length=256)


class DeckConfig(BaseModel):
    monitoring: List[MonitoringWidget] = Field(default_factory=lambda: [MonitoringWidget(**w) for w in DEFAULT_WIDGETS], min_length=1, max_length=6)

    active_page_id: Optional[str] = Field(default="page_main", description="Page affichée par défaut")
    pages: List[PageConfig] = Field(default_factory=list, max_length=50, description="Liste des profils / pages")

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_or_normalize(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        data = dict(data)

        # Backward compatibility: transparent migration from the legacy {"buttons": [...]} structure
        if "pages" not in data and "buttons" in data:
            data = {
                **data,
                "active_page_id": "page_main",
                "pages": [
                    {
                        "id": "page_main",
                        "name": "Principal",
                        "icon": "🏠",
                        "buttons": data.get("buttons", [])
                    }
                ]
            }

        pages = data.get("pages") or []
        if not pages:
            pages = [
                {
                    "id": "page_main",
                    "name": "Principal",
                    "icon": "🏠",
                    "buttons": []
                }
            ]

        normalized_pages = []
        page_ids = []
        page_id_map: Dict[str, str] = {}
        used_page_ids: set[str] = set()
        used_button_ids: set[str] = set()

        for page_index, page in enumerate(pages):
            if isinstance(page, BaseModel):
                page = page.model_dump()
            if not isinstance(page, dict):
                normalized_pages.append(page)
                continue

            page = dict(page)
            original_id = page.get("id")
            page_id = _sanitize_identifier(original_id, "page", page_index, used_page_ids)
            if isinstance(original_id, str):
                page_id_map.setdefault(original_id, page_id)
            page["id"] = page_id
            page_ids.append(page_id)

            buttons = page.get("buttons")
            if isinstance(buttons, list):
                normalized_buttons = []
                for button in buttons:
                    if isinstance(button, BaseModel):
                        button = button.model_dump()
                    if isinstance(button, dict):
                        button = dict(button)
                        button["id"] = _sanitize_identifier(
                            button.get("id"), f"b{page_index}", len(normalized_buttons), used_button_ids
                        )
                    normalized_buttons.append(button)
                page["buttons"] = normalized_buttons

            normalized_pages.append(page)

        folder_ids = {page.get("id") for page in normalized_pages if isinstance(page, dict) and page.get("is_folder")}
        for page in normalized_pages:
            if not isinstance(page, dict):
                continue
            parent = page.get("parent_id")
            if isinstance(parent, str):
                parent = page_id_map.get(parent, parent)
            if page.get("is_folder") or parent not in folder_ids or parent == page.get("id"):
                parent = None
            page["parent_id"] = parent

        data["pages"] = normalized_pages

        # "Principal" is the opening profile; navigation stays local to each interface.
        page_ids = [page.get("id") for page in normalized_pages if isinstance(page, dict)]
        content_page_ids = [
            page.get("id") for page in normalized_pages
            if isinstance(page, dict) and not page.get("is_folder")
        ]
        active_page_id = data.get("active_page_id")
        if isinstance(active_page_id, str):
            active_page_id = page_id_map.get(active_page_id, active_page_id)
        if "page_main" in content_page_ids:
            data["active_page_id"] = "page_main"
        elif active_page_id in content_page_ids:
            data["active_page_id"] = active_page_id
        elif content_page_ids:
            data["active_page_id"] = content_page_ids[0]
        else:
            data["active_page_id"] = page_ids[0] if page_ids else "page_main"

        return data


DEFAULT_CONFIG = DeckConfig(
    active_page_id="page_main",
    pages=[
        PageConfig(
            id="page_main",
            name="Principal",
            icon="🏠",
            buttons=[
                ButtonConfig(id="b1", label="Mute Micro", icon="🎙️", type="volume_app", target="mic:mute", color="#161c2e", is_toggle=True, active_label="MUTÉ", active_icon="🔇", active_color="#991b1b"),
                ButtonConfig(id="b2", label="Pause/Play", icon="⏯️", type="key", target="playpause", color="#161c2e"),
                ButtonConfig(id="b3", label="REC / OBS", icon="🔴", type="hotkey", target="ctrl,f9", color="#161c2e", is_toggle=True, active_label="REC EN COURS", active_icon="⏹️", active_color="#991b1b"),
                ButtonConfig(id="b4", label="Master", icon="🔊", type="slider", target="master", color="#38bdf8"),
                ButtonConfig(id="b5", label="Discord", icon="💬", type="launch", target="start discord:", color="#5865f2"),
                ButtonConfig(id="b6", label="Spotify", icon="🎵", type="launch", target="start spotify:", color="#1db954"),
                ButtonConfig(id="b7", label="Bureau", icon="🖥️", type="hotkey", target="win,d", color="#1e3a8a"),
                ButtonConfig(id="b8", label="Calculatrice", icon="🧮", type="launch", target="calc.exe", color="#161c2e"),
            ]
        ),
        PageConfig(
            id="page_gaming",
            name="Gaming",
            icon="🎮",
            buttons=[
                ButtonConfig(id="g1", label="Mute Micro", icon="🎙️", type="volume_app", target="mic:mute", color="#161c2e", is_toggle=True, active_label="MICRO MUTÉ", active_icon="🔇", active_color="#991b1b"),
                ButtonConfig(id="g2", label="Sourdine", icon="🎧", type="hotkey", target="ctrl,shift,d", color="#161c2e", is_toggle=True, active_label="SOURDINE ON", active_icon="🔇", active_color="#991b1b"),
                ButtonConfig(id="g3", label="Discord", icon="🎙️", type="slider", target="app:discord", color="#a855f7"),
                ButtonConfig(id="g4", label="Steam", icon="🎮", type="launch", target="start steam://", color="#171a21"),
                ButtonConfig(id="g5", label="Capture", icon="📸", type="hotkey", target="win,shift,s", color="#161c2e"),
                ButtonConfig(id="g6", label="Overlay Jeu", icon="🎯", type="hotkey", target="shift,tab", color="#161c2e"),
                ButtonConfig(id="g7", label="Game Bar", icon="🎯", type="hotkey", target="win,g", color="#107c10"),
                ButtonConfig(id="g8", label="Master", icon="🔊", type="slider", target="master", color="#38bdf8"),
            ]
        ),
        PageConfig(
            id="page_music",
            name="Musique",
            icon="🎵",
            buttons=[
                ButtonConfig(id="m1", label="Ouvrir Spotify", icon="🎵", type="launch", target="start spotify:", color="#1db954"),
                ButtonConfig(id="m2", label="Play / Pause", icon="⏯️", type="key", target="playpause", color="#065f46"),
                ButtonConfig(id="m3", label="Précédent", icon="⏮️", type="key", target="prevtrack", color="#161c2e"),
                ButtonConfig(id="m4", label="Suivant", icon="⏭️", type="key", target="nexttrack", color="#161c2e"),
                ButtonConfig(id="m5", label="Spotify", icon="🎵", type="slider", target="app:spotify", color="#22c55e"),
                ButtonConfig(id="m6", label="Master", icon="🔊", type="slider", target="master", color="#38bdf8"),
            ]
        )
    ]
)


# ============================================================================
# 2. SERIALIZED, ATOMIC CONFIGURATION PERSISTENCE
# ============================================================================

T = TypeVar("T")


def _write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    """Write a complete JSON document then replace the file, using a unique temporary file."""
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        # Windows scanners can briefly hold a handle without delete sharing.
        # Keep the completed temporary file and retry only permission failures.
        for attempt in range(5):
            try:
                os.replace(tmp_name, path)
                break
            except PermissionError:
                if os.name != "nt" or attempt == 4:
                    raise
                time.sleep(.02 * (attempt + 1))
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


class ConfigStore:
    """Single source of truth: serialized reads, mutations and writes.

    Every mutation goes through ``update`` so that a slow save can never
    overwrite a modification made in the meantime. Writes use a unique
    temporary file, and the backup always represents the previously validated
    configuration, never a corrupted file.
    """

    def __init__(self, path: Path = CONFIG_PATH, backup_path: Path = CONFIG_BAK_PATH, debounce: float = 0.15, retry_delay: float = 0.5) -> None:
        self.path = path
        self.backup_path = backup_path
        self.backup_dir = path.parent / "backups"
        self.debounce = max(0.0, debounce)
        self.retry_delay = max(0.01, retry_delay)
        self._lock = threading.RLock()
        self._config: Optional[DeckConfig] = None
        self._written_config: Optional[DeckConfig] = None
        self._mtime_ns: Optional[int] = None
        self._dirty = False
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._writer = threading.Thread(target=self._writer_loop, daemon=True, name="DeckEdgeConfigWriter")
        self._writer.start()

    def _read_mtime(self) -> Optional[int]:
        try:
            return self.path.stat().st_mtime_ns
        except OSError:
            return None

    def _load_from_disk(self) -> DeckConfig:
        if not self.path.exists():
            self._write_locked(DEFAULT_CONFIG, keep_backup=False)
            assert self._config is not None
            return self._config.model_copy(deep=True)

        try:
            raw_data = json.loads(self.path.read_text(encoding="utf-8"))
            return DeckConfig.model_validate(raw_data)
        except (json.JSONDecodeError, ValidationError, OSError) as e:
            logger.error("Fichier config.json corrompu (%s). Tentative de récupération .bak...", e)
            if self.backup_path.exists():
                try:
                    raw_bak = json.loads(self.backup_path.read_text(encoding="utf-8"))
                    valid_config = DeckConfig.model_validate(raw_bak)
                    logger.info("Restauration réussie depuis le backup .bak.")
                    return valid_config
                except Exception as e_bak:
                    logger.critical("Backup .bak également illisible (%s). Restauration configuration usine.", e_bak)
            return DEFAULT_CONFIG.model_copy(deep=True)

    def _read_locked(self) -> DeckConfig:
        if self._config is None:
            self._config = self._load_from_disk()
            self._written_config = self._config.model_copy(deep=True)
            self._mtime_ns = self._read_mtime()
        elif not self._dirty:
            mtime = self._read_mtime()
            if mtime is not None and mtime != self._mtime_ns:
                self._config = self._load_from_disk()
                self._written_config = self._config.model_copy(deep=True)
                self._mtime_ns = mtime
        return self._config.model_copy(deep=True)

    def _write_locked(self, config: DeckConfig, keep_backup: bool = True) -> None:
        previous = self._written_config
        if keep_backup and previous is not None:
            try:
                _write_json_atomic(self.backup_path, previous.model_dump(mode="json"))
            except Exception as e:
                logger.warning("Impossible de créer config.json.bak: %s", e)

        _write_json_atomic(self.path, config.model_dump(mode="json"))
        self._config = config.model_copy(deep=True)
        self._written_config = self._config.model_copy(deep=True)
        self._mtime_ns = self._read_mtime()
        logger.info("Configuration persistée de manière atomique.")

    def load(self) -> DeckConfig:
        """Return an isolated copy of the current configuration."""
        with self._lock:
            return self._read_locked()

    def _writer_loop(self) -> None:
        while not self._stop.is_set():
            if not self._wake.wait(0.5):
                continue
            # Group bursts of clicks and state synchronizations.
            time.sleep(self.debounce)
            if self._stop.is_set():
                break
            self._wake.clear()
            try:
                self.flush()
            except Exception:
                logger.exception("Échec de la sauvegarde différée de la configuration; nouvelle tentative")
                # flush() leaves _dirty set to True. Re-arm the wake event, otherwise
                # the writer would wait forever for a new modification.
                self._wake.set()
                time.sleep(self.retry_delay)

    def flush(self) -> None:
        """Write pending changes immediately."""
        with self._lock:
            if not self._dirty or self._config is None:
                return
            config = self._config.model_copy(deep=True)
            self._write_locked(config)
            self._dirty = False
            self._wake.clear()

    def close(self) -> None:
        """Write the last changes then stop the writer."""
        try:
            self.flush()
        except Exception:
            logger.exception("Sauvegarde finale de la configuration impossible")
        finally:
            self._stop.set()
            self._wake.set()
            if self._writer.is_alive():
                self._writer.join(timeout=2.0)

    def save(self, config: DeckConfig) -> None:
        """Replace the configuration atomically and under the lock."""
        with self._lock:
            self._write_locked(config)
            self._dirty = False
            self._wake.clear()

    def update(self, mutator: Callable[[DeckConfig], Tuple[T, bool]]) -> T:
        """Apply an atomic mutation; the write is batched in the background."""
        with self._lock:
            config = self._read_locked()
            result, dirty = mutator(config)
            if dirty:
                self._config = config.model_copy(deep=True)
                self._dirty = True
                self._wake.set()
            return result

    def get_button(self, btn_id: str) -> Optional[ButtonConfig]:
        with self._lock:
            config = self._read_locked()
            for page in config.pages:
                for button in page.buttons:
                    if button.id == btn_id:
                        return button.model_copy(deep=True)
        return None

    def _backup_path_locked(self, name: str) -> Optional[Path]:
        if not isinstance(name, str) or not _BACKUP_NAME_RE.fullmatch(name):
            return None
        path = self.backup_dir / name
        return path if path.parent == self.backup_dir else None

    @staticmethod
    def _backup_metadata(path: Path) -> Dict[str, Any]:
        stat = path.stat()
        return {
            "name": path.name,
            "size": stat.st_size,
            "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
        }

    def _prune_backups_locked(self, limit: int = 20) -> None:
        if not self.backup_dir.exists():
            return
        backups = sorted(
            (path for path in self.backup_dir.glob("deckedge-*.json") if _BACKUP_NAME_RE.fullmatch(path.name)),
            key=lambda path: path.name,
            reverse=True,
        )
        for path in backups[limit:]:
            try:
                path.unlink()
            except OSError as e:
                logger.warning("Impossible de supprimer l'ancienne sauvegarde %s: %s", path.name, e)

    def create_backup(self) -> Dict[str, Any]:
        """Create a timestamped backup of the current configuration."""
        with self._lock:
            config = self._read_locked()
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = time.strftime("%Y%m%d-%H%M%S")
            milliseconds = int(time.time() * 1000) % 1000
            path = None
            for attempt in range(1000):
                candidate = self.backup_dir / f"deckedge-{stamp}-{(milliseconds + attempt) % 1000:03d}.json"
                if not candidate.exists():
                    path = candidate
                    break
            if path is None:
                raise RuntimeError("Impossible de créer un nom de sauvegarde unique")
            _write_json_atomic(path, config.model_dump(mode="json"))
            self._prune_backups_locked()
            return self._backup_metadata(path)

    def list_backups(self) -> List[Dict[str, Any]]:
        with self._lock:
            if not self.backup_dir.exists():
                return []
            entries = []
            for path in sorted(
                (item for item in self.backup_dir.glob("deckedge-*.json") if _BACKUP_NAME_RE.fullmatch(item.name)),
                key=lambda item: item.name,
                reverse=True,
            ):
                try:
                    entries.append(self._backup_metadata(path))
                except OSError:
                    continue
            return entries[:50]

    def restore_backup(self, name: str) -> DeckConfig:
        """Restore a validated backup, after backing up the current state."""
        with self._lock:
            path = self._backup_path_locked(name)
            if path is None or not path.exists():
                raise FileNotFoundError(name)
            raw = json.loads(path.read_text(encoding="utf-8"))
            config = DeckConfig.model_validate(raw)
            try:
                self.create_backup()
            except Exception as e:
                raise RuntimeError(
                    "Restauration annulée : impossible de sauvegarder la configuration actuelle."
                ) from e
            self.save(config)
            return config.model_copy(deep=True)


config_store = ConfigStore()


def active_button_display(button: ButtonConfig) -> Tuple[str, str]:
    """Compute the canonical active icon/label shared by every interface."""
    target = (button.target or "").lower()
    if button.active_icon:
        icon = button.active_icon
    elif button.icon in ("🎙️", "🔊", "🎧"):
        icon = "🔇"
    elif button.icon == "⏯️":
        icon = "⏸️"
    elif button.icon == "🔴":
        icon = "⏹️"
    else:
        icon = "⚡"

    if button.active_label:
        label = button.active_label
    elif "deaf" in target:
        label = "SOURDINE"
    elif "mute" in target:
        label = "MUTÉ"
    else:
        text = (button.label or "").lower()
        if "sourdine" in text or "deaf" in text:
            label = "SOURDINE"
        elif "micro" in text or "mute" in text:
            label = "MUTÉ"
        elif "discord" in text:
            label = "DISCORD MUTÉ"
        elif "rec" in text or "obs" in text:
            label = "REC EN COURS"
        elif "pause" in text or "play" in text:
            label = "EN PAUSE"
        else:
            label = button.label or ""
    return icon, label


def button_state_payload(button: ButtonConfig) -> Dict[str, Any]:
    icon, label = active_button_display(button)
    return {
        "type": "button_state",
        "btn_id": button.id,
        "state": button.state,
        "active_label": label,
        "active_icon": icon,
        "active_color": button.active_color or "#991b1b",
        "label": button.label,
        "icon": button.icon,
        "color": button.color or "#161c2e",
    }


def hardware_state_for(
    button: ButtonConfig,
    mic_muted: bool,
    master_muted: bool,
    apps_muted: Dict[str, bool],
) -> Optional[bool]:
    """Map a toggle target to the current Windows/Discord hardware state."""
    target = (button.target or "").strip().lower()
    if target == "discord:mute":
        if discord_rpc.is_authenticated:
            return discord_rpc.mute
        return apps_muted.get("discord", False)
    if target in ("discord:deaf", "discord:deafen"):
        if discord_rpc.is_authenticated:
            return discord_rpc.deaf
        return None
    if target in ("mic:mute", "mic", "windows:mic"):
        return mic_muted
    if target in ("master:mute", "master", "windows:master"):
        return master_muted
    if target.startswith("app:"):
        return apps_muted.get(target[4:].strip())
    if ":mute" in target:
        return apps_muted.get(target.split(":", 1)[0].strip())
    return None


# ============================================================================
# 3. CENTRALIZED, HIGH-PERFORMANCE AUDIO ENGINE (pycaw / WASAPI)
# ============================================================================

from pycaw.constants import AudioDeviceState, EDataFlow
import queue

class AudioEngine(threading.Thread):
    """
    Dedicated Windows COM thread for all audio operations.
    - Avoids the perpetual creation/destruction of COM apartments.
    - Caches audio devices and sessions for response times < 0.2ms.
    - Coalesces volume updates to eliminate any lag / stutter while dragging the touch slider.
    """

    def __init__(self) -> None:
        super().__init__(daemon=True, name="DeckEdgeAudioWorker")
        self._cmd_queue: queue.Queue = queue.Queue()
        self._pending_volumes: Dict[str, int] = {}
        self._lock = threading.Lock()
        self.device_cache: Dict[str, Any] = {}
        self.app_cache: Dict[str, Any] = {}
        self._cache_refreshed_at = 0.0
        self.start()

    def run(self) -> None:
        comtypes.CoInitialize()
        try:
            self._refresh_caches()
            while True:
                if time.monotonic() - self._cache_refreshed_at >= 2.0:
                    self._refresh_caches()
                # 1. Coalesced, immediate processing of pending volumes
                pending = {}
                with self._lock:
                    if self._pending_volumes:
                        pending = dict(self._pending_volumes)
                        self._pending_volumes.clear()

                for target, pct in pending.items():
                    self._apply_volume(target, pct)

                # 2. Synchronous commands
                try:
                    item = self._cmd_queue.get(timeout=0.02)
                except queue.Empty:
                    continue

                if item is None:
                    break

                cmd, args, resp_event, resp_container = item
                try:
                    if cmd == "get_targets":
                        resp_container["result"] = self._get_targets()
                    elif cmd == "toggle_mute":
                        resp_container["result"] = self._toggle_mute(args[0])
                    elif cmd == "adjust_relative":
                        resp_container["result"] = self._adjust_relative(args[0], args[1])
                    elif cmd == "get_sessions_list":
                        resp_container["result"] = self._get_sessions_list()
                    elif cmd == "get_system_states":
                        resp_container["result"] = self._get_system_states()
                except Exception as e:
                    logger.error(f"Erreur AudioEngine [{cmd}]: {e}")
                finally:
                    if resp_event:
                        resp_event.set()
        finally:
            comtypes.CoUninitialize()

    def _refresh_caches(self) -> None:
        self._cache_refreshed_at = time.monotonic()
        try:
            dev_map = {}
            for d in AudioUtilities.GetAllDevices(data_flow=EDataFlow.eRender.value, device_state=AudioDeviceState.Active.value):
                if d.state == AudioDeviceState.Active:
                    dev_map[d.FriendlyName.lower()] = d
            self.device_cache = dev_map
        except Exception as e:
            logger.debug(f"Erreur actualisation périphériques: {e}")

        try:
            self.app_cache = collect_application_volumes(
                self.device_cache.values(), AudioSession, IAudioSessionControl2, ISimpleAudioVolume
            )
        except Exception as e:
            logger.debug(f"Erreur actualisation sessions: {e}")

    def _resolve_device(self, device_name: str):
        if not device_name:
            return None
        for name, device in self.device_cache.items():
            if device_name in name:
                return device
        self._refresh_caches()
        for name, device in self.device_cache.items():
            if device_name in name:
                return device
        return None

    def _resolve_app(self, app_name: str):
        if not app_name:
            return None
        for name, control in self.app_cache.items():
            if app_name in name:
                return control
        self._refresh_caches()
        for name, control in self.app_cache.items():
            if app_name in name:
                return control
        return None

    def _apply_volume(self, target: str, pct: int) -> None:
        val = max(0.0, min(1.0, float(pct) / 100.0))
        t = target.strip().lower()
        if not t:
            return

        # Master
        if t in ("master", "general", "windows"):
            try:
                AudioUtilities.GetSpeakers().EndpointVolume.SetMasterVolumeLevelScalar(val, None)
            except Exception as e:
                logger.debug(f"Erreur set master volume: {e}")
            return

        # Specific device
        if t.startswith("device:"):
            device = self._resolve_device(t[7:].strip().lower())
            if device is not None:
                try:
                    device.EndpointVolume.SetMasterVolumeLevelScalar(val, None)
                except Exception as e:
                    logger.debug(f"Erreur set device volume: {e}")
            return

        # Application (an empty target must never hit the first session)
        app_name = t[4:].strip().lower() if t.startswith("app:") else t
        control = self._resolve_app(app_name)
        if control is not None:
            try:
                control.SetMasterVolume(val, None)
            except Exception as e:
                logger.debug(f"Erreur set app volume: {e}")

    def _toggle_mute(self, target: str) -> bool:
        t = target.strip().lower()
        if not t:
            return False

        # Master
        if t in ("master", "general", "windows"):
            try:
                spk = AudioUtilities.GetSpeakers()
                m = spk.EndpointVolume.GetMute()
                spk.EndpointVolume.SetMute(0 if m else 1, None)
                return not m
            except Exception:
                return False

        # Windows hardware microphone
        if t in ("mic", "microphone", "mic:mute", "microphone:mute"):
            try:
                from pycaw.pycaw import IAudioEndpointVolume
                mic = AudioUtilities.GetMicrophone()
                if mic:
                    volume = mic.Activate(IAudioEndpointVolume._iid_, comtypes.CLSCTX_ALL, None).QueryInterface(IAudioEndpointVolume)
                    m = volume.GetMute()
                    volume.SetMute(0 if m else 1, None)
                    return not m
            except Exception as e:
                logger.debug(f"Erreur mute micro: {e}")
            return False

        # Specific device
        if t.startswith("device:"):
            device = self._resolve_device(t[7:].strip().lower())
            if device is None:
                return False
            try:
                m = device.EndpointVolume.GetMute()
                device.EndpointVolume.SetMute(0 if m else 1, None)
                return not m
            except Exception:
                return False

        # Application
        app_name = t[4:].strip().lower() if t.startswith("app:") else t
        control = self._resolve_app(app_name)
        if control is None:
            return False
        try:
            m = control.GetMute()
            control.SetMute(0 if m else 1, None)
            return not m
        except Exception:
            return False

    def _adjust_relative(self, target_spec: str, delta: float) -> bool:
        t = target_spec.strip().lower()
        if not t:
            return False
        if t in ("master", "general", "windows"):
            try:
                spk = AudioUtilities.GetSpeakers()
                curr = spk.EndpointVolume.GetMasterVolumeLevelScalar()
                new_vol = max(0.0, min(1.0, curr + delta))
                spk.EndpointVolume.SetMasterVolumeLevelScalar(new_vol, None)
                return True
            except Exception:
                return False

        if t.startswith("device:"):
            device = self._resolve_device(t[7:].strip().lower())
            if device is None:
                return False
            try:
                curr = device.EndpointVolume.GetMasterVolumeLevelScalar()
                new_vol = max(0.0, min(1.0, curr + delta))
                device.EndpointVolume.SetMasterVolumeLevelScalar(new_vol, None)
                return True
            except Exception:
                return False

        app_name = t[4:].strip().lower() if t.startswith("app:") else t
        control = self._resolve_app(app_name)
        if control is None:
            return False
        try:
            curr = control.GetMasterVolume()
            new_vol = max(0.0, min(1.0, curr + delta))
            control.SetMasterVolume(new_vol, None)
            return True
        except Exception:
            return False

    def _get_targets(self) -> Dict[str, Any]:
        devices = []
        try:
            spk = AudioUtilities.GetSpeakers()
            devices.append({
                "name": "Général (Master Windows)",
                "target": "master",
                "volume": int(round(spk.EndpointVolume.GetMasterVolumeLevelScalar() * 100)),
                "muted": bool(spk.EndpointVolume.GetMute())
            })
        except Exception:
            pass

        self._refresh_caches()
        for name, dev in self.device_cache.items():
            try:
                devices.append({
                    "name": dev.FriendlyName,
                    "target": f"device:{dev.FriendlyName}",
                    "volume": int(round(dev.EndpointVolume.GetMasterVolumeLevelScalar() * 100)),
                    "muted": bool(dev.EndpointVolume.GetMute())
                })
            except Exception:
                pass

        apps = []
        for name, vol_ctl in self.app_cache.items():
            try:
                apps.append({
                    "name": name.capitalize(),
                    "process": f"{name}.exe",
                    "target": f"app:{name}",
                    "volume": int(round(vol_ctl.GetMasterVolume() * 100)),
                    "muted": bool(vol_ctl.GetMute()),
                    "outputs": list(vol_ctl.outputs),
                    "sessions": len(vol_ctl.controls)
                })
            except Exception:
                pass

        return {"devices": devices, "apps": apps}

    def _get_sessions_list(self) -> List[str]:
        self._refresh_caches()
        apps = {"master"}
        for name in self.app_cache.keys():
            apps.add(f"{name}.exe")
        return sorted(list(apps))

    def set_volume(self, target: str, percent: int) -> None:
        """Ultra-fast non-blocking coalescing (0ms)."""
        with self._lock:
            self._pending_volumes[target] = percent

    def get_targets(self) -> Dict[str, Any]:
        evt = threading.Event()
        resp: Dict[str, Any] = {}
        self._cmd_queue.put(("get_targets", (), evt, resp))
        evt.wait(timeout=3.0)
        return resp.get("result", {"devices": [], "apps": []})

    def toggle_mute(self, target: str) -> bool:
        evt = threading.Event()
        resp: Dict[str, Any] = {}
        self._cmd_queue.put(("toggle_mute", (target,), evt, resp))
        evt.wait(timeout=2.0)
        return resp.get("result", False)

    def adjust_relative(self, target_spec: str, delta: float) -> bool:
        evt = threading.Event()
        resp: Dict[str, Any] = {}
        self._cmd_queue.put(("adjust_relative", (target_spec, delta), evt, resp))
        evt.wait(timeout=2.0)
        return resp.get("result", False)

    def _get_system_states(self) -> Dict[str, Any]:
        mic_mute = False
        master_mute = False
        try:
            from pycaw.pycaw import IAudioEndpointVolume
            mic = AudioUtilities.GetMicrophone()
            if mic:
                vol = mic.Activate(IAudioEndpointVolume._iid_, comtypes.CLSCTX_ALL, None).QueryInterface(IAudioEndpointVolume)
                mic_mute = bool(vol.GetMute())
        except Exception:
            pass

        try:
            spk = AudioUtilities.GetSpeakers()
            master_mute = bool(spk.EndpointVolume.GetMute())
        except Exception:
            pass

        apps_mute = {}
        for name, vol_ctl in self.app_cache.items():
            try:
                apps_mute[name] = bool(vol_ctl.GetMute())
            except Exception:
                pass

        return {
            "mic_muted": mic_mute,
            "master_muted": master_mute,
            "apps_muted": apps_mute,
        }

    def get_system_states(self) -> Dict[str, Any]:
        evt = threading.Event()
        resp: Dict[str, Any] = {}
        self._cmd_queue.put(("get_system_states", (), evt, resp))
        evt.wait(timeout=1.0)
        return resp.get("result", {"mic_muted": False, "master_muted": False, "apps_muted": {}})

    def get_sessions(self) -> List[str]:
        evt = threading.Event()
        resp: Dict[str, Any] = {}
        self._cmd_queue.put(("get_sessions_list", (), evt, resp))
        evt.wait(timeout=2.0)
        return resp.get("result", ["master"])


audio_engine = AudioEngine()


def get_audio_targets() -> Dict[str, Any]:
    return audio_engine.get_targets()

def set_audio_target_volume(target: str, percent: int) -> bool:
    audio_engine.set_volume(target, percent)
    return True

def toggle_audio_target_mute(target: str) -> bool:
    return audio_engine.toggle_mute(target)

def get_audio_sessions_list() -> List[str]:
    return audio_engine.get_sessions()

def adjust_audio_volume(target_spec: str) -> bool:
    if ":" not in target_spec:
        return False
    app_name, action = target_spec.rsplit(":", 1)
    app_name = app_name.strip().lower()
    action = action.strip().lower()

    if not app_name or app_name in ("app:", "device:"):
        return False

    if action == "mute":
        return toggle_audio_target_mute(app_name)

    if action.startswith("+") or action.startswith("-"):
        try:
            delta = float(action) / 100.0
            return audio_engine.adjust_relative(app_name, delta)
        except Exception:
            return False
    return False


# ============================================================================
# 4. RESILIENT WEBSOCKET CONNECTION MANAGER
# ============================================================================

class ConnectionManager:
    """Manage the WebSocket lifecycle and silently drop ghost sockets."""

    def __init__(self) -> None:
        self._active: set[WebSocket] = set()
        self._devices: Dict[WebSocket, Optional[str]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket, device_id: Optional[str] = None) -> None:
        await ws.accept()
        async with self._lock:
            self._active.add(ws)
            self._devices[ws] = device_id
        logger.info(f"Nouveau client connecté. Total: {len(self._active)}")

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._active.discard(ws)
            self._devices.pop(ws, None)
        logger.info(f"Client déconnecté. Total: {len(self._active)}")

    async def disconnect_device(self, device_id: str) -> int:
        async with self._lock:
            sockets = [ws for ws, owner in self._devices.items() if owner == device_id]
        for ws in sockets:
            try:
                await ws.close(code=1008)
            except Exception:
                pass
        if sockets:
            async with self._lock:
                for ws in sockets:
                    self._active.discard(ws)
                    self._devices.pop(ws, None)
            logger.info("Téléphone révoqué : %s session(s) fermée(s).", len(sockets))
        return len(sockets)

    async def disconnect_phones(self) -> int:
        async with self._lock:
            sockets = list(self._active)
        for ws in sockets:
            try:
                await ws.close(code=1008)
            except Exception:
                pass
        if sockets:
            async with self._lock:
                for ws in sockets:
                    self._active.discard(ws)
                    self._devices.pop(ws, None)
        return len(sockets)

    @property
    def client_count(self) -> int:
        return len(self._active)

    async def broadcast(self, message: Dict[str, Any], exclude_ws: Optional[WebSocket] = None) -> None:
        async with self._lock:
            sockets = [ws for ws in self._active if ws != exclude_ws]

        if not sockets:
            return

        dead_sockets: List[WebSocket] = []

        for ws in sockets:
            try:
                await ws.send_json(message)
            except Exception:
                dead_sockets.append(ws)

        if dead_sockets:
            async with self._lock:
                for ws in dead_sockets:
                    self._active.discard(ws)
            logger.debug(f"{len(dead_sockets)} socket(s) fantôme(s) purgé(s).")


manager = ConnectionManager()

_background_tasks: set[asyncio.Task] = set()


def _finish_background_task(task: asyncio.Task) -> None:
    _background_tasks.discard(task)
    if task.cancelled():
        return
    error = task.exception()
    if error is not None:
        logger.error("Erreur dans une tâche de clic: %s", error)


def _spawn_button_click(btn_id: str) -> None:
    """Keep a strong reference to fire-and-forget click tasks."""
    task = asyncio.create_task(handle_button_click(btn_id))
    _background_tasks.add(task)
    task.add_done_callback(_finish_background_task)


# ============================================================================
# 5. CENTRALIZED HARDWARE TELEMETRY SERVICE (LHM)
# ============================================================================

class LHMTelemetryService(MonitoringState):
    """Broadcast the measurements received from the LHM engine built into DeckEdge."""

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._task = None

    async def _poll_loop(self) -> None:
        while self._running:
            self.refresh()
            if manager.client_count > 0:
                config = await asyncio.to_thread(config_store.load)
                payload = self.payload(config.monitoring)
                await manager.broadcast(payload)

                # Automatic synchronization of hardware state (Windows mic, master, Discord...)
                try:
                    sys_states = await asyncio.to_thread(audio_engine.get_system_states)
                    mic_muted = sys_states.get("mic_muted", False)
                    master_muted = sys_states.get("master_muted", False)
                    apps_muted = sys_states.get("apps_muted", {})

                    def apply_hardware_states(cfg: DeckConfig):
                        messages = []
                        for page in cfg.pages:
                            for button in page.buttons:
                                if not button.is_toggle:
                                    continue
                                new_state = hardware_state_for(button, mic_muted, master_muted, apps_muted)
                                if new_state is not None and button.state != new_state:
                                    button.state = new_state
                                    messages.append(button_state_payload(button))
                        return messages, bool(messages)

                    messages = await asyncio.to_thread(config_store.update, apply_hardware_states)
                    for message in messages:
                        await manager.broadcast(message)
                except Exception as e_st:
                    logger.debug(f"Erreur sync hardware states: {e_st}")

            await asyncio.sleep(MONITORING_POLL_INTERVAL_SEC)

    def start(self) -> None:
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._poll_loop())
            logger.info("Service de monitoring intégré démarré.")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Service de monitoring intégré arrêté.")


telemetry = LHMTelemetryService()


def setup_discord_integration(main_loop: asyncio.AbstractEventLoop):
    def on_state(mute: bool, deaf: bool):
        async def _notify():
            def apply_discord_state(cfg: DeckConfig):
                messages = []
                for page in cfg.pages:
                    for button in page.buttons:
                        if not button.is_toggle:
                            continue
                        target = (button.target or "").strip().lower()
                        new_state = None
                        if target == "discord:mute":
                            new_state = mute
                        elif target in ("discord:deaf", "discord:deafen"):
                            new_state = deaf
                        if new_state is not None and button.state != new_state:
                            button.state = new_state
                            messages.append(button_state_payload(button))
                return messages, bool(messages)

            messages = await asyncio.to_thread(config_store.update, apply_discord_state)
            for message in messages:
                await manager.broadcast(message)

        try:
            asyncio.run_coroutine_threadsafe(_notify(), main_loop)
        except Exception as e:
            logger.debug(f"Erreur notify Discord: {e}")

    discord_rpc.register_state_callback(on_state)


# ============================================================================
# 6. APPLICATION LIFECYCLE (FastAPI Lifespan)
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_running_loop()
    setup_discord_integration(loop)
    discord_rpc.start()
    telemetry.start()
    discovery_task = asyncio.create_task(asyncio.to_thread(discovery.start))
    try:
        yield
    finally:
        await discovery_task
        await asyncio.to_thread(discovery.stop)
        await telemetry.stop()
        discord_rpc.stop()
        await asyncio.to_thread(config_store.close)


app = FastAPI(title="DeckEdge Server", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
PHONE_KEY = pairing_key()
phones = PhoneRegistry()


def _matches_master_key(value) -> bool:
    return isinstance(value, str) and value.isascii() and hmac.compare_digest(value, PHONE_KEY)

_SERVER_TEXTS = {
    "fr": {
        "origin": "Origine non autorisée",
        "desktop_only": "Ce réglage se modifie dans le Studio sur le PC.",
        "phone_missing": "Téléphone introuvable",
        "backup_missing": "Sauvegarde introuvable",
        "backup_invalid": "Sauvegarde invalide",
        "pairing_title": "Connecter DeckEdge",
        "pairing_heading": "Retrouver votre Deck",
        "pairing_intro": "Cette adresse n’est pas encore associée à votre téléphone.",
        "pairing_step1": "Sur le PC, ouvrez DeckEdge.",
        "pairing_step2": "Cliquez sur <b>Connecter le téléphone</b>.",
        "pairing_step3": "Scannez le QR code avec l’appareil photo.",
        "pairing_outro": "Ajoutez ensuite le Deck à votre écran d’accueil pour le retrouver aux prochains démarrages.",
    },
    "en": {
        "origin": "Origin not allowed",
        "desktop_only": "This setting can only be changed in the Studio on the PC.",
        "phone_missing": "Phone not found",
        "backup_missing": "Backup not found",
        "backup_invalid": "Invalid backup",
        "pairing_title": "Connect DeckEdge",
        "pairing_heading": "Find your Deck",
        "pairing_intro": "This address is not paired with your phone yet.",
        "pairing_step1": "On the PC, open DeckEdge.",
        "pairing_step2": "Click <b>Connect phone</b>.",
        "pairing_step3": "Scan the QR code with your camera.",
        "pairing_outro": "Then add the Deck to your home screen to find it again on future launches.",
    },
}


def request_language(connection) -> str:
    for value in (
        connection.query_params.get("lang") if hasattr(connection, "query_params") else None,
        connection.cookies.get("deckedge_lang") if hasattr(connection, "cookies") else None,
    ):
        if value in ("fr", "en"):
            return value
    header = connection.headers.get("accept-language", "") if hasattr(connection, "headers") else ""
    first = header.split(",", 1)[0].strip().lower()
    return "fr" if first.startswith("fr") else "en"


def server_text(language: str, key: str) -> str:
    return _SERVER_TEXTS.get(language, _SERVER_TEXTS["en"]).get(key, key)


def pairing_page(language: str) -> str:
    text = _SERVER_TEXTS.get(language, _SERVER_TEXTS["en"])
    return f'''<!doctype html><html lang="{language}"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{text["pairing_title"]}</title><body style="margin:0;background:#191b22;color:#eef1fc;font:17px/1.65 system-ui;padding:28px"><main style="max-width:480px;margin:12vh auto"><h1>{text["pairing_heading"]}</h1><p>{text["pairing_intro"]}</p><ol><li>{text["pairing_step1"]}</li><li>{text["pairing_step2"]}</li><li>{text["pairing_step3"]}</li></ol><p>{text["pairing_outro"]}</p></main></body></html>'''

_PRIVATE_IP_RE = re.compile(r"\b((?:10|127|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3})\.\d{1,3}\b")


def _path_pattern(path: str) -> str:
    """Case- and separator-insensitive Windows/Linux regex."""
    parts = [part for part in re.split(r"[\\/]+", path) if part]
    return r"[\\/]+".join(re.escape(part) for part in parts)


def _redact_text(value: Any) -> str:
    """Mask personal paths, the phone key and private IPs."""
    text = "" if value is None else str(value)
    for path, replacement in (
        (str(DATA_DIR), "<données>"),
        (str(BASE_DIR), "<installation>"),
        (str(Path.home()), "<utilisateur>"),
    ):
        pattern = _path_pattern(path)
        if pattern:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    for name in {os.environ.get("USERNAME"), os.environ.get("USER")}:
        if name:
            text = re.sub(re.escape(name), "<utilisateur>", text, flags=re.IGNORECASE)
    text = re.sub(re.escape(PHONE_KEY), "<clé téléphone>", text, flags=re.IGNORECASE)
    for secret in (
        getattr(discord_rpc, "access_token", ""),
        getattr(discord_rpc, "refresh_token", ""),
        getattr(discord_rpc, "client_secret", ""),
    ):
        if secret:
            text = re.sub(re.escape(secret), "<secret>", text, flags=re.IGNORECASE)
    return _PRIVATE_IP_RE.sub(r"\1.x", text)


def _tail(path: Path) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as file:
            return [_redact_text(line.rstrip()) for line in deque(file, maxlen=LOG_TAIL_LINES)]
    except OSError:
        return []


def _app_version() -> str:
    try:
        return (BASE_DIR / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "inconnue"


@app.middleware("http")
async def protect_desktop_and_pair_phone(request: Request, call_next):
    local = is_local(request.client.host) if request.client else False
    language = request_language(request)
    if not allowed_origin(request):
        return JSONResponse({"detail": server_text(language, "origin")}, status_code=403)
    issued_token = None
    if not local:
        ip = request.client.host if request.client else ""
        user_agent = request.headers.get("user-agent", "")
        cookie = request.cookies.get(COOKIE, "")
        device = phones.authenticate(cookie, ip)
        supplied = request.query_params.get("key")
        if device is None and cookie and _matches_master_key(cookie):
            device, issued_token = phones.pair(user_agent, ip)
        if device is None and supplied and _matches_master_key(supplied):
            device, issued_token = phones.pair(user_agent, ip)
        if device is None:
            return HTMLResponse(pairing_page(language), status_code=401)
    desktop_only = request.url.path in {"/admin", "/api/apps", "/api/diagnostics", "/api/monitoring/sensors", "/api/discord/connect", "/api/discord/disconnect", "/api/config/validate", "/api/config/restore", "/api/config/backups", "/api/actions/test"} or request.url.path.startswith("/api/phones") or (request.url.path == "/api/config" and request.method != "GET")
    if desktop_only and not local:
        return JSONResponse({"detail": server_text(language, "desktop_only")}, status_code=403)
    response = await call_next(request)
    if issued_token:
        response.set_cookie(COOKIE, issued_token, httponly=True, samesite="strict", max_age=31536000, path="/")
    if request.url.path in ('/', '/manifest.webmanifest'):
        response.headers['Cache-Control'] = 'no-store'
    response.headers["Content-Language"] = language
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
    return response


# ============================================================================
# 7. NATIVE WIN32 KEY EMULATION & ACTION EXECUTION
# ============================================================================

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]
    _anonymous_ = ("_input",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("_input", _INPUT),
    ]

def ensure_default_desktop() -> None:
    """Ensure the current thread is attached to the Windows interactive Default desktop."""
    try:
        hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if hdesk:
            user32.SetThreadDesktop(hdesk)
            user32.CloseDesktop(hdesk)
    except Exception:
        pass

VK_MAP = {
    "win": 0x5B, "lwin": 0x5B, "rwin": 0x5C, "winleft": 0x5B, "winright": 0x5C,
    "ctrl": 0x11, "ctrlleft": 0xA2, "ctrlright": 0xA3,
    "shift": 0x10, "shiftleft": 0xA0, "shiftright": 0xA1,
    "alt": 0x12, "altleft": 0xA4, "altright": 0xA5,
    "playpause": 0xB3, "play/pause": 0xB3, "play_pause": 0xB3, "pause/play": 0xB3, "pause_play": 0xB3, "play": 0xB3, "pause": 0xB3,
    "volumeup": 0xAF, "volumedown": 0xAE, "volumemute": 0xAD, "mute": 0xAD,
    "nexttrack": 0xB0, "next": 0xB0,
    "prevtrack": 0xB1, "prev": 0xB1, "previous": 0xB1,
    "stop": 0xB2,
    "tab": 0x09,
    "enter": 0x0D, "return": 0x0D,
    "esc": 0x1B, "escape": 0x1B,
    "space": 0x20,
    "backspace": 0x08,
    "delete": 0x2E, "del": 0x2E,
    "insert": 0x2D, "ins": 0x2D,
    "home": 0x24, "end": 0x23,
    "pageup": 0x21, "pgup": 0x21,
    "pagedown": 0x22, "pgdn": 0x22,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74, "f6": 0x75,
    "f7": 0x76, "f8": 0x77, "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "f13": 0x7C, "f14": 0x7D, "f15": 0x7E, "f16": 0x7F, "f17": 0x80, "f18": 0x81,
    "f19": 0x82, "f20": 0x83, "f21": 0x84, "f22": 0x85, "f23": 0x86, "f24": 0x87,
}

EXTENDED_KEYS = {
    0x5B, 0x5C, # LWIN, RWIN
    0xAD, 0xAE, 0xAF, # VOLUME_MUTE, VOLUME_DOWN, VOLUME_UP
    0xB0, 0xB1, 0xB2, 0xB3, # NEXT, PREV, STOP, PLAY_PAUSE
    0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E, # Navigation
    0xA3, 0xA5, # RCONTROL, RMENU
}

def _press_vk(vk: int, down: bool) -> None:
    flags = 0
    if vk in EXTENDED_KEYS:
        flags |= KEYEVENTF_EXTENDEDKEY
    if not down:
        flags |= KEYEVENTF_KEYUP
    scan = user32.MapVirtualKeyW(vk, 0)
    
    inp = INPUT()
    inp.type = 1  # INPUT_KEYBOARD
    inp.ki.wVk = vk
    inp.ki.wScan = scan
    inp.ki.dwFlags = flags
    inp.ki.time = 0
    inp.ki.dwExtraInfo = 0
    
    arr = (INPUT * 1)(inp)
    ret = user32.SendInput(1, arr, ctypes.sizeof(INPUT))
    if ret != 1:
        user32.keybd_event(vk, scan, flags, 0)

def send_win32_key(key_str: str) -> bool:
    """Send a single key with a native scan code and extended flags."""
    ensure_default_desktop()
    k = key_str.lower().strip()
    if k in VK_MAP:
        vk = VK_MAP[k]
    elif len(k) == 1 and k.isalnum():
        vk = ord(k.upper())
    else:
        try:
            pyautogui.press(k)
            return True
        except Exception:
            return False

    _press_vk(vk, True)
    time.sleep(0.02)
    _press_vk(vk, False)
    return True

def send_win32_hotkey(keys_str: str) -> bool:
    """Send a native key combination (e.g. 'win,d', 'ctrl,shift,m')."""
    ensure_default_desktop()
    tokens = [k.strip().lower() for k in keys_str.split(",") if k.strip()]
    if not tokens:
        return False

    vks = []
    for k in tokens:
        if k in VK_MAP:
            vks.append(VK_MAP[k])
        elif len(k) == 1 and k.isalnum():
            vks.append(ord(k.upper()))
        else:
            try:
                pyautogui.hotkey(*tokens)
                return True
            except Exception:
                return False

    # Ordered key press with scan codes and extended flags
    for vk in vks:
        _press_vk(vk, True)
    time.sleep(0.03)
    # Release in reverse order
    for vk in reversed(vks):
        _press_vk(vk, False)
    return True

def force_foreground_window(hwnd: int) -> bool:
    """Restore a window and force it to the foreground, bypassing the Windows focus lock."""
    try:
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        else:
            user32.ShowWindow(hwnd, 5)  # SW_SHOW
            
        fore_hwnd = user32.GetForegroundWindow()
        cur_tid = kernel32.GetCurrentThreadId()
        fore_tid = user32.GetWindowThreadProcessId(fore_hwnd, None)
        if fore_tid != cur_tid:
            user32.AttachThreadInput(cur_tid, fore_tid, True)
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
            user32.AttachThreadInput(cur_tid, fore_tid, False)
        else:
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)
        return True
    except Exception as e:
        logger.debug(f"force_foreground_window error: {e}")
        return False

def bring_window_to_front_by_keyword(keyword: str) -> bool:
    """Find a visible window matching the keyword and bring it to the foreground."""
    ensure_default_desktop()
    kw = keyword.lower().strip()
    if not kw:
        return False
    hdesk = user32.GetThreadDesktop(kernel32.GetCurrentThreadId())
    targets = []
    
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def enum_cb(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                if kw in buf.value.lower():
                    targets.append(hwnd)
        return True
        
    user32.EnumDesktopWindows(hdesk, WNDENUMPROC(enum_cb), 0)
    if targets:
        return force_foreground_window(targets[0])
    return False

_button_click_locks = weakref.WeakValueDictionary()


async def handle_button_click(btn_id: str) -> None:
    """Execute first; a failed or slow save must not suppress the command."""
    lock = _button_click_locks.setdefault(btn_id, asyncio.Lock())
    async with lock:
        target_btn = await asyncio.to_thread(config_store.get_button, btn_id)
        if target_btn is None:
            logger.warning("Bouton introuvable : %s", btn_id)
            return

        logger.info("Clic reçu [%s] '%s'", target_btn.id, target_btn.label)
        await asyncio.to_thread(_execute_button, target_btn)
        # Mute commands return the new mute state: False also means a successful
        # unmute. Keep the existing optimistic toggle; telemetry reconciles it.
        if not target_btn.is_toggle:
            return

        expected_state = not target_btn.state

        def apply_state(config: DeckConfig):
            for page in config.pages:
                for button in page.buttons:
                    if button.id != btn_id:
                        continue
                    # A Studio edit made during the command must not be overwritten.
                    if not button.is_toggle or (button.type, button.target) != (target_btn.type, target_btn.target):
                        return None, False
                    changed = button.state != expected_state
                    button.state = expected_state
                    return button.model_copy(deep=True), changed
            return None, False

        try:
            updated = await asyncio.to_thread(config_store.update, apply_state)
        except OSError:
            logger.exception("Action exécutée, mais son état n'a pas pu être sauvegardé")
            return
        if updated is not None:
            await manager.broadcast(button_state_payload(updated))


def launch_win32_target(target: str) -> bool:
    """Launch any kind of Windows target (.lnk, .exe, url, uri protocol) natively and silently."""
    ensure_default_desktop()
    t = target.strip()
    # Strip any leading 'start ""' or 'start' prefixes
    if t.lower().startswith("start "):
        t = t[6:].strip()
        if t.startswith('""'):
            t = t[2:].strip()
        elif t.startswith("''"):
            t = t[2:].strip()
    # Remove surrounding quotes
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        t = t[1:-1].strip()

    t_lower = t.lower()

    # 1. If an application window is already open, bring it to the foreground instantly!
    if "youtube music" in t_lower or "cinhimbnkkaeohfgghhklpknlkffjgod" in t_lower or "music.youtube.com" in t_lower:
        if bring_window_to_front_by_keyword("youtube music"):
            return True
    elif "spotify" in t_lower:
        if bring_window_to_front_by_keyword("spotify"):
            return True
    elif "discord" in t_lower:
        if bring_window_to_front_by_keyword("discord"):
            return True
    elif "steelseries" in t_lower:
        if bring_window_to_front_by_keyword("steelseries"):
            return True

    # 2. YouTube Music special case (Chrome PWA application)
    if "youtube music" in t_lower or "cinhimbnkkaeohfgghhklpknlkffjgod" in t_lower or "music.youtube.com" in t_lower:
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
        ]
        for cpath in chrome_paths:
            if os.path.exists(cpath):
                try:
                    subprocess.Popen([cpath, "--profile-directory=Default", "--app-id=cinhimbnkkaeohfgghhklpknlkffjgod"])
                    return True
                except Exception:
                    pass

    # 3. Standard Windows launch (files, shortcuts, URI protocols)
    try:
        os.startfile(t)
        return True
    except Exception as e:
        logger.debug(f"os.startfile a échoué pour '{t}' ({e}), essai avec ShellExecute...")
        try:
            res = ctypes.windll.shell32.ShellExecuteW(None, "open", t, None, None, 1)
            if res > 32:
                return True
        except Exception as e2:
            logger.debug(f"ShellExecuteW a échoué: {e2}")

    logger.error(f"Erreur lancement '{t}': aucune méthode Windows n'a fonctionné")
    return False


def _find_config_button(config: Optional[DeckConfig], button_id: str) -> Optional[ButtonConfig]:
    if config is None or not button_id:
        return None
    for page in config.pages:
        for button in page.buttons:
            if button.id == button_id:
                return button
    return None


def _is_app_running(name: str) -> bool:
    needle = (name or "").strip().lower()
    if not needle:
        return False
    if needle.endswith(".exe"):
        needle = needle[:-4]
    try:
        for process in psutil.process_iter(["name"]):
            pname = (process.info.get("name") or "").lower()
            if pname.endswith(".exe"):
                pname = pname[:-4]
            if pname == needle or needle in pname:
                return True
    except Exception:
        logger.debug("Application lookup failed for %s", needle, exc_info=True)
    return False


def _condition_met(step: ActionStep, config: Optional[DeckConfig] = None) -> bool:
    condition = step.condition or "always"
    target = (step.condition_target or "").strip()
    if condition == "always":
        return True
    if condition in ("button_on", "button_off"):
        # Execution reads live state for every step; explicit configs are used
        # by isolated callers. Validation separately uses the unsaved Studio config.
        button = _find_config_button(config, target) if config is not None else config_store.get_button(target)
        if button is None or not button.is_toggle:
            return False
        return bool(button.state) if condition == "button_on" else not bool(button.state)
    if condition == "app_running":
        return _is_app_running(target)
    if condition in ("mic_muted", "mic_unmuted"):
        muted = bool(audio_engine.get_system_states().get("mic_muted"))
        return muted if condition == "mic_muted" else not muted
    return True


def _execute_action(b_type: str, target: str) -> bool:
    ensure_default_desktop()
    target = target.strip()
    try:
        if b_type == "key":
            return send_win32_key(target)
        elif b_type == "hotkey":
            return send_win32_hotkey(target)
        elif b_type == "launch":
            return launch_win32_target(target)
        elif b_type == "volume_app":
            # Direct Discord RPC controls (work in the background even without focus)
            t_lower = target.lower()
            if t_lower == "discord:mute":
                if discord_rpc.is_authenticated:
                    return discord_rpc.toggle_mute() is not None
                else:
                    logger.info("Discord RPC non lié : envoi du raccourci global Discord 'ctrl,shift,m'")
                    return send_win32_hotkey("ctrl,shift,m")
            elif t_lower in ("discord:deaf", "discord:deafen"):
                if discord_rpc.is_authenticated:
                    return discord_rpc.toggle_deaf() is not None
                else:
                    logger.info("Discord RPC non lié : envoi du raccourci global Discord 'ctrl,shift,d'")
                    return send_win32_hotkey("ctrl,shift,d")
            return adjust_audio_volume(target)
        return False
    except Exception as e:
        logger.error(f"Erreur exécution action [{b_type} -> {target}]: {e}")
        return False


def _execute_sequence(steps: List[ActionStep], config: Optional[DeckConfig] = None) -> bool:
    if not steps:
        return False
    for index, step in enumerate(steps):
        if not _condition_met(step, config):
            logger.info("Step %s skipped: condition %s not met", index + 1, step.condition)
            continue
        if not _execute_action(step.type, step.target):
            return False
        if step.delay > 0 and index < len(steps) - 1:
            time.sleep(min(5.0, step.delay))
    return True


def _execute_button(button: ButtonConfig, config: Optional[DeckConfig] = None) -> bool:
    if button.type == "sequence":
        return _execute_sequence(button.steps, config)
    return _execute_action(button.type, button.target)


def _test_check(code: str, ok: bool, detail: str = "") -> Dict[str, Any]:
    return {"code": code, "ok": bool(ok), "detail": detail}


def _valid_key_token(token: str) -> bool:
    key = (token or "").strip().lower()
    return bool(key) and (key in VK_MAP or (len(key) == 1 and key.isalnum()) or key in pyautogui.KEYBOARD_KEYS)


def _clean_launch_target(target: str) -> str:
    value = (target or "").strip()
    if value.lower().startswith("start "):
        value = value[6:].strip()
        if value.startswith('""') or value.startswith("''"):
            value = value[2:].strip()
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1].strip()
    return value


def _audio_app_present(name: str) -> bool:
    needle = (name or "").strip().lower()
    if needle.startswith("app:"):
        needle = needle[4:]
    if needle.endswith(".exe"):
        needle = needle[:-4]
    if not needle:
        return False
    for app in get_audio_targets().get("apps", []):
        if (needle in (app.get("name") or "").lower()
                or needle in (app.get("process") or "").lower()
                or needle == (app.get("target") or "").lower()[4:]):
            return True
    return False


def _audio_device_present(name: str) -> bool:
    needle = (name or "").strip().lower()
    if needle.startswith("device:"):
        needle = needle[7:]
    if not needle:
        return False
    for device in get_audio_targets().get("devices", []):
        if needle in (device.get("name") or "").lower() or needle in (device.get("target") or "").lower():
            return True
    return False


def _test_audio_target(b_type: str, target: str) -> List[Dict[str, Any]]:
    value = (target or "").strip().lower()
    if not value:
        return [_test_check("action.target.required", False)]

    if b_type == "slider":
        if value in ("master", "general", "windows"):
            return [_test_check("action.audio.ready", True, target)]
        if value.startswith("app:"):
            present = _audio_app_present(value)
            return [_test_check("action.audio.ready" if present else "action.audio.inactive", present, target)]
        if value.startswith("device:"):
            present = _audio_device_present(value)
            return [_test_check("action.audio.ready" if present else "action.audio.inactive", present, target)]
        present = _audio_app_present(value)
        return [_test_check("action.audio.ready" if present else "action.audio.inactive", present, target)]

    if value in ("discord:mute", "discord:deaf", "discord:deafen", "mic:mute", "mic", "windows:mic",
                 "master:mute", "master", "windows:master"):
        return [_test_check("action.audio.ready", True, target)]

    if ":" not in value:
        return [_test_check("action.audio.action_invalid", False, target)]

    app_name, action = value.rsplit(":", 1)
    action = action.strip()
    if action != "mute" and not re.fullmatch(r"[+-]\d+(?:\.\d+)?", action):
        return [_test_check("action.audio.action_invalid", False, target)]
    if app_name.strip().lower() in ("master", "general", "windows"):
        return [_test_check("action.audio.ready", True, target)]
    present = _audio_device_present(app_name) if app_name.startswith("device:") else _audio_app_present(app_name)
    return [_test_check("action.audio.ready" if present else "action.audio.inactive", present, target)]


def _test_condition(step: ActionStep, config: Optional[DeckConfig]) -> List[Dict[str, Any]]:
    condition = step.condition or "always"
    target = (step.condition_target or "").strip()
    if condition == "always":
        return []
    if condition in ("button_on", "button_off"):
        button = _find_config_button(config, target)
        if button is None or not button.is_toggle:
            return [_test_check("action.condition.button_missing", False, target)]
        return [_test_check("action.condition.ready", True, target)]
    if condition == "app_running":
        if not target:
            return [_test_check("action.condition.app_required", False)]
        if _is_app_running(target):
            return [_test_check("action.condition.ready", True, target)]
        return [_test_check("action.condition.app_idle", True, target)]
    return [_test_check("action.condition.ready", True)]


def _test_action(b_type: str, target: str) -> List[Dict[str, Any]]:
    value = (target or "").strip()
    if b_type in ("key", "hotkey"):
        if not value:
            return [_test_check("action.target.required", False)]
        tokens = [token.strip().lower() for token in value.split(",") if token.strip()]
        invalid = [token for token in tokens if not _valid_key_token(token)]
        if not tokens or invalid:
            return [_test_check("action.hotkey.unknown" if b_type == "hotkey" else "action.key.unknown",
                                False, ", ".join(invalid) or value)]
        return [_test_check("action.hotkey.ready" if b_type == "hotkey" else "action.key.ready", True, value)]
    if b_type == "launch":
        if not value:
            return [_test_check("action.target.required", False)]
        cleaned = _clean_launch_target(value)
        if not cleaned:
            return [_test_check("action.target.required", False)]
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", cleaned) and not re.match(r"^[a-zA-Z]:[\\/]", cleaned):
            return [_test_check("action.launch.uri", True, cleaned)]
        expanded = os.path.expandvars(os.path.expanduser(cleaned))
        if os.path.exists(expanded) or shutil.which(expanded):
            return [_test_check("action.launch.ready", True, cleaned)]
        return [_test_check("action.launch.missing", False, cleaned)]
    if b_type in ("slider", "volume_app"):
        return _test_audio_target(b_type, value)
    return [_test_check("action.type.unknown", False, b_type)]


def _test_action_request(button: ButtonConfig, config: Optional[DeckConfig]) -> Dict[str, Any]:
    checks: List[Dict[str, Any]] = []
    if button.type == "sequence":
        if not button.steps:
            checks.append(_test_check("action.sequence.empty", False))
        else:
            checks.append(_test_check("action.sequence.ready", True, str(len(button.steps))))
            for index, step in enumerate(button.steps, start=1):
                condition_checks = _test_condition(step, config)
                action_checks = _test_action(step.type, step.target)
                checks.extend(condition_checks)
                checks.extend(action_checks)
                for check in condition_checks + action_checks:
                    check["step"] = index
    else:
        checks.extend(_test_action(button.type, button.target))
    if button.is_toggle:
        checks.append(_test_check("action.toggle.ready", True))
    return {"ok": all(check["ok"] for check in checks), "checks": checks}


# ============================================================================
# 8. ROUTES HTTP & API REST
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def get_index():
    if not INDEX_HTML_PATH.exists():
        raise HTTPException(status_code=404, detail="index.html introuvable")
    return HTMLResponse(content=INDEX_HTML_PATH.read_text(encoding="utf-8"))


@app.get("/admin", response_class=HTMLResponse)
async def get_admin():
    if not ADMIN_HTML_PATH.exists():
        raise HTTPException(status_code=404, detail="admin.html introuvable")
    return HTMLResponse(content=ADMIN_HTML_PATH.read_text(encoding="utf-8"))


@app.get('/manifest.webmanifest', include_in_schema=False)
async def phone_manifest():
    return JSONResponse({'id': '/', 'name': 'DeckEdge', 'short_name': 'DeckEdge',
                         'start_url': '/', 'scope': '/',
                         'display': 'standalone', 'background_color': '#191b22',
                         'theme_color': '#191b22', 'icons': [{'src': '/phone-icon.svg', 'sizes': 'any', 'type': 'image/svg+xml'}]},
                        media_type='application/manifest+json', headers={'Cache-Control': 'no-store'})


@app.get('/phone-icon.svg', include_in_schema=False)
async def phone_icon():
    return HTMLResponse('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192"><rect width="192" height="192" rx="40" fill="#242a3c"/><g fill="#91adff"><rect x="35" y="35" width="52" height="52" rx="10"/><rect x="105" y="35" width="52" height="52" rx="10"/><rect x="35" y="105" width="52" height="52" rx="10"/><rect x="105" y="105" width="52" height="52" rx="10"/></g></svg>', media_type='image/svg+xml')


@app.get("/studio-shell.css", include_in_schema=False)
async def get_studio_shell_styles():
    return FileResponse(BASE_DIR / "studio-shell.css", media_type="text/css")


@app.get("/studio-shell.js", include_in_schema=False)
async def get_studio_shell_script():
    return FileResponse(BASE_DIR / "studio-shell.js", media_type="text/javascript")


@app.get("/studio.js", include_in_schema=False)
async def get_studio_script():
    return FileResponse(BASE_DIR / "studio.js", media_type="text/javascript")


@app.get("/studio-colors.js", include_in_schema=False)
async def get_studio_colors_script():
    return FileResponse(BASE_DIR / "studio-colors.js", media_type="text/javascript")


@app.get("/i18n.js", include_in_schema=False)
async def get_i18n_script():
    return FileResponse(BASE_DIR / "i18n.js", media_type="text/javascript")


@app.get("/deck-layout.js", include_in_schema=False)
async def get_deck_layout_script():
    return FileResponse(BASE_DIR / "deck-layout.js", media_type="text/javascript")


@app.get("/deck-layout.css", include_in_schema=False)
async def get_deck_layout_styles():
    return FileResponse(BASE_DIR / "deck-layout.css", media_type="text/css")


@app.get("/api/config", response_model=DeckConfig)
async def get_config_endpoint():
    return await asyncio.to_thread(config_store.load)


@app.post("/api/config")
async def save_config_endpoint(config: DeckConfig):
    """Receive the new config, validate it via Pydantic, save it and notify."""
    try:
        await asyncio.to_thread(config_store.save, config)
        await manager.broadcast({"type": "reload_config"})
        return {"status": "ok", "pages_count": len(config.pages)}
    except Exception as e:
        logger.error(f"Échec enregistrement configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class BackupNamePayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


@app.post("/api/config/validate")
async def validate_config_endpoint(config: DeckConfig):
    """Validate and normalize an imported profile without saving it."""
    return {"status": "ok", "config": config.model_dump(mode="json")}


class ActionTestPayload(BaseModel):
    button: ButtonConfig
    config: Optional[DeckConfig] = None


@app.post("/api/actions/test")
async def test_action_endpoint(payload: ActionTestPayload):
    """Validate an action and its targets without executing it."""
    config = payload.config or await asyncio.to_thread(config_store.load)
    return await asyncio.to_thread(_test_action_request, payload.button, config)


class PhoneRenamePayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=40)


@app.get("/api/phones")
async def list_phones_endpoint():
    return {"phones": phones.list()}


@app.delete("/api/phones/{phone_id}")
async def revoke_phone_endpoint(phone_id: str, request: Request):
    global PHONE_KEY
    if not phones.revoke(phone_id):
        raise HTTPException(status_code=404, detail=server_text(request_language(request), "phone_missing"))
    PHONE_KEY = rotate_pairing_key()
    closed = await manager.disconnect_device(phone_id)
    logger.info("Phone %s revoked; pairing link renewed; %s session(s) closed", phone_id, closed)
    return {"status": "ok", "closed_sessions": closed, "pairing_key_rotated": True}


@app.patch("/api/phones/{phone_id}")
async def rename_phone_endpoint(phone_id: str, payload: PhoneRenamePayload, request: Request):
    if not phones.rename(phone_id, payload.name):
        raise HTTPException(status_code=404, detail=server_text(request_language(request), "phone_missing"))
    return {"status": "ok"}


@app.post("/api/phones/revoke-all")
async def revoke_all_phones_endpoint():
    global PHONE_KEY
    revoked = phones.revoke_all()
    PHONE_KEY = rotate_pairing_key()
    closed = await manager.disconnect_phones()
    logger.info("All phones revoked (%s); pairing link renewed; %s session(s) closed", revoked, closed)
    return {"status": "ok", "revoked": revoked, "closed_sessions": closed, "pairing_key_rotated": True}


@app.get("/api/config/backups")
async def list_config_backups():
    return {"backups": await asyncio.to_thread(config_store.list_backups)}


@app.post("/api/config/backups")
async def create_config_backup_endpoint():
    try:
        backup = await asyncio.to_thread(config_store.create_backup)
    except Exception as e:
        logger.exception("Création de sauvegarde impossible")
        raise HTTPException(status_code=500, detail=str(e))
    return {
        "status": "ok",
        "backup": backup,
        "backups": await asyncio.to_thread(config_store.list_backups),
    }


@app.post("/api/config/restore")
async def restore_config_backup_endpoint(payload: BackupNamePayload, request: Request):
    language = request_language(request)
    try:
        config = await asyncio.to_thread(config_store.restore_backup, payload.name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=server_text(language, "backup_missing"))
    except (json.JSONDecodeError, ValidationError):
        raise HTTPException(status_code=400, detail=server_text(language, "backup_invalid"))
    except Exception as e:
        logger.exception("Restauration de sauvegarde impossible")
        raise HTTPException(status_code=500, detail=str(e))
    await manager.broadcast({"type": "reload_config"})
    return {"status": "ok", "config": config.model_dump(mode="json")}


@app.get("/api/audio/sessions")
async def get_audio_sessions():
    """Return the list of active Windows applications that are producing sound."""
    sessions = await asyncio.to_thread(get_audio_sessions_list)
    return {"sessions": sessions}


@app.get("/api/audio/targets")
async def get_audio_targets_endpoint():
    """Return the full tree of output devices and apps with their volumes."""
    targets = await asyncio.to_thread(get_audio_targets)
    return targets


class VolumeSetPayload(BaseModel):
    target: str
    value: int


@app.post("/api/audio/volume")
async def set_volume_endpoint(payload: VolumeSetPayload):
    """Set the absolute volume (0-100) for a slider."""
    ok = await asyncio.to_thread(set_audio_target_volume, payload.target, payload.value)
    if ok:
        await manager.broadcast({
            "type": "volume_update",
            "target": payload.target,
            "value": payload.value
        })
    return {"status": "ok" if ok else "not_found"}


_apps_cache: List[Dict[str, Any]] = []
_apps_cache_time: float = 0.0

def get_installed_apps_and_games() -> List[Dict[str, Any]]:
    """Scan Steam games, Start menu shortcuts and Windows system utilities."""
    global _apps_cache, _apps_cache_time
    now = time.time()
    if _apps_cache and (now - _apps_cache_time) < 30.0:
        return _apps_cache

    items: List[Dict[str, Any]] = []
    seen_names = set()

    # 1. Installed Steam games
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
            sp = Path(winreg.QueryValueEx(key, "SteamPath")[0]) / "steamapps"
            if sp.exists():
                for f in sp.glob("appmanifest_*.acf"):
                    try:
                        lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
                        gname, appid = "", ""
                        for l in lines:
                            if '"name"' in l and not gname:
                                parts = l.split('"name"')
                                if len(parts) > 1 and '"' in parts[1]:
                                    gname = parts[1].split('"')[1]
                            if '"appid"' in l and not appid:
                                parts = l.split('"appid"')
                                if len(parts) > 1 and '"' in parts[1]:
                                    appid = parts[1].split('"')[1]
                        if gname and appid and gname.lower() not in seen_names:
                            seen_names.add(gname.lower())
                            items.append({
                                "name": gname,
                                "target": f"start steam://run/{appid}",
                                "type": "launch",
                                "icon": "🎮",
                                "color": "#171a21",
                                "category": "Jeux"
                            })
                    except Exception:
                        pass
    except Exception as e:
        logger.debug(f"Erreur scan Steam: {e}")

    # 2. Start menu applications (shortcuts, .lnk)
    start_dirs = [
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    ]
    for sdir in start_dirs:
        if sdir.exists():
            for p in sdir.rglob("*.lnk"):
                nm = p.stem.strip()
                if not nm or nm.lower() in seen_names:
                    continue
                if any(x in nm.lower() for x in ["uninstall", "desinstall", "aide", "help", "readme", "documentation", "update", "dsinstall"]):
                    continue
                seen_names.add(nm.lower())

                icon = "⚡"
                col = "#161c2e"
                nl = nm.lower()
                if "discord" in nl: icon, col, target = "💬", "#5865f2", "start discord:"
                elif "spotify" in nl: icon, col, target = "🎵", "#1db954", "start spotify:"
                elif "youtube music" in nl: icon, col, target = "🎧", "#ff0000", str(p)
                elif "youtube" in nl: icon, col, target = "▶️", "#ff0000", str(p)
                elif "steam" in nl: icon, col, target = "🎮", "#171a21", "start steam://"
                elif any(b in nl for b in ["chrome", "brave", "edge", "firefox"]): icon, col, target = "🌐", "#eab308", str(p)
                elif "obs" in nl: icon, col, target = "🔴", "#991b1b", str(p)
                elif any(g in nl for g in ["game", "play", "riot", "battle.net"]): icon, col, target = "🎮", "#f97316", str(p)
                elif "calc" in nl: icon, col, target = "🧮", "#161c2e", "calc.exe"
                else: target = str(p)

                items.append({
                    "name": nm,
                    "target": target,
                    "type": "launch",
                    "icon": icon,
                    "color": col,
                    "category": "Applications"
                })

    # 3. Essential system tools & popular web shortcuts
    system_tools = [
        { "name": "YouTube Music (Web)", "target": "https://music.youtube.com", "type": "launch", "icon": "🎧", "color": "#ff0000", "category": "Applications" },
        { "name": "Calculatrice", "target": "calc.exe", "type": "launch", "icon": "🧮", "color": "#161c2e", "category": "Système" },
        { "name": "Gestionnaire des tâches", "target": "taskmgr.exe", "type": "launch", "icon": "📊", "color": "#161c2e", "category": "Système" },
        { "name": "Explorateur de fichiers", "target": "explorer.exe", "type": "launch", "icon": "📁", "color": "#161c2e", "category": "Système" },
        { "name": "Barre de jeu Xbox", "target": "start ms-gamebar:", "type": "launch", "icon": "🎯", "color": "#107c10", "category": "Système" },
        { "name": "Paramètres Windows", "target": "start ms-settings:", "type": "launch", "icon": "⚙️", "color": "#161c2e", "category": "Système" },
        { "name": "Bloc-notes", "target": "notepad.exe", "type": "launch", "icon": "📝", "color": "#161c2e", "category": "Système" },
        { "name": "Capture d'écran (Win+Shift+S)", "target": "win,shift,s", "type": "hotkey", "icon": "📸", "color": "#161c2e", "category": "Système" },
        { "name": "Afficher le Bureau (Win+D)", "target": "win,d", "type": "hotkey", "icon": "🖥️", "color": "#1e3a8a", "category": "Système" },
    ]
    for st in system_tools:
        if st["name"].lower() not in seen_names:
            seen_names.add(st["name"].lower())
            items.append(st)

    _apps_cache = sorted(items, key=lambda x: (0 if x["category"] == "Jeux" else (1 if x["category"] == "Applications" else 2), x["name"].lower()))
    _apps_cache_time = now
    return _apps_cache


@app.get("/api/apps")
async def get_apps_endpoint():
    """Return the list of Steam games, Start menu applications and system tools."""
    apps = await asyncio.to_thread(get_installed_apps_and_games)
    return {"apps": apps}


@app.get("/api/monitoring/sensors")
async def get_monitoring_sensors():
    return telemetry.catalog()


@app.get("/api/diagnostics", include_in_schema=False)
async def get_diagnostics(request: Request):
    """Local support report; paths and secrets are masked."""
    config = await asyncio.to_thread(config_store.load)
    try:
        audio = await asyncio.to_thread(get_audio_targets)
    except Exception:
        logger.exception("Diagnostic audio indisponible")
        audio = {"devices": [], "apps": []}

    devices = [{
        "name": _redact_text(device.get("name")),
        "target": _redact_text(device.get("target")),
        "volume": device.get("volume"),
        "muted": device.get("muted"),
    } for device in (audio.get("devices") or [])]
    apps = [{
        "name": _redact_text(app.get("name")),
        "target": _redact_text(app.get("target")),
        "volume": app.get("volume"),
        "muted": app.get("muted"),
        "outputs": [_redact_text(output) for output in (app.get("outputs") or [])],
        "sessions": app.get("sessions", 0),
    } for app in (audio.get("apps") or [])]

    config_file = {"exists": CONFIG_PATH.exists()}
    try:
        stat = CONFIG_PATH.stat()
        config_file.update({
            "size": stat.st_size,
            "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
        })
    except OSError:
        pass

    status = discord_rpc.get_status()
    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "app": {
            "name": "DeckEdge",
            "version": _app_version(),
            "data_dir": _redact_text(DATA_DIR),
            "config_file": config_file,
            "config_backup": CONFIG_BAK_PATH.exists(),
            "pages": len(config.pages),
            "buttons": sum(len(page.buttons) for page in config.pages),
            "monitoring_widgets": len(config.monitoring),
        },
        "system": {
            "platform": _redact_text(platform.platform()),
            "python": platform.python_version(),
            "executable": _redact_text(sys.executable),
        },
        "network": {
            "hostname": HOSTNAME,
            "port": request.url.port or PORT,
            "discovery_available": discovery.available,
            "clients_connected": manager.client_count,
            "phones_paired": phones.count(),
            "phone_key_present": (DATA_DIR / ".phone-key").exists(),
        },
        "audio": {
            "devices": devices,
            "apps": apps,
        },
        "monitoring": {
            "connected": telemetry.is_connected,
            "elevated": telemetry.elevated,
            "sensors_count": len(telemetry.sensors),
            "last_poll": telemetry.last_poll_timestamp,
            "metrics": telemetry.last_metrics,
            "widgets": [{
                "label": _redact_text(widget.label),
                "sensor_id": widget.sensor_id,
                "secondary_sensor_id": widget.secondary_sensor_id,
            } for widget in config.monitoring],
        },
        "discord": {
            key: status.get(key)
            for key in ("has_config", "is_connected", "is_authenticated", "mute", "deaf", "user")
        },
        "logs": {
            "deckedge": _tail(DATA_DIR / "deckedge.log"),
            "desktop": _tail(DATA_DIR / "desktop.log"),
        },
    }
    return JSONResponse(report, headers={"Cache-Control": "no-store"})


@app.get("/api/health")
async def healthcheck():
    """Full health check."""
    config = await asyncio.to_thread(config_store.load)
    return {
        "app": "DeckEdge",
        "status": "healthy",
        "timestamp": time.time(),
        "clients_connected": manager.client_count,
        "phones_paired": phones.count(),
        "phone": {"hostname": HOSTNAME, "discovery_available": discovery.available},
        "pages_count": len(config.pages),
        "discord": discord_rpc.get_status(),
        "monitoring": {
            "source": "integrated",
            "elevated": telemetry.elevated,
            "sensors_count": len(telemetry.sensors),
            "connected": telemetry.is_connected,
            "last_poll": telemetry.last_poll_timestamp,
            "metrics": telemetry.last_metrics,
        }
    }


# --- DISCORD RPC INTEGRATION ROUTES ---

class DiscordConnectPayload(BaseModel):
    client_id: str
    client_secret: str


@app.get("/api/discord/status")
async def get_discord_status_endpoint():
    """Return the current Discord RPC link state and voice state (Mute / Deafen)."""
    return discord_rpc.get_status()


@app.post("/api/discord/connect")
async def connect_discord_endpoint(payload: DiscordConnectPayload):
    """
    Start the native authorization flow in Discord on the PC,
    retrieve the code from the named pipe and exchange it for an OAuth2 token.
    """
    res = await asyncio.to_thread(discord_rpc.authorize_flow, payload.client_id, payload.client_secret)
    return res


@app.post("/api/discord/disconnect")
async def disconnect_discord_endpoint():
    """Disconnect and delete the stored Discord keys."""
    discord_rpc.client_id = ""
    discord_rpc.client_secret = ""
    discord_rpc.access_token = ""
    discord_rpc.refresh_token = ""
    discord_rpc.user_info = {}
    discord_rpc.save_config()
    discord_rpc._close_pipe()
    return {"success": True, "message": "Compte Discord déconnecté avec succès."}


@app.post("/api/discord/toggle-mute")
async def toggle_discord_mute_endpoint():
    """Toggle the Discord microphone directly without focus."""
    res = await asyncio.to_thread(discord_rpc.toggle_mute)
    return {"success": res is not None, "mute": discord_rpc.mute}


@app.post("/api/discord/toggle-deaf")
async def toggle_discord_deaf_endpoint():
    """Toggle Discord deafen directly without focus."""
    res = await asyncio.to_thread(discord_rpc.toggle_deaf)
    return {"success": res is not None, "deaf": discord_rpc.deaf}


# ============================================================================
# 9. WEBSOCKET ENDPOINT
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    local = is_local(websocket.client.host) if websocket.client else False
    ip = websocket.client.host if websocket.client else ""
    device = None if local else phones.authenticate(websocket.cookies.get(COOKIE, ""), ip)
    legacy = (not local and device is None and _matches_master_key(websocket.cookies.get(COOKIE, "")))
    if not allowed_origin(websocket) or (not local and device is None and not legacy):
        await websocket.close(code=1008)
        return
    await manager.connect(websocket, device["id"] if device else None)

    # On client connection, send the initial state of the audio devices/apps and buttons
    try:
        targets_init = await asyncio.to_thread(get_audio_targets)
        await websocket.send_json({"type": "audio_targets", "data": targets_init})

        cfg = await asyncio.to_thread(config_store.load)
        states_init = {b.id: b.state for p in cfg.pages for b in p.buttons if b.is_toggle}
        if discord_rpc.is_authenticated:
            for p in cfg.pages:
                for b in p.buttons:
                    if b.is_toggle:
                        if b.target == "discord:mute":
                            states_init[b.id] = discord_rpc.mute
                        elif b.target in ("discord:deaf", "discord:deafen"):
                            states_init[b.id] = discord_rpc.deaf
        await websocket.send_json({"type": "all_button_states", "data": states_init})
        await websocket.send_json({"type": "discord_status", "data": discord_rpc.get_status()})
        await websocket.send_json(telemetry.payload(cfg.monitoring))
    except Exception as e:
        logger.debug(f"Erreur envoi init data: {e}")

    click_window_start = time.monotonic()
    click_count = 0

    def allow_button_click() -> bool:
        nonlocal click_window_start, click_count
        now = time.monotonic()
        if now - click_window_start >= 1.0:
            click_window_start = now
            click_count = 0
        if click_count >= MAX_BUTTON_CLICKS_PER_SECOND:
            return False
        click_count += 1
        return True

    try:
        while True:
            raw_msg = await websocket.receive_text()
            if not raw_msg or len(raw_msg) > MAX_WS_MESSAGE_BYTES:
                continue

            # Accept either a JSON object {action: "set_volume" / "toggle_mute" / "click"} or a raw button ID ("b1")
            if raw_msg.startswith("{"):
                try:
                    parsed = json.loads(raw_msg)
                except (TypeError, ValueError) as e:
                    logger.debug(f"Erreur parsing WS payload: {e}")
                    continue
                if not isinstance(parsed, dict):
                    continue

                action = parsed.get("action")

                # 1. Slider: real-time volume adjustment (immediate and coalesced)
                if action == "set_volume":
                    target = parsed.get("target")
                    if not isinstance(target, str) or not target.strip() or len(target) > 256:
                        continue
                    target = target.strip()
                    try:
                        val = int(parsed.get("value", 50))
                    except (TypeError, ValueError):
                        continue
                    val = max(0, min(100, val))
                    set_audio_target_volume(target, val)
                    # Broadcast to the OTHER clients to synchronize (avoids any echo/stutter on the phone doing the drag)
                    await manager.broadcast({
                        "type": "volume_update",
                        "target": target,
                        "value": val
                    }, exclude_ws=websocket)
                    continue

                # 2. Slider: Mute toggle
                if action == "toggle_mute":
                    target = parsed.get("target")
                    if not isinstance(target, str) or not target.strip() or len(target) > 256:
                        continue
                    target = target.strip()
                    new_mute = await asyncio.to_thread(toggle_audio_target_mute, target)
                    await manager.broadcast({
                        "type": "mute_update",
                        "target": target,
                        "muted": new_mute
                    }, exclude_ws=websocket)
                    continue

                # 3. Button click via JSON
                btn_id = parsed.get("btn_id")
                if isinstance(btn_id, str) and _IDENTIFIER_PATTERN.fullmatch(btn_id) and allow_button_click():
                    _spawn_button_click(btn_id)
                continue

            # Handle a button click sent as plain text
            btn_id = raw_msg.strip()
            if _IDENTIFIER_PATTERN.fullmatch(btn_id) and allow_button_click():
                _spawn_button_click(btn_id)
    except (WebSocketDisconnect, ConnectionResetError):
        pass
    except Exception as e:
        logger.debug(f"Exception WebSocket: {e}")
    finally:
        await manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=PORT, reload=False, proxy_headers=False)
