import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/publish-infinity-isos-r2'
loader = importlib.machinery.SourceFileLoader('iso_r2', str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
publisher = importlib.util.module_from_spec(spec)
loader.exec_module(publisher)
REVISION = 'a' * 40
ENV = {'R2_ACCOUNT_ID': 'b' * 32, 'R2_BUCKET': 'infinityos-releases',
       'R2_PUBLIC_URL': 'https://download.infinityos.eu'}


class R2PublishTests(unittest.TestCase):
    def test_pair_is_verified_before_latest_is_published(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, ENV):
            paths = []
            for arch in ('x86_64', 'aarch64'):
                image = Path(directory) / f'InfinityOS-2.0-{arch}-{REVISION[:7]}-20261114.iso'
                image.write_bytes(arch.encode())
                image.with_suffix('.iso.sha256').write_text(hashlib.sha256(image.read_bytes()).hexdigest())
                paths.append(image)
            calls = []
            def run(command, **kwargs):
                calls.append(command)
                if 'head-object' in command:
                    path = next(p for p in paths if command[-1].endswith(p.name))
                    return SimpleNamespace(stdout=json.dumps({'ContentLength': path.stat().st_size,
                        'Metadata': {'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}}))
                return SimpleNamespace(stdout='')
            with patch.object(publisher.subprocess, 'run', side_effect=run):
                publisher.publish(directory, REVISION)
            self.assertIn('s3://infinityos-releases/latest.json', calls[-1])
            manifest = json.loads((Path(directory) / 'latest.json').read_text())
            self.assertEqual(set(manifest['images']), {'arm', 'x64'})
            for image in manifest['images'].values():
                self.assertIn(f'/releases/{REVISION}/', image['url'])
                self.assertEqual(len(image['md5']), 32)
            # A failed transfer must never promote an incomplete pair.
            calls.clear()
            with patch.object(publisher.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'aws')) as aws:
                with self.assertRaises(subprocess.CalledProcessError):
                    publisher.publish(directory, REVISION)
                self.assertEqual(aws.call_count, 1)
                self.assertNotIn('s3://infinityos-releases/latest.json', aws.call_args.args[0])
            paths[1].write_bytes(b'corrupt')
            with patch.object(publisher.subprocess, 'run') as aws:
                with self.assertRaises(ValueError):
                    publisher.publish(directory, REVISION)
                aws.assert_not_called()

    def test_missing_architecture_does_not_publish(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, ENV), \
             patch.object(publisher.subprocess, 'run') as aws:
            with self.assertRaises(ValueError):
                publisher.publish(directory, REVISION)
            aws.assert_not_called()
