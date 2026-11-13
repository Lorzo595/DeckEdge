import unittest
from types import SimpleNamespace
from audio_sessions import collect_application_volumes


class Volume:
    def __init__(self, level=0.5, muted=False):
        self.level, self.muted = level, muted

    def QueryInterface(self, _): return self
    def GetMasterVolume(self): return self.level
    def GetMute(self): return self.muted
    def SetMasterVolume(self, value, _): self.level = value
    def SetMute(self, value, _): self.muted = bool(value)


def session(name, volume=None, state=0):
    item = SimpleNamespace(Process=SimpleNamespace(name=lambda: name), State=state, _ctl=volume or Volume())
    item.QueryInterface = lambda _: item
    return item


def device(name, sessions):
    enumerator = SimpleNamespace(GetCount=lambda: len(sessions), GetSession=lambda i: sessions[i])
    return SimpleNamespace(FriendlyName=name, AudioSessionManager=SimpleNamespace(GetSessionEnumerator=lambda: enumerator))


def collect(*devices):
    return collect_application_volumes(devices, lambda value: value, object(), object())


class AudioSessionTests(unittest.TestCase):
    def test_chrome_on_secondary_output_is_detected(self):
        result = collect(device('Default', [session('Discord.exe')]), device('Sonar Aux', [session('chrome.exe')]))
        self.assertIn('chrome', result)
        self.assertEqual(result['chrome'].outputs, ['Sonar Aux'])

    def test_all_chrome_sessions_are_controlled(self):
        first, second = Volume(0.2), Volume(0.8, True)
        chrome = collect(device('Aux', [session('chrome.exe', first), session('chrome.exe', second)]))['chrome']
        self.assertEqual(chrome.GetMasterVolume(), 0.8)
        self.assertFalse(chrome.GetMute())
        chrome.SetMasterVolume(0.35, None)
        chrome.SetMute(True, None)
        self.assertEqual((first.level, second.level), (0.35, 0.35))
        self.assertTrue(first.muted and second.muted)

    def test_sessions_on_distinct_outputs_are_grouped(self):
        chrome = collect(device('Aux', [session('chrome.exe')]), device('Media', [session('Chrome.EXE')]))['chrome']
        self.assertEqual(chrome.outputs, ['Aux', 'Media'])
        self.assertEqual(len(chrome.controls), 2)

    def test_inaccessible_process_does_not_hide_following_sessions(self):
        broken = session('closed.exe')
        def inaccessible(): raise PermissionError()
        broken.Process.name = inaccessible
        result = collect(device('Aux', [broken, session('chrome.exe')]))
        self.assertIn('chrome', result)

    def test_expired_ignored_but_inactive_retained(self):
        result = collect(device('Aux', [session('expired.exe', state=2), session('chrome.exe', state=0)]))
        self.assertNotIn('expired', result)
        self.assertIn('chrome', result)

    def test_unavailable_device_does_not_hide_other_outputs(self):
        result = collect(SimpleNamespace(), device('Aux', [session('chrome.exe')]))
        self.assertIn('chrome', result)

    def test_zero_volume_is_valid(self):
        chrome = collect(device('Aux', [session('chrome.exe', Volume(0))]))['chrome']
        self.assertEqual(chrome.GetMasterVolume(), 0)

    def test_closed_session_does_not_block_other_session(self):
        closed, active = Volume(), Volume(0.7)
        def unavailable(*_): raise RuntimeError('Session terminée')
        closed.GetMasterVolume = unavailable
        closed.SetMasterVolume = unavailable
        chrome = collect(device('Aux', [session('chrome.exe', closed), session('chrome.exe', active)]))['chrome']
        self.assertEqual(chrome.GetMasterVolume(), 0.7)
        chrome.SetMasterVolume(0.25, None)
        self.assertEqual(active.level, 0.25)


if __name__ == '__main__': unittest.main()
