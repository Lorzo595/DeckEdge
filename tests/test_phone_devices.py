import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import network_access
import server
from local_discovery import HOSTNAME
from server import PHONE_KEY, app


class PhoneRegistryTests(unittest.TestCase):
    def registry(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        return network_access.PhoneRegistry(Path(folder.name) / '.phones.json')

    def test_pair_authenticate_rename_and_revoke(self):
        registry = self.registry()
        phone, token = registry.pair('Mozilla/5.0 (iPhone) Version/17.0 Safari/604.1', '192.168.1.20')
        self.assertEqual(phone['name'], 'iPhone · Safari')
        self.assertEqual(phone['last_ip'], '192.168.1.20')
        self.assertEqual(registry.authenticate(token, '192.168.1.21')['id'], phone['id'])
        self.assertTrue(registry.rename(phone['id'], 'Salon'))
        self.assertEqual(registry.list()[0]['name'], 'Salon')
        self.assertTrue(registry.revoke(phone['id']))
        self.assertIsNone(registry.authenticate(token))
        self.assertEqual(registry.count(), 0)

    def test_tokens_are_hashed_on_disk_and_survive_restart(self):
        registry = self.registry()
        phone, token = registry.pair('Android Chrome', '192.168.1.30')
        text = registry.path.read_text(encoding='utf-8')
        self.assertNotIn(token, text)
        self.assertIn('token_hash', text)
        reloaded = network_access.PhoneRegistry(registry.path)
        self.assertEqual(reloaded.authenticate(token)['id'], phone['id'])
        self.assertEqual(reloaded.list()[0]['name'], 'Android · Chrome')

    def test_revoke_all(self):
        registry = self.registry()
        registry.pair('iPhone Safari', '192.168.1.40')
        registry.pair('Android Chrome', '192.168.1.41')
        self.assertEqual(registry.revoke_all(), 2)
        self.assertEqual(registry.list(), [])


class PhoneAccessTests(unittest.TestCase):
    def remote(self, address='192.168.1.100'):
        return TestClient(app, base_url='http://' + HOSTNAME + ':5000', client=(address, 1000))

    def local(self):
        return TestClient(app, base_url='http://127.0.0.1:5000', client=('127.0.0.1', 1000))

    def test_pairing_issues_a_device_token_and_revocation_locks_it_out(self):
        with tempfile.TemporaryDirectory() as folder:
            registry = network_access.PhoneRegistry(Path(folder) / '.phones.json')
            with patch.object(server, 'phones', registry):
                phone = self.remote()
                self.assertEqual(phone.get('/').status_code, 401)
                response = phone.get('/', params={'key': PHONE_KEY})
                self.assertEqual(response.status_code, 200)
                cookie = phone.cookies.get(network_access.COOKIE)
                self.assertTrue(cookie)
                self.assertNotEqual(cookie, PHONE_KEY)
                self.assertEqual(len(registry.list()), 1)
                self.assertNotIn(PHONE_KEY, cookie)

                manifest = phone.get('/manifest.webmanifest')
                self.assertEqual(manifest.status_code, 200)
                self.assertEqual(manifest.json()['start_url'], '/')
                self.assertNotIn(PHONE_KEY, manifest.text)

                phone_id = registry.list()[0]['id']
                self.assertTrue(registry.revoke(phone_id))
                self.assertEqual(phone.get('/').status_code, 401)

    def test_legacy_master_cookie_is_migrated(self):
        with tempfile.TemporaryDirectory() as folder:
            registry = network_access.PhoneRegistry(Path(folder) / '.phones.json')
            with patch.object(server, 'phones', registry):
                phone = self.remote()
                response = phone.get('/', cookies={network_access.COOKIE: PHONE_KEY})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(registry.list()), 1)
                self.assertNotEqual(phone.cookies.get(network_access.COOKIE), PHONE_KEY)

    def test_local_phone_management_api(self):
        with tempfile.TemporaryDirectory() as folder:
            registry = network_access.PhoneRegistry(Path(folder) / '.phones.json')
            phone, _ = registry.pair('iPhone Safari', '192.168.1.50')
            with patch.object(server, 'phones', registry), \
                 patch.object(server, 'PHONE_KEY', server.PHONE_KEY), \
                 patch.object(network_access, 'KEY_FILE', Path(folder) / '.phone-key'):
                local = self.local()
                listed = local.get('/api/phones')
                self.assertEqual(listed.status_code, 200)
                self.assertEqual(listed.json()['phones'][0]['id'], phone['id'])
                self.assertNotIn('token_hash', listed.text)

                renamed = local.patch('/api/phones/' + phone['id'], json={'name': 'Salon'})
                self.assertEqual(renamed.status_code, 200)
                self.assertEqual(registry.list()[0]['name'], 'Salon')

                old_key = server.PHONE_KEY
                revoked = local.delete('/api/phones/' + phone['id'])
                self.assertEqual(revoked.status_code, 200)
                self.assertTrue(revoked.json()['pairing_key_rotated'])
                self.assertNotEqual(server.PHONE_KEY, old_key)
                self.assertEqual(registry.list(), [])

                stale = self.remote('192.168.1.102')
                self.assertEqual(stale.get('/', params={'key': old_key}).status_code, 401)

                phone, _ = registry.pair('Android Chrome', '192.168.1.51')
                remote = self.remote('192.168.1.101')
                remote.get('/', params={'key': server.PHONE_KEY})
                forbidden = remote.post('/api/phones/revoke-all')
                self.assertEqual(forbidden.status_code, 403)

                local = self.local()
                all_phones = local.post('/api/phones/revoke-all')
                self.assertEqual(all_phones.status_code, 200)
                self.assertEqual(all_phones.json()['revoked'], 2)


class PhoneSocketTests(unittest.IsolatedAsyncioTestCase):
    class FakeSocket:
        def __init__(self):
            self.closed = None

        async def accept(self):
            pass

        async def close(self, code=1000):
            self.closed = code

    async def test_revoking_a_phone_closes_its_socket(self):
        manager = server.ConnectionManager()
        socket = self.FakeSocket()
        await manager.connect(socket, 'phone-1')
        self.assertIsNone(socket.closed)
        self.assertEqual(await manager.disconnect_device('phone-1'), 1)
        self.assertEqual(socket.closed, 1008)
        self.assertEqual(manager.client_count, 0)


if __name__ == '__main__':
    unittest.main()
