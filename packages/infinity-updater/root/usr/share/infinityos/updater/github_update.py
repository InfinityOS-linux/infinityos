"""Updates for GitHub RPMs and AppImages installed by InfinitySetup."""

import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from launcher_backend import (APPS, _latest_rpm, appimage_paths, available, install,
                              installed, latest_appimage_asset, latest_rpm_asset)


def _installed():
    result = subprocess.run(['rpm', '-qa', '--qf', '%{NAME}|%{VERSION}|%{RELEASE}\n'],
                            capture_output=True, text=True, check=True, timeout=30)
    return {fields[0]: (fields[1], fields[2])
            for line in result.stdout.splitlines()
            if len(fields := line.split('|')) == 3}


def _newer(latest, current):
    import rpm

    tag = latest.removeprefix('v')
    if not re.fullmatch(r'[0-9][A-Za-z0-9.+_~]*(?:-[0-9][A-Za-z0-9.+_~]*)?', tag):
        raise ValueError(f'Unrecognized release version: {latest}')
    version, separator, release = tag.partition('-')
    return rpm.labelCompare(('0', version, release if separator else '0'),
                            ('0', *current)) > 0


def check_github_updates(home=None):
    updates, errors = [], []
    home = Path(home or Path.home())
    try:
        installed_rpms = _installed()
    except (OSError, subprocess.SubprocessError) as error:
        installed_rpms = {}
        errors.append('InfinitySetup RPM: ' + str(error))
    for app in APPS:
        if app.kind == 'github-appimage':
            if not available(app) or not installed(app, home):
                continue
            try:
                release, asset = latest_appimage_asset(app, os.uname().machine)
                binary, _desktop = appimage_paths(app, home)
                with binary.open('rb') as current:
                    digest = hashlib.file_digest(current, 'sha256').hexdigest()
                if digest != asset['digest'][7:]:
                    updates.append({'kind': 'InfinitySetup AppImage', 'name': app.name,
                                    'version': release['tag_name'], 'source': app.source})
            except (OSError, ValueError, KeyError, RuntimeError, TimeoutError) as error:
                errors.append(f'{app.name}: {error}')
            continue
        if app.kind not in ('github-rpm', 'winboat-rpm'):
            continue
        package = app.package or app.source.rsplit('/', 1)[-1].lower()
        if package not in installed_rpms:
            continue
        try:
            release, _asset = latest_rpm_asset(app, os.uname().machine)
            tag = release['tag_name']
            if _newer(tag, installed_rpms[package]):
                updates.append({'kind': 'InfinitySetup RPM', 'name': app.name,
                                'version': tag, 'source': app.source})
        except (OSError, ValueError, KeyError, RuntimeError, TimeoutError) as error:
            errors.append(f'{app.name}: {error}')
    return updates, errors


def install_github_update(source, home=None):
    app = next((app for app in APPS if app.source == source and
                app.kind in ('github-rpm', 'winboat-rpm', 'github-appimage')), None)
    if app is None:
        raise ValueError('Unknown InfinitySetup GitHub source.')
    if app.kind == 'github-appimage':
        if not installed(app, home):
            raise ValueError(f'{app.name} is no longer installed.')
        install(app, home)
        return
    package = app.package or app.source.rsplit('/', 1)[-1].lower()
    current_version = _installed().get(package)
    if current_version is None:
        raise ValueError(f'{app.name} is no longer installed.')
    with tempfile.TemporaryDirectory(prefix='infinity-updater-rpm-') as directory:
        path = _latest_rpm(app, os.uname().machine, directory)
        result = subprocess.run(['rpm', '-qp', '--qf', '%{NAME}|%{VERSION}|%{RELEASE}|%{ARCH}',
                                 str(path)], capture_output=True, text=True, check=True, timeout=30)
        name, version, release, arch = result.stdout.split('|')
        if name != package or arch not in (os.uname().machine, 'noarch'):
            raise ValueError('Downloaded RPM identity or architecture did not match the installed app.')
        if not _newer(f'{version}-{release}', current_version):
            raise ValueError('Downloaded RPM is not newer than the installed app.')
        subprocess.run(['pkexec', '/usr/libexec/infinityos-upgrade-system', '--local-rpm',
                        str(path)], check=True)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: github_update.py OWNER/REPOSITORY')
    install_github_update(sys.argv[1])
