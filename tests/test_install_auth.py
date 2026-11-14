"""One polkit prompt per Apply without turning the helper into a root shell."""

import importlib.util
import io
import json
import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'packages/infinity-setup/root/usr/share/infinityos/launcher_backend.py'
HELPER = ROOT / 'root/usr/libexec/infinityos-install-session'
backend_spec = importlib.util.spec_from_file_location('launcher_backend', SOURCE)
backend = importlib.util.module_from_spec(backend_spec)
backend_spec.loader.exec_module(backend)
helper = ModuleType('install_session')
exec(compile(HELPER.read_text(), str(HELPER), 'exec'), helper.__dict__)


class Input(io.StringIO):
    def close(self):
        self.contents = self.getvalue()
        super().close()


class InstallAuthTests(unittest.TestCase):
    def test_one_authorization_process_handles_multiple_commands(self):
        process = SimpleNamespace(
            stdin=Input(),
            stdout=io.StringIO('{"ready": true}\n{"output": "installed"}\n{"returncode": 0}\n'
                               '{"output": "enabled"}\n{"returncode": 0}\n'),
            wait=lambda timeout: 0,
        )
        with patch.object(backend.subprocess, 'Popen', return_value=process) as popen:
            with backend.privileged_transaction():
                backend._run(['pkexec', 'dnf', '-y', 'install', 'gamescope'])
                backend._run(['pkexec', '/usr/libexec/infinityos-tv-control',
                              'activate', 'steam', '1000'])
        popen.assert_called_once()
        self.assertEqual([json.loads(line) for line in process.stdin.contents.splitlines()], [
            ['dnf', '-y', 'install', 'gamescope'],
            ['/usr/libexec/infinityos-tv-control', 'activate', 'steam', '1000'],
        ])

    def test_helper_accepts_installer_actions_and_rejects_arbitrary_root_commands(self):
        with patch.dict(os.environ, {'PKEXEC_UID': str(os.getuid())}):
            self.assertTrue(helper.allowed(['dnf', '-y', 'install', 'gamescope']))
            self.assertTrue(helper.allowed(['/usr/libexec/infinityos-tv-control',
                                            'activate', 'steam', str(os.getuid())]))
            self.assertTrue(helper.allowed(['/usr/libexec/infinityos-upgrade-system']))
            self.assertFalse(helper.allowed(['sh', '-c', 'touch /root/exposed']))
            self.assertFalse(helper.allowed(['dnf', '-y', 'remove', 'kernel']))
            self.assertFalse(helper.allowed(['rpm', '-e', '--', 'kernel']))
            self.assertFalse(helper.allowed(['flatpak', 'uninstall', '--system',
                                             '--noninteractive', '--assumeyes', 'org.gnome.Software']))
            self.assertFalse(helper.allowed(['/usr/libexec/infinityos-tv-control',
                                             'activate', 'steam', '9999']))

    def test_downloaded_packages_must_stay_in_their_owned_temporary_directory(self):
        with patch.dict(os.environ, {'PKEXEC_UID': str(os.getuid())}), \
             tempfile.TemporaryDirectory(prefix='infinity-setup-', dir='/tmp') as directory:
            package = Path(directory) / 'photo.rpm'
            package.write_bytes(b'rpm')
            self.assertTrue(helper.allowed(['dnf', '-y', 'install', str(package)]))
            self.assertFalse(helper.allowed(['dnf', '-y', 'install', '/tmp/photo.rpm']))

    def test_authorization_is_not_retained_after_apply(self):
        policy = ET.parse(ROOT / 'root/usr/share/polkit-1/actions/org.infinityos.install-session.policy')
        action = policy.find("./action[@id='org.infinityos.install-session']")
        self.assertEqual(action.findtext('./defaults/allow_active'), 'auth_admin')
        self.assertEqual(action.find("./annotate[@key='org.freedesktop.policykit.exec.path']").text,
                         '/usr/libexec/infinityos-install-session')

    def test_cancelled_authorization_is_not_requested_again_in_the_same_apply(self):
        process = SimpleNamespace(stdin=Input(), stdout=io.StringIO(''), wait=lambda timeout: 126)
        with patch.object(backend.subprocess, 'Popen', return_value=process) as popen:
            with backend.privileged_transaction():
                first = backend.run_privileged(['dnf', '-y', 'install', 'mpv'])
                second = backend.run_privileged(['dnf', '-y', 'install', 'gamescope'])
        self.assertNotEqual(first.returncode, 0)
        self.assertNotEqual(second.returncode, 0)
        popen.assert_called_once()


if __name__ == '__main__':
    unittest.main()
