"""
Service Discord RPC pour DeckEdge.
Permet de contrôler le micro (Mute) et la sourdine (Deafen) de Discord en arrière-plan
via le Named Pipe local (\\\\.\\pipe\\discord-ipc-0), même lorsque Discord n'est pas au premier plan.
Architecture threadée avec lecteur dédié asynchrone non-bloquant (PeekNamedPipe) et zéro deadlock.
"""

import ctypes
from ctypes import wintypes
import json
import logging
import msvcrt
from pathlib import Path
import struct
import threading
import time
from typing import Any, Callable, Dict, Optional, Tuple
import uuid

import httpx
from app_paths import DATA_DIR

logger = logging.getLogger("DiscordRPC")
kernel32 = ctypes.windll.kernel32

BASE_DIR = Path(__file__).resolve().parent
DISCORD_CONFIG_FILE = DATA_DIR / "discord_config.json"
OAUTH_TOKEN_URL = "https://discord.com/api/oauth2/token"


class DiscordRPCService:
    def __init__(self) -> None:
        self.client_id: str = ""
        self.client_secret: str = ""
        self.access_token: str = ""
        self.refresh_token: str = ""
        self.redirect_uri: str = "https://localhost/"
        self.user_info: Dict[str, Any] = {}

        self.pipe = None
        self.handle = None
        self._lock = threading.RLock()
        self._write_lock = threading.Lock()
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None
        self._reader_thread: Optional[threading.Thread] = None

        # Synchronisation requête-réponse via nonce (évite toute course entre threads)
        self._pending_events: Dict[str, threading.Event] = {}
        self._pending_responses: Dict[str, Any] = {}

        self.is_connected: bool = False
        self.is_authenticated: bool = False
        self.mute: bool = False
        self.deaf: bool = False

        self._state_callbacks: list[Callable[[bool, bool], None]] = []

        self._load_config()

    def _load_config(self) -> None:
        if DISCORD_CONFIG_FILE.exists():
            try:
                with open(DISCORD_CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.client_id = data.get("client_id", "")
                    self.client_secret = data.get("client_secret", "")
                    self.access_token = data.get("access_token", "")
                    self.refresh_token = data.get("refresh_token", "")
                    self.redirect_uri = data.get("redirect_uri", "https://localhost/")
                    self.user_info = data.get("user_info", {})
            except Exception as e:
                logger.error(f"Erreur chargement discord_config.json: {e}")

    def save_config(self) -> None:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "redirect_uri": self.redirect_uri,
            "user_info": self.user_info,
        }
        try:
            temp_file = DISCORD_CONFIG_FILE.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            temp_file.replace(DISCORD_CONFIG_FILE)
        except Exception as e:
            logger.error(f"Erreur sauvegarde discord_config.json: {e}")

    def register_state_callback(self, cb: Callable[[bool, bool], None]) -> None:
        self._state_callbacks.append(cb)

    def _notify_state(self) -> None:
        for cb in self._state_callbacks:
            try:
                cb(self.mute, self.deaf)
            except Exception as e:
                logger.debug(f"Erreur callback Discord state: {e}")

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="DiscordRPCWorker")
        self._worker_thread.start()
        logger.info("Service Discord RPC démarré.")

    def stop(self) -> None:
        self._running = False
        self._close_pipe()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)
        logger.info("Service Discord RPC arrêté.")

    def _connect_and_handshake(self) -> bool:
        """Trouve le named pipe Discord actif et effectue le handshake initial."""
        with self._lock:
            if self.pipe:
                return True
            for i in range(10):
                pipe_path = f"\\\\.\\pipe\\discord-ipc-{i}"
                try:
                    p = open(pipe_path, "r+b", buffering=0)
                    h = msvcrt.get_osfhandle(p.fileno())

                    # Handshake opcode 0
                    cid = self.client_id if self.client_id else "1567221858099531927"
                    hs = json.dumps({"v": 1, "client_id": cid}).encode("utf-8")
                    p.write(struct.pack("<II", 0, len(hs)) + hs)

                    # Lecture synchrone de la réponse READY au handshake
                    avail = wintypes.DWORD()
                    t0 = time.time()
                    got_hs = False
                    while (time.time() - t0) < 2.0:
                        if kernel32.PeekNamedPipe(h, None, 0, None, ctypes.byref(avail), None) and avail.value >= 8:
                            hdr = p.read(8)
                            op, length = struct.unpack("<II", hdr)
                            p.read(length)  # message READY consommé
                            got_hs = True
                            break
                        time.sleep(0.01)

                    if not got_hs:
                        p.close()
                        continue

                    self.pipe = p
                    self.handle = h
                    self.is_connected = True
                    logger.info(f"Connecté au pipe Discord : {pipe_path}")

                    # Démarrer le reader thread dédié qui dépilera tous les messages suivants
                    if not self._reader_thread or not self._reader_thread.is_alive():
                        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True, name="DiscordRPCReader")
                        self._reader_thread.start()

                    return True
                except (FileNotFoundError, PermissionError):
                    continue
                except Exception as e:
                    logger.debug(f"Erreur tentative {pipe_path}: {e}")

            self.is_connected = False
            self.pipe = None
            self.handle = None
            return False

    def _close_pipe(self) -> None:
        """Ferme proprement le pipe et débloque les requêtes en attente."""
        with self._lock:
            with self._write_lock:
                if self.pipe:
                    try:
                        self.pipe.close()
                    except Exception:
                        pass
                    self.pipe = None
                    self.handle = None
            self.is_connected = False
            self.is_authenticated = False

            # Débloquer immédiatement les threads en attente pour éviter les blocages
            for evt in list(self._pending_events.values()):
                evt.set()
            self._pending_events.clear()
            self._pending_responses.clear()

    def send_command(self, cmd: str, args: Dict[str, Any], evt: Optional[str] = None, timeout: float = 3.5) -> Optional[Dict[str, Any]]:
        """Envoie une commande JSON RPC à Discord et attend la réponse associée au nonce."""
        if not self.pipe or not self.handle or not self.is_connected:
            return None

        nonce = str(uuid.uuid4())
        done_event = threading.Event()

        with self._lock:
            self._pending_events[nonce] = done_event

        payload: Dict[str, Any] = {
            "cmd": cmd,
            "args": args,
            "nonce": nonce
        }
        if evt:
            payload["evt"] = evt

        raw = json.dumps(payload).encode("utf-8")
        packet = struct.pack("<II", 1, len(raw)) + raw

        try:
            with self._write_lock:
                if not self.pipe:
                    with self._lock:
                        self._pending_events.pop(nonce, None)
                    return None
                self.pipe.write(packet)
        except Exception as e:
            logger.debug(f"Erreur écriture pipe: {e}")
            self._close_pipe()
            return None

        # Attente du signal déclenché par le reader thread indépendant
        if done_event.wait(timeout=timeout):
            with self._lock:
                self._pending_events.pop(nonce, None)
                return self._pending_responses.pop(nonce, None)
        else:
            with self._lock:
                self._pending_events.pop(nonce, None)
                self._pending_responses.pop(nonce, None)
            return None

    def _reader_loop(self) -> None:
        """Boucle dédiée de lecture non-bloquante du pipe Discord."""
        avail = wintypes.DWORD()
        while self._running:
            h = self.handle
            p = self.pipe
            if not h or not p or not self.is_connected:
                time.sleep(0.05)
                continue

            try:
                res = kernel32.PeekNamedPipe(h, None, 0, None, ctypes.byref(avail), None)
                if not res:
                    self._close_pipe()
                    time.sleep(0.5)
                    continue

                if avail.value >= 8:
                    hdr = p.read(8)
                    if not hdr or len(hdr) < 8:
                        self._close_pipe()
                        continue

                    op, length = struct.unpack("<II", hdr)
                    body = p.read(length)
                    if len(body) < length:
                        self._close_pipe()
                        continue

                    msg = json.loads(body.decode("utf-8"))
                    nonce = msg.get("nonce")

                    # 1. Réponse à une commande en attente (nonce)
                    if nonce and nonce in self._pending_events:
                        with self._lock:
                            self._pending_responses[nonce] = msg
                            self._pending_events[nonce].set()

                    # 2. Événement vocal spontané envoyé par Discord
                    elif msg.get("cmd") == "DISPATCH" and msg.get("evt") == "VOICE_SETTINGS_UPDATE":
                        d = msg.get("data", {})
                        old_mute, old_deaf = self.mute, self.deaf
                        self.mute = bool(d.get("mute", self.mute))
                        self.deaf = bool(d.get("deaf", self.deaf))
                        if self.mute != old_mute or self.deaf != old_deaf:
                            logger.info(f"Discord Voice Update: Mute={self.mute}, Deaf={self.deaf}")
                            self._notify_state()
                else:
                    time.sleep(0.01)
            except Exception as e:
                logger.debug(f"Exception dans worker pipe Discord: {e}")
                self._close_pipe()
                time.sleep(0.5)

    def _worker_loop(self) -> None:
        """Superviseur de connexion et d'authentification."""
        while self._running:
            if not self.pipe or not self.is_connected:
                if not self._connect_and_handshake():
                    time.sleep(2.0)
                    continue

            # Authentifier la session si nécessaire
            if self.is_connected and not self.is_authenticated and self.client_id and self.access_token:
                self._authenticate_session()

            time.sleep(1.0)

    def _authenticate_session(self) -> bool:
        """Authentifie le client auprès de Discord avec l'access_token OAuth2."""
        if not self.pipe or not self.is_connected:
            return False

        res = self.send_command("AUTHENTICATE", {"access_token": self.access_token}, timeout=4.0)
        if res and res.get("data", {}).get("user"):
            self.is_authenticated = True
            u = res["data"]["user"]
            self.user_info = {
                "id": u.get("id"),
                "username": u.get("username"),
                "global_name": u.get("global_name") or u.get("username")
            }
            self.save_config()
            logger.info(f"Discord RPC Authentifié avec succès ! Compte : {self.user_info.get('global_name')}")

            # Souscription aux événements vocaux
            self.send_command("SUBSCRIBE", {}, evt="VOICE_SETTINGS_UPDATE", timeout=2.0)

            # Récupération de l'état vocal actuel
            vres = self.send_command("GET_VOICE_SETTINGS", {}, timeout=2.0)
            if vres and "data" in vres:
                v_data = vres["data"]
                self.mute = bool(v_data.get("mute", False))
                self.deaf = bool(v_data.get("deaf", False))
                self._notify_state()
            return True
        else:
            logger.warning(f"Échec authentification Discord : {res}")
            # Si le jeton est expiré, tenter un rafraîchissement
            if self.refresh_token:
                logger.info("Tentative de rafraîchissement du jeton OAuth2 Discord...")
                if self._refresh_oauth_token():
                    res2 = self.send_command("AUTHENTICATE", {"access_token": self.access_token}, timeout=4.0)
                    if res2 and res2.get("data", {}).get("user"):
                        self.is_authenticated = True
                        u = res2["data"]["user"]
                        self.user_info = {
                            "id": u.get("id"),
                            "username": u.get("username"),
                            "global_name": u.get("global_name") or u.get("username")
                        }
                        self.save_config()
                        self.send_command("SUBSCRIBE", {}, evt="VOICE_SETTINGS_UPDATE", timeout=2.0)
                        vres2 = self.send_command("GET_VOICE_SETTINGS", {}, timeout=2.0)
                        if vres2 and "data" in vres2:
                            self.mute = bool(vres2["data"].get("mute", False))
                            self.deaf = bool(vres2["data"].get("deaf", False))
                            self._notify_state()
                        return True
            return False

    def _refresh_oauth_token(self) -> bool:
        if not self.client_id or not self.client_secret or not self.refresh_token:
            return False
        try:
            resp = httpx.post(
                OAUTH_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0
            )
            if resp.status_code == 200:
                t_data = resp.json()
                self.access_token = t_data.get("access_token", "")
                self.refresh_token = t_data.get("refresh_token", self.refresh_token)
                self.save_config()
                logger.info("Jeton Discord rafraîchi avec succès !")
                return True
            else:
                logger.error(f"Erreur refresh token Discord ({resp.status_code}): {resp.text}")
                return False
        except Exception as e:
            logger.error(f"Exception refresh token Discord: {e}")
            return False

    def authorize_flow(self, client_id: str, client_secret: str) -> Dict[str, Any]:
        """Déclenche la pop-up native d'autorisation sur Discord et échange le code."""
        with self._lock:
            self.client_id = client_id.strip()
            self.client_secret = client_secret.strip()
            self.save_config()

        self._close_pipe()
        if not self._connect_and_handshake():
            return {"success": False, "error": "Impossible d'ouvrir le pipe Discord. Discord est-il lancé ?"}

        # Envoyer AUTHORIZE (déclenche la fenêtre de permission native Discord sur le PC)
        logger.info("Envoi de la commande AUTHORIZE à Discord...")
        res = self.send_command(
            "AUTHORIZE",
            {
                "client_id": self.client_id,
                "scopes": ["rpc", "rpc.voice.read", "rpc.voice.write"]
            },
            timeout=45.0
        )

        if not res:
            return {"success": False, "error": "Délai dépassé ou refus d'autorisation dans Discord."}

        if res.get("evt") == "ERROR":
            err_data = res.get("data", {})
            return {"success": False, "error": f"Erreur Discord : {err_data.get('message', 'Inconnue')} (code {err_data.get('code')})"}

        code = res.get("data", {}).get("code")
        if not code:
            return {"success": False, "error": "Aucun code d'autorisation reçu de Discord."}

        # Échange du code contre un access_token
        try:
            post_data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self.redirect_uri
            }
            resp = httpx.post(
                OAUTH_TOKEN_URL,
                data=post_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=12.0
            )

            if resp.status_code != 200:
                logger.error(f"Erreur échange token Discord ({resp.status_code}): {resp.text}")
                return {"success": False, "error": f"Erreur échange OAuth2 ({resp.status_code}): {resp.text}"}

            token_data = resp.json()
            self.access_token = token_data.get("access_token", "")
            self.refresh_token = token_data.get("refresh_token", "")
            self.save_config()

            auth_ok = self._authenticate_session()

            if auth_ok:
                return {
                    "success": True,
                    "message": f"Connecté avec succès à Discord ! Compte : {self.user_info.get('global_name', 'Inconnu')}",
                    "user": self.user_info,
                    "mute": self.mute,
                    "deaf": self.deaf
                }
            else:
                return {"success": True, "message": "Autorisé avec succès, synchronisation en cours..."}
        except Exception as e:
            logger.error(f"Exception lors de l'échange du token Discord: {e}")
            return {"success": False, "error": str(e)}

    def toggle_mute(self) -> Optional[bool]:
        """Bascule l'état du micro dans Discord (sans avoir besoin du focus)."""
        if not self.is_authenticated:
            logger.warning("Discord RPC non authentifié. Impossible de couper le micro via RPC.")
            return None
        new_mute = not self.mute
        res = self.send_command("SET_VOICE_SETTINGS", {"mute": new_mute})
        if res and "data" in res:
            self.mute = bool(res["data"].get("mute", new_mute))
            self._notify_state()
            return self.mute
        return None

    def toggle_deaf(self) -> Optional[bool]:
        """Bascule la sourdine (casque) dans Discord (sans avoir besoin du focus)."""
        if not self.is_authenticated:
            logger.warning("Discord RPC non authentifié. Impossible de couper le casque via RPC.")
            return None
        new_deaf = not self.deaf
        res = self.send_command("SET_VOICE_SETTINGS", {"deaf": new_deaf})
        if res and "data" in res:
            self.deaf = bool(res["data"].get("deaf", new_deaf))
            self._notify_state()
            return self.deaf
        return None

    def get_status(self) -> Dict[str, Any]:
        return {
            "has_config": bool(self.client_id and self.client_secret),
            "is_connected": self.is_connected,
            "is_authenticated": self.is_authenticated,
            "mute": self.mute,
            "deaf": self.deaf,
            "user": self.user_info,
            "client_id": self.client_id
        }


discord_rpc = DiscordRPCService()
