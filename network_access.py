"""LAN pairing and localhost-only administration; no secrets in logs."""
import hmac
import ipaddress
import secrets
from urllib.parse import urlsplit
from app_paths import DATA_DIR
from local_discovery import HOSTNAME

COOKIE = 'deckedge_pairing'
KEY_FILE = DATA_DIR / '.phone-key'

def pairing_key():
    try:
        value = KEY_FILE.read_text(encoding='ascii').strip()
        if len(value) == 64 and all(c in '0123456789abcdef' for c in value):
            return value
    except FileNotFoundError:
        pass
    value = secrets.token_hex(32)
    KEY_FILE.write_text(value, encoding='ascii')
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
    supplied = connection.query_params.get('key') or connection.cookies.get(COOKIE, '')
    return isinstance(supplied, str) and hmac.compare_digest(supplied, key)
