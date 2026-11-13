"""Stable, PC-specific LAN name. Discovery never advertises a pairing key."""
import hashlib
import ipaddress
import logging
import os
import secrets
import socket
import threading
from app_paths import DATA_DIR

log = logging.getLogger('DeckEdge.discovery')


def pc_hostname():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Cryptography', 0,
                            winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            identity = winreg.QueryValueEx(key, 'MachineGuid')[0].strip().lower()
    except (ImportError, OSError):
        path = DATA_DIR / '.device-id'
        try:
            identity = path.read_text(encoding='ascii').strip()
        except FileNotFoundError:
            identity = secrets.token_hex(32)
            path.write_text(identity, encoding='ascii')
    return 'deckedge-' + hashlib.sha256(('DeckEdge:' + identity).encode('utf-8')).hexdigest()[:12] + '.local'


HOSTNAME = pc_hostname()


def preferred_address():
    import psutil
    stats = psutil.net_if_stats()
    candidates = []
    for name, entries in psutil.net_if_addrs().items():
        if name in stats and not stats[name].isup:
            continue
        for entry in entries:
            if entry.family != socket.AF_INET:
                continue
            address = ipaddress.ip_address(entry.address)
            if address.is_loopback or address.is_link_local or address.is_unspecified or not address.is_private:
                continue
            virtual = any(word in name.lower() for word in ('virtual', 'vethernet', 'vpn', 'tailscale', 'wireguard', 'tap-'))
            candidates.append((virtual, entry.address))
    requested = os.environ.get('DECKEDGE_LAN_IP')
    if requested and any(ip == requested for _, ip in candidates):
        return requested
    candidates.sort(key=lambda entry: entry[0])
    return candidates[0][1] if candidates else None


class LocalDiscovery:
    def __init__(self):
        self.available = False
        self._zc = self._info = None
        self._address = None
        self._stop = threading.Event()
        self._lock = threading.RLock()
        self._thread = None

    def _service(self, address):
        from zeroconf import ServiceInfo
        return ServiceInfo('_http._tcp.local.', HOSTNAME[:-6] + '._http._tcp.local.',
                           addresses=[socket.inet_aton(address)], port=5000,
                           properties={'app': 'DeckEdge', 'path': '/'}, server=HOSTNAME + '.')

    def start(self):
        with self._lock:
            try:
                from zeroconf import Zeroconf, IPVersion
                address = preferred_address()
                if address:
                    self._zc = Zeroconf(ip_version=IPVersion.V4Only)
                    self._info = self._service(address)
                    self._zc.register_service(self._info)
                    self._address = address
                    self.available = True
                self._thread = threading.Thread(target=self._refresh, daemon=True)
                self._thread.start()
            except Exception:
                # IP-based pairing stays usable when multicast is unavailable.
                log.info('Adresse locale permanente indisponible ; connexion par IP conservée.')
                if self._zc:
                    self._zc.close()
                    self._zc = None

    def _refresh(self):
        while not self._stop.wait(10):
            try:
                address = preferred_address()
                with self._lock:
                    if address and address != self._address:
                        from zeroconf import Zeroconf, IPVersion
                        self.available = False
                        if self._zc:
                            if self._info:
                                self._zc.unregister_service(self._info)
                            self._zc.close()
                        self._zc = Zeroconf(ip_version=IPVersion.V4Only)
                        info = self._service(address)
                        self._zc.register_service(info)
                        self._info, self._address = info, address
                        self.available = True
                    elif not address:
                        self.available = False
                        self._address = None
            except Exception:
                log.debug('Actualisation de la découverte locale différée.')

    def stop(self):
        self._stop.set()
        with self._lock:
            self.available = False
            if self._zc:
                try:
                    if self._info:
                        self._zc.unregister_service(self._info)
                finally:
                    self._zc.close()
                    self._zc = None


discovery = LocalDiscovery()
