import importlib.machinery
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader('nested', str(Path(__file__).resolve().parents[1] / 'root/usr/libexec/infinityos-backups-nested'))
spec = importlib.util.spec_from_loader(loader.name, loader)
nested = importlib.util.module_from_spec(spec)
loader.exec_module(nested)


class NestedTests(unittest.TestCase):
    def test_only_var_descendants_are_selected_in_parent_first_order(self):
        for fsroot, target in [('/root', '/'), ('/root/var', '/var')]:
            with patch.object(nested, 'run', side_effect=[
                json.dumps({'filesystems': [{'fsroot': fsroot, 'target': target}]}),
                '\n'.join('ID 258 gen 36 top level 257 path ' + p for p in [
                    '<FS_TREE>/root/var/lib/machines/guest', 'root/var/lib/machines',
                    '<FS_TREE>/root/var/lib/portables', 'root/various/other', 'home',
                    'root/.snapshots/1/snapshot', 'root/var'
                ])
            ]):
                self.assertEqual(nested.nested_paths(), ['lib/machines', 'lib/portables', 'lib/machines/guest'])

    def test_rejects_unsafe_paths(self):
        for value in ['', '/', '/etc', '../etc', 'lib/../../etc', '.', 'lib//machines']:
            with self.assertRaises(ValueError):
                nested.relative_path(value)

    def test_incomplete_or_writable_companions_cannot_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            with self.assertRaises(FileNotFoundError):
                nested.manifest(directory)
            (directory / 'paths.json').write_text('["lib/machines"]')
            with patch.object(nested, 'run', return_value='ro=false'):
                with self.assertRaises(ValueError):
                    nested.manifest(directory)
