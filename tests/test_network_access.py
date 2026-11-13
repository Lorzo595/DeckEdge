import unittest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from server import app, PHONE_KEY


class NetworkAccessTests(unittest.TestCase):
    def client(self, address='127.0.0.1', host='127.0.0.1:5000'):
        return TestClient(app, base_url=f'http://{host}', client=(address, 12345))

    def test_local_admin_works_without_pairing(self):
        self.assertEqual(self.client().get('/admin').status_code, 200)

    def test_external_origin_and_rebinding_are_rejected(self):
        self.assertEqual(self.client().get('/api/config', headers={'Origin': 'https://example.org'}).status_code, 403)
        self.assertEqual(self.client(host='malicious.example:5000').get('/admin').status_code, 403)

    def test_phone_requires_key_then_gets_private_cookie(self):
        phone = self.client('192.168.1.100', '192.168.1.50:5000')
        self.assertEqual(phone.get('/').status_code, 401)
        self.assertEqual(phone.get('/?key=incorrect').status_code, 401)
        response = phone.get('/', params={'key': PHONE_KEY})
        self.assertEqual(response.status_code, 200)
        self.assertIn('HttpOnly', response.headers['set-cookie'])
        self.assertIn('SameSite=strict', response.headers['set-cookie'])
        self.assertEqual(phone.get('/deck-layout.css').status_code, 200)
        self.assertEqual(phone.get('/admin').status_code, 403)
        self.assertEqual(phone.post('/api/config', json={}).status_code, 403)
        self.assertEqual(phone.post('/api/discord/connect', json={}).status_code, 403)
        self.assertEqual(phone.get('/api/apps').status_code, 403)

    def test_websocket_requires_key_and_rejects_external_origin(self):
        phone = self.client('192.168.1.100', '192.168.1.50:5000')
        with self.assertRaises(WebSocketDisconnect):
            with phone.websocket_connect('/ws'):
                self.fail('WebSocket non associé accepté')
        with self.assertRaises(WebSocketDisconnect):
            with self.client().websocket_connect('/ws', headers={'Origin': 'https://example.org'}):
                self.fail('Origine externe acceptée')


if __name__ == '__main__':
    unittest.main()
