import unittest
from unittest.mock import call, patch

from pydantic import ValidationError

import server
from server import ActionStep, ButtonConfig, DeckConfig, PageConfig


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
                        {"type": "hotkey", "target": "ctrl,shift,m", "delay": 0.2, "condition": "button_on", "condition_target": "gate"},
                        {"type": "launch", "target": "calc.exe", "delay": 0},
                    ],
                }],
            }],
        })
        restored = DeckConfig.model_validate_json(config.model_dump_json())
        self.assertEqual([step.type for step in restored.pages[0].buttons[0].steps], ["hotkey", "launch"])
        self.assertEqual(restored.pages[0].buttons[0].steps[0].delay, 0.2)
        self.assertEqual(restored.pages[0].buttons[0].steps[0].condition, "button_on")
        self.assertEqual(restored.pages[0].buttons[0].steps[0].condition_target, "gate")
        self.assertEqual(restored.pages[0].buttons[0].steps[1].condition, "always")

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


class SequenceConditionTests(unittest.TestCase):
    def config(self, state=False):
        return DeckConfig(pages=[PageConfig(
            id="page_main", name="Principal",
            buttons=[ButtonConfig(id="gate", type="key", target="playpause", is_toggle=True, state=state)],
        )])

    def test_condition_is_optional_and_defaults_to_always(self):
        step = ActionStep(type="key", target="a")
        self.assertEqual(step.condition, "always")
        self.assertTrue(server._condition_met(step))

    def test_button_condition_skips_or_runs_steps(self):
        config = self.config(state=False)
        steps = [
            ActionStep(type="key", target="first", condition="button_on", condition_target="gate"),
            ActionStep(type="key", target="second", condition="button_off", condition_target="gate"),
            ActionStep(type="key", target="third", condition="button_on", condition_target="missing"),
        ]
        calls = []
        with patch.object(server, "_execute_action", side_effect=lambda kind, target: calls.append(target) or True):
            self.assertTrue(server._execute_sequence(steps, config))
        self.assertEqual(calls, ["second"])

        config.pages[0].buttons[0].state = True
        calls.clear()
        with patch.object(server, "_execute_action", side_effect=lambda kind, target: calls.append(target) or True):
            self.assertTrue(server._execute_sequence(steps, config))
        self.assertEqual(calls, ["first"])

    def test_app_and_microphone_conditions(self):
        app_step = ActionStep(type="key", target="a", condition="app_running", condition_target="spotify")
        with patch.object(server, "_is_app_running", return_value=False):
            self.assertFalse(server._condition_met(app_step))
        with patch.object(server, "_is_app_running", return_value=True):
            self.assertTrue(server._condition_met(app_step))

        mic_step = ActionStep(type="key", target="a", condition="mic_muted")
        with patch.object(server.audio_engine, "get_system_states", return_value={"mic_muted": True}):
            self.assertTrue(server._condition_met(mic_step))
        unmuted = ActionStep(type="key", target="a", condition="mic_unmuted")
        with patch.object(server.audio_engine, "get_system_states", return_value={"mic_muted": True}):
            self.assertFalse(server._condition_met(unmuted))

    def test_execution_reads_button_state_between_steps(self):
        for initial in (False, True):
            with self.subTest(initial=initial):
                gate = self.config(initial).pages[0].buttons[0]
                steps = [
                    ActionStep(type="key", target="first"),
                    ActionStep(type="key", target="on", condition="button_on", condition_target="gate"),
                    ActionStep(type="key", target="off", condition="button_off", condition_target="gate"),
                ]
                executed = []
                def execute(kind, target):
                    executed.append(target)
                    if target == "first":
                        gate.state = not initial
                    return True
                with patch.object(server.config_store, "get_button", side_effect=lambda _: gate.model_copy(deep=True)), \
                     patch.object(server, "_execute_action", side_effect=execute):
                    self.assertTrue(server._execute_button(ButtonConfig(id="s", type="sequence", steps=steps)))
                self.assertEqual(executed, ["first", "off" if initial else "on"])

    def test_missing_or_non_toggle_live_button_never_satisfies_condition(self):
        for button in (None, ButtonConfig(id="gate", type="key", target="a", state=True)):
            with self.subTest(button=button), patch.object(server.config_store, "get_button", return_value=button):
                for condition in ("button_on", "button_off"):
                    self.assertFalse(server._condition_met(ActionStep(type="key", target="a", condition=condition, condition_target="gate")))


