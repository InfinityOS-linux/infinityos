import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'packages/infinity-config/root/usr/share/infinityos/config_proton.py'
spec = importlib.util.spec_from_file_location('config_proton', SOURCE)
proton = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proton)


def asset(provider='Proton-Cachy', arch='x86_64'):
    name = 'proton-cachyos-11-slr-' + ('arm64' if arch == 'aarch64' else arch) + '.tar.xz' if provider == 'Proton-Cachy' else 'GE-Proton11-' + arch + '.tar.gz'
    return dict(provider=provider, tag='v11', arch=arch, name=name, size=100,
                digest='sha256:' + '0' * 64,
                browser_download_url=f'https://github.com/{proton.PROVIDERS[provider]}/releases/download/v11/{name}')


def archive(path, entries=None):
    entries = entries or {'Proton-test/proton': b'#!/bin/sh\n', 'Proton-test/compatibilitytool.vdf': b'"compatibilitytools" {}'}
    with tarfile.open(path, 'w:gz') as tar:
        for name, data in entries.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o755
            tar.addfile(info, io.BytesIO(data))


class ProtonTests(unittest.TestCase):
    def test_cachy_and_ge_select_matching_architecture_not_optimized_x64(self):
        for provider in proton.PROVIDERS:
            data = {'tag_name': 'v11', 'assets': [asset(provider, 'x86_64'), asset(provider, 'aarch64')]}
            data['assets'].append({**asset(provider), 'name': 'proton-cachyos-11-slr-x86_64_v3.tar.xz'})
            for arch in ('x86_64', 'aarch64'):
                self.assertEqual(proton.release_asset(provider, data, arch)['arch'], arch)
            self.assertIsNone(proton.release_asset(provider, data, 'riscv64'))

    def test_checksum_and_download_origin_are_required(self):
        for change in ({'digest': None}, {'browser_download_url': 'http://evil.test/file'}, {'size': 0}):
            with self.assertRaises(ValueError):
                proton.release_asset('Proton-Cachy', {'tag_name': 'v11', 'assets': [{**asset(), **change}]}, 'x86_64')

    def test_install_is_shared_with_native_and_flatpak_and_removal_clears_both(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            def download(_asset, destination, _progress):
                archive(destination)
            with patch.object(proton, 'download', side_effect=download), patch.object(proton.os, 'uname') as uname:
                uname.return_value.machine = 'x86_64'
                proton.install(asset(), home)
            roots = proton.tool_roots(home)
            self.assertEqual(len(roots), 2)
            for root in roots:
                self.assertTrue(proton.valid_tool(root / 'Proton-test'))
            self.assertEqual((roots[0] / 'Proton-test/proton').stat().st_ino,
                             (roots[1] / 'Proton-test/proton').stat().st_ino)
            rows = proton.installed(home)
            self.assertEqual(len(rows), 1)
            self.assertEqual(len(rows[0]['paths']), 2)
            proton.remove(rows[0], home)
            self.assertEqual(proton.installed(home), [])

    def test_publish_conflict_rolls_back_without_touching_other_tool(self):
        with tempfile.TemporaryDirectory() as directory:
            roots = proton.tool_roots(directory)
            other = roots[1] / 'Proton-test'
            other.mkdir(parents=True)
            (other / 'keep').write_text('user data')
            with patch.object(proton, 'download', side_effect=lambda _, dest, progress: archive(dest)), \
                 patch.object(proton.os, 'uname') as uname:
                uname.return_value.machine = 'x86_64'
                with self.assertRaises(FileExistsError):
                    proton.install(asset(), directory)
            self.assertFalse((roots[0] / 'Proton-test').exists())
            self.assertEqual((other / 'keep').read_text(), 'user data')

    def test_archive_cannot_escape_extraction_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.tar.gz'
            archive(path, {'../outside': b'bad'})
            destination = Path(directory) / 'out'
            destination.mkdir()
            with self.assertRaises(ValueError):
                proton.unpack(path, destination)
            self.assertFalse((Path(directory) / 'outside').exists())

    def test_removing_external_symlink_never_deletes_target(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            external = home / 'external'
            external.mkdir()
            for name in ('proton', 'compatibilitytool.vdf'):
                (external / name).touch()
            root = proton.tool_roots(home)[0]
            root.mkdir(parents=True)
            (root / 'linked').symlink_to(external, target_is_directory=True)
            proton.remove(proton.installed(home)[0], home)
            self.assertTrue((external / 'proton').exists())
            self.assertFalse((root / 'linked').is_symlink())

    def test_steam_managed_versions_are_not_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            tool = home / '.local/share/Steam/steamapps/common/Proton 11'
            tool.mkdir(parents=True)
            for name in ('proton', 'compatibilitytool.vdf'):
                (tool / name).touch()
            row = proton.installed(home)[0]
            self.assertTrue(row['steam'])
            with self.assertRaises(ValueError):
                proton.remove(row, home)
            self.assertTrue(tool.exists())

    def test_corrupt_download_never_reaches_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            response = io.BytesIO(b'corrupt')
            response.geturl = lambda: 'https://release-assets.githubusercontent.com/file'
            with patch.object(proton.urllib.request, 'urlopen', return_value=response):
                with self.assertRaises(ValueError):
                    proton.download({**asset(), 'size': 7}, Path(directory) / 'file', lambda *_: None)

    def test_archive_link_cannot_point_outside_tool(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'links.tar.gz'
            with tarfile.open(path, 'w:gz') as tar:
                for name in ('tool/proton', 'tool/compatibilitytool.vdf'):
                    entry = tarfile.TarInfo(name)
                    tar.addfile(entry, io.BytesIO())
                link = tarfile.TarInfo('tool/escape')
                link.type = tarfile.SYMTYPE
                link.linkname = '../outside'
                tar.addfile(link)
            destination = Path(directory) / 'out'
            destination.mkdir()
            with self.assertRaises(ValueError):
                proton.unpack(path, destination)

    def test_update_keeps_previously_installed_versions(self):
        with tempfile.TemporaryDirectory() as directory:
            def download(item, destination, _progress):
                name = 'Proton-' + item['tag']
                archive(destination, {name + '/proton': b'code', name + '/compatibilitytool.vdf': b'manifest'})
            with patch.object(proton, 'download', side_effect=download), patch.object(proton.os, 'uname') as uname:
                uname.return_value.machine = 'x86_64'
                proton.install(asset(), directory)
                proton.install({**asset(), 'tag': 'v12', 'digest': 'sha256:' + '1' * 64}, directory)
            self.assertEqual({row['metadata']['tag'] for row in proton.installed(directory)}, {'v11', 'v12'})

    def test_alias_roots_do_not_duplicate_or_remove_games(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            steam = home / '.local/share/Steam'
            steam.mkdir(parents=True)
            (home / '.steam').mkdir()
            (home / '.steam/root').symlink_to(steam, target_is_directory=True)
            self.assertEqual(len(proton.tool_roots(home)), 2)
            games = steam / 'steamapps/compatdata/42/pfx'
            games.mkdir(parents=True)
            with self.assertRaises(ValueError):
                proton.remove({'paths': [games], 'steam': False}, home)
            self.assertTrue(games.exists())
