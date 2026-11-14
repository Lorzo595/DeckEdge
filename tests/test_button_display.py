import unittest

from server import ButtonConfig, active_button_display, hardware_state_for


class ButtonDisplayTests(unittest.TestCase):
    def test_active_display_is_shared_for_record_and_audio_icons(self):
        self.assertEqual(
            active_button_display(ButtonConfig(id="rec", icon="🔴", label="REC / OBS")),
            ("⏹️", "REC EN COURS"),
        )
        self.assertEqual(
            active_button_display(ButtonConfig(id="deaf", icon="🎧", label="Sourdine")),
            ("🔇", "SOURDINE"),
        )

    def test_app_prefixed_target_maps_to_application_mute_state(self):
        button = ButtonConfig(id="discord", type="volume_app", target="app:discord", is_toggle=True)
        self.assertIs(hardware_state_for(button, False, False, {"discord": True}), True)

    def test_master_and_microphone_states(self):
        master = ButtonConfig(id="master", type="volume_app", target="master", is_toggle=True)
        mic = ButtonConfig(id="mic", type="volume_app", target="mic:mute", is_toggle=True)
        self.assertIs(hardware_state_for(master, False, True, {}), True)
        self.assertIs(hardware_state_for(mic, True, False, {}), True)

    def test_unknown_target_does_not_invent_a_state(self):
        button = ButtonConfig(id="unknown", type="hotkey", target="ctrl,f9", is_toggle=True)
        self.assertIsNone(hardware_state_for(button, False, False, {}))


if __name__ == "__main__":
    unittest.main()