class ActionTestTests(unittest.TestCase):
    def test_key_and_hotkey_validation(self):
        self.assertTrue(server._test_action_request(ButtonConfig(id="k", type="key", target="playpause"), None)["ok"])
        self.assertFalse(server._test_action_request(ButtonConfig(id="k", type="key", target="not-a-key"), None)["ok"])
        self.assertTrue(server._test_action_request(ButtonConfig(id="h", type="hotkey", target="ctrl,shift,m"), None)["ok"])
        self.assertFalse(server._test_action_request(ButtonConfig(id="h", type="hotkey", target="ctrl,nope"), None)["ok"])

    def test_launch_validation(self):
        self.assertTrue(server._test_action_request(ButtonConfig(id="l", type="launch", target="https://example.com"), None)["ok"])
        self.assertTrue(server._test_action_request(ButtonConfig(id="l", type="launch", target="ms-settings:"), None)["ok"])
        self.assertTrue(server._test_action_request(ButtonConfig(id="l", type="launch", target="start discord:"), None)["ok"])
        self.assertFalse(server._test_action_request(ButtonConfig(id="l", type="launch", target="C:/missing/file.exe"), None)["ok"])

    def test_audio_validation_reports_missing_session(self):
        inventory = {"devices": [{"name": "Speakers", "target": "device:Speakers"}], "apps": [{"name": "Spotify", "process": "spotify.exe", "target": "app:spotify"}]}
        with patch.object(server, "get_audio_targets", return_value=inventory):
            self.assertTrue(server._test_action_request(ButtonConfig(id="a", type="slider", target="master"), None)["ok"])
            self.assertTrue(server._test_action_request(ButtonConfig(id="a", type="slider", target="app:spotify"), None)["ok"])
            self.assertFalse(server._test_action_request(ButtonConfig(id="a", type="slider", target="app:discord"), None)["ok"])
            self.assertTrue(server._test_action_request(ButtonConfig(id="a", type="volume_app", target="spotify:+10"), None)["ok"])
            self.assertFalse(server._test_action_request(ButtonConfig(id="a", type="volume_app", target="spotify:jump"), None)["ok"])

    def test_sequence_validation_includes_conditions(self):
        config = DeckConfig(pages=[PageConfig(id="p", name="P", buttons=[ButtonConfig(id="gate", type="key", target="a", is_toggle=True)])])
        valid = ButtonConfig(id="s", type="sequence", steps=[
            {"type": "key", "target": "a", "condition": "button_on", "condition_target": "gate"},
            {"type": "launch", "target": "https://example.com"},
        ])
        self.assertTrue(server._test_action_request(valid, config)["ok"])
        invalid = ButtonConfig(id="s", type="sequence", steps=[
            {"type": "key", "target": "a", "condition": "button_on", "condition_target": "missing"},
        ])
        result = server._test_action_request(invalid, config)
        self.assertFalse(result["ok"])
        self.assertIn("action.condition.button_missing", [check["code"] for check in result["checks"]])

    def test_audio_device_actions_use_devices_not_app_sessions(self):
        inventory = {"devices": [{"name": "Speakers", "target": "device:Speakers"}], "apps": []}
        with patch.object(server, "get_audio_targets", return_value=inventory), \
             patch.object(server.audio_engine, "adjust_relative", return_value=True) as adjust, \
             patch.object(server, "toggle_audio_target_mute", return_value=True) as mute:
            for target in ("device:Speakers:+10", "device:Speakers:-2.5", "device:Speakers:mute", "general:+5"):
                with self.subTest(target=target):
                    button = ButtonConfig(id="a", type="volume_app", target=target)
                    self.assertTrue(server._test_action_request(button, None)["ok"])
                    # Validation must never execute the audio command.
                    adjust.assert_not_called()
                    mute.assert_not_called()
            self.assertFalse(server._test_action_request(ButtonConfig(id="a", type="volume_app", target="device:Missing:+10"), None)["ok"])
            self.assertFalse(server._test_action_request(ButtonConfig(id="a", type="volume_app", target="device:Speakers:jump"), None)["ok"])


if __name__ == "__main__":
    unittest.main()
