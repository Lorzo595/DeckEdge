import unittest
from unittest.mock import call, patch

from pydantic import ValidationError

import server
from server import ActionStep, ButtonConfig, DeckConfig


class SequenceValidationTests(unittest.TestCase):
    def test_sequence_roundtrip_preserves_steps(self):
        config = DeckConfig.model_validate({
            "pages": [{
                "id": "page_main",
                "name": "Principal",
                "buttons": [{
                    "id": "s1",
                    "label": "Séquence",
                    "type": "sequence",
                    "steps": [
                        {"type": "hotkey", "target": "ctrl,shift,m", "delay": 0.2},
                        {"type": "launch", "target": "calc.exe", "delay": 0},
                    ],
                }],
            }],
        })
        restored = DeckConfig.model_validate_json(config.model_dump_json())
        self.assertEqual([step.type for step in restored.pages[0].buttons[0].steps], ["hotkey", "launch"])
        self.assertEqual(restored.pages[0].buttons[0].steps[0].delay, 0.2)

    def test_empty_sequence_is_rejected(self):
        with self.assertRaises(ValidationError):
            ButtonConfig(id="s1", type="sequence", steps=[])

    def test_nested_sequence_and_invalid_delay_are_rejected(self):
        for step in (
            {"type": "sequence", "target": "x"},
            {"type": "key", "target": "a", "delay": 6},
            {"type": "key", "target": "a", "delay": -1},
        ):
            with self.subTest(step=step), self.assertRaises(ValidationError):
                ButtonConfig(id="s1", type="sequence", steps=[step])

    def test_more_than_ten_steps_are_rejected(self):
        with self.assertRaises(ValidationError):
            ButtonConfig(id="s1", type="sequence", steps=[{"type": "key", "target": "a"}] * 11)


class SequenceExecutionTests(unittest.TestCase):
    def test_steps_run_in_order_with_delay_after_each_step(self):
        calls = []
        steps = [
            ActionStep(type="key", target="first", delay=0.5),
            ActionStep(type="hotkey", target="ctrl,shift,m", delay=1.5),
            ActionStep(type="launch", target="calc.exe", delay=5),
        ]
        with patch.object(server, "_execute_action", side_effect=lambda kind, target: calls.append((kind, target)) or True), \
             patch.object(server.time, "sleep") as sleep:
            self.assertTrue(server._execute_sequence(steps))
        self.assertEqual(calls, [("key", "first"), ("hotkey", "ctrl,shift,m"), ("launch", "calc.exe")])
        self.assertEqual(sleep.call_args_list, [call(0.5), call(1.5)])

    def test_failure_stops_the_sequence(self):
        calls = []
        def execute(kind, target):
            calls.append((kind, target))
            return len(calls) == 1
        with patch.object(server, "_execute_action", side_effect=execute):
            self.assertFalse(server._execute_sequence([
                ActionStep(type="key", target="first"),
                ActionStep(type="key", target="second"),
                ActionStep(type="key", target="third"),
            ]))
        self.assertEqual(calls, [("key", "first"), ("key", "second")])

    def test_execute_button_dispatches_sequence_and_simple_actions(self):
        sequence = ButtonConfig(id="s1", type="sequence", steps=[{"type": "key", "target": "a"}])
        simple = ButtonConfig(id="b1", type="key", target="playpause")
        with patch.object(server, "_execute_action", return_value=True) as execute:
            self.assertTrue(server._execute_button(sequence))
            self.assertTrue(server._execute_button(simple))
        self.assertEqual(execute.call_args_list, [call("key", "a"), call("key", "playpause")])


if __name__ == "__main__":
    unittest.main()
