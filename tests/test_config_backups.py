import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import server
from server import ConfigStore, DeckConfig, PageConfig


def make_config(name="Principal"):
    return DeckConfig(pages=[PageConfig(id="page_main", name=name, buttons=[])])


class ConfigBackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.store = ConfigStore(root / "config.json", root / "config.json.bak")
        self.addCleanup(self.store.close)

    def test_create_list_and_restore_backup(self):
        self.store.save(make_config("Original"))
        backup = self.store.create_backup()
        self.assertRegex(backup["name"], r"^deckedge-\d{8}-\d{6}-\d{3}\.json$")
        self.assertTrue((self.store.backup_dir / backup["name"]).exists())
        self.assertEqual(self.store.list_backups()[0]["name"], backup["name"])

        self.store.save(make_config("Modifié"))
        restored = self.store.restore_backup(backup["name"])
        self.assertEqual(restored.pages[0].name, "Original")
        self.assertEqual(self.store.load().pages[0].name, "Original")
        self.assertGreaterEqual(len(self.store.list_backups()), 2)

    def test_backup_names_reject_path_traversal(self):
        for name in ("../config.json", "..\\config.json", "deckedge-20260101-120000-000.json/..", "config.json"):
            with self.subTest(name=name), self.assertRaises(FileNotFoundError):
                self.store.restore_backup(name)

    def test_restore_aborts_when_safety_backup_fails(self):
        self.store.save(make_config("Ancien"))
        backup = self.store.create_backup()
        self.store.save(make_config("Actuel à conserver"))
        before = self.store.path.read_bytes()
        for error in (PermissionError("read-only backup folder"), FileNotFoundError("backup folder unavailable")):
            with self.subTest(error=type(error).__name__):
                with patch.object(self.store, "create_backup", side_effect=error):
                    with self.assertRaisesRegex(RuntimeError, "Restauration annulée"):
                        self.store.restore_backup(backup["name"])
                self.assertEqual(self.store.path.read_bytes(), before)
                self.assertEqual(self.store.load().pages[0].name, "Actuel à conserver")

    def test_old_backups_are_pruned(self):
        self.store.save(make_config())
        for _ in range(23):
            self.store.create_backup()
        self.assertLessEqual(len(self.store.list_backups()), 20)

    def test_non_backup_files_are_ignored(self):
        self.store.backup_dir.mkdir(parents=True)
        (self.store.backup_dir / "config.json").write_text("{}", encoding="utf-8")
        (self.store.backup_dir / "deckedge-invalid.json").write_text("{}", encoding="utf-8")
        self.assertEqual(self.store.list_backups(), [])


class ConfigBackupEndpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.store = ConfigStore(root / "config.json", root / "config.json.bak")
        self.addCleanup(self.store.close)
        self.store.save(make_config("Original"))
        patcher = patch.object(server, "config_store", self.store)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = TestClient(server.app, base_url="http://127.0.0.1:5000", client=("127.0.0.1", 1000))

    def test_validate_backup_create_and_restore(self):
        config = make_config("Importé").model_dump(mode="json")
        response = self.client.post("/api/config/validate", json=config)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["config"]["pages"][0]["name"], "Importé")

        created = self.client.post("/api/config/backups")
        self.assertEqual(created.status_code, 200)
        name = created.json()["backup"]["name"]
        self.assertIn(name, [item["name"] for item in created.json()["backups"]])

        self.store.save(make_config("Modifié"))
        restored = self.client.post("/api/config/restore", json={"name": name})
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.json()["config"]["pages"][0]["name"], "Original")

    def test_backup_endpoints_are_desktop_only(self):
        client = TestClient(
            server.app,
            base_url="http://" + server.HOSTNAME + ":5000",
            client=("192.168.1.100", 1000),
        )
        self.assertEqual(client.get("/api/config/backups", params={"key": server.PHONE_KEY}).status_code, 403)
        self.assertEqual(client.post("/api/config/validate", params={"key": server.PHONE_KEY}, json={}).status_code, 403)

    def test_restore_endpoint_reports_safety_failure_without_replacing_config(self):
        backup = self.store.create_backup()
        self.store.save(make_config("À conserver"))
        before = self.store.path.read_bytes()
        with patch.object(self.store, "create_backup", side_effect=FileNotFoundError("backup unavailable")):
            response = self.client.post("/api/config/restore", json={"name": backup["name"]})
        self.assertEqual(response.status_code, 500)
        self.assertIn("Restauration annulée", response.json()["detail"])
        self.assertEqual(self.store.path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
