"""Small durable evidence helpers. Raw artifacts never belong in tracked results."""
from __future__ import annotations

import json
import os
from pathlib import Path

from scripts.study_v6.common import canonical_bytes, sha256


def exclusive(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = value if isinstance(value, bytes) else canonical_bytes(value) + b'\n'
    with path.open('xb') as stream:
        os.chmod(path, 0o600)
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    # Persist the directory entry before a caller can dispatch a request.
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return sha256(data)


def immutable(path, value):
    data = value if isinstance(value, bytes) else canonical_bytes(value) + b'\n'
    path = Path(path)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError('Preserved evidence differs: ' + str(path))
        return sha256(data)
    return exclusive(path, data)


def load(path):
    return json.loads(Path(path).read_text())


def file_receipt(path, root):
    path = Path(path)
    return {'path': str(path.relative_to(root)), 'sha256': sha256(path.read_bytes()),
            'bytes': path.stat().st_size}
