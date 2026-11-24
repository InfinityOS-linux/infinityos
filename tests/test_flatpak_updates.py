import os
import runpy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'packages/infinity-setup/root/usr/share/infinityos'))
sys.path.insert(0, str(ROOT / 'packages/infinity-updater/root/usr/share/infinityos/updater'))
import flatpak_updates as fp
import updater


class FlatpakUpdateTests(unittest.TestCase):
    def test_failed_or_unchanged_ref_is_held_by_scope_branch_and_plan(self):
        ref = 'runtime/org.example.Platform/aarch64/45'
        args = ['flatpak', 'update', '--user', '--noninteractive', '--assumeyes', ref]
        for status in (0, 1):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory, \
                    patch.dict(os.environ, XDG_STATE_HOME=directory), \
                    patch.object(fp, 'plan', return_value=[(ref, 'abc')]) as plan, \
                    patch.object(updater, 'apply_command',
                        return_value=subprocess.CompletedProcess(args, status, '', 'disk full')):
                row = fp.classify('user', ref, '', 'fedora')
                self.assertNotIn('deferred', row)
                self.assertNotEqual(updater.apply_flatpak(row, 'user', ref, args, None).returncode, 0)
                held = fp.classify('user', ref, '', 'fedora')
                self.assertTrue(held['retryable'])
                self.assertIn('disk full' if status else 'pending', held['problem'])
                self.assertEqual(updater.install_commands([held]), [])
                self.assertNotIn('deferred', fp.classify('system', ref, '', 'fedora'))
                self.assertNotIn('deferred', fp.classify('user', ref.replace('/45', '/46'), '', 'fedora'))
                plan.return_value = [(ref, 'new')]
                self.assertNotIn('deferred', fp.classify('user', ref, '', 'fedora'))
                plan.return_value = []
                self.assertIsNone(fp.classify('user', ref, '', 'fedora'))

    def test_broker_accepts_only_a_single_full_ref_after_fixed_update_options(self):
        allowed = runpy.run_path(str(ROOT / 'root/usr/libexec/infinityos-install-session'))['allowed']
        prefix = ['/usr/bin/flatpak', 'update', '--system', '--noninteractive', '--assumeyes']
        ref = 'runtime/org.fedoraproject.Platform.GL.default/x86_64/45'
        with patch.dict(os.environ, PKEXEC_UID='1000'):
            self.assertTrue(allowed(prefix + [ref]))
            for suffix in ([ref, ref], ['--commit=abc'], ['org.example.Reader'], [ref + '/extra']):
                self.assertFalse(allowed(prefix + suffix))

    def test_planning_error_visible_next_to_one_ref(self):
        with patch.object(fp, 'plan', side_effect=RuntimeError('runtime unavailable')):
            row = fp.classify('system', 'app/org.test.Reader/x86_64/stable', '1.0', 'test')
            self.assertEqual(row['problem'], 'runtime unavailable')
            self.assertTrue(row['deferred'])


@unittest.skipUnless(os.environ.get('INFINITY_NATIVE_FLATPAK'), 'requires a disposable Fedora Flatpak installation')
class NativeFlatpakTests(unittest.TestCase):
    def test_preview_and_apply_local_runtime_without_reboot(self):
        def run(*args):
            return subprocess.check_output(['flatpak', *map(str, args)], text=True).strip()

        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
                'XDG_DATA_HOME': tmp + '/data', 'XDG_CACHE_HOME': tmp + '/cache',
                'XDG_STATE_HOME': tmp + '/state', 'XDG_CONFIG_HOME': tmp + '/config'}):
            root = Path(tmp)
            name = 'org.infinityos.TestRuntime'
            arch = run('--default-arch')
            ref = f'runtime/{name}/{arch}/stable'
            build = root / 'build'
            repo = root / 'repo'
            (build / 'usr').mkdir(parents=True)
            (build / 'files').mkdir()
            (build / 'metadata').write_text(f'[Runtime]\nname={name}\n')
            def export(revision):
                (build / 'usr/revision').write_text(revision)
                run('build-export', '--runtime', '--arch=' + arch, repo, build, 'stable')
            export('one')
            run('remote-add', '--user', '--no-gpg-verify', 'test-origin', repo.as_uri())
            run('install', '--user', '--assumeyes', '--noninteractive', 'test-origin', ref)
            self.assertIsNone(fp.classify('user', ref, '', 'test-origin'))
            export('two')
            fields = run('remote-ls', '--user', '--updates', '--columns=ref,version,origin').split('\t')
            self.assertEqual(fields[0], ref)
            row = fp.classify('user', *fields)
            self.assertNotIn('deferred', row)
            label, args = updater.install_commands([row])[0]
            previous = run('info', '--user', '--show-commit', ref)
            self.assertTrue(fp.plan('user', ref))
            self.assertEqual(previous, run('info', '--user', '--show-commit', ref))
            result = updater.apply_flatpak(row, 'user', label, args, lambda *_: None)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotEqual(previous, run('info', '--user', '--show-commit', ref))
            self.assertIsNone(fp.classify('user', ref, '', 'test-origin'))


if __name__ == '__main__':
    unittest.main()
