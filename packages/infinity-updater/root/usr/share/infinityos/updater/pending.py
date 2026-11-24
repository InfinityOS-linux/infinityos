"""Read and refresh DNF's pending transaction without dropping downloaded updates."""
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

RESULT_DIRECTORY = Path('/var/lib/infinityos')
OFFLINE = Path('/usr/lib/sysimage/libdnf5/offline')
TRIGGER = Path('/system-update')
INBOUND = {'Install', 'Upgrade', 'Downgrade', 'Reinstall'}


def packages(directory=None):
    directory = directory or OFFLINE
    transaction = json.loads((directory / 'transaction.json').read_text())
    return transaction_packages(transaction)


def transaction_packages(transaction):
    if not any(transaction.get(key) for key in ('rpms', 'groups', 'environments')):
        raise ValueError('The offline transaction is empty.')
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


def package_key(item):
    return item['name'], item.get('arch'), item['version'].removeprefix('0:')


def read_result(directory=None):
    path = (directory or RESULT_DIRECTORY) / 'offline-update-result.json'
    try:
        result = json.loads(path.read_text())
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError):
        return {}


def write_result(result, directory=None):
    directory = directory or RESULT_DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=directory, delete=False) as file:
        temporary = Path(file.name)
        try:
            json.dump(result, file)
            file.write('\n')
            file.flush()
            os.fchmod(file.fileno(), 0o644)
            os.fsync(file.fileno())
            temporary.replace(directory / 'offline-update-result.json')
        finally:
            temporary.unlink(missing_ok=True)
    fd = os.open(directory, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def failed_result(result, directory=None):
    if result.get('status') == 'running':
        holds = result.get('held_packages', [])
        if not result.get('release'):
            holds = record_holds(holds, result['attempted_packages'], result['phase'])
        return {**result, 'status': 'failed', 'interrupted': True, 'held_packages': holds}
    if result.get('status') == 'failed' and 'held_packages' not in result:
        # Older updaters did not write package identities. Reuse the transaction
        # only if its metadata predates the recorded failure.
        path = (directory or RESULT_DIRECTORY) / 'offline-update-result.json'
        try:
            if (OFFLINE / 'transaction.json').stat().st_mtime_ns <= path.stat().st_mtime_ns:
                holds = record_holds([], packages(), 'transaction')
                return {**result, 'held_packages': holds}
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            pass
    return result


def record_holds(previous, failed, phase):
    holds = {package_key(item): item for item in previous}
    for item in failed:
        holds[package_key(item)] = {
            **{key: item[key] for key in ('name', 'arch', 'version', 'source', 'nevra')},
            'phase': phase,
        }
    return list(holds.values())


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


def stage_command(command, allow_retry=True):
    """One metadata-only retry for a failed offline repository download.

    Pages can publish newer RPMs while a client still has old metadata. Keep
    downloaded packages and the existing offline transaction intact; do not
    retry local installs or the reboot/arming step.
    """
    try:
        return subprocess.run(command, check=True)
    except subprocess.CalledProcessError:
        if not allow_retry or '--offline' not in command or not any(action in command for action in ('upgrade', 'do')):
            raise
        print('Refreshing repository metadata and retrying package downloads once...', flush=True)
        subprocess.run(['dnf', 'clean', 'metadata'], check=True)
        return subprocess.run(command, check=True)


def stage(local_rpm=None):
    if Path('/etc/infinityos-release-pending.json').exists():
        raise RuntimeError('A release upgrade is pending. Complete or recover it first.')
    if local_rpm:
        local_rpm = str(Path(local_rpm).resolve(strict=True))
    existing = TRIGGER.is_symlink()
    if (TRIGGER.exists() or existing) and (not existing or TRIGGER.resolve() != OFFLINE):
        raise RuntimeError('Another updater owns the pending transaction. Restart first.')
    previous = read_result()
    result = failed_result(previous)
    if result != previous:
        write_result(result)
    holds = result.get('held_packages', [])
    held_keys = {package_key(item) for item in holds}
    pending = []
    if existing:
        try:
            transaction = json.loads((OFFLINE / 'transaction.json').read_text())
            pending = transaction_packages(transaction)
        except (FileNotFoundError, ValueError, KeyError, TypeError, AttributeError):
            TRIGGER.unlink()
            existing = False
        else:
            if transaction.get('groups') or transaction.get('environments'):
                raise RuntimeError('A group update is pending. Restart to complete it first.')
            if any(item.get('action') not in INBOUND | {'Replaced'}
                   for item in transaction.get('rpms', [])):
                raise RuntimeError('The pending transaction contains removals or unsupported actions. Restart to complete it first.')
            if not pending or any(package_key(item) in held_keys for item in pending):
                # An old updater may have already armed a transaction that is
                # now known to be invalid. Replace it using the current solver.
                TRIGGER.unlink()
                existing = False
                pending = []
    command = ['dnf', '-y']
    if holds:
        # The version and architecture are part of the exclusion, so a new build
        # can resolve normally. Include both spellings of a zero epoch.
        exclusions = {spec for item in holds for spec in (
            item['nevra'], f"{item['name']}-{item['version']}.{item['arch']}")}
        command.append('--exclude=' + ','.join(sorted(exclusions)))
    replacing = None
    if local_rpm and (pending or holds):
        identity = subprocess.check_output(
            ['rpm', '-qp', '--qf', '%{NAME}|%{ARCH}|%{EVR}', local_rpm], text=True)
        name, arch, version = identity.split('|')
        replacing = (name, arch)
        if package_key(dict(name=name, arch=arch, version=version)) in held_keys:
            raise RuntimeError(f'{name} {version} is on hold after a failed offline update.')
    if pending:
        import rpm
        query = subprocess.run(['dnf', '--quiet', '--refresh', 'repoquery', '--available',
                                '--qf', '%{name}|%{arch}|%{evr}\\n',
                                *sorted({p['name'] for p in pending})],
                               check=True, capture_output=True, text=True)
        available = []
        for line in query.stdout.splitlines():
            name, arch, version = line.split('|', 2)
            candidate = dict(name=name, arch=arch, version=version,
                             nevra=f'{name}-{version}.{arch}')
            if package_key(candidate) not in held_keys:
                available.append(candidate)
        if replacing and any((p['name'], p['arch']) == replacing and
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
        if existing:
            for name in ('transaction.json', 'offline-transaction-state.toml'):
                source = OFFLINE / name
                if source.exists():
                    shutil.copy2(source, saved / name)
            TRIGGER.unlink()
        transaction_path = OFFLINE / 'transaction.json'
        try:
            # A no-op DNF command may leave old files untouched. A fresh queue
            # must contain a transaction written by this staging attempt.
            if not existing:
                transaction_path.unlink(missing_ok=True)
                (OFFLINE / 'offline-transaction-state.toml').unlink(missing_ok=True)
            stage_command(command, allow_retry=not local_rpm)
            if not transaction_path.exists():
                if existing:
                    raise RuntimeError('No replacement transaction was prepared.')
                return
            transaction = json.loads(transaction_path.read_text())
            if not any(transaction.get(key) for key in ('rpms', 'groups', 'environments')):
                if existing:
                    raise RuntimeError('No replacement transaction was prepared.')
                return
            if held_keys and any(package_key(item) in held_keys
                                 for item in transaction_packages(transaction)):
                raise RuntimeError('DNF included a held package. No restart was scheduled.')
            if pending:
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
            if TRIGGER.is_symlink() and TRIGGER.resolve() == OFFLINE:
                TRIGGER.unlink()
            if existing:
                OFFLINE.mkdir(parents=True, exist_ok=True)
                for source in saved.iterdir():
                    shutil.copy2(source, OFFLINE / source.name)
                TRIGGER.symlink_to(OFFLINE)
            raise


def main():
    if os.geteuid() != 0 or len(sys.argv) > 2:
        raise RuntimeError('System update preparation requires administrator authorization.')
    with open('/run/infinityos-update.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        stage(sys.argv[1] if len(sys.argv) == 2 else None)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        sys.exit(f'System update preparation stopped: {error}')
