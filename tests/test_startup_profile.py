import unittest
from server import DeckConfig


class StartupProfileTests(unittest.TestCase):
    def test_principal_wins_over_previously_saved_music(self):
        config = DeckConfig.model_validate({'active_page_id': 'page_music', 'pages': [
            {'id': 'page_music', 'name': 'Musique'}, {'id': 'page_main', 'name': 'Principal'}]})
        self.assertEqual(config.active_page_id, 'page_main')

    def test_without_principal_keep_existing_default(self):
        config = DeckConfig.model_validate({'active_page_id': 'b', 'pages': [
            {'id': 'a', 'name': 'A'}, {'id': 'b', 'name': 'B'}]})
        self.assertEqual(config.active_page_id, 'b')

    def test_missing_default_falls_back_to_first_profile(self):
        config = DeckConfig.model_validate({'active_page_id': 'missing', 'pages': [{'id': 'a', 'name': 'A'}]})
        self.assertEqual(config.active_page_id, 'a')


if __name__ == '__main__': unittest.main()
