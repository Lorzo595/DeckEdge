import json
import tempfile
import threading
import unittest
from pathlib import Path

from server import ButtonConfig, ConfigStore, DEFAULT_CONFIG, DeckConfig, PageConfig


class ConfigStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.path = root / "config.json"
        self.backup = root / "config.json.bak"
        self.store = ConfigStore(self.path, self.backup)

    def test_missing_file_creates_default_and_returns_isolated_copies(self):
        config = self.store.load()
        self.assertTrue(self.path.exists())
        self.assertEqual(config.pages[0].name, "Principal")

        config.pages[0].name = "Modifié"
        self.assertEqual(self.store.load().pages[0].name, "Principal")
        self.assertEqual(DEFAULT_CONFIG.pages[0].name, "Principal")

    def test_corrupt_file_uses_last_good_backup(self):
        first = self.store.load()
        first.pages[0].name = "Premier"
        self.store.save(first)
        second = self.store.load()
        second.pages[0].name = "Deuxième"
        self.store.save(second)

        self.path.write_text("{ json invalide", encoding="utf-8")
        restored = ConfigStore(self.path, self.backup).load()
        self.assertEqual(restored.pages[0].name, "Premier")

        # A recovered config must not let the corrupt file overwrite the good backup.
        restored.pages[0].name = "Nouveau"
        ConfigStore(self.path, self.backup).save(restored)
        backup = json.loads(self.backup.read_text(encoding="utf-8"))
        self.assertEqual(backup["pages"][0]["name"], "Premier")

    def test_concurrent_updates_are_serialized_and_not_lost(self):
        self.store.save(DeckConfig(pages=[PageConfig(id="page_main", name="Principal", buttons=[])]))
        errors = []

        def add_button(_index):
            def mutate(config):
                page = config.pages[0]
                page.buttons.append(ButtonConfig(
                    id=f"b{len(page.buttons)}", type="key", target="playpause"
                ))
                return None, True
            try:
                self.store.update(mutate)
            except Exception as exc:  # pragma: no cover - only on failure
                errors.append(exc)

        threads = [threading.Thread(target=add_button, args=(index,)) for index in range(25)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(errors, [])
        buttons = self.store.load().pages[0].buttons
        self.assertEqual(len(buttons), 25)
        self.assertEqual(len({button.id for button in buttons}), 25)

    def test_invalid_schema_also_falls_back_to_backup(self):
        first = self.store.load()
        first.pages[0].name = "Valide"
        self.store.save(first)
        second = self.store.load()
        second.pages[0].name = "Valide 2"
        self.store.save(second)

        self.path.write_text(json.dumps({"pages": "invalide"}), encoding="utf-8")
        restored = ConfigStore(self.path, self.backup).load()
        self.assertEqual(restored.pages[0].name, "Valide")

    def test_invalid_and_duplicate_identifiers_are_normalized(self):
        config = DeckConfig.model_validate({
            "pages": [{
                "id": "page principal",
                "name": "Principal",
                "buttons": [
                    {"id": "same", "type": "key", "target": "playpause"},
                    {"id": "same", "type": "key", "target": "nexttrack"},
                ],
            }],
        })

        page = config.pages[0]
        self.assertRegex(page.id, r"^[A-Za-z0-9_-]+$")
        self.assertEqual(page.id, "page_0")
        self.assertEqual(config.active_page_id, "page_0")
        self.assertEqual([button.id for button in page.buttons][0], "same")
        self.assertNotEqual([button.id for button in page.buttons][1], "same")

    def test_legacy_migration_preserves_monitoring(self):
        config = DeckConfig.model_validate({
            "monitoring": [{"label": "CPU", "sensor_id": "cpu_load"}],
            "buttons": [{"id": "b1", "type": "key", "target": "playpause"}],
        })
        self.assertEqual(config.monitoring[0].label, "CPU")
        self.assertEqual(config.pages[0].id, "page_main")
        self.assertEqual(config.pages[0].buttons[0].id, "b1")


if __name__ == "__main__":
    unittest.main()
