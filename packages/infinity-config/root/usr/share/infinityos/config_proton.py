"""Verified Proton downloads and per-user native/Flatpak Steam installations."""
import errno
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import tempfile
import urllib.request

PROVIDERS = {'Proton-Cachy': 'CachyOS/proton-cachyos',
             'GE-Proton': 'GloriousEggroll/proton-ge-custom'}
MARKER = '.infinity-proton.json'


def tool_roots(home=None):
    home = Path(home or Path.home())
    roots = [home / '.local/share/Steam/compatibilitytools.d',
             home / '.var/app/com.valvesoftware.Steam/data/Steam/compatibilitytools.d']
    for steam in (home / '.steam/root', home / '.steam/steam',
                  home / '.var/app/com.valvesoftware.Steam/.local/share/Steam'):
        if steam.exists():
            roots.append(steam / 'compatibilitytools.d')
    return list(dict.fromkeys(path.resolve() for path in roots))


def valid_tool(path):
    return (path / 'proton').is_file() and (path / 'compatibilitytool.vdf').is_file()


def metadata(path):
    try:
        data = json.loads((path / MARKER).read_text())
        if data['provider'] in PROVIDERS and all(isinstance(data[k], str) for k in ('tag', 'arch', 'digest')):
            return data
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def installed(home=None):
    records = {}
    for root in tool_roots(home):
        if not root.is_dir():
            continue
        for path in sorted(root.iterdir()):
            if path.name.startswith('.') or not valid_tool(path):
                continue
            info = metadata(path)
            key = tuple(info[k] for k in ('provider', 'tag', 'arch', 'digest')) if info else str(path.resolve())
            if key not in records:
                records[key] = {'name': path.name, 'paths': [], 'metadata': info, 'steam': False}
            records[key]['paths'].append(path)
    # Valve-managed installs must be changed through Steam, including external libraries.
    libraries = set()
    for root in tool_roots(home):
        steam = root.parent
        libraries.add(steam)
        manifest = steam / 'steamapps/libraryfolders.vdf'
        if manifest.is_file():
            for value in re.findall(r'"path"\s+"((?:\\.|[^"\\])*)"', manifest.read_text(errors='replace')):
                libraries.add(Path(value.replace('\\\\', '\\').replace('\\"', '"')))
    for library in libraries:
        common = library / 'steamapps/common'
        if common.is_dir():
            for path in common.iterdir():
                if valid_tool(path):
                    records.setdefault(str(path.resolve()), {'name': path.name, 'paths': [path],
                                                           'metadata': None, 'steam': True})
    return sorted(records.values(), key=lambda record: record['name'].casefold())


def release_asset(provider, release, arch):
    repo = PROVIDERS[provider]
    suffix = {'aarch64': ('-aarch64', '-arm64'), 'x86_64': ('-x86_64',)}.get(arch, ())
    candidates = []
    for asset in release.get('assets', []):
        name = asset.get('name', '')
        stem = re.sub(r'\.tar\.(?:gz|xz)$', '', name)
        if stem == name or not stem.endswith(suffix):
            continue
        if provider == 'Proton-Cachy' and '-slr-' not in name:
            continue
        candidates.append(asset)
    # Earlier GE releases used unqualified names for x86_64.
    if not candidates and provider == 'GE-Proton' and arch == 'x86_64':
        candidates = [a for a in release.get('assets', [])
                      if a.get('name') == release.get('tag_name', '') + '.tar.gz']
    if len(candidates) != 1:
        return None
    asset = candidates[0]
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,199}', asset['name']):
        raise ValueError('Invalid release filename')
    if not re.fullmatch(r'sha256:[a-fA-F0-9]{64}', asset.get('digest') or ''):
        raise ValueError('Release checksum unavailable')
    if not 0 < asset.get('size', 0) <= 2_000_000_000:
        raise ValueError('Invalid release size')
    if not asset.get('browser_download_url', '').casefold().startswith(f'https://github.com/{repo}/releases/download/'.casefold()):
        raise ValueError('Invalid download URL')
    return {**asset, 'provider': provider, 'tag': release['tag_name'], 'arch': arch}


