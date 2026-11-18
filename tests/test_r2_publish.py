import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/publish-infinity-isos-r2'
if not SCRIPT.exists():
    SCRIPT = Path(__file__).with_name('publish-infinity-isos-r2')
publish = runpy.run_path(str(SCRIPT))['publish']
REVISION = 'a' * 40


class R2PublishTests(unittest.TestCase):
    def exercise(self, failures=0, corrupt=False, bad_remote=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for arch in ('x86_64', 'aarch64'):
                image = root / f'InfinityOS-2.0-{arch}-{REVISION[:7]}-20261118.iso'
                image.write_bytes(arch.encode())
                image.with_suffix('.iso.sha256').write_text(
                    'bad' if corrupt else hashlib.sha256(image.read_bytes()).hexdigest())
            self.calls = []
            remaining = failures
            def aws(command, **kwargs):
                nonlocal remaining
                config = Path(kwargs['env']['AWS_CONFIG_FILE']).read_text()
                self.assertIn('preferred_transfer_client = classic', config)
                self.assertIn('multipart_chunksize = 64MB', config)
                self.calls.append(command)
                if 'cp' in command and command[5].endswith('.iso'):
                    if remaining:
                        remaining -= 1
                        raise subprocess.CalledProcessError(1, command)
                output = '{}'
                if 'head-object' in command:
                    path = root / command[-1].split('/')[-1]
                    output = json.dumps({'ContentLength': 0 if bad_remote else path.stat().st_size,
                                         'Metadata': {'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}})
                if 'list-objects-v2' in command:
                    output = '[]'
                return subprocess.CompletedProcess(command, 0, stdout=output)
            with patch.dict(os.environ, {'R2_ACCOUNT_ID': 'b' * 32,
                                         'R2_BUCKET': 'test-releases',
                                         'R2_PUBLIC_URL': 'https://example.com'}), \
                    patch('subprocess.run', side_effect=aws), patch('time.sleep'):
                publish(directory, REVISION)

    def test_retries_iso_and_publishes_manifest_last(self):
        self.exercise(failures=1)
        uploads = [call for call in self.calls if 'cp' in call]
        self.assertEqual(sum(call[5].endswith('.iso') for call in uploads), 3)
        self.assertEqual(uploads[-1][6], 's3://test-releases/latest.json')

    def test_exhausted_upload_never_changes_manifest(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.exercise(failures=3)
        self.assertFalse(any('s3://test-releases/latest.json' in call for call in self.calls))

    def test_invalid_pair_uploads_nothing(self):
        with self.assertRaises(ValueError):
            self.exercise(corrupt=True)
        self.assertEqual(self.calls, [])

    def test_remote_mismatch_never_changes_manifest(self):
        with self.assertRaises(ValueError):
            self.exercise(bad_remote=True)
        self.assertFalse(any('s3://test-releases/latest.json' in call for call in self.calls))


if __name__ == '__main__':
    unittest.main()
