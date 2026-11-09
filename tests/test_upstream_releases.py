import importlib.machinery
import importlib.util
import json
from pathlib import Path
import shutil
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
            upstream.stage(root, p, f)
            for name in ('proview', 'iosevka'):
                text = (dest / f'infinityos-install-{name}').read_text()
                self.assertIn('/v9.1/', text)
                self.assertIn('a' * 64, text)
                self.assertIn('sha256sum --check --status', text)
            manifest = json.loads((root / 'root/usr/share/infinityos/upstream-versions.json').read_text())
            self.assertEqual(len(manifest['proview']['assets']), 2)
            self.assertEqual(manifest['iosevka']['tag'], 'v9.1')
