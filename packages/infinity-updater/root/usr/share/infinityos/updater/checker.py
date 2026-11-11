import json
import os
from pathlib import Path
import subprocess
import tempfile
from datetime import datetime, timezone

from release import available_release, installed_version, load_manifest
from github_update import check_github_updates
from pending import packages as pending_packages


def offline_status(directory=Path('/var/lib/infinityos'), trigger=Path('/system-update')):
    if trigger.is_symlink():
        result = {'pending': True}
        try:
            result['packages'] = pending_packages(trigger.resolve())
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return result
    try:
        result = json.loads((directory / 'offline-update-result.json').read_text())
        if not isinstance(result, dict):
            return {}
        if result.get('status') == 'failed':
            result['log'] = result.get('error', '')
            try:
                with (directory / 'offline-update.log').open('rb') as log:
                    log.seek(0, 2)
                    log.seek(max(0, log.tell() - 16000))
                    result['log'] = log.read().decode('utf-8', errors='replace')
            except OSError:
                pass  # Keep the public error summary when the detailed root log is private.
        return result
    except (OSError, ValueError):
        return {}


def state_path():
    cache = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache'))
    return cache / 'infinityos' / 'updates.json'


def _run(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=240, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return subprocess.CompletedProcess(args, 1, '', str(error))


def firmware_updates(result):
    try:
        data = json.loads(result.stdout)
    except (TypeError, ValueError):
        return None
    devices = data.get('Devices') if isinstance(data, dict) else None
    if not isinstance(devices, list):
        return None
    updates = []
    for device in devices:
        if not isinstance(device, dict):
            continue
        releases = device.get('Releases', [])
        if not isinstance(releases, list) or not releases:
            continue
        release = releases[0]
        if isinstance(release, dict):
            updates.append({'kind': 'Firmware', 'name': device.get('Name') or 'Device firmware',
                            'version': release.get('Version') or '',
                            'source': release.get('RemoteId') or 'LVFS'})
    return updates


def check_updates(report=None):
    report = report or (lambda _source: None)
    report("System packages")
    updates = []
    errors = []
    # The user only needs the RPM database for this read-only query. Fresh
    # images can have root-only DNF system state files that repoquery cannot open.
    with tempfile.TemporaryDirectory(prefix='infinityos-dnf-state-') as state_dir:
        result = _run(['dnf', '--quiet', '--assumeyes', '--refresh',
                       f'--setopt=system_state_dir={state_dir}', 'repoquery', '--upgrades',
                       '--qf', '%{name}|%{evr}|%{repoid}|%{arch}\n'])
    rpm_check_ok = result.returncode == 0
    if rpm_check_ok:
        for line in result.stdout.splitlines():
            fields = line.split('|', 3)
            if len(fields) in (3, 4):
                updates.append({'kind': 'RPM', 'name': fields[0],
                                'version': fields[1], 'source': fields[2],
                                **({'arch': fields[3]} if len(fields) == 4 else {})})
    else:
        errors.append('RPM: ' + (result.stderr.strip() or 'Could not check updates'))

    report("InfinitySetup apps")
    github_updates, github_errors = check_github_updates()
    updates.extend(github_updates)
    errors.extend(github_errors)

    for scope in ('system', 'user'):
        report('System Flatpaks' if scope == 'system' else 'Your Flatpaks')
        result = _run(['flatpak', 'remote-ls', '--' + scope, '--updates',
                       '--columns=application,version,origin'])
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                fields = line.split('\t')
                if len(fields) >= 3:
                    updates.append({'kind': 'Flatpak ' + scope, 'name': fields[0],
                                    'version': fields[1], 'source': fields[2]})
        else:
            errors.append('Flatpak ' + scope + ': ' +
                          (result.stderr.strip() or 'Could not check updates'))

    report('Device firmware')
    result = _run(['fwupdmgr', 'get-updates', '--json'])
    firmware = firmware_updates(result)
    if result.returncode == 0 and firmware is not None:
        updates.extend(firmware)
    elif not (result.returncode == 2 and firmware == []) and not any(
            message in (result.stdout + result.stderr).lower() for message in
            ('no updates available', 'no updatable devices', 'no supported devices')):
        errors.append('Firmware: ' + (result.stderr.strip() or result.stdout.strip() or
                                      'Could not check updates'))

    report('Infinity OS releases')
    release = None
    try:
        current, fedora = installed_version()
        release = available_release(load_manifest(), current, fedora)
    except (OSError, ValueError, KeyError, TimeoutError, subprocess.SubprocessError) as error:
        errors.append('Release: ' + str(error))

    return {'checked_at': datetime.now(timezone.utc).isoformat(),
            'updates': updates, 'release': release,
            'rpm_check_ok': rpm_check_ok, 'errors': errors}


def save_state(state, path=None):
    path = Path(path or state_path())
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                     dir=path.parent, delete=False) as temp:
        json.dump(state, temp)
        temp.write('\n')
        temporary = temp.name
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def read_state(path=None):
    try:
        with open(path or state_path(), encoding='utf-8') as file:
            return json.load(file)
    except (OSError, ValueError):
        return {'checked_at': None, 'updates': [], 'release': None,
                'rpm_check_ok': False, 'errors': []}
