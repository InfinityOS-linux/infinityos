#!/usr/bin/env python3
"""Renderer identity, independent of unrelated system/application commits."""
import hashlib
from pathlib import Path
import sys


def cache_key(root, image, platform):
    digest = hashlib.sha256()
    for value in (image, platform, 'ReleaseFast', 'baseline', 'ghostty-cache-v1'):
        digest.update(value.encode() + b'\0')
    for path in sorted(root.iterdir()):
        if path.suffix == '.patch' or path.name in ('Dockerfile', 'build-and-stage.sh', 'cache-key.py'):
            digest.update(path.name.encode() + b'\0' + path.read_bytes() + b'\0')
    return digest.hexdigest()


if __name__ == '__main__':
    print(cache_key(Path(__file__).resolve().parent, sys.argv[1], sys.argv[2]))
