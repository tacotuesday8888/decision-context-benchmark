"""Rebuild frozen collection in isolation from pinned local source files/replay.

No source code, models or network calls are executed; this reuses the saved clean
AgentDojo replay and inventories. It is not a fresh upstream clone/replay test.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/extension-v3'
RAW = ROOT / 'data/raw/extension-v3'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    destination = Path(tempfile.mkdtemp(prefix='prepare-reproduction-', dir=RAW))
    subprocess.run(['git', 'checkout-index', '--all', '--prefix=' + str(destination) + '/'], cwd=ROOT, check=True)
    assert not (destination / '.secrets').exists() and not (destination / '.env.local').exists()
    source_paths = {RAW / 'agentdojo-clean-replay.jsonl'}
    for inventory, directory in [('injecagent-inventory.jsonl', 'InjecAgent'), ('agentdyn-inventory.jsonl', 'AgentDyn')]:
        rows = map(json.loads, (OUT / inventory).read_text().splitlines())
        for row in rows:
            path = RAW / directory / row['path']
            assert path.resolve().is_relative_to((RAW / directory).resolve())
            source_paths.add(path)
    inputs = {}
    for path in sorted(source_paths):
        relative = path.relative_to(ROOT)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        inputs[str(relative)] = sha(path)
        assert sha(target) == inputs[str(relative)]
    compared = ['results/extension-v3/' + name for name in
        ['collection-manifest-v1.jsonl', 'collection-summary-v1.json', 'collection-exclusions-v1.json', 'collection-validation-v1.json']]
    compared += ['data/raw/extension-v3/prepared-collection-v1.jsonl']
    expected = {name: sha(ROOT / name) for name in compared}
    commands = ['scripts/extension_v3/prepare.py', 'scripts/extension_v3/validate_collection.py']
    for command in commands:
        result = subprocess.run([sys.executable, command], cwd=destination, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError('Isolated preparation failed: ' + command + '\n' + result.stderr[-2000:])
    differences = [name for name, digest in expected.items() if sha(destination / name) != digest]
    assert not differences, differences
    assert all(sha(ROOT / name) == digest for name, digest in expected.items()), 'Original collection changed'
    result = {'status': 'passed', 'scope': 'Deterministic preparation and independent validation from pinned local artifacts and saved clean replay. No fresh downloads, upstream replay, model inference, or generated examples/labels.',
        'index_tree': subprocess.check_output(['git', 'write-tree'], cwd=ROOT, text=True).strip(),
        'commands': commands, 'input_sha256': inputs, 'byte_identical_artifacts': expected,
        'source_files_copied': len(inputs), 'script_sha256': sha(Path(__file__)),
        'local_export': str(destination.relative_to(ROOT)), 'python_version': sys.version}
    (OUT / 'preparation-reproduction-v1.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': 'passed', 'source_files_copied': len(inputs), 'byte_identical_artifacts': len(expected)}))


if __name__ == '__main__':
    main()
