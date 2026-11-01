"""Verify every completed-study tracked file, including historical failures."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def verify():
    manifest = json.loads((ROOT / 'results/extension-v3/completed-study-freeze.json').read_text())
    bad = [name for name, digest in manifest['hashes'].items()
           if not (ROOT / name).is_file()
           or hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest]
    if bad:
        raise ValueError('Completed study changed: ' + ', '.join(bad))
    return {'baseline_commit': manifest['baseline_commit'], 'unchanged_files': len(manifest['hashes'])}


if __name__ == '__main__':
    print(json.dumps(verify(), indent=2))
