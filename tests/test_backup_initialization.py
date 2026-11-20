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
                        TEST_COMMAND_LOG=str(self.log), TEST_SCENARIO='normal')
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


if __name__ == '__main__':
    unittest.main()
