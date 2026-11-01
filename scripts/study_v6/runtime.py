"""Freeze selected installed runtime versions without importing/loading models."""
from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys

from scripts.study_v6.common import ROOT

PACKAGES = ('numpy', 'scipy', 'matplotlib', 'transformers', 'tokenizers', 'torch',
            'safetensors', 'laya', 'huggingface-hub', 'sentencepiece')


def current():
    versions = {}
    for name in PACKAGES:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return {'python': platform.python_version(), 'packages': versions,
            'implementation': platform.python_implementation(), 'machine': platform.machine()}


def capture():
    snapshots = {}
    for name in ('.venv', '.venv-laya'):
        executable = ROOT / name / 'bin/python'
        output = subprocess.check_output([str(executable), '-c',
            'import json; from scripts.study_v6.runtime import current; print(json.dumps(current()))'], cwd=ROOT, text=True)
        snapshots[name] = json.loads(output)
    if snapshots['.venv-laya']['packages']['laya'] != '0.4.17':
        raise PermissionError('Pinned Laya SDK changed')
    return {'version': 'v6-runtime-1', 'environments': snapshots, 'model_imports': 0, 'forward_passes': 0}


def verify(receipt):
    executable = Path(sys.executable).absolute()
    # venv binaries may be symlinks; use the invocation path rather than resolving
    # to the shared interpreter and losing environment identity.
    match = [name for name in receipt['environments'] if executable == (ROOT / name / 'bin/python').absolute()]
    if len(match) != 1 or current() != receipt['environments'][match[0]]:
        raise PermissionError('Execution runtime differs from frozen environment')
    return match[0]
