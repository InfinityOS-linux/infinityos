import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_updater import SOURCE


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ImprovementsTests(unittest.TestCase):
    def test_cache_invalidates_image_platform_and_patch_but_not_other_files(self):
        module = load(Path(__file__).resolve().parents[1] / 'ghostty/cache-key.py', 'renderer_cache')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'renderer.patch').write_text('one')
            key = module.cache_key(root, 'sha256:one', 'linux/amd64')
            (root / 'README.md').write_text('documentation')
            self.assertEqual(key, module.cache_key(root, 'sha256:one', 'linux/amd64'))
            self.assertNotEqual(key, module.cache_key(root, 'sha256:two', 'linux/amd64'))
            self.assertNotEqual(key, module.cache_key(root, 'sha256:one', 'linux/arm64'))
            (root / 'renderer.patch').write_text('two')
            self.assertNotEqual(key, module.cache_key(root, 'sha256:one', 'linux/amd64'))

    def test_history_keeps_newest_100_private_entries(self):
        history = load(SOURCE / 'history.py', 'operation_history')
        with tempfile.TemporaryDirectory() as tmp, patch.object(history, 'state_path', return_value=Path(tmp)/'state.json'):
            for index in range(103):
                history.record_operation(str(index), 'Failed', 'x' * 3000)
            entries = history.read_history()
            self.assertEqual(len(entries), 100)
            self.assertEqual(entries[0]['source'], '102')
            self.assertEqual(len(entries[0]['detail']), 2000)
            self.assertEqual((Path(tmp)/'history.json').stat().st_mode & 0o777, 0o600)
