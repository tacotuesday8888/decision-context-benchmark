"""Reproduce completed-arm artifacts in an isolated staged Git export.

Requires the analysis environment already installed. Does not install dependencies,
load credentials/weights, reconstruct raw source data or perform model inference.
Stage intended changes first; the Git index is the reproducible input snapshot.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'results/extension-v3'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    base = ROOT / 'data/raw/extension-v3'
    destination = Path(tempfile.mkdtemp(prefix='offline-export-', dir=base))
    subprocess.run(['git', 'checkout-index', '--all', '--prefix=' + str(destination) + '/'], cwd=ROOT, check=True)
    assert not (destination / '.env.local').exists() and not (destination / '.secrets').exists()
    assert not (destination / 'models').exists()
    directory = destination / 'results/extension-v3/analysis'
    configs = sorted(p.name.removesuffix('-ledger.json') for p in directory.glob('*-ledger.json'))
    compared = [p for p in directory.glob('*') if p.suffix in ('.json', '.csv')]
    compared += list((destination / 'results/extension-v3/figures').glob('*'))
    final_report = destination / 'results/extension-v3/report.md'
    if final_report.exists():
        compared += [final_report, final_report.with_name('report-inputs-v1.json'),
                     final_report.with_name('execution-closure-v1.json')]
    before = {str(p.relative_to(destination)): sha(p) for p in compared}
    commands = [[sys.executable, 'scripts/extension_v3/integrity.py']]
    for config in configs:
        commands += [[sys.executable, 'scripts/extension_v3/analyze.py', '--config', config],
                     [sys.executable, 'scripts/extension_v3/verify_analysis.py', '--config', config]]
        if (directory / (config + '-record-audit.json')).exists():
            commands.append([sys.executable, 'scripts/extension_v3/audit_records.py', '--config', config])
        if (directory / (config + '-bootstrap-verification.json')).exists():
            commands.append([sys.executable, 'scripts/extension_v3/verify_bootstrap.py', '--config', config])
    commands += [[sys.executable, 'scripts/extension_v3/tables.py'],
                 [sys.executable, 'scripts/extension_v3/figures.py'],
                 [sys.executable, 'scripts/extension_v3/reliability_figures.py']]
    if final_report.exists():
        commands += [[sys.executable, 'scripts/extension_v3/closure.py', '--require-terminal'],
                     [sys.executable, 'scripts/extension_v3/report.py']]
    completed = []
    for command in commands:
        result = subprocess.run(command, cwd=destination, capture_output=True, text=True,
            env=dict(os.environ, HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1'))
        if result.returncode:
            raise RuntimeError('Offline command failed: ' + repr(command) + '\n' + result.stderr[-2000:])
        completed.append(command[1:])
        print(json.dumps({'offline_command_passed': command[1:]}), flush=True)
    changed = [name for name, digest in before.items() if sha(destination / name) != digest]
    if changed:
        raise ValueError('Reproduction mismatch: ' + repr(changed))
    report = {'status': 'passed', 'scope': 'Completed arms only; isolated staged export, existing installed environment, no inference or raw-source reconstruction.',
        'index_tree': subprocess.check_output(['git', 'write-tree'], cwd=ROOT, text=True).strip(),
        'script_sha256': sha(Path(__file__)), 'commands': completed, 'byte_identical_artifacts': before,
        'configs': configs, 'credentials_or_weights_in_export': False,
        'python_version': sys.version, 'local_export': str(destination.relative_to(ROOT))}
    (OUTPUT / 'offline-reproduction-v1.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': 'passed', 'commands': len(completed), 'byte_identical_artifacts': len(before)}))


if __name__ == '__main__':
    main()
