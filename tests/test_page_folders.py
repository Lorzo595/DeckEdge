import unittest

from server import DeckConfig


class PageFolderTests(unittest.TestCase):
    def test_folder_and_subpage_roundtrip(self):
        config = DeckConfig.model_validate({
            "active_page_id": "steam",
            "pages": [
                {"id": "games", "name": "Games", "icon": "📁", "is_folder": True},
                {"id": "steam", "name": "Steam", "parent_id": "games"},
                {"id": "desktop", "name": "Desktop"},
            ],
        })
        folder = config.pages[0]
        child = config.pages[1]
        self.assertTrue(folder.is_folder)
        self.assertIsNone(folder.parent_id)
        self.assertEqual(child.parent_id, "games")
        self.assertEqual(config.active_page_id, "steam")

        restored = DeckConfig.model_validate_json(config.model_dump_json())
        self.assertEqual(restored.pages[1].parent_id, "games")
        self.assertTrue(restored.pages[0].is_folder)

    def test_invalid_parent_and_nested_folder_are_cleared(self):
        config = DeckConfig.model_validate({
            "pages": [
                {"id": "page_main", "name": "Main"},
                {"id": "orphan", "name": "Orphan", "parent_id": "missing"},
                {"id": "nested", "name": "Nested", "is_folder": True, "parent_id": "page_main"},
            ],
        })
        by_id = {page.id: page for page in config.pages}
        self.assertIsNone(by_id["orphan"].parent_id)
        self.assertIsNone(by_id["nested"].parent_id)

    def test_active_page_skips_folders(self):
        config = DeckConfig.model_validate({
            "active_page_id": "folder",
            "pages": [
                {"id": "folder", "name": "Folder", "is_folder": True},
                {"id": "page_main", "name": "Main"},
            ],
        })
        self.assertEqual(config.active_page_id, "page_main")

    def test_legacy_flat_pages_remain_flat(self):
        config = DeckConfig.model_validate({"pages": [{"id": "page_main", "name": "Main"}]})
        self.assertFalse(config.pages[0].is_folder)
        self.assertIsNone(config.pages[0].parent_id)


if __name__ == "__main__":
    unittest.main()
