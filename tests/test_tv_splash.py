"""Verify the boot card follows Steam's lifecycle without a graphical session."""
import runpy
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
with patch.dict('sys.modules', {
    'gi': SimpleNamespace(require_version=lambda *args: None),
    'gi.repository': SimpleNamespace(Gio=SimpleNamespace(),
        GLib=SimpleNamespace(SOURCE_CONTINUE=True, SOURCE_REMOVE=False),
        Gtk=SimpleNamespace(Application=object)),
}):
    module = runpy.run_path(str(ROOT / 'root/usr/libexec/infinityos-tv-steam-splash'))
SteamBoot = module['SteamBoot']


class SteamSplashTests(unittest.TestCase):
    def test_portals_receive_compositor_display_without_changing_user_manager(self):
        update = module['update_activation_environment']
        with patch.dict('os.environ', {'DISPLAY': ':2', 'WAYLAND_DISPLAY': 'gamescope-0',
                                      'GDK_BACKEND': 'x11'}, clear=True), \
             patch.object(update.__globals__['subprocess'], 'run') as run:
            update()
        run.assert_called_once_with(['dbus-update-activation-environment',
            'DISPLAY=:2', 'WAYLAND_DISPLAY=gamescope-0', 'XAUTHORITY=',
            'GDK_BACKEND=x11', 'XDG_SESSION_TYPE=', 'XDG_CURRENT_DESKTOP='],
            check=True, timeout=10)

    def test_keeps_card_while_client_runs_and_preserves_exit_status(self):
        state = SimpleNamespace(process=Mock(), quit=Mock(), status=1)
        state.process.poll.side_effect = [None, 7]
        self.assertTrue(SteamBoot.check_client(state))
        state.quit.assert_not_called()
        self.assertFalse(SteamBoot.check_client(state))
        self.assertEqual(state.status, 7)
        state.quit.assert_called_once()

    def test_client_starts_once_after_card_maps(self):
        state = SimpleNamespace(process=None, command=['steam', '-gamepadui'], check_client=Mock())
        with patch.dict(SteamBoot.start_steam.__globals__, subprocess=SimpleNamespace(Popen=Mock()),
                        GLib=SimpleNamespace(timeout_add=Mock())):
            spawn = SteamBoot.start_steam.__globals__['subprocess'].Popen
            SteamBoot.start_steam(state, None)
            SteamBoot.start_steam(state, None)
            spawn.assert_called_once_with(['steam', '-gamepadui'])
