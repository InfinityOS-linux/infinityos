import importlib.machinery
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('upstream', str(ROOT / 'scripts/resolve-infinity-upstream'))
spec = importlib.util.spec_from_loader(loader.name, loader)
upstream = importlib.util.module_from_spec(spec)
loader.exec_module(upstream)


def release(repo, names, tag='v9.1'):
    return dict(tag_name=tag, draft=False, prerelease=False, assets=[dict(
        name=name, digest='sha256:' + 'a' * 64,
        browser_download_url=f'https://github.com/{repo}/releases/download/{tag}/{name}') for name in names])


class UpstreamTests(unittest.TestCase):
    def test_missing_checksum_asset_and_prerelease_are_rejected(self):
        good = release('owner/project', ['asset.zip'])
        for bad in [dict(good, prerelease=True), dict(good, assets=[]),
                    dict(good, assets=[dict(good['assets'][0], digest=None)]),
                    dict(good, assets=[dict(good['assets'][0], browser_download_url='http://other/asset.zip')])]:
            with self.subTest(bad=bad), patch.object(upstream, 'fetch', return_value=json.dumps(bad).encode()):
                with self.assertRaises(ValueError):
                    upstream.resolve('owner/project', lambda _: ['asset.zip'])

    def test_new_release_updates_both_architectures_font_and_manifest(self):
        proview = release('emanuelelongo/proview', ['Proview-v9.1-linux-arm64.AppImage', 'Proview-v9.1-linux-amd64.AppImage'])
        font = release('be5invis/Iosevka', ['PkgTTF-IosevkaTerm-9.1.zip'])
        with patch.object(upstream, 'fetch', side_effect=[json.dumps(proview).encode(), json.dumps(font).encode()]):
            p = upstream.resolve('emanuelelongo/proview', lambda v: [f'Proview-v{v}-linux-{a}.AppImage' for a in ('arm64', 'amd64')])
            f = upstream.resolve('be5invis/Iosevka', lambda v: [f'PkgTTF-IosevkaTerm-{v}.zip'])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dest = root / 'root/usr/libexec'
            dest.mkdir(parents=True)
            for name in ('proview', 'iosevka'):
                shutil.copy(ROOT / f'root/usr/libexec/infinityos-install-{name}', dest)
            upstream.stage(root, p, f, {'version': '4.4.5'})
            for name in ('proview', 'iosevka'):
                text = (dest / f'infinityos-install-{name}').read_text()
                self.assertIn('/v9.1/', text)
                self.assertIn('a' * 64, text)
                self.assertIn('sha256sum --check --status', text)
            manifest = json.loads((root / 'root/usr/share/infinityos/upstream-versions.json').read_text())
            self.assertEqual(len(manifest['proview']['assets']), 2)
            self.assertEqual(manifest['iosevka']['tag'], 'v9.1')

    def test_live_policy_excludes_addon_until_target_installation(self):
        config = (ROOT / 'config.sh').read_text()
        program = config.split("<< 'FIREFOX_LIVE_POLICY'\n", 1)[1].split('\nFIREFOX_LIVE_POLICY', 1)[0]
        original = ROOT / 'root/etc/firefox/policies/policies.json'
        hook = (ROOT / 'root/usr/libexec/infinityos-liveinstall-boot-setup').read_text()
        restore = 'install -D -m 0644 /usr/share/infinityos/firefox/installed-policies.json /etc/firefox/policies/policies.json'
        self.assertIn(restore, hook)
        with tempfile.TemporaryDirectory() as directory:
            live = Path(directory) / 'policies.json'
            saved = Path(directory) / 'installed-policies.json'
            shutil.copy(original, live)
            shutil.copy(live, saved)
            for _ in range(2):
                subprocess.run([sys.executable, '-', str(live)], input=program, text=True, check=True)
            policy = json.loads(live.read_text())['policies']
            self.assertNotIn('Extensions', policy)
            expected = json.loads(original.read_text())['policies']
            self.assertEqual(policy, {k: v for k, v in expected.items() if k != 'Extensions'})
            subprocess.run(['install', '-m', '0644', str(saved), str(live)], check=True)
            self.assertEqual(live.read_bytes(), original.read_bytes())

    def test_firefox_addon_is_bundled_and_identity_is_checked(self):
        import hashlib
        import io
        from zipfile import ZipFile
        guid = 'adblockultimate@adblockultimate.net'
        stream = io.BytesIO()
        with ZipFile(stream, 'w') as archive:
            archive.writestr('manifest.json', json.dumps({'version': '4.4.5',
                'browser_specific_settings': {'gecko': {'id': guid}}}))
        data = stream.getvalue()
        asset = {'status': 'public', 'hash': 'sha256:' + hashlib.sha256(data).hexdigest(),
                 'url': 'https://addons.mozilla.org/firefox/downloads/file/123/addon.xpi'}
        good = {'guid': guid, 'current_version': {'version': '4.4.5', 'file': asset}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(upstream, 'fetch', side_effect=[json.dumps(good).encode(), data]):
                result = upstream.stage_firefox_addon(root)
            destination = root / 'root/usr/share/infinityos/firefox/adblocker-ultimate.xpi'
            self.assertEqual(destination.read_bytes(), data)
            self.assertEqual(result['sha256'], asset['hash'][7:])
            policy = json.loads((ROOT / 'root/etc/firefox/policies/policies.json').read_text())
            self.assertEqual(policy['policies']['EncryptedMediaExtensions'], {'Enabled': True, 'Locked': False})
            self.assertEqual(policy['policies']['Extensions'],
                {'Install': ['/usr/share/infinityos/firefox/adblocker-ultimate.xpi']})
            for bad in [dict(good, guid='other'),
                        dict(good, current_version={'version': '9', 'file': asset}),
                        dict(good, current_version={'version': '4.4.5', 'file': dict(asset, status='disabled')}),
                        dict(good, current_version={'version': '4.4.5', 'file': dict(asset, hash='sha256:' + '0' * 64)}),
                        dict(good, current_version={'version': '4.4.5', 'file': dict(asset, url='https://example.com/addon.xpi')})]:
                with self.subTest(bad=bad), patch.object(upstream, 'fetch', side_effect=[json.dumps(bad).encode(), data]):
                    with self.assertRaises(ValueError):
                        upstream.stage_firefox_addon(root)
