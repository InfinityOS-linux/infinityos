"""Signed Infinity OS release metadata shared by the checker and upgrade helper."""

import json
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.request import urlopen


BASE_URL = 'https://infinityos-linux.github.io/infinityos'
MANIFEST_URL = BASE_URL + '/releases/stable.json'
KEY_PATH = Path('/etc/pki/rpm-gpg/RPM-GPG-KEY-infinityos')
INSTALLED_VERSION = Path('/etc/infinityos-release')
OS_RELEASE = Path('/etc/os-release')
VERSION = re.compile(r'^[1-9][0-9]*\.[0-9]+(?:\.[0-9]+)?$')
ARCHES = {'aarch64', 'x86_64'}


def version_tuple(version):
    if not isinstance(version, str) or not VERSION.fullmatch(version):
        raise ValueError('Invalid Infinity OS version')
    return tuple(int(part) for part in version.split('.'))


def os_release(path=OS_RELEASE):
    values = {}
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if '=' in line and not line.startswith('#'):
            key, value = line.split('=', 1)
            values[key] = value.strip().strip('"')
    return values


def installed_version(path=INSTALLED_VERSION, os_path=OS_RELEASE):
    info = os_release(os_path)
    if info.get('ID') != 'infinityos':
        raise ValueError('This is not an Infinity OS installation')
    marker = Path(path)
    value = marker.read_text(encoding='utf-8').strip() if marker.exists() else info.get('INFINITYOS_VERSION_ID', '1.0')
    version_tuple(value)
    return value, int(info['VERSION_ID'])


def repository_url(version, fedora_release, arch):
    version_tuple(version)
    if type(fedora_release) is not int or not 1 <= fedora_release <= 99:
        raise ValueError('Invalid Fedora release')
    if arch not in ARCHES:
        raise ValueError('Unsupported architecture')
    return f'{BASE_URL}/rpm/{fedora_release}/releases/{version}/{arch}/'


def _fetch(url):
    with urlopen(url, timeout=15) as response:
        data = response.read(16385)
    if len(data) > 16384:
        raise ValueError('Release metadata is too large')
    return data


def _verify(payload, signature, key_path=KEY_PATH):
    with tempfile.TemporaryDirectory(prefix='infinityos-release-') as directory:
        root = Path(directory)
        manifest = root / 'stable.json'
        sig = root / 'stable.json.asc'
        keyring = root / 'trusted.gpg'
        manifest.write_bytes(payload)
        sig.write_bytes(signature)
        dearmor = subprocess.run(['gpg', '--batch', '--yes', '--dearmor', '--output', str(keyring), str(key_path)],
                                 capture_output=True, text=True, timeout=15, check=False)
        if dearmor.returncode:
            raise ValueError('Could not load the Infinity OS signing key')
        result = subprocess.run(['gpgv', '--keyring', str(keyring), str(sig), str(manifest)],
                                capture_output=True, text=True, timeout=15, check=False)
        if result.returncode:
            raise ValueError('Release metadata signature is invalid')


def load_manifest():
    payload = _fetch(MANIFEST_URL)
    signature = _fetch(MANIFEST_URL + '.asc')
    _verify(payload, signature)
    data = json.loads(payload)
    if not isinstance(data, dict) or data.get('schema') != 1:
        raise ValueError('Unsupported release metadata')
    version_tuple(data.get('version'))
    fedora = data.get('fedora_release')
    if type(fedora) is not int or not 1 <= fedora <= 99:
        raise ValueError('Invalid release base')
    return {'version': data['version'], 'fedora_release': fedora}


def available_release(manifest, current_version, current_fedora):
    if version_tuple(manifest['version']) <= version_tuple(current_version):
        return None
    return {'version': manifest['version'], 'fedora_release': manifest['fedora_release'],
            'supported': manifest['fedora_release'] == current_fedora}
