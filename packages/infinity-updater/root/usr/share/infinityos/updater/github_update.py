"""Updates for GitHub RPMs and AppImages installed by InfinityApps."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from launcher_backend import (APPS, _latest_rpm, appimage_paths, available, install,
                              installed, latest_appimage_asset, latest_rpm_asset, run_privileged)

RELEASE_TTL = 3600
STALE_RELEASE_TTL = 86400


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


def _read_cache(path):
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        if isinstance(data, dict) and isinstance(data.get('releases'), dict):
            return data
    except (OSError, ValueError):
        pass
    return {'releases': {}, 'retry_at': 0}


def _save_cache(path, cache):
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as file:
            temporary = Path(file.name)
            try:
                json.dump(cache, file)
                file.close()
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
    except OSError:
        pass  # Checking for updates can still work without a writable cache.


def _rate_limit_retry(error, now):
    if not isinstance(error, HTTPError) or error.code not in (403, 429):
        return None
    headers = error.headers or {}
    reset = headers.get('X-RateLimit-Reset', '')
    retry_after = headers.get('Retry-After', '')
    exhausted = headers.get('X-RateLimit-Remaining') == '0'
    if error.code != 429 and not (exhausted or retry_after or 'rate limit' in str(error.reason).lower()):
        return None
    waits = []
    if retry_after.isdigit():
        waits.append(int(retry_after))
    if exhausted and reset.isdigit():
        waits.append(int(reset) - now)
    return now + max(60, max(waits, default=600))


def check_github_updates(home=None):
    updates, errors = [], []
    deadline = time.monotonic() + 180
    cache_root = Path(home) / '.cache' if home is not None else Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache'))
    cache_path = cache_root / 'infinityos' / 'github-app-releases.json'
    cache = _read_cache(cache_path)
    releases = cache['releases']
    retry_at = cache.get('retry_at', 0)
    if not isinstance(retry_at, (int, float)):
        retry_at = 0
    dirty = False
    arch = os.uname().machine
    home = Path(home or Path.home())
    try:
        installed_rpms = _installed()
    except (OSError, subprocess.SubprocessError) as error:
        installed_rpms = {}
        errors.append('InfinityApps RPM: ' + str(error))
    for app in APPS:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            errors.append("InfinityApps: check timed out; some apps could not be checked")
            break
        appimage = app.kind == 'github-appimage'
        if appimage:
            if not available(app) or not installed(app, home):
                continue
            package = None
        elif app.kind in ('github-rpm', 'winboat-rpm'):
            package = app.package or app.source.rsplit('/', 1)[-1].lower()
            if package not in installed_rpms:
                continue
        else:
            continue
        now = time.time()
        key = f'{app.source}:{arch}:{app.kind}'
        cached = releases.get(key)
        has_cache = (isinstance(cached, dict) and isinstance(cached.get('tag'), str) and
                     isinstance(cached.get('checked'), (int, float)) and
                     0 <= now - cached['checked'] < STALE_RELEASE_TTL and
                     (not appimage or isinstance(cached.get('digest'), str)))
        if not has_cache or now - cached['checked'] >= RELEASE_TTL:
            if now >= retry_at:
                try:
                    fetch = latest_appimage_asset if appimage else latest_rpm_asset
                    release, asset = fetch(app, arch, timeout=min(15, remaining))
                    cached = {'tag': release['tag_name'], 'checked': now}
                    if appimage:
                        cached['digest'] = asset['digest']
                    releases[key] = cached
                    has_cache = dirty = True
                except (OSError, ValueError, KeyError, RuntimeError, TimeoutError) as error:
                    retry = _rate_limit_retry(error, now)
                    if isinstance(error, HTTPError):
                        error.close()
                    if retry is not None:
                        cache['retry_at'] = retry_at = retry
                        dirty = True
                    else:
                        errors.append(f'{app.name}: {error}')
            if not has_cache:
                continue
        try:
            tag = cached['tag']
            if appimage:
                binary, _desktop = appimage_paths(app, home)
                with binary.open('rb') as current:
                    digest = hashlib.file_digest(current, 'sha256').hexdigest()
                if digest != cached['digest'][7:]:
                    updates.append({'kind': 'InfinityApps AppImage', 'name': app.name,
                                    'version': tag, 'source': app.source})
            elif _newer(tag, installed_rpms[package]):
                updates.append({'kind': 'InfinityApps RPM', 'name': app.name,
                                'version': tag, 'source': app.source})
        except (OSError, ValueError, KeyError, RuntimeError, TimeoutError) as error:
            errors.append(f'{app.name}: {error}')
    if dirty:
        _save_cache(cache_path, cache)
    return updates, errors


def install_github_update(source, home=None):
    app = next((app for app in APPS if app.source == source and
                app.kind in ('github-rpm', 'winboat-rpm', 'github-appimage')), None)
    if app is None:
        raise ValueError('Unknown InfinityApps GitHub source.')
    if app.kind == 'github-appimage':
        if not installed(app, home):
            raise ValueError(f'{app.name} is no longer installed.')
        install(app, home)
        return
    package = app.package or app.source.rsplit('/', 1)[-1].lower()
    current_version = _installed().get(package)
    if current_version is None:
        raise ValueError(f'{app.name} is no longer installed.')
    with tempfile.TemporaryDirectory(prefix='infinity-updater-rpm-', dir='/tmp') as directory:
        path = _latest_rpm(app, os.uname().machine, directory)
        result = subprocess.run(['rpm', '-qp', '--qf', '%{NAME}|%{VERSION}|%{RELEASE}|%{ARCH}',
                                 str(path)], capture_output=True, text=True, check=True, timeout=30)
        name, version, release, arch = result.stdout.split('|')
        if name != package or arch not in (os.uname().machine, 'noarch'):
            raise ValueError('Downloaded RPM identity or architecture did not match the installed app.')
        if not _newer(f'{version}-{release}', current_version):
            raise ValueError('Downloaded RPM is not newer than the installed app.')
        command = ['/usr/libexec/infinityos-upgrade-system', '--local-rpm', str(path)]
        result = run_privileged(command)
        if result is None:
            subprocess.run(['pkexec', *command], check=True)
        elif result.returncode:
            raise subprocess.CalledProcessError(result.returncode, command,
                                                output=result.stdout, stderr=result.stderr)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: github_update.py OWNER/REPOSITORY')
    install_github_update(sys.argv[1])
