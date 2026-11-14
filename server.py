"""
DeckEdge - Backend FastAPI & Orchestrateur WebSocket
Architecture sécurisée avec validation Pydantic v2 :
- Support Multi-Pages / Profils (Gaming, Stream, Desktop, Musique)
- Contrôle de volume par application spécifique Windows via pycaw (Discord, Spotify, Master...)
- Boutons à bascule (Toggle state) avec retour d'état visuel en temps réel
- Télémétrie LHM asynchrone et persistance atomique
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import ctypes
from ctypes import wintypes
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import time
import weakref
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, TypeVar
import sys
from monitoring import MonitoringState, DEFAULT_WIDGETS
from audio_sessions import collect_application_volumes

# Redirection obligatoire sous pythonw.exe
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import comtypes
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
import pyautogui
from pydantic import BaseModel, Field, ValidationError, model_validator
from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume, IAudioSessionControl2
from pycaw.utils import AudioSession
from discord_rpc import discord_rpc
from app_paths import DATA_DIR
from network_access import COOKIE, pairing_key, is_local, allowed_origin, is_paired
from local_discovery import discovery, HOSTNAME

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("DeckEdge")

# Chemins absolus
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = DATA_DIR / "config.json"
CONFIG_BAK_PATH = DATA_DIR / "config.json.bak"
INDEX_HTML_PATH = BASE_DIR / "index.html"
ADMIN_HTML_PATH = BASE_DIR / "admin.html"

MONITORING_POLL_INTERVAL_SEC = 1.0
MAX_WS_MESSAGE_BYTES = 8192
MAX_BUTTON_CLICKS_PER_SECOND = 30

pyautogui.FAILSAFE = False


# ============================================================================
# 1. MODÈLES DE VALIDATION (Pydantic v2)
# ============================================================================

ActionType = Literal["hotkey", "key", "launch", "volume_app", "slider"]

_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


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
    width: Literal["auto", "quarter", "third", "half", "full"] = "auto"
    height: Literal["compact", "normal", "tall"] = "normal"
    color: Optional[str] = Field(
        default="#161c2e",
        pattern=r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$",
        description="Couleur hexadécimale de fond (état inactif)"
    )
    # Bouton à bascule (Toggle)
    is_toggle: bool = Field(default=False, description="Activer le mode bascule ON/OFF")
    state: bool = Field(default=False, description="État actif (True) ou inactif (False)")
    active_label: Optional[str] = Field(default="", max_length=50, description="Libellé affiché si actif")
    active_icon: Optional[str] = Field(default="", max_length=10, description="Icône si actif")
    active_color: Optional[str] = Field(
        default="#991b1b",
        pattern=r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$",
        description="Couleur hexadécimale de fond si actif"
    )

class PageConfig(BaseModel):
    id: str = Field(..., min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$", description="Identifiant unique de la page")
    name: str = Field(..., min_length=1, max_length=50, description="Nom affiché de la page")
    icon: str = Field(default="📄", max_length=10, description="Icône de l'onglet")
    buttons: List[ButtonConfig] = Field(default_factory=list, max_length=500, description="Liste ordonnée des boutons")

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

        # Rétrocompatibilité : migration transparente depuis l'ancienne structure {"buttons": [...]}
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

        data["pages"] = normalized_pages

        # Principal est le profil d'ouverture ; la navigation reste locale aux interfaces.
        active_page_id = data.get("active_page_id")
        if isinstance(active_page_id, str):
            active_page_id = page_id_map.get(active_page_id, active_page_id)
        if "page_main" in page_ids:
            data["active_page_id"] = "page_main"
        elif active_page_id not in page_ids:
            data["active_page_id"] = page_ids[0] if page_ids else "page_main"
        else:
            data["active_page_id"] = active_page_id

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
# 2. PERSISTANCE SÉRIALISÉE ET ATOMIQUE DE LA CONFIGURATION
# ============================================================================

T = TypeVar("T")


def _write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    """Écrit un JSON complet puis remplace le fichier, avec un temporaire unique."""
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
    """Source de vérité unique : lectures, mutations et écritures sérialisées.

    Toutes les mutations passent par ``update`` afin qu'une sauvegarde lente ne
    puisse pas écraser une modification faite entre-temps. Les écritures utilisent
    un fichier temporaire unique et le backup représente toujours la configuration
    précédemment validée, jamais un fichier corrompu.
    """

    def __init__(self, path: Path = CONFIG_PATH, backup_path: Path = CONFIG_BAK_PATH) -> None:
        self.path = path
        self.backup_path = backup_path
        self._lock = threading.RLock()
        self._config: Optional[DeckConfig] = None
        self._mtime_ns: Optional[int] = None

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
            self._mtime_ns = self._read_mtime()
        else:
            mtime = self._read_mtime()
            if mtime is not None and mtime != self._mtime_ns:
                self._config = self._load_from_disk()
                self._mtime_ns = mtime
        return self._config.model_copy(deep=True)

    def _write_locked(self, config: DeckConfig, keep_backup: bool = True) -> None:
        previous = self._config
        if keep_backup and previous is not None:
            try:
                _write_json_atomic(self.backup_path, previous.model_dump(mode="json"))
            except Exception as e:
                logger.warning("Impossible de créer config.json.bak: %s", e)

        _write_json_atomic(self.path, config.model_dump(mode="json"))
        self._config = config.model_copy(deep=True)
        self._mtime_ns = self._read_mtime()
        logger.info("Configuration persistée de manière atomique.")

    def load(self) -> DeckConfig:
        """Retourne une copie isolée de la configuration courante."""
        with self._lock:
            return self._read_locked()

    def save(self, config: DeckConfig) -> None:
        """Remplace la configuration de façon atomique et sérialisée."""
        with self._lock:
            self._write_locked(config)

    def update(self, mutator: Callable[[DeckConfig], Tuple[T, bool]]) -> T:
        """Applique une mutation atomique ; n'écrit que si ``dirty`` est vrai."""
        with self._lock:
            config = self._read_locked()
            result, dirty = mutator(config)
            if dirty:
                self._write_locked(config)
            return result

    def get_button(self, btn_id: str) -> Optional[ButtonConfig]:
        with self._lock:
            config = self._read_locked()
            for page in config.pages:
                for button in page.buttons:
                    if button.id == btn_id:
                        return button.model_copy(deep=True)
        return None


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
# 3. MOTEUR AUDIO CENTRALISÉ ET HAUTE PERFORMANCE (pycaw / WASAPI)
# ============================================================================

