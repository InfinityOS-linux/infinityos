"""Run production shell entry points in an isolated filesystem with fault injection."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BackupInitializationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='infinity-backup-test-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.target = self.base / 'target'
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        self.log = self.base / 'commands.log'
        self.env = dict(os.environ, PATH=str(self.bin) + ':' + os.environ['PATH'],
                        TEST_COMMAND_LOG=str(self.log), TEST_SCENARIO='normal', TEST_ROOT=str(self.target))
        self.command('findmnt', '''
if [[ "$*" == *efi* ]]; then
    [[ $TEST_SCENARIO == missing-efi ]] && exit 1
    echo vfat
elif [[ $TEST_SCENARIO == non-btrfs ]]; then echo ext4
else echo btrfs; fi''')
        self.command('systemctl', '''
printf 'systemctl %s\\n' "$*" >> "$TEST_COMMAND_LOG"
if [[ $1 == is-enabled ]]; then
    case $TEST_SCENARIO in disabled|masked) echo "$TEST_SCENARIO"; exit 1;; *) echo enabled;; esac
elif [[ $1 == is-failed ]]; then
    [[ $TEST_SCENARIO == failed ]]
elif [[ $1 == start && $TEST_SCENARIO == retry-initializes ]]; then
    mkdir -p "$TEST_ROOT/etc/snapper/configs" "$TEST_ROOT/var/lib/infinityos"
    touch "$TEST_ROOT/etc/snapper/configs/root" "$TEST_ROOT/var/lib/infinityos/backups-ready"
elif [[ $1 == disable && $TEST_SCENARIO == disable-error ]]; then exit 1
elif [[ $1 == mask && $TEST_SCENARIO == mask-error ]]; then exit 1
fi''')
        self.command('snapper', 'printf "snapper %s\\n" "$*" >> "$TEST_COMMAND_LOG"')
        self.command('efibootmgr', 'exit 0')
        self.command('dconf', 'exit 0')
        self.command('mount', 'echo mount >> "$TEST_COMMAND_LOG"; exit 1')
        self.command('mountpoint', '[[ $TEST_SCENARIO != unmounted ]]')
        self.command('systemd-inhibit', 'echo update-started >> "$TEST_COMMAND_LOG"')
        # Match GNU install -D and sed -i on the macOS source-test host too.
        self.command('install', '''
if [[ $TEST_SCENARIO == efi-full && "$*" == *efi/os/.initramfs* ]]; then
    echo 'No space left on EFI partition' >&2; exit 1
fi
if [[ $1 == -D ]]; then shift; mkdir -p "$(dirname "${@: -1}")"; fi
exec /usr/bin/install "$@"''')
        self.command('sed', '[[ $1 == -i ]] && exit 0; exec /usr/bin/sed "$@"')

    def command(self, name, body):
        path = self.bin / name
        path.write_text('#!/bin/bash\n' + body + '\n')
        path.chmod(0o755)

    def write(self, name, content=''):
        path = self.target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def helper(self, name, body):
        path = self.write('usr/libexec/' + name, '#!/bin/bash\n' + body + '\n')
        path.chmod(0o755)

    def exercise(self, source, scenario='normal', root_helper=False, arguments=()):
        script = (ROOT / source).read_text()
        # Redirect only production filesystem paths; no host mounts/services run.
        for prefix in ('/sys/firmware/efi', '/usr/lib/systemd/system', '/usr/lib/modules',
                       '/usr/share/infinityos', '/usr/libexec', '/var/lib/infinityos',
                       '/.snapshots', '/etc', '/boot'):
            script = script.replace(prefix, str(self.target) + prefix)
        if root_helper:
            script = script.replace('$EUID', '0')
        path = self.base / 'entry-point.sh'
        path.write_text(script)
        return subprocess.run(['/bin/bash', str(path), *arguments], text=True, capture_output=True,
                              env=dict(self.env, TEST_SCENARIO=scenario))

    def prepare_installer(self):
        for directory in ('sys/firmware/efi', 'boot/efi/EFI/refind', 'boot/efi/EFI/BOOT',
                          'etc/dconf/profile', 'etc/infinityos'):
            (self.target / directory).mkdir(parents=True, exist_ok=True)
        self.write('boot/loader/entries/test.conf', 'version 1.2.3\n')
        self.write('boot/vmlinuz-1.2.3', 'kernel')
        self.write('boot/initramfs-1.2.3.img', 'initrd')
        self.write('etc/kernel/cmdline', 'root=UUID=test rootflags=subvol=root rw\n')
        self.write('etc/os-release', 'PRETTY_NAME="Infinity OS 2.0 (Fedora 45)"\n')
        self.write('usr/share/infinityos/image-release-version', '2.0\n')
        self.write('usr/share/infinityos/firefox/installed-policies.json', '{}')
        self.helper('infinityos-refind-install', '''
printf 'refind-install %s\n' "${2:-copy}" >> "$TEST_COMMAND_LOG"
if [[ ${2:-} == --activate && $TEST_SCENARIO == nvram-denied ]]; then
    echo 'NVRAM write denied' >&2; exit 1
fi''')
        self.helper('infinityos-remove-obsolete-efi-loaders', 'exit 0')
        self.helper('infinityos-refind-config', '''
printf 'menuentry "Backups" {}\\n' > "$1/EFI/refind/refind.conf"
cp "$1/EFI/refind/refind.conf" "$1/EFI/BOOT/refind.conf"''')

    def test_missing_optional_boot_units_do_not_abort_installer(self):
        self.prepare_installer()
        result = self.exercise('root/usr/libexec/infinityos-liveinstall-boot-setup')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.target / 'etc/infinityos/refind-installed').is_file())
        log = self.log.read_text()
        self.assertIn('enable infinityos-snapper-setup.service', log)
        self.assertNotIn('systemctl disable ', log)
        self.assertIn('systemctl mask --force ', log)
        self.assertLess(log.index('refind-install --activate'), log.index('refind-install --remove-obsolete-entries'))

    def test_failed_efi_or_nvram_work_does_not_leave_backup_services_unregistered(self):
        for scenario in ('efi-full', 'nvram-denied', 'missing-efi'):
            with self.subTest(scenario=scenario):
                self.prepare_installer()
                result = self.exercise('root/usr/libexec/infinityos-liveinstall-boot-setup', scenario)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('enable infinityos-snapper-setup.service', self.log.read_text())
                self.assertFalse((self.target / 'etc/infinityos/refind-installed').exists())

    def test_real_disable_and_mask_errors_still_fail_installation(self):
        self.prepare_installer()
        self.write('usr/lib/systemd/system/systemd-boot-update.service', '[Service]\n')
        for scenario in ('disable-error', 'mask-error'):
            with self.subTest(scenario=scenario):
                result = self.exercise('root/usr/libexec/infinityos-liveinstall-boot-setup', scenario)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.target / 'etc/infinityos/refind-installed').exists())

    def test_backup_preflight_failure_leaves_fstab_and_storage_untouched(self):
        self.write('etc/snapper/configs/root', 'SUBVOLUME="/"\n')
        self.write('etc/fstab', 'original fstab\n')
        self.write('etc/kernel/cmdline', 'root=UUID=test rw\n')
        self.write('boot/efi/EFI/refind/refind.conf', 'menuentry "Backups" {}\n')
        result = self.exercise('root/usr/libexec/infinityos-backups-setup')
        self.assertIn('boot installation is incomplete', result.stderr)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists(), 'preflight must not mount or mutate storage')
        self.assertEqual((self.target / 'etc/fstab').read_text(), 'original fstab\n')
        self.assertFalse((self.target / 'var/lib/infinityos/backups-ready').exists())
        self.write('etc/infinityos/refind-installed')
        for scenario, cmdline in [('missing-efi', 'root=UUID=test rw\n'),
                                  ('normal', 'root=UUID=test\nquiet\n')]:
            with self.subTest(scenario=scenario):
                self.write('etc/kernel/cmdline', cmdline)
                result = self.exercise('root/usr/libexec/infinityos-backups-setup', scenario)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.log.exists())
                self.assertEqual((self.target / 'etc/fstab').read_text(), 'original fstab\n')

    def test_snapper_initializer_rejects_non_btrfs_without_changes(self):
        result = self.exercise('root/usr/libexec/infinityos-snapper-setup', 'non-btrfs')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())
        self.assertFalse((self.target / 'var/lib/infinityos/snapper-ready').exists())

    def test_snapper_repairs_context_before_config_creation_and_stops_on_relabel_failure(self):
        self.write('etc/sysconfig/snapper', 'SNAPPER_CONFIGS=""\n')
        self.command('restorecon', '''
echo restorecon >> "$TEST_COMMAND_LOG"
[[ $TEST_SCENARIO != relabel-error ]]''')
        self.command('snapper', '''
printf 'snapper %s\\n' "$*" >> "$TEST_COMMAND_LOG"
[[ $* != *get-config* ]]''')
        result = self.exercise('root/usr/libexec/infinityos-snapper-setup', 'relabel-error')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.log.read_text(), 'restorecon\n')
        self.assertFalse((self.target / 'var/lib/infinityos/snapper-ready').exists())
        self.log.unlink()
        result = self.exercise('root/usr/libexec/infinityos-snapper-setup')
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.log.read_text()
        self.assertLess(log.index('restorecon'), log.index('snapper -c root create-config'))
        self.assertTrue((self.target / 'var/lib/infinityos/snapper-ready').exists())

    def test_setup_rpm_delivers_retry_helpers_without_running_boot_conversion(self):
        spec = (ROOT / 'packages/infinity-setup/infinity-setup.spec').read_text()
        staging = (ROOT / 'packages/build-rpm.sh').read_text()
        for helper in ('infinityos-liveinstall-boot-setup', 'infinityos-remove-obsolete-efi-loaders'):
            self.assertIn('/usr/libexec/' + helper, spec.split('%files', 1)[1])
            self.assertIn('/usr/libexec/' + helper, staging)
            self.assertNotIn(helper, spec.split('%files', 1)[0])

    def test_updater_distinguishes_missing_config_disabled_failed_incomplete_and_unmounted(self):
        source = 'packages/infinity-updater/root/usr/libexec/infinityos-upgrade-system'
        for scenario, expected in [('disabled', 'not enabled (disabled)'),
                                   ('masked', 'not enabled (masked)'),
                                   ('failed', 'initialization failed')]:
            with self.subTest(scenario=scenario):
                result = self.exercise(source, scenario, root_helper=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Snapper root configuration is missing', result.stderr)
                self.assertIn(expected, result.stderr)
                self.assertNotIn('update-started', self.log.read_text())
        self.write('etc/snapper/configs/root')
        result = self.exercise(source, root_helper=True)
        self.assertIn('backup initialization is incomplete', result.stderr)
        self.write('var/lib/infinityos/backups-ready')
        result = self.exercise(source, 'unmounted', root_helper=True)
        self.assertIn('is not mounted', result.stderr)
        self.assertNotIn('update-started', self.log.read_text())
        local_rpm = self.write('tmp/fixture.rpm')
        result = self.exercise(source, root_helper=True, arguments=('--local-rpm', str(local_rpm)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('update-started', self.log.read_text())

    def test_presets_cover_live_payload_and_units_exclude_running_live_media(self):
        preset = (ROOT / 'root/usr/lib/systemd/system-preset/00-infinityos-backups.preset').read_text()
        for unit in ('infinityos-snapper-setup.service', 'infinityos-backups-setup.service',
                     'infinityos-backups-entry.service', 'infinityos-backups-entry.path'):
            self.assertIn('enable ' + unit, preset)
            text = (ROOT / 'root/usr/lib/systemd/system' / unit).read_text()
            self.assertIn('ConditionKernelCommandLine=!rd.live.image', text)
            self.assertIn('ConditionPathExists=!/run/initramfs/live', text)
        for unit in ('infinityos-snapper-setup.service', 'infinityos-backups-setup.service'):
            text = (ROOT / 'root/usr/lib/systemd/system' / unit).read_text()
            self.assertIn('ExecCondition=/usr/bin/findmnt --noheadings --types btrfs --mountpoint /', text)
        package = (ROOT / 'packages/infinity-updater/infinity-updater.spec').read_text()
        self.assertIn('if [ "$1" -eq 1 ]', package)
        self.assertIn('/usr/libexec/infinityos-snapper-setup', package)
        self.assertIn('/usr/lib/systemd/system-preset/00-infinityos-backups.preset', package)

    def test_update_waits_for_enabled_initialization_before_staging_rpms(self):
        source = 'packages/infinity-updater/root/usr/libexec/infinityos-upgrade-system'
        result = self.exercise(source, 'retry-initializes', root_helper=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.log.read_text()
        self.assertLess(log.index('start infinityos-backups-setup.service'), log.index('update-started'))

        self.log.unlink()
        (self.target / 'var/lib/infinityos/backups-ready').unlink()
        blocked = self.exercise(source, 'disabled', root_helper=True)
        self.assertNotEqual(blocked.returncode, 0)
        self.assertNotIn('systemctl start', self.log.read_text())

    def test_backup_setup_waits_for_any_queued_boot_conversion(self):
        units = ROOT / 'root/usr/lib/systemd/system'
        backup = (units / 'infinityos-backups-setup.service').read_text()
        boot = (units / 'infinityos-liveinstall-boot-setup.service').read_text()
        after = next(line.removeprefix('After=').split() for line in backup.splitlines() if line.startswith('After='))
        self.assertIn('infinityos-liveinstall-boot-setup.service', after)
        self.assertIn('Wants=infinityos-liveinstall-boot-setup.service', backup)
        self.assertIn('ConditionKernelCommandLine=!rd.live.image', boot)
        self.assertIn('WantedBy=multi-user.target', backup)
        self.assertIn('WantedBy=multi-user.target', boot)
        self.assertIn('Type=oneshot', boot)

    def test_obsolete_loader_cleanup_stops_on_either_failed_rpm_query(self):
        script = ROOT / 'root/usr/libexec/infinityos-remove-obsolete-efi-loaders'
        self.command('rpm', '''
printf '%s\n' "$*" >> "$TEST_COMMAND_LOG"
if [[ $3 == -qa ]]; then
    if [[ $TEST_SCENARIO == initial-error ]]; then exit 1; fi
    if grep -q -- --noscripts "$TEST_COMMAND_LOG"; then
        if [[ $TEST_SCENARIO == final-error ]]; then exit 1; fi
        printf 'grub2-tools\n'
    else
        printf 'shim-x64\ngrub2-tools\n'
    fi
fi
exit 0''')
        self.target.mkdir()
        for scenario in ('initial-error', 'final-error', 'normal'):
            with self.subTest(scenario=scenario):
                self.log.unlink(missing_ok=True)
                result = subprocess.run(['bash', script, self.target], capture_output=True,
                                        env=dict(self.env, TEST_SCENARIO=scenario))
                self.assertEqual(result.returncode, 0 if scenario == 'normal' else 1)
                erasures = [line.split(' -e ', 1)[1] for line in self.log.read_text().splitlines() if ' -e ' in line]
                self.assertEqual(erasures, [] if scenario == 'initial-error' else
                                 ['--test shim-x64', '--noscripts --notriggers shim-x64'])


if __name__ == '__main__':
    unittest.main()
