"""Exercise rEFInd activation and cleanup against firmware snapshots."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / 'root/usr/libexec/infinityos-refind-install'
TARGET = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
OTHER = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'
REFIND = r'\EFI\refind\refind_x64.efi'


def efi_entry(label='Infinity OS rEFInd', partuuid=TARGET, path=REFIND, active=True, wrapped=True):
    flag = '*' if active else ' '
    loader = f'File({path})' if wrapped else path
    return f'{flag} {label}\tHD(1,GPT,{partuuid},0x800,0x100000)/{loader}'


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
                        TEST_EFI_LOG=str(self.log), TEST_EFI_FAILURE='', TEST_ESP_PARTUUID=TARGET)
        self.write('usr/share/rEFInd/refind/refind_x64.efi', 'EFI fixture')
        self.write('usr/share/infinityos/refind-theme/theme.conf', 'theme')
        for suffix in ('', '_recovery', '_esde', '_steam'):
            self.write(f'usr/share/infinityos/refind-theme/icons/os_infinityos{suffix}.png', 'icon')
        self.write('usr/share/infinityos/efi-drivers/x64/UsbXbox360Dxe.efi', 'driver')
        self.write('usr/share/infinityos/efi-drivers/config.ini', 'config')
        self.write('usr/libexec/infinityos-refind-short-labels', '#!/bin/sh\nexit 0\n', executable=True)
        for name, body in [('uname', 'echo x86_64'), ('findmnt', 'echo /dev/nvme0n1p1'),
                           ('lsblk', 'case "$*" in *PARTUUID*) echo "$TEST_ESP_PARTUUID";; '
                            '*PKNAME*) echo nvme0n1;; *) echo 1;; esac')]:
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
if operation == '-C':
    label = args[args.index('-L') + 1]
    loader = args[args.index('-l') + 1]
    partuuid = os.environ['TEST_ESP_PARTUUID']
    if os.environ['TEST_EFI_WRAP_CREATE'] == '1':
        loader = f'File({loader})'
    state['entries']['00AB'] = f'* {label}\tHD(1,GPT,{partuuid},0x800,0x100000)/{loader}'
    path.write_text(json.dumps(state))
elif operation == '-o':
    order = args[1].split(',')
    if any(entry.upper() not in state['entries'] for entry in order):
        print('entry does not exist', file=sys.stderr)
        sys.exit(8)
    state['order'] = args[1]
    path.write_text(json.dumps(state))
elif operation == '-b':
    del state['entries'][args[1]]
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

    def run_firmware(self, order, entries, failure='', mode='--activate', partuuid=TARGET,
                     wrapped_create=True):
        self.log.unlink(missing_ok=True)
        state = {'entries': entries}
        if order is not None:
            state['order'] = order
        self.state.write_text(json.dumps(state))
        return subprocess.run(['/bin/bash', str(INSTALL), str(self.esp), mode],
                              env=dict(self.env, TEST_EFI_FAILURE=failure, TEST_ESP_PARTUUID=partuuid,
                                       TEST_EFI_WRAP_CREATE='1' if wrapped_create else '0'),
                              capture_output=True, text=True)

    def commands(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def test_reported_missing_2002_preserves_other_firmware_entries(self):
        result = self.run_firmware('0004,0000,2001,2005,2002', {
            '0004': efi_entry(), '0000': '* Windows Boot Manager',
            '2001': '* EFI USB Device', '2005': ' EFI Network'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.state.read_text())['order'], '0004,0000,2001,2005')
        self.assertIn('2002', result.stderr)
        self.assertEqual(self.commands(), [['-v'], ['-o', '0004,0000,2001,2005']])

    def test_existing_entries_keep_order_and_inactive_entries_survive(self):
        result = self.run_firmware('00cd,0004,00CD,0000,2002', {
            '0004': efi_entry(), '00CD': ' Other operating system',
            '0000': '* Windows Boot Manager', '2001': '* Unordered device'})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.state.read_text())['order'], '0004,00CD,0000')

    def test_new_refind_entry_uses_refreshed_firmware_snapshot(self):
        result = self.run_firmware('0000,2002', {'0000': efi_entry(partuuid=OTHER)})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.state.read_text())['order'], '00AB,0000')
        self.assertEqual([command[0] for command in self.commands()], ['-v', '-C', '-v', '-o'])
        self.assertEqual(self.commands()[1][1:], [
            '-d', '/dev/nvme0n1', '-p', '1', '-L', 'Infinity OS rEFInd', '-l', REFIND])

    def test_live_x64_install_activates_a_bare_refind_path_in_dual_boot(self):
        entries = {
            '0000': efi_entry('cachyos', OTHER, r'\EFI\CACHYOS\GRUBX64.EFI', wrapped=False),
            '0001': efi_entry('UEFI OS', OTHER, r'\EFI\BOOT\BOOTX64.EFI0000424f', wrapped=False),
            '0002': '* Live USB',
            '0003': efi_entry('Infinity OS', TARGET, r'\EFI\infinityos\shimx64.efi', wrapped=False),
        }
        result = self.run_firmware('0003,0000,0001,0002', entries, wrapped_create=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads(self.state.read_text())
        self.assertEqual(state['order'], '00AB,0003,0000,0001,0002')
        self.assertEqual({identifier: state['entries'][identifier] for identifier in entries}, entries)
        self.assertEqual([command[0] for command in self.commands()], ['-v', '-C', '-v', '-o'])

    def test_bare_refind_paths_still_require_active_entry_and_exact_esp_and_loader(self):
        entries = {
            '0001': efi_entry(partuuid=OTHER, wrapped=False),
            '0002': efi_entry(path=REFIND + '.bak', wrapped=False),
            '0003': efi_entry(active=False, wrapped=False),
            '0004': efi_entry('Renamed', TARGET.upper(), REFIND.upper(), wrapped=False),
        }
        result = self.run_firmware('0001,0002,0003,0004', entries)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.commands(), [['-v'], ['-o', '0004,0001,0002,0003']])

    def test_missing_bootorder_can_be_initialized(self):
        result = self.run_firmware(None, {'0004': efi_entry()})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.state.read_text())['order'], '0004')

    def test_malformed_order_and_real_firmware_errors_still_fail(self):
        for failure, order, entries in [
            ('', '0004,not-an-id', {'0004': efi_entry()}),
            ('', '0004,', {'0004': efi_entry()}),
            ('-v', '0004', {'0004': efi_entry()}),
            ('-C', '0000', {'0000': '* Windows Boot Manager'}),
            ('-o', '0000,0004', {'0000': '* Windows Boot Manager', '0004': efi_entry()}),
        ]:
            with self.subTest(failure=failure, order=order):
                result = self.run_firmware(order, entries, failure)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(json.loads(self.state.read_text())['order'], order)

    def test_matching_label_on_other_partition_or_wrong_path_is_ignored(self):
        result = self.run_firmware('0001,0002,0003,0004', {
            '0001': efi_entry(partuuid=OTHER),
            '0002': efi_entry(path=REFIND + '.bak'),
            '0003': efi_entry(active=False),
            '0004': efi_entry(label='Renamed entry', partuuid=TARGET.upper(), path=REFIND.upper()),
        })
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.commands(), [['-v'], ['-o', '0004,0001,0002,0003']])

    def test_unchanged_order_does_not_require_an_nvram_write(self):
        result = self.run_firmware('000a,0000', {
            '000A': efi_entry(), '0000': '* Windows Boot Manager'}, failure='-o')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.commands(), [['-v']])

    def test_mbr_partition_id_can_be_matched(self):
        label = f'* Infinity OS rEFInd\tHD(1,MBR,0x12ab,0x800,0x100000)/File({REFIND})'
        result = self.run_firmware('0004', {'0004': label}, partuuid='000012ab-01')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.commands(), [['-v']])

    def test_cleanup_deletes_only_obsolete_entries_on_target_esp(self):
        systemd_loader = r'\EFI\SYSTEMD\SYSTEMD-BOOTX64.EFI'
        entries = {
            '0001': efi_entry('Linux Boot Manager', OTHER, systemd_loader),
            '0002': efi_entry('Linux Boot Manager', TARGET, systemd_loader),
            '0003': efi_entry('Old Infinity OS', TARGET, r'\EFI\infinityos\shimx64.efi',
                              active=False, wrapped=False),
            '0004': efi_entry('Fedora', TARGET, r'\EFI\fedora\shimx64.efi'),
            '0005': efi_entry('Systemd loader backup', TARGET, systemd_loader + '.bak'),
            '0006': efi_entry(f'Label\tHD(1,GPT,{TARGET},0,0)/File({systemd_loader})', OTHER, systemd_loader),
            '0007': efi_entry(),
            '0008': efi_entry('Ambiguous loader', TARGET, systemd_loader + '0000424f', wrapped=False),
            '0009': efi_entry('Other system', OTHER, systemd_loader, wrapped=False),
        }
        result = self.run_firmware('0001,0002,0003,0004,0005,0006,0007,0008,0009', entries,
                                   mode='--remove-obsolete-entries')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.commands(), [['-v'], ['-b', '0002', '-B'], ['-b', '0003', '-B']])
        self.assertEqual(set(json.loads(self.state.read_text())['entries']),
                         {'0001', '0004', '0005', '0006', '0007', '0008', '0009'})

    def test_cleanup_propagates_read_write_and_invalid_partition_failures(self):
        entries = {'0001': efi_entry(path=r'\EFI\systemd\systemd-bootx64.efi')}
        for failure, partuuid in (('-v', TARGET), ('-b', TARGET), ('', '')):
            with self.subTest(failure=failure, partuuid=partuuid):
                result = self.run_firmware('0001', entries, failure, '--remove-obsolete-entries', partuuid)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(json.loads(self.state.read_text())['entries'], entries)


if __name__ == '__main__':
    unittest.main()
