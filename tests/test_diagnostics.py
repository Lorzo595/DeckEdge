import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app_paths import DATA_DIR
from local_discovery import HOSTNAME
from server import BASE_DIR, PHONE_KEY, _redact_text, app


class DiagnosticsTests(unittest.TestCase):
    def test_local_report_redacts_paths_key_and_ip_addresses(self):
        targets = {
            "devices": [{"name": "Casque", "target": "device:Casque", "volume": 50, "muted": False}],
            "apps": [{"name": "Spotify", "target": "app:spotify", "volume": 30, "muted": True,
                      "outputs": ["Casque"], "sessions": 1}],
        }
        with patch("server.get_audio_targets", return_value=targets):
            client = TestClient(app, base_url="http://127.0.0.1:5000", client=("127.0.0.1", 1000))
            response = client.get("/api/diagnostics")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        body = response.text
        self.assertNotIn(str(PHONE_KEY), body)
        self.assertNotIn(str(DATA_DIR), body)
        self.assertNotIn("192.168.1.50", _redact_text("client 192.168.1.50"))
        report = response.json()
        self.assertEqual(report["app"]["version"], (BASE_DIR / "VERSION").read_text(encoding="utf-8").strip())
        self.assertIn("system", report)
        self.assertIn("logs", report)
        self.assertEqual(report["audio"]["apps"][0]["name"], "Spotify")

    def test_remote_diagnostics_are_desktop_only_even_when_paired(self):
        client = TestClient(app, base_url="http://" + HOSTNAME + ":5000", client=("192.168.1.100", 1000))
        response = client.get("/api/diagnostics", params={"key": PHONE_KEY})
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
