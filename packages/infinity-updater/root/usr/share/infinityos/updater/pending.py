"""Read and refresh DNF's pending transaction without dropping downloaded updates."""
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

OFFLINE = Path('/usr/lib/sysimage/libdnf5/offline')
TRIGGER = Path('/system-update')
INBOUND = {'Install', 'Upgrade', 'Downgrade', 'Reinstall'}


def packages(directory=None):
    directory = directory or OFFLINE
    transaction = json.loads((directory / 'transaction.json').read_text())
    result = []
    for item in transaction.get('rpms', []):
        if item['action'] not in INBOUND:
            continue
        nvr, arch = item['nevra'].rsplit('.', 1)
        name, version, release = nvr.rsplit('-', 2)
        evr = version + '-' + release
        if evr.startswith('0:'):
            evr = evr[2:]
        result.append({'kind': 'RPM', 'name': name, 'arch': arch, 'version': evr,
                       'source': item.get('repo_id', ''), 'nevra': item['nevra'],
                       'path': item.get('package_path', ''), 'reason': item.get('reason', 'User')})
    return result


def evr_tuple(value):
    epoch, sep, rest = value.partition(':')
    if not sep:
        epoch, rest = '0', epoch
    version, release = rest.rsplit('-', 1)
    return epoch, version, release


def refresh_specs(pending, available, compare, replacing=None):
    specs = []
    for item in pending:
        if replacing == (item['name'], item['arch']):
            continue
        candidates = [p for p in available if p['name'] == item['name'] and p['arch'] == item['arch']
                      and compare(evr_tuple(p['version']), evr_tuple(item['version'])) >= 0]
        best = None
        for candidate in candidates:
            if best is None or compare(evr_tuple(candidate['version']), evr_tuple(best['version'])) > 0:
                best = candidate
        if best:
            specs.append(best['nevra'])
        else:
            path = (OFFLINE / item['path']).resolve()
            if not item['path'] or not path.is_file():
                raise RuntimeError(f"Downloaded package is missing: {item['name']}. The pending update was kept.")
            specs.append(str(path))
    return specs


def stage(local_rpm=None):
    if Path('/etc/infinityos-release-pending.json').exists():
        raise RuntimeError('A release upgrade is pending. Complete or recover it first.')
    if local_rpm:
        local_rpm = str(Path(local_rpm).resolve(strict=True))
    existing = TRIGGER.is_symlink()
    if (TRIGGER.exists() or existing) and (not existing or TRIGGER.resolve() != OFFLINE):
        raise RuntimeError('Another updater owns the pending transaction. Restart first.')
    pending = packages() if existing else []
    if existing:
        transaction = json.loads((OFFLINE / 'transaction.json').read_text())
        if transaction.get('groups') or transaction.get('environments'):
            raise RuntimeError('A group update is pending. Restart to complete it first.')
        if any(item.get('action') not in INBOUND | {'Replaced'}
               for item in transaction.get('rpms', [])):
            raise RuntimeError('The pending transaction contains removals or unsupported actions. Restart to complete it first.')
    command = ['dnf', '-y']
    if pending:
        import rpm
        query = subprocess.run(['dnf', '--quiet', '--refresh', 'repoquery', '--available',
                                '--qf', '%{name}|%{arch}|%{evr}\\n',
                                *sorted({p['name'] for p in pending})],
                               check=True, capture_output=True, text=True)
        available = []
        for line in query.stdout.splitlines():
            name, arch, version = line.split('|', 2)
            available.append(dict(name=name, arch=arch, version=version,
                                  nevra=f'{name}-{version}.{arch}'))
        replacing = None
        if local_rpm:
            identity = subprocess.check_output(
                ['rpm', '-qp', '--qf', '%{NAME}|%{ARCH}|%{EVR}', local_rpm], text=True)
            name, arch, version = identity.split('|')
            replacing = (name, arch)
            if any((p['name'], p['arch']) == replacing and
                   rpm.labelCompare(evr_tuple(version), evr_tuple(p['version'])) < 0 for p in pending):
                raise RuntimeError('A newer version is already downloaded. The pending update was kept.')
        specs = refresh_specs(pending, available, rpm.labelCompare, replacing)
        command += ['do', '--offline', '--refresh', '--no-best', '--no-allow-downgrade', '--action=upgrade', '*', '--action=install', *specs]
        if local_rpm:
            command.append(local_rpm)
    elif local_rpm:
        command += ['install', '--offline', '--', local_rpm]
    else:
        command += ['upgrade', '--offline', '--refresh', '--no-best', '--skip-unavailable']

    # DNF keeps downloaded RPMs; preserve metadata until the replacement is ready.
    with tempfile.TemporaryDirectory(prefix='infinityos-pending-') as temporary:
        saved = Path(temporary)
        for name in ('transaction.json', 'offline-transaction-state.toml'):
            source = OFFLINE / name
            if source.exists():
                shutil.copy2(source, saved / name)
        if existing:
            TRIGGER.unlink()
        try:
            subprocess.run(command, check=True)
            if pending:
                transaction = json.loads((OFFLINE / 'transaction.json').read_text())
                reasons = {(p['name'], p['arch']): p['reason'] for p in pending}
                for item in transaction.get('rpms', []):
                    nvr, arch = item['nevra'].rsplit('.', 1)
                    name = nvr.rsplit('-', 2)[0]
                    if item['action'] in INBOUND and (name, arch) in reasons:
                        item['reason'] = reasons[name, arch]
                temporary_json = OFFLINE / 'transaction.json.tmp'
                temporary_json.write_text(json.dumps(transaction) + '\n')
                temporary_json.replace(OFFLINE / 'transaction.json')
            subprocess.run(['dnf', '-y', 'offline', 'reboot'], check=True,
                           env={**os.environ, 'DNF_SYSTEM_UPGRADE_NO_REBOOT': '1'})
        except BaseException:
            OFFLINE.mkdir(parents=True, exist_ok=True)
            for source in saved.iterdir():
                shutil.copy2(source, OFFLINE / source.name)
            if existing:
                TRIGGER.unlink(missing_ok=True)
                TRIGGER.symlink_to(OFFLINE)
            raise


def main():
    if os.geteuid() != 0 or len(sys.argv) > 2:
        raise RuntimeError('System update preparation requires administrator authorization.')
    with open('/run/infinityos-update.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        stage(sys.argv[1] if len(sys.argv) == 2 else None)


if __name__ == '__main__':
    main()