from pycaw.constants import AudioDeviceState, EDataFlow
import queue

class AudioEngine(threading.Thread):
    """
    Thread dédié Windows COM pour toutes les opérations audio.
    - Évite la création/destruction perpétuelle d'appartements COM.
    - Cache les périphériques et sessions audio pour des temps de réponse < 0.2ms.
    - Coalescence des mises à jour de volume pour éliminer tout lag / saccade lors du glissement tactile.
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
                # 1. Traitement coalescent et instantané des volumes en attente
                pending = {}
                with self._lock:
                    if self._pending_volumes:
                        pending = dict(self._pending_volumes)
                        self._pending_volumes.clear()

                for target, pct in pending.items():
                    self._apply_volume(target, pct)

                # 2. Commandes synchrones
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

        # Périphérique spécifique
        if t.startswith("device:"):
            device = self._resolve_device(t[7:].strip().lower())
            if device is not None:
                try:
                    device.EndpointVolume.SetMasterVolumeLevelScalar(val, None)
                except Exception as e:
                    logger.debug(f"Erreur set device volume: {e}")
            return

        # Application (une cible vide ne doit jamais toucher la première session)
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

        # Microphone matériel Windows
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

        # Périphérique spécifique
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
        """Coalescence ultra-rapide non-bloquante (0ms)."""
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
# 4. GESTIONNAIRE DE CONNEXIONS WEBSOCKET RÉSISTANT
# ============================================================================

class ConnectionManager:
    """Gère le cycle de vie des WebSockets et élimine silencieusement les sockets fantômes."""

    def __init__(self) -> None:
        self._active: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._active.add(ws)
        logger.info(f"Nouveau client connecté. Total: {len(self._active)}")

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._active.discard(ws)
        logger.info(f"Client déconnecté. Total: {len(self._active)}")

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
# 5. SERVICE CENTRALISÉ DE TÉLÉMÉTRIE HARDWARE (LHM)
# ============================================================================

class LHMTelemetryService(MonitoringState):
    """Diffuse les mesures reçues du moteur LHM intégré à DeckEdge."""

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

                # Synchronisation automatique de l'état matériel (Micro Windows, Master, Discord...)
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
# 6. CYCLE DE VIE DE L'APPLICATION (FastAPI Lifespan)
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


app = FastAPI(title="DeckEdge Server", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
PHONE_KEY = pairing_key()


@app.middleware("http")
async def protect_desktop_and_pair_phone(request: Request, call_next):
    local = is_local(request.client.host) if request.client else False
    if not allowed_origin(request):
        return JSONResponse({"detail": "Origine non autorisée"}, status_code=403)
    if not local and not is_paired(request, PHONE_KEY):
        return HTMLResponse('''<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Connecter DeckEdge</title><body style="margin:0;background:#191b22;color:#eef1fc;font:17px/1.65 system-ui;padding:28px"><main style="max-width:480px;margin:12vh auto"><h1>Retrouver votre Deck</h1><p>Cette adresse n’est pas encore associée à votre téléphone.</p><ol><li>Sur le PC, ouvrez DeckEdge.</li><li>Cliquez sur <b>Connecter le téléphone</b>.</li><li>Scannez le QR code avec l’appareil photo.</li></ol><p>Ajoutez ensuite le Deck à votre écran d’accueil pour le retrouver aux prochains démarrages.</p></main></body></html>''', status_code=401)
    desktop_only = request.url.path in {"/admin", "/api/apps", "/api/monitoring/sensors", "/api/discord/connect", "/api/discord/disconnect"} or (request.url.path == "/api/config" and request.method != "GET")
    if desktop_only and not local:
        return JSONResponse({"detail": "Ce réglage se modifie dans le Studio sur le PC."}, status_code=403)
    response = await call_next(request)
    if not local and request.query_params.get("key"):
        response.set_cookie(COOKIE, PHONE_KEY, httponly=True, samesite="strict", max_age=31536000)
    if request.url.path in ('/', '/manifest.webmanifest'):
        response.headers['Cache-Control'] = 'no-store'
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
    return response


# ============================================================================
# 7. ÉMULATION DE TOUCHES WIN32 NATIVE & EXÉCUTION D'ACTIONS
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
    """Garantit que le thread actif est attaché au bureau interactif Default de Windows."""
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
    """Envoie une touche simple avec scan code et drapeaux étendus natifs."""
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
    """Envoie une combinaison de touches native (ex: 'win,d', 'ctrl,shift,m')."""
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

    # Appui ordonné avec scan codes et drapeaux étendus
    for vk in vks:
        _press_vk(vk, True)
    time.sleep(0.03)
    # Relâchement en ordre inverse
    for vk in reversed(vks):
        _press_vk(vk, False)
    return True

def force_foreground_window(hwnd: int) -> bool:
    """Restaure et force une fenêtre au premier plan en contournant le verrouillage de focus Windows."""
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
    """Recherche une fenêtre visible correspondant au mot-clé et l'amène au premier plan."""
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
        await asyncio.to_thread(_execute_action, target_btn.type, target_btn.target)
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
    """Lance tout type de cible Windows (.lnk, .exe, url, protocole uri) de façon native et silencieuse."""
    ensure_default_desktop()
    t = target.strip()
    # Nettoyer d'éventuels préfixes 'start ""' ou 'start'
    if t.lower().startswith("start "):
        t = t[6:].strip()
        if t.startswith('""'):
            t = t[2:].strip()
        elif t.startswith("''"):
            t = t[2:].strip()
    # Supprimer les guillemets englobants
    if (t.startswith('"') and t.endswith('"')) or (t.startswith("'") and t.endswith("'")):
        t = t[1:-1].strip()

    t_lower = t.lower()

    # 1. Si une fenêtre de l'application est déjà ouverte, l'amener instantanément au premier plan !
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

    # 2. Cas spécifique YouTube Music (Application PWA Chrome)
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

    # 3. Lancement standard Windows (fichiers, raccourcis, protocoles URI)
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
            # Contrôles directs Discord RPC (fonctionne en tâche de fond même sans focus)
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
                         'start_url': '/?key=' + PHONE_KEY, 'scope': '/',
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
    """Reçoit la nouvelle config, valide via Pydantic, sauvegarde et notifie."""
    try:
        await asyncio.to_thread(config_store.save, config)
        await manager.broadcast({"type": "reload_config"})
        return {"status": "ok", "pages_count": len(config.pages)}
    except Exception as e:
        logger.error(f"Échec enregistrement configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/audio/sessions")
