import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ReleaseManifestTests(unittest.TestCase):
    def test_prepare_next_release_on_disposable_source_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory)
            for name in ('scripts/set-infinityos-release', 'releases/stable.json',
                         'root/usr/share/infinityos/image-release-version',
                         'root/usr/share/infinityos/repos/infinityos.repo',
                         'repositories/infinityos.xml'):
                target = copy / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, target)
            result = subprocess.run([sys.executable, str(copy / 'scripts/set-infinityos-release'),
                                     '1.1'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((copy / 'releases/stable.json').read_text())
            self.assertEqual(manifest['version'], '1.1')
            self.assertEqual(manifest['previous'], ['1.0'])
            self.assertEqual((copy / 'root/usr/share/infinityos/image-release-version').read_text(),
                             '1.1\n')
            expected = 'https://infinityos-linux.github.io/infinityos/rpm/44/releases/1.1/$basearch/'
            for name in ('root/usr/share/infinityos/repos/infinityos.repo',
                         'repositories/infinityos.xml'):
                self.assertIn(expected, (copy / name).read_text())
            result = subprocess.run([sys.executable, str(copy / 'scripts/set-infinityos-release'),
                                     '1.0'], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)

    def test_published_version_matches_image_and_repository_sources(self):
        manifest = json.loads((ROOT / 'releases/stable.json').read_text())
        version = manifest['version']
        fedora = manifest['fedora_release']
        self.assertRegex(version, r'^[1-9][0-9]*\.[0-9]+(?:\.[0-9]+)?$')
        self.assertEqual(fedora, 44)
        self.assertEqual((ROOT / 'root/usr/share/infinityos/image-release-version').read_text().strip(),
                         version)
        url = (f'https://infinityos-linux.github.io/infinityos/rpm/{fedora}/$basearch/'
               if version == '1.0' else
               f'https://infinityos-linux.github.io/infinityos/rpm/{fedora}/releases/{version}/$basearch/')
        repo = (ROOT / 'root/usr/share/infinityos/repos/infinityos.repo').read_text()
        kiwi = (ROOT / 'repositories/infinityos.xml').read_text()
        self.assertIn(url, repo)
        self.assertIn(url, kiwi)
        self.assertEqual(len(re.findall(r'https://infinityos-linux.github.io/infinityos/rpm/', repo)), 1)
        self.assertEqual(len(re.findall(r'https://infinityos-linux.github.io/infinityos/rpm/', kiwi)), 1)

    def test_archived_versions_are_unique_and_older(self):
        manifest = json.loads((ROOT / 'releases/stable.json').read_text())
        previous = manifest['previous']
        self.assertEqual(len(previous), len(set(previous)))
        to_tuple = lambda value: tuple(map(int, value.split('.')))
        self.assertEqual(previous, sorted(previous, key=to_tuple))
        self.assertTrue(all(to_tuple(version) < to_tuple(manifest['version']) for version in previous))


if __name__ == '__main__':
    unittest.main()
