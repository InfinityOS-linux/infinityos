import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'packages/infinity-updater/root/usr/share/infinityos/updater'
sys.path.insert(0, str(SOURCE))
sys.path.insert(0, str(SOURCE.parents[5] / 'infinity-setup/root/usr/share/infinityos'))
import compatibility
import checker
import updater


def package(name, version='2-1', arch='x86_64'):
    return SimpleNamespace(get_name=lambda: name, get_evr=lambda: version, get_arch=lambda: arch)


def row(name, version='2-1', arch='x86_64', **extra):
    return dict(kind='RPM', name=name, version=version, arch=arch, source='test', **extra)


class CompatibilityTests(unittest.TestCase):
    def test_only_exact_skipped_versions_and_architectures_are_deferred(self):
        transaction = SimpleNamespace(get_broken_dependency_packages=lambda: [package('held')],
                                      get_conflicting_packages=lambda: [package('conflict')])
        rows = [row('held'), row('held', arch='i686'), row('held', version='1.5-1'), row('ready'), row('conflict')]
        marked = compatibility.classify_transaction(rows, transaction)
        self.assertEqual([item['name'] for item in marked if item.get('deferred')], ['held', 'conflict'])
        self.assertNotIn('deferred', rows[0], 'input data must not be mutated')
        self.assertEqual(marked[-1]['deferred_reason'], 'conflict')

    def test_new_solver_result_clears_a_previous_hold(self):
        transaction = SimpleNamespace(get_broken_dependency_packages=lambda: [], get_conflicting_packages=lambda: [])
        result = compatibility.classify_transaction([row('held', deferred=True, deferred_reason='dependencies')], transaction)
        self.assertNotIn('deferred', result[0])
        self.assertEqual(updater.install_commands(result)[0][0], 'System packages')

    def test_held_packages_do_not_enable_an_install_or_remaining_update_warning(self):
        held = row('held', deferred=True)
        self.assertEqual(updater.install_commands([held]), [])
        self.assertEqual(updater.pending_rpm_names([held], [held]), [])
        ready = row('ready')
        self.assertEqual(len(updater.install_commands([held, ready])), 1)

    def test_a_downloaded_pending_version_takes_precedence_over_a_hold(self):
        held = row('held', deferred=True)
        offline = {'pending': True, 'packages': [row('held')]}
        result = updater.update_rows([held], offline)
        self.assertTrue(result[0]['pending'])
        self.assertFalse(result[0]['deferred'])

    def test_failed_solver_keeps_the_update_visible_and_reports_uncertainty(self):
        outputs = [SimpleNamespace(returncode=0, stdout='held|2-1|test|x86_64\n', stderr=''),
                   SimpleNamespace(returncode=0, stdout='', stderr=''),
                   SimpleNamespace(returncode=0, stdout='', stderr=''),
                   SimpleNamespace(returncode=0, stdout='{"Devices": []}', stderr='')]
        with patch.object(checker, '_run', side_effect=outputs), \
             patch.object(checker, 'classify_updates', side_effect=RuntimeError('metadata unavailable')), \
             patch.object(checker, 'check_github_updates', return_value=([], [])), \
             patch.object(checker, 'installed_version', return_value=('1.0', 45)), \
             patch.object(checker, 'load_manifest', return_value={'version': '1.0', 'fedora_release': 45}):
            state = checker.check_updates()
        self.assertEqual(len(state['updates']), 1)
        self.assertNotIn('deferred', state['updates'][0])
        self.assertFalse(state['rpm_check_ok'])
        self.assertIn('metadata unavailable', ' '.join(state['errors']))