async def get_audio_sessions():
    """Retourne la liste des applications Windows actives ayant du son."""
    sessions = await asyncio.to_thread(get_audio_sessions_list)
    return {"sessions": sessions}


@app.get("/api/audio/targets")
async def get_audio_targets_endpoint():
    """Retourne l'arborescence complète des périphériques de sortie et apps avec leurs volumes."""
    targets = await asyncio.to_thread(get_audio_targets)
    return targets


class VolumeSetPayload(BaseModel):
    target: str
    value: int


@app.post("/api/audio/volume")
async def set_volume_endpoint(payload: VolumeSetPayload):
    """Règle le volume absolu (0-100) pour un slider."""
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
    """Scanne les jeux Steam, raccourcis du menu Démarrer et utilitaires Windows."""
    global _apps_cache, _apps_cache_time
    now = time.time()
    if _apps_cache and (now - _apps_cache_time) < 30.0:
        return _apps_cache

    items: List[Dict[str, Any]] = []
    seen_names = set()

    # 1. Jeux Steam installés
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

    # 2. Applications du menu Démarrer (Raccourcis .lnk)
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

    # 3. Outils Système essentiels & Raccourcis Web populaires
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
    """Retourne la liste des jeux Steam, applications du menu Démarrer et outils système."""
    apps = await asyncio.to_thread(get_installed_apps_and_games)
    return {"apps": apps}


