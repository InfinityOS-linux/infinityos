"""Exercise rEFInd activation against firmware snapshots with stale boot IDs."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / 'root/usr/libexec/infinityos-refind-install'


class RefindBootOrderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='infinity-efi-test-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.source = self.base / 'source'
        self.esp = self.base / 'esp'
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        (self.esp / 'EFI').mkdir(parents=True)
        self.state = self.base / 'firmware.json'
        self.log = self.base / 'commands.jsonl'
        self.env = dict(os.environ, PATH=str(self.bin) + ':' + os.environ['PATH'],
                        INFINITYOS_ROOT=str(self.source), TEST_FIRMWARE=str(self.state),
                        TEST_EFI_LOG=str(self.log), TEST_EFI_FAILURE='')
        self.write('usr/share/rEFInd/refind/refind_x64.efi', 'EFI fixture')
        self.write('usr/share/infinityos/refind-theme/theme.conf', 'theme')
        for suffix in ('', '_recovery', '_esde', '_steam'):
            self.write(f'usr/share/infinityos/refind-theme/icons/os_infinityos{suffix}.png', 'icon')
        self.write('usr/share/infinityos/efi-drivers/x64/UsbXbox360Dxe.efi', 'driver')
        self.write('usr/share/infinityos/efi-drivers/config.ini', 'config')
        self.write('usr/libexec/infinityos-refind-short-labels', '#!/bin/sh\nexit 0\n', executable=True)
        for name, body in [('uname', 'echo x86_64'), ('findmnt', 'echo /dev/nvme0n1p1'),
                           ('lsblk', 'case "$*" in *PKNAME*) echo nvme0n1;; *) echo 1;; esac')]:
            path = self.bin / name
            path.write_text('#!/bin/sh\n' + body + '\n')
            path.chmod(0o755)
        firmware = self.bin / 'efibootmgr'
        firmware.write_text(f'#!{sys.executable}\n' + '''
import json, os, pathlib, sys
path = pathlib.Path(os.environ['TEST_FIRMWARE'])
state = json.loads(path.read_text())
args = sys.argv[1:]
with open(os.environ['TEST_EFI_LOG'], 'a') as log:
    log.write(json.dumps(args) + '\\n')
operation = args[0] if args else 'read'
if operation == os.environ.get('TEST_EFI_FAILURE'):
    print('injected firmware error', file=sys.stderr)
    sys.exit(8)
if operation == '-c':
    state['entries']['00AB'] = '* Infinity OS rEFInd'
    state['order'] = '00AB,' + state.get('order', '')
    path.write_text(json.dumps(state))
elif operation == '-o':
    order = args[1].split(',')
    if any(entry.upper() not in state['entries'] for entry in order):
        print('entry does not exist', file=sys.stderr)
        sys.exit(8)
    state['order'] = args[1]
    path.write_text(json.dumps(state))
else:
    if 'order' in state:
        print('BootOrder: ' + state['order'])
    for entry, label in state['entries'].items():
        print('Boot' + entry + label)
''')
        firmware.chmod(0o755)

    def write(self, relative, content, executable=False):
        path = self.source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        if executable:
            path.chmod(0o755)

    def activate(self, order, entries, failure=''):
        state = {'entries': entries}
        if order is not None:
            state['order'] = order
        self.state.write_text(json.dumps(state))
        return subprocess.run(['/bin/bash', str(INSTALL), str(self.esp), '--activate'],
                              env=dict(self.env, TEST_EFI_FAILURE=failure),
                              capture_output=True, text=True)

    def test_reported_missing_2002_preserves_other_firmware_entries(self):
        result = self.activate('0004,0000,2001,2005,2002', {
            '0004': '* Infinity OS rEFInd', '0000': '* Windows Boot Manager',
            '2001': '* EFI USB Device', '2005': ' EFI Network'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.state.read_text())['order'], '0004,0000,2001,2005')
        self.assertIn('2002', result.stderr)
        commands = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual([command for command in commands if command],
                         [['-o', '0004,0000,2001,2005']])

    def test_existing_entries_keep_order_and_inactive_entries_survive(self):
        result = self.activate('00cd,0004,00CD,0000,2002', {
            '0004': '* Infinity OS rEFInd', '00CD': ' Other operating system',
            '0000': '* Windows Boot Manager', '2001': '* Unordered device'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.state.read_text())['order'], '0004,00CD,0000')

    def test_new_refind_entry_uses_refreshed_firmware_snapshot(self):
        result = self.activate('0000,2002', {'0000': '* Windows Boot Manager'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.state.read_text())['order'], '00AB,0000')

    def test_missing_bootorder_can_be_initialized(self):
        result = self.activate(None, {'0004': '* Infinity OS rEFInd'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.state.read_text())['order'], '0004')

    def test_malformed_order_and_real_firmware_errors_still_fail(self):
        for failure, order, entries in [
            ('', '0004,not-an-id', {'0004': '* Infinity OS rEFInd'}),
            ('read', '0004', {'0004': '* Infinity OS rEFInd'}),
            ('-c', '0000', {'0000': '* Windows Boot Manager'}),
            ('-o', '0004', {'0004': '* Infinity OS rEFInd'}),
        ]:
            with self.subTest(failure=failure, order=order):
                result = self.activate(order, entries, failure)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(json.loads(self.state.read_text())['order'], order)


if __name__ == '__main__':
    unittest.main()