class NativeSolverTests(unittest.TestCase):
    def test_real_solver_holds_and_releases_an_update_without_installing_anything(self):
        ready = (importlib.util.find_spec('libdnf5') is not None and
                 all(shutil.which(name) for name in ('rpmbuild', 'rpm', 'createrepo_c', 'dnf5')) and os.geteuid() == 0)
        if not ready:
            if os.environ.get('INFINITY_NATIVE_DNF_REQUIRED'):
                self.fail('Native libdnf5/RPM fixture dependencies are unavailable')
            self.skipTest('Native DNF fixture requires Fedora, libdnf5, RPM tools and root in a disposable container')
        import libdnf5
        import libdnf5.base
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            top, repo, system = (root / name for name in ('build', 'repo', 'system'))
            for path in (repo, system, top / 'SPECS'):
                path.mkdir(parents=True)
            def run(args):
                try:
                    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)
                except subprocess.CalledProcessError as error:
                    self.fail(f'{args}:\n{error.output}')
            def build(name, version, requires=''):
                spec = top / 'SPECS' / f'{name}-{version}.spec'
                spec.write_text(f'''Name: {name}
Version: {version}
Release: 1
Summary: Disposable InfinityUpdater solver fixture
License: MIT
BuildArch: noarch
{requires}
%description
A metadata-only dependency solver test package.
%files
''')
                run(['rpmbuild', '--quiet', '--define', f'_topdir {top}', '-bb', str(spec)])
                return top / 'RPMS/noarch' / f'{name}-{version}-1.noarch.rpm'
            old = [build(name, '1') for name in ('infinity-test-ready', 'infinity-test-held')]
            for name, requires in (('infinity-test-ready', ''), ('infinity-test-held', 'Requires: infinity-test-dependency >= 2')):
                shutil.copy2(build(name, '2', requires), repo)
            run(['createrepo_c', '--quiet', str(repo)])
            run(['rpm', '--root', str(system), '--initdb'])
            run(['rpm', '--root', str(system), '-i', '--nodeps', '--nosignature', *map(str, old)])
            installed = run(['rpm', '--root', str(system), '-qa'])
            rows = [row(name, arch='noarch') for name in ('infinity-test-ready', 'infinity-test-held')]
            def inspect(phase):
                base = libdnf5.base.Base()
                config = base.get_config()
                config.installroot = str(system)
                config.plugins = False
                config.reposdir = []
                config.cachedir = str(root / f'cache-{phase}')
                config.system_state_dir = str(root / f'state-{phase}')
                config.best = False
                config.skip_unavailable = True
                base.get_vars().get().set('releasever', '45')
                base.setup()
                sack = base.get_repo_sack()
                source = sack.create_repo('fixture')
                source.get_config().baseurl = [repo.as_uri()]
                source.get_config().gpgcheck = False
                source.get_config().repo_gpgcheck = False
                sack.load_repos()
                return compatibility.classify_transaction(rows, compatibility.resolve(base, libdnf5))
            first = inspect('held')
            self.assertEqual([item['name'] for item in first if item.get('deferred')], ['infinity-test-held'])
            shutil.copy2(build('infinity-test-dependency', '2'), repo)
            run(['createrepo_c', '--quiet', '--update', str(repo)])
            second = inspect('ready')
            self.assertFalse(any(item.get('deferred') for item in second))
            # Verify the CLI used by privileged staging excludes only the failed
            # NEVRA. The other update must proceed without an RPM database write.
            run(['dnf5', '-y', '--installroot', str(system), '--releasever=45',
                 '--setopt=reposdir=/nonexistent', '--repofrompath=fixture,' + repo.as_uri(),
                 '--setopt=fixture.gpgcheck=0', '--setopt=fixture.repo_gpgcheck=0',
                 '--exclude=infinity-test-held-0:2-1.noarch,infinity-test-held-2-1.noarch',
                 'upgrade', '--offline', '--no-best', '--skip-unavailable'])
            transaction = system / 'usr/lib/sysimage/libdnf5/offline/transaction.json'
            batch = json.loads(transaction.read_text())['rpms']
            self.assertEqual([item['nevra'].replace('-0:', '-') for item in batch
                              if item['action'] == 'Upgrade'], ['infinity-test-ready-2-1.noarch'])
            self.assertEqual(run(['rpm', '--root', str(system), '-qa']), installed)


if __name__ == '__main__':
    unittest.main()
