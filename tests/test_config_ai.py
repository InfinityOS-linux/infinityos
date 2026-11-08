import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'packages/infinity-config/root/usr/share/infinityos/config_ai.py'
spec = importlib.util.spec_from_file_location('config_ai', SOURCE)
ai = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ai)


class ConfigAiTests(unittest.TestCase):
    def test_tab_requires_setup_selection_and_disappears_on_removal(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            binary = home / '.local/bin/codex'
            binary.parent.mkdir(parents=True)
            binary.touch()
            self.assertEqual(ai.selected_ai(home), ())
            desktop = home / '.local/share/applications/infinityos-codex.desktop'
            desktop.parent.mkdir(parents=True)
            desktop.touch()
            self.assertEqual(ai.selected_ai(home), ('codex',))
            desktop.unlink()
            marker = home / '.config/infinityos/local-ai-model'
            marker.parent.mkdir(parents=True)
            marker.write_text('custom:latest')
            self.assertEqual(ai.selected_ai(home), ('local',))
            marker.unlink()
            self.assertEqual(ai.selected_ai(home), ())

    def test_model_name_rejects_options_and_modelfile_injection(self):
        for name in ('-bad', 'model\nFROM secret', '../secret', '', 'a b'):
            self.assertFalse(ai.valid_model(name))
        self.assertTrue(ai.valid_model('library/model:q4'))

    def test_account_commands_use_argv(self):
        self.assertEqual(ai.provider_command('claude', 'logout')[-2:], ['auth', 'logout'])
        with self.assertRaises(ValueError):
            ai.provider_command('other', 'logout')

    def test_claude_signed_out_is_not_an_error(self):
        import subprocess
        with patch.object(ai.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '{"loggedIn":false}')):
            self.assertIsNone(ai.provider_status('claude')['account'])
        with patch.object(ai.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '{}')):
            with self.assertRaises(ValueError):
                ai.provider_status('claude')

    def test_local_settings_save_only_after_ollama_success(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / '.config/infinityos/local-ai-model'
            marker.parent.mkdir(parents=True)
            marker.write_text('old')
            with patch.object(ai, 'ollama', side_effect=[{}, RuntimeError('offline')]):
                with self.assertRaises(RuntimeError):
                    ai.select_local('new', 4096, 1024, 0.5, directory)
            self.assertEqual(marker.read_text(), 'old')
            with patch.object(ai, 'ollama', return_value={}) as api:
                ai.select_local('new', 4096, 1024, 0.5, directory)
            self.assertTrue(marker.read_text().startswith('infinity-config-'))
            self.assertEqual(api.call_args.args[1]['parameters']['num_ctx'], 4096)

    def test_settings_cannot_reenable_ai_removed_during_request(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / '.config/infinityos/local-ai-model'
            marker.parent.mkdir(parents=True)
            marker.write_text('old')
            def api(path, *args, **kwargs):
                if path == 'create':
                    marker.unlink()
                return {}
            with patch.object(ai, 'ollama', side_effect=api):
                with self.assertRaises(RuntimeError):
                    ai.select_local('new', 4096, 1024, 0.5, directory)
            self.assertFalse(marker.exists())

    def test_context_bounds_before_requests(self):
        with patch.object(ai, 'ollama') as api:
            with self.assertRaises(ValueError):
                ai.select_local('model', 1024, 2048, 0.8)
            api.assert_not_called()

    def test_codex_stdio_handles_notifications_and_optional_unsupported_usage(self):
        import sys
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / 'codex'
            binary.write_text(f'#!{sys.executable}\n' + '''import sys,json
for line in sys.stdin:
    message=json.loads(line)
    if 'id' not in message: continue
    method=message['method']
    reply={'id':message['id'], 'result':{}}
    if method=='account/read': reply['result']={'account':{'type':'chatgpt','email':'example@example.test'}}
    if method=='account/rateLimits/read': reply['result']={'rateLimits':{'primary':{'usedPercent':25}}}
    if method=='account/usage/read': reply={'id':message['id'],'error':{'message':'unsupported'}}
    print(json.dumps({'method':'account/updated','params':{}}), flush=True)
    print(json.dumps(reply),flush=True)
''')
            binary.chmod(0o700)
            result = ai.codex_account(str(binary))
            self.assertEqual(result['account']['email'], 'example@example.test')
            self.assertEqual(result['limits']['rateLimits']['primary']['usedPercent'], 25)
            self.assertEqual(result['usage'], {})

    def test_import_rejects_modelfile_injection(self):
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / 'bad\nPARAMETER.gguf'
            filename.touch()
            with self.assertRaises(ValueError):
                ai.import_model(filename)
