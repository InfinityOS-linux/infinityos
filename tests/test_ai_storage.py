import importlib.machinery
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

SOURCE = Path(__file__).resolve().parents[1] / 'packages/infinity-config/root/usr/libexec/infinity-ai-storage'
loader = importlib.machinery.SourceFileLoader('ai_storage', str(SOURCE))
spec = importlib.util.spec_from_loader(loader.name, loader)
storage = importlib.util.module_from_spec(spec)
loader.exec_module(storage)


class StorageTests(unittest.TestCase):
    def test_rejects_unauthenticated_call(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            storage.move('/tmp/model')

    def test_copy_failure_preserves_service_override_and_original_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root / 'source', root / 'target'
            source.mkdir()
            target.mkdir()
            (source / 'weights').write_text('model data')
            dropin = root / 'service' / 'override.conf'
            dropin.parent.mkdir()
            dropin.write_text('previous config')
            def run(*args):
                if args[:2] == ('systemctl', 'show'):
                    return 'ollama'
                if 'cp' in args:
                    raise RuntimeError('disk full')
                return ''
            with patch.object(storage.os, 'geteuid', return_value=0), \
                 patch.dict(os.environ, {'PKEXEC_UID': str(os.getuid())}), \
                 patch.object(storage, 'storage_path', return_value=source), \
                 patch.object(storage, 'DROPIN', dropin), \
                 patch.object(storage, 'run', side_effect=run) as commands, \
                 patch.object(storage.os, 'fchown'), \
                 patch.object(storage.pwd, 'getpwnam', return_value=SimpleNamespace(pw_gid=1000)):
                # In root-run CI the requesting desktop account is simulated.
                caller = os.getuid() or 1000
                with patch.dict(os.environ, {'PKEXEC_UID': str(caller)}), \
                     patch.object(storage.os, 'fstat', return_value=SimpleNamespace(st_uid=caller)):
                    with self.assertRaises(RuntimeError):
                        storage.move(str(target))
            self.assertEqual(dropin.read_text(), 'previous config')
            self.assertEqual((source / 'weights').read_text(), 'model data')
            self.assertIn(('systemctl', 'restart', 'ollama.service'), [call.args for call in commands.call_args_list])

    def test_environment_path_with_spaces(self):
        with patch.object(storage, 'run', return_value='OLLAMA_HOST=127.0.0.1 "OLLAMA_MODELS=/mnt/My Models"'):
            self.assertEqual(storage.storage_path(), Path('/mnt/My Models'))