@app.get("/api/monitoring/sensors")
async def get_monitoring_sensors():
    return telemetry.catalog()


@app.get("/api/health")
async def healthcheck():
    """Healthcheck complet."""
    config = await asyncio.to_thread(config_store.load)
    return {
        "app": "DeckEdge",
        "status": "healthy",
        "timestamp": time.time(),
        "clients_connected": manager.client_count,
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


# --- ROUTES DISCORD RPC INTÉGRATION ---

class DiscordConnectPayload(BaseModel):
    client_id: str
    client_secret: str


@app.get("/api/discord/status")
async def get_discord_status_endpoint():
    """Retourne l'état actuel de la liaison Discord RPC et de la voix (Mute / Sourdine)."""
    return discord_rpc.get_status()


@app.post("/api/discord/connect")
async def connect_discord_endpoint(payload: DiscordConnectPayload):
    """
    Lance le flux d'autorisation native dans Discord sur le PC,
    récupère le code sur le named pipe et échange le jeton OAuth2.
    """
    res = await asyncio.to_thread(discord_rpc.authorize_flow, payload.client_id, payload.client_secret)
    return res


@app.post("/api/discord/disconnect")
async def disconnect_discord_endpoint():
    """Déconnecte et supprime les clés Discord enregistrées."""
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
    """Bascule le micro Discord directement sans focus."""
    res = await asyncio.to_thread(discord_rpc.toggle_mute)
    return {"success": res is not None, "mute": discord_rpc.mute}


@app.post("/api/discord/toggle-deaf")
async def toggle_discord_deaf_endpoint():
    """Bascule la sourdine Discord directement sans focus."""
    res = await asyncio.to_thread(discord_rpc.toggle_deaf)
    return {"success": res is not None, "deaf": discord_rpc.deaf}


# ============================================================================
# 9. WEBSOCKET ENDPOINT
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    local = is_local(websocket.client.host) if websocket.client else False
    if not allowed_origin(websocket) or (not local and not is_paired(websocket, PHONE_KEY)):
        await websocket.close(code=1008)
        return
    await manager.connect(websocket)

    # À la connexion d'un client, lui transmettre l'état initial des périphériques/apps audio et des boutons
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

            # Support soit d'un objet JSON {action: "set_volume" / "toggle_mute" / "click"}, soit d'un ID de bouton brut ("b1")
            if raw_msg.startswith("{"):
                try:
                    parsed = json.loads(raw_msg)
                except (TypeError, ValueError) as e:
                    logger.debug(f"Erreur parsing WS payload: {e}")
                    continue
                if not isinstance(parsed, dict):
                    continue

                action = parsed.get("action")

                # 1. Slider : réglage en temps réel du volume (instantané et coalescé)
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
                    # Diffusion aux AUTRES clients pour synchroniser (évite tout écho/saccade sur le téléphone qui manipule)
                    await manager.broadcast({
                        "type": "volume_update",
                        "target": target,
                        "value": val
                    }, exclude_ws=websocket)
                    continue

                # 2. Slider : bascule Mute
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

                # 3. Clic bouton via JSON
                btn_id = parsed.get("btn_id")
                if isinstance(btn_id, str) and _IDENTIFIER_PATTERN.fullmatch(btn_id) and allow_button_click():
                    _spawn_button_click(btn_id)
                continue

            # Traitement d'un clic bouton envoyé sous forme de texte brut
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
    uvicorn.run("server:app", host="0.0.0.0", port=5000, reload=False, proxy_headers=False)
