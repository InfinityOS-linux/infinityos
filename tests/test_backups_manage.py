import importlib.machinery
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'root/usr/libexec/infinityos-backups-manage'
loader = importlib.machinery.SourceFileLoader('backups_manage', str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
backend = importlib.util.module_from_spec(spec)
loader.exec_module(backend)


class BackupsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ready = self.root / 'ready'
        self.ready.touch()
        for name, value in [('SNAPSHOTS', self.root), ('READY', self.ready)]:
            patcher = patch.object(backend, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def snapshot(self, number, companion=True):
        path = self.root / str(number)
        (path / 'snapshot').mkdir(parents=True)
        (path / 'info.xml').write_text(f'<snapshot><num>{number}</num><date>2026-11-08 12:00:00</date><description>Before &amp; after</description></snapshot>')
        if companion:
            (self.root / f'var-{number}').mkdir()

    def command(self, *args):
        if args[:3] == ('btrfs', 'subvolume', 'get-default'):
            return 'ID 256 gen 10 top level 5 path root'
        if args[:3] == ('btrfs', 'inspect-internal', 'rootid'):
            return '256' if args[-1] == '/' else '257' if args[-1] == '/var' else '300'
        return ''

    def test_lists_pairs_legacy_and_partial_deletion_for_retry(self):
        self.snapshot(2)
        self.snapshot(3, companion=False)
        (self.root / 'var-in-root-3').touch()
        self.snapshot(4, companion=False)
        (self.root / 'var-5').mkdir()
        records = backend.snapshots()['snapshots']
        self.assertEqual([r['number'] for r in records], ['5', '4', '3', '2'])
        self.assertEqual([r['complete'] for r in records], [False, False, True, True])
        self.assertEqual(records[-1]['description'], 'Before & after')
        self.ready.unlink()
        self.assertEqual(backend.snapshots(), {'ready': False, 'snapshots': []})

    def test_delete_root_before_companion_and_remove_marker(self):
        self.snapshot(2)
        marker = self.root / 'var-in-root-2'
        marker.touch()
        with patch.object(backend, 'run', side_effect=self.command) as run:
            backend.delete('2')
        commands = [c.args for c in run.call_args_list]
        self.assertLess(commands.index(('snapper', '-c', 'root', 'delete', '2')),
                        commands.index(('btrfs', 'subvolume', 'delete', str(self.root / 'var-2'))))
        self.assertFalse(marker.exists())

    def test_failed_root_deletion_keeps_companion(self):
        self.snapshot(2)
        def command(*args):
            if args[0] == 'snapper':
                raise subprocess.CalledProcessError(1, args)
            return self.command(*args)
        with patch.object(backend, 'run', side_effect=command) as run:
            with self.assertRaises(subprocess.CalledProcessError):
                backend.delete('2')
        self.assertFalse(any(c.args[:3] == ('btrfs', 'subvolume', 'delete') for c in run.call_args_list))

    def test_rejects_path_injection_zero_and_default_root(self):
        with patch.object(backend, 'run') as run:
            for number in ['0', '../2', '2-3', '2;reboot', '-1']:
                with self.assertRaises(ValueError):
                    backend.delete(number)
            run.assert_not_called()
        self.snapshot(2)
        def command(*args):
            if args[-1] == str(self.root / '2/snapshot'):
                return '256'
            return self.command(*args)
        with patch.object(backend, 'run', side_effect=command) as run:
            with self.assertRaises(ValueError):
                backend.delete('2')
        self.assertFalse(any(c.args[0] == 'snapper' for c in run.call_args_list))

    def test_orphan_companion_can_be_deleted_on_retry(self):
        (self.root / 'var-7').mkdir()
        with patch.object(backend, 'run', side_effect=self.command) as run:
            backend.delete('7')
        self.assertIn(('btrfs', 'subvolume', 'delete', str(self.root / 'var-7')), [c.args for c in run.call_args_list])
        self.assertFalse(any(c.args[0] == 'snapper' for c in run.call_args_list))


if __name__ == '__main__':
    unittest.main()
