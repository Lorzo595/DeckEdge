import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from unittest.mock import Mock
from fastapi.testclient import TestClient
import network_access
from local_discovery import HOSTNAME, LocalDiscovery
from server import app, PHONE_KEY


class PersistentPhoneTests(unittest.TestCase):
    def test_saved_key_survives_repeated_starts(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.phone-key'
            with patch.object(network_access, 'KEY_FILE', path):
                first = network_access.pairing_key()
                timestamp = path.stat().st_mtime_ns
                self.assertEqual(network_access.pairing_key(), first)
                self.assertEqual(path.stat().st_mtime_ns, timestamp)
                self.assertEqual(len(first), 64)

    def test_only_own_pc_name_is_accepted(self):
        self.assertRegex(HOSTNAME, r'^deckedge-[a-f0-9]{12}\.local$')
        self.assertTrue(network_access.valid_host(HOSTNAME))
        self.assertFalse(network_access.valid_host('another-pc.local'))

    def test_home_screen_link_reassociates_without_old_cookies(self):
        phone = TestClient(app, base_url='http://' + HOSTNAME + ':5000', client=('192.168.1.100', 1000))
        self.assertEqual(phone.get('/manifest.webmanifest').status_code, 401)
        self.assertEqual(phone.get('/', params={'key': PHONE_KEY}).status_code, 200)
        manifest = phone.get('/manifest.webmanifest')
        self.assertEqual(manifest.status_code, 200)
        self.assertEqual(manifest.headers['cache-control'], 'no-store')
        self.assertEqual(manifest.json()['start_url'], '/?key=' + PHONE_KEY)
        fresh = TestClient(app, base_url='http://' + HOSTNAME + ':5000', client=('192.168.1.101', 1001))
        self.assertEqual(fresh.get(manifest.json()['start_url']).status_code, 200)
        self.assertEqual(fresh.get('/deck-layout.js').status_code, 200)
        self.assertEqual(fresh.get('/admin').status_code, 403)

    def test_discovery_does_not_broadcast_pairing_secret(self):
        info = LocalDiscovery()._service('192.168.1.50')
        self.assertEqual(info.server, HOSTNAME + '.')
        self.assertNotIn(PHONE_KEY.encode(), info.text)
        self.assertNotIn(b'key=', info.text)

    def test_discovery_recovers_when_same_network_returns(self):
        service = LocalDiscovery()
        service._address = '192.168.1.50'
        service._info = object()
        service._zc = previous = Mock()
        service.available = True
        service._stop = Mock()
        service._stop.wait.side_effect = [False, False, True]
        replacement = Mock()
        with patch('local_discovery.preferred_address', side_effect=[None, '192.168.1.50']), patch('zeroconf.Zeroconf', return_value=replacement):
            service._refresh()
        self.assertTrue(service.available)
        previous.close.assert_called_once()
        replacement.register_service.assert_called_once()


if __name__ == '__main__':
    unittest.main()
