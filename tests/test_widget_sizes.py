import unittest
from pydantic import ValidationError
from server import ButtonConfig, DeckConfig


class WidgetSizeTests(unittest.TestCase):
    def test_existing_widgets_get_responsive_defaults(self):
        widget = ButtonConfig.model_validate({'id': 'old', 'type': 'slider'})
        self.assertEqual((widget.width, widget.height), ('auto', 'normal'))

    def test_all_sizes_survive_config_roundtrip(self):
        widgets = [{'id': f'{width}-{height}', 'width': width, 'height': height}
                   for width in ('auto', 'quarter', 'third', 'half', 'full')
                   for height in ('compact', 'normal', 'tall')]
        config = DeckConfig.model_validate({'pages': [{'id': 'page_main', 'name': 'Principal', 'buttons': widgets}]})
        restored = DeckConfig.model_validate_json(config.model_dump_json())
        self.assertEqual([(b.width, b.height) for b in restored.pages[0].buttons], [(w['width'], w['height']) for w in widgets])

    def test_invalid_sizes_are_rejected(self):
        for value in ({'width': 'huge'}, {'height': 999}, {'width': -2}):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                ButtonConfig.model_validate({'id': 'invalid', **value})


if __name__ == '__main__': unittest.main()
