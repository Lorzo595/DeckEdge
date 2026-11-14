import asyncio
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import server
from discord_rpc import DiscordRPCService


@unittest.skipUnless(os.name == 'nt', 'Windows replacement sharing')
class AtomicWriteTests(unittest.TestCase):
    def test_transient_permission_failure_retries_completed_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'config.json'
            replace = os.replace
            attempts = []
            def busy(source, target):
                attempts.append(source)
                if len(attempts) < 3:
                    raise PermissionError('temporarily in use')
                replace(source, target)
            with patch.object(server.os, 'replace', side_effect=busy), patch.object(server.time, 'sleep'):
                server._write_json_atomic(path, {'saved': True})
            self.assertEqual(len(attempts), 3)
            self.assertEqual(len(set(attempts)), 1)
            self.assertIn('true', path.read_text())

    def test_permanent_failure_is_bounded_and_keeps_original(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'config.json'
            path.write_text('original')
            with patch.object(server.os, 'replace', side_effect=PermissionError('denied')) as replace:
                with patch.object(server.time, 'sleep'), self.assertRaises(PermissionError):
                    server._write_json_atomic(path, {'saved': True})
            self.assertEqual(replace.call_count, 5)
            self.assertEqual(path.read_text(), 'original')
            self.assertEqual(list(Path(folder).glob('*.tmp')), [])


class AudioCommandTests(unittest.TestCase):
    def test_relative_device_and_prefixed_application_reach_engine(self):
        with patch.object(server.audio_engine, 'adjust_relative', return_value=True) as adjust:
            self.assertTrue(server.adjust_audio_volume('device:Headphones:+5'))
            adjust.assert_called_with('device:headphones', .05)
            self.assertTrue(server.adjust_audio_volume('app:spotify:-10'))
            adjust.assert_called_with('app:spotify', -.1)

    def test_mute_keeps_device_prefix_and_empty_targets_are_ignored(self):
        with patch.object(server, 'toggle_audio_target_mute', return_value=True) as mute:
            self.assertTrue(server.adjust_audio_volume('device:Headphones:mute'))
            mute.assert_called_once_with('device:headphones')
            for target in (':mute', 'app::mute', 'device::mute'):
                self.assertFalse(server.adjust_audio_volume(target))
            mute.assert_called_once()


class ButtonCommandTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name)
        self.store = server.ConfigStore(root / 'config.json', root / 'config.json.bak')
        self.store.save(server.DeckConfig(pages=[server.PageConfig(
            id='page_main', name='Principal', buttons=[server.ButtonConfig(
                id='toggle', type='key', target='playpause', is_toggle=True,
            )],
        )]))
        for name, value in [('config_store', self.store), ('manager', Mock(broadcast=AsyncMock()))]:
            patcher = patch.object(server, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    async def test_disk_failure_does_not_suppress_command(self):
        with patch.object(server, '_execute_action', return_value=True) as execute:
            with patch.object(self.store, 'update', side_effect=OSError('disk full')):
                with self.assertLogs('DeckEdge', level='ERROR'):
                    await server.handle_button_click('toggle')
            execute.assert_called_once_with('key', 'playpause')

    async def test_command_runs_before_slow_write(self):
        entered, release = threading.Event(), threading.Event()
        original = self.store.update
        def slow_write(mutator):
            entered.set()
            if not release.wait(3):
                raise TimeoutError('test write not released')
            return original(mutator)
        with patch.object(server, '_execute_action', return_value=True) as execute:
            with patch.object(self.store, 'update', side_effect=slow_write):
                task = asyncio.create_task(server.handle_button_click('toggle'))
                try:
                    self.assertTrue(await asyncio.to_thread(entered.wait, 2))
                    execute.assert_called_once()
                finally:
                    release.set()
                    await task

    async def test_two_clicks_execute_twice_and_restore_original_state(self):
        with patch.object(server, '_execute_action', return_value=True) as execute:
            await asyncio.gather(server.handle_button_click('toggle'), server.handle_button_click('toggle'))
            self.assertEqual(execute.call_count, 2)
            self.assertFalse(self.store.get_button('toggle').state)

    async def test_hardware_sync_during_command_is_not_toggled_again(self):
        def execute(*args):
            def sync(config):
                config.pages[0].buttons[0].state = True
                return None, True
            self.store.update(sync)
            return True
        with patch.object(server, '_execute_action', side_effect=execute):
            await server.handle_button_click('toggle')
        self.assertTrue(self.store.get_button('toggle').state)

    async def test_false_mute_result_does_not_suppress_successful_unmute(self):
        def setup(config):
            button = config.pages[0].buttons[0]
            button.type, button.target, button.state = 'volume_app', 'master:mute', True
            return None, True
        self.store.update(setup)
        with patch.object(server, '_execute_action', return_value=False):
            await server.handle_button_click('toggle')
        self.assertFalse(self.store.get_button('toggle').state)

    async def test_edit_during_command_is_preserved(self):
        def execute(*args):
            def edit(config):
                config.pages[0].buttons[0].target = 'nexttrack'
                return None, True
            self.store.update(edit)
            return True
        with patch.object(server, '_execute_action', side_effect=execute):
            await server.handle_button_click('toggle')
        button = self.store.get_button('toggle')
        self.assertEqual(button.target, 'nexttrack')
        self.assertFalse(button.state)


class DiscordDisconnectTests(unittest.TestCase):
    def test_pipe_lost_before_write_cleans_pending_without_inverting_locks(self):
        service = DiscordRPCService.__new__(DiscordRPCService)
        service.pipe, service.handle, service.is_connected = Mock(), 1, True
        service._pending_events, service._pending_responses = {}, {}
        held = []
        class StateLock:
            def __enter__(self):
                if held:
                    raise AssertionError('state lock acquired while write lock is held')
            def __exit__(self, *args):
                pass
        class WriteLock:
            def __enter__(self):
                held.append(True)
                service.pipe = None
            def __exit__(self, *args):
                held.clear()
        service._lock, service._write_lock = StateLock(), WriteLock()
        # Keep errors observable: the production method catches write exceptions.
        service._close_pipe = Mock(side_effect=AssertionError('unexpected write failure'))
        self.assertIsNone(service.send_command('test', {}))
        self.assertEqual(service._pending_events, {})
        self.assertEqual(service._pending_responses, {})
        service._close_pipe.assert_not_called()
