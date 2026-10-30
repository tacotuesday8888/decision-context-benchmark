"""Document continuation of unattempted cells after isolated transport failures."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import time
from source_audit import sha

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/extension-v3'


def resolve(config):
    amendment = json.loads((OUT / 'runtime-amendment-v3.0.1.json').read_text())
    if sha(Path(__file__).read_bytes()) != amendment['continuation_tool_sha256']:
        raise ValueError('Continuation tool differs from amendment')
    if config not in ('jev_firstparty', 'luna_decisions', 'luna_chat', 'astra_chat'):
        raise ValueError('Only hosted transport failures are eligible')
    directory = OUT / 'confirmation' / config
    stops = sorted(directory.glob('STOP*.json'))
    if len(stops) > 10:
        raise PermissionError('Bounded transport-continuation limit exceeded; review route feasibility')
    for stop_path in stops:
        stop = json.loads(stop_path.read_text())
        record_path = ROOT / stop['record']
        record = json.loads(record_path.read_text())
        obs = record.get('observation', {})
        status = obs.get('http_status')
        if record.get('status') != 'failed' or record.get('parsed', {}).get('status') != 'http_error' or status not in (0, 500, 502, 503, 504):
            raise PermissionError('Not an isolated HTTP/transport failure; no authorization or semantic failure bypass')
        if record.get('accounting_error'):
            raise PermissionError('Accounting failure requires separate resolution')
        retry_after = obs.get('response_headers', {}).get('retry-after', '60')
        try:
            delay = max(60.0, float(retry_after))
        except ValueError:
            raise PermissionError('Non-numeric Retry-After requires explicit interpretation')
        end = datetime.fromisoformat(record['started_at']).timestamp() + record['elapsed_seconds']
        receipt = {'config': config, 'stop_sha256': sha(stop_path.read_bytes()),
            'failure_sha256': sha(record_path.read_bytes()), 'not_before_epoch': end + delay,
            'policy': 'Skip preserved failed cell; continue only previously unattempted frozen jobs.',
            'amendment_sha256': sha((OUT / 'runtime-amendment-v3.0.1.json').read_bytes())}
        target = OUT / 'continuations' / (receipt['stop_sha256'] + '.json')
        target.parent.mkdir(exist_ok=True)
        if target.exists() and json.loads(target.read_text()) != receipt:
            raise ValueError('Existing continuation receipt differs')
        if not target.exists():
            target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
        print(json.dumps({'config': config, 'failed_cell_preserved': record['job'],
            'cooldown_remaining_seconds': max(0, receipt['not_before_epoch'] - time.time())}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    resolve(parser.parse_args().config)
