"""LAN pairing and localhost-only administration; no secrets in logs."""
import hashlib
import hmac
import ipaddress
import json
import logging
import os
import re
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from app_paths import DATA_DIR
from local_discovery import HOSTNAME

COOKIE = 'deckedge_pairing'
KEY_FILE = DATA_DIR / '.phone-key'
DEVICE_FILE = DATA_DIR / '.phones.json'
logger = logging.getLogger('DeckEdge')


def _write_key(value):
    temp = KEY_FILE.with_name(KEY_FILE.name + f'.{os.getpid()}.tmp')
    try:
        temp.write_text(value, encoding='ascii')
        os.replace(temp, KEY_FILE)
    except OSError:
        try:
            temp.unlink()
        except OSError:
            pass
        KEY_FILE.write_text(value, encoding='ascii')


def pairing_key():
    try:
        value = KEY_FILE.read_text(encoding='ascii').strip()
        if len(value) == 64 and all(c in '0123456789abcdef' for c in value):
            return value
    except FileNotFoundError:
        pass
    value = secrets.token_hex(32)
    _write_key(value)
    return value


def rotate_pairing_key():
    value = secrets.token_hex(32)
    _write_key(value)
    return value


def is_local(host):
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def valid_host(host):
    if host.lower() in ('localhost', HOSTNAME):
        return True
    try:
        return ipaddress.ip_address(host).is_private or ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def allowed_origin(connection):
    if not valid_host(connection.url.hostname or ''):
        return False
    origin = connection.headers.get('origin')
    if not origin:
        return True
    parsed = urlsplit(origin)
    return parsed.scheme == 'http' and parsed.netloc == connection.headers.get('host')


def is_paired(connection, key):
    """Legacy master-key check kept for imports and old WebSocket tests."""
    supplied = connection.query_params.get('key') or connection.cookies.get(COOKIE, '')
    return isinstance(supplied, str) and hmac.compare_digest(supplied, key)


def device_label(user_agent):
    ua = (user_agent or '').lower()
    if 'iphone' in ua or 'ipod' in ua:
        platform = 'iPhone'
    elif 'ipad' in ua:
        platform = 'iPad'
    elif 'android' in ua:
        platform = 'Android'
    elif 'windows' in ua:
        platform = 'Windows'
    elif 'macintosh' in ua or 'mac os' in ua:
        platform = 'Mac'
    elif 'linux' in ua:
        platform = 'Linux'
    else:
        platform = 'Phone'
    if 'edg/' in ua or 'edgios/' in ua:
        browser = 'Edge'
    elif 'opr/' in ua or 'opera' in ua:
        browser = 'Opera'
    elif 'firefox' in ua or 'fxios' in ua:
        browser = 'Firefox'
    elif 'chrome' in ua or 'crios' in ua:
        browser = 'Chrome'
    elif 'safari' in ua:
        browser = 'Safari'
    else:
        browser = ''
    return f'{platform} · {browser}' if browser else platform


def _utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


class PhoneRegistry:
    """Per-device pairing tokens stored as SHA256 hashes in a small JSON file."""

    def __init__(self, path=DEVICE_FILE):
        self.path = Path(path)
        self._lock = threading.RLock()
        self._phones = {}
        self._by_hash = {}
        self._last_seen_persist = 0.0
        self._load()

    def _load(self):
        try:
            payload = json.loads(self.path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return
        items = payload.get('phones') if isinstance(payload, dict) else None
        if not isinstance(items, list):
            return
        for item in items:
            if not isinstance(item, dict):
                continue
            phone_id = str(item.get('id', ''))
            token_hash = str(item.get('token_hash', ''))
            name = str(item.get('name', '')).strip()
            if not re.fullmatch(r'[a-f0-9]{16}', phone_id):
                continue
            if phone_id in self._phones:
                continue
            if not re.fullmatch(r'[a-f0-9]{64}', token_hash) or token_hash in self._by_hash:
                continue
            record = {
                'id': phone_id,
                'name': name[:40] or 'Phone',
                'token_hash': token_hash,
                'created_at': str(item.get('created_at') or _utc_now()),
                'last_seen': str(item.get('last_seen') or _utc_now()),
                'last_ip': str(item.get('last_ip') or ''),
                'user_agent': str(item.get('user_agent') or '')[:300],
            }
            self._phones[phone_id] = record
            self._by_hash[token_hash] = phone_id

    def _save(self):
        with self._lock:
            temporary = self.path.with_name(self.path.name + f'.{os.getpid()}.tmp')
            payload = {'version': 1, 'phones': [dict(phone) for phone in self._phones.values()]}
            try:
                temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
                os.replace(temporary, self.path)
                self._last_seen_persist = time.monotonic()
            finally:
                try:
                    if temporary.exists():
                        temporary.unlink()
                except OSError:
                    pass

    @staticmethod
    def _public(phone):
        return {
            'id': phone['id'],
            'name': phone['name'],
            'created_at': phone['created_at'],
            'last_seen': phone['last_seen'],
            'last_ip': phone['last_ip'],
        }

    def pair(self, user_agent='', ip=''):
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
        phone_id = secrets.token_hex(8)
        now = _utc_now()
        record = {
            'id': phone_id,
            'name': device_label(user_agent)[:40],
            'token_hash': token_hash,
            'created_at': now,
            'last_seen': now,
            'last_ip': (ip or '')[:64],
            'user_agent': (user_agent or '')[:300],
        }
        with self._lock:
            self._phones[phone_id] = record
            self._by_hash[token_hash] = phone_id
            try:
                self._save()
            except Exception:
                self._phones.pop(phone_id, None)
                self._by_hash.pop(token_hash, None)
                raise
            return self._public(record), token

    def authenticate(self, token, ip=''):
        if not isinstance(token, str):
            return None
        token = token.strip()
        if not token or len(token) > 200:
            return None
        token_hash = hashlib.sha256(token.encode('utf-8')).hexdigest()
        now = _utc_now()
        with self._lock:
            phone_id = self._by_hash.get(token_hash)
            if not phone_id:
                return None
            record = self._phones.get(phone_id)
            if record is None:
                return None
            record['last_seen'] = now
            if ip:
                record['last_ip'] = ip[:64]
            if time.monotonic() - self._last_seen_persist >= 30:
                try:
                    self._save()
                except OSError:
                    logger.warning("Unable to persist phone activity", exc_info=True)
            return self._public(record)

    def list(self):
        with self._lock:
            phones = [self._public(phone) for phone in self._phones.values()]
        return sorted(phones, key=lambda phone: phone['last_seen'], reverse=True)

    def revoke(self, phone_id):
        with self._lock:
            record = self._phones.pop(phone_id, None)
            if record is None:
                return False
            self._by_hash.pop(record['token_hash'], None)
            try:
                self._save()
            except Exception:
                self._phones[phone_id] = record
                self._by_hash[record['token_hash']] = phone_id
                raise
            return True

    def revoke_all(self):
        with self._lock:
            count = len(self._phones)
            phones = dict(self._phones)
            by_hash = dict(self._by_hash)
            self._phones.clear()
            self._by_hash.clear()
            try:
                self._save()
            except Exception:
                self._phones.update(phones)
                self._by_hash.update(by_hash)
                raise
            return count

    def rename(self, phone_id, name):
        name = (name or '').strip()[:40]
        if not name:
            return False
        with self._lock:
            record = self._phones.get(phone_id)
            if record is None:
                return False
            previous = record['name']
            record['name'] = name
            try:
                self._save()
            except Exception:
                record['name'] = previous
                raise
            return True

    def count(self):
        with self._lock:
            return len(self._phones)