def releases(provider, arch=None):
    arch = arch or os.uname().machine
    request = urllib.request.Request(f'https://api.github.com/repos/{PROVIDERS[provider]}/releases?per_page=10',
                                     headers={'User-Agent': 'InfinityConfig', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.loads(response.read(5_000_001))
    if not isinstance(data, list):
        raise ValueError('Invalid release list')
    result = []
    for release in data:
        if not release.get('draft') and not release.get('prerelease'):
            asset = release_asset(provider, release, arch)
            if asset:
                result.append(asset)
    return result


def download(asset, destination, progress):
    request = urllib.request.Request(asset['browser_download_url'], headers={'User-Agent': 'InfinityConfig'})
    digest = hashlib.sha256()
    total = 0
    with urllib.request.urlopen(request, timeout=60) as response, destination.open('wb') as output:
        if not response.geturl().startswith('https://'):
            raise ValueError('Insecure download redirect')
        while chunk := response.read(1024 * 1024):
            total += len(chunk)
            if total > asset['size']:
                raise ValueError('Download exceeds expected size')
            digest.update(chunk)
            output.write(chunk)
            progress(total, asset['size'])
    if total != asset['size'] or digest.hexdigest() != asset['digest'][7:].lower():
        raise ValueError('Download verification failed')


def unpack(archive, destination):
    with tarfile.open(archive, 'r:*') as package:
        members = []
        total = 0
        for member in package:
            total += member.size
            if len(members) >= 200_000 or total > 15_000_000_000:
                raise ValueError('Archive too large')
            if PurePosixPath(member.name).is_absolute() or '..' in PurePosixPath(member.name).parts:
                raise ValueError('Unsafe archive path')
            members.append(member)
        if shutil.disk_usage(destination).free < total:
            raise OSError('Insufficient disk space')
        package.extractall(destination, members=members, filter='data')
    tools = [path for path in destination.iterdir() if path.is_dir() and not path.is_symlink() and valid_tool(path)]
    if len(tools) != 1:
        raise ValueError('Archive must contain one Proton tool')
    tool = tools[0]
    for path in tool.rglob('*'):
        if path.is_symlink() and not path.resolve().is_relative_to(tool.resolve()):
            raise ValueError('Archive link leaves the Proton directory')
    return tool


def link_or_copy(source, destination):
    try:
        os.link(source, destination)
    except OSError as error:
        if error.errno != errno.EXDEV:
            raise
        shutil.copy2(source, destination)


def install(asset, home=None, progress=lambda done, total: None):
    # Revalidate metadata at the write boundary, including architecture.
    verified = release_asset(asset['provider'], {'assets': [asset], 'tag_name': asset['tag']}, os.uname().machine)
    if verified is None or asset['arch'] != os.uname().machine:
        raise ValueError('Release does not support this computer')
    roots = tool_roots(home)
    for root in roots:
        root.mkdir(parents=True, exist_ok=True)
    info = {key: asset[key] for key in ('provider', 'tag', 'arch', 'digest')}
    created = []
    try:
        with tempfile.TemporaryDirectory(prefix='.infinity-proton-', dir=roots[0].parent) as temporary:
            temporary = Path(temporary)
            archive = temporary / asset['name']
            download(asset, archive, progress)
            extracted = temporary / 'unpacked'
            extracted.mkdir()
            tool = unpack(archive, extracted)
            (tool / MARKER).write_text(json.dumps(info))
            for root in roots:
                target = root / tool.name
                if target.exists() or target.is_symlink():
                    if not target.is_symlink() and valid_tool(target) and metadata(target) == info:
                        continue
                    raise FileExistsError('A different tool already uses this directory')
                with tempfile.TemporaryDirectory(prefix='.infinity-proton-', dir=root.parent) as staging:
                    staged = Path(staging) / tool.name
                    # Share immutable files on one filesystem; copy across mounts.
                    shutil.copytree(tool, staged, symlinks=True, copy_function=link_or_copy)
                    staged.rename(target)
                created.append(target)
    except Exception:
        for path in reversed(created):
            shutil.rmtree(path)
        raise


def remove(record, home=None):
    roots = tool_roots(home)
    paths = record['paths']
    if record['steam'] or not paths:
        raise ValueError('Manage this version in Steam')
    for path in paths:
        path = Path(path)
        if path.parent.resolve() not in roots or not valid_tool(path):
            raise ValueError('Not an installed custom Proton')
        if not path.is_symlink() and path.resolve().parent not in roots:
            raise ValueError('Refusing removal outside Proton directories')
    # Rename first so a failure can restore every visible installation.
    moved = []
    try:
        for path in paths:
            path = Path(path)
            staging = Path(tempfile.mkdtemp(prefix='.infinity-remove-', dir=path.parent.parent))
            destination = staging / path.name
            try:
                path.rename(destination)
            except Exception:
                staging.rmdir()
                raise
            moved.append((path, destination))
    except Exception:
        for original, destination in reversed(moved):
            destination.rename(original)
            destination.parent.rmdir()
        raise
    for _, destination in moved:
        if destination.is_symlink():
            destination.unlink()
        else:
            shutil.rmtree(destination)
        destination.parent.rmdir()
