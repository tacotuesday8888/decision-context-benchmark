"""One hash-bound empty HTTP200/curl28 continuation; no requests or retries."""
from datetime import datetime
import json
from pathlib import Path
import time
from source_audit import sha

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/extension-v3'


def resolve():
    path = OUT / 'runtime-amendment-v3.0.2.json'
    policy = json.loads(path.read_text())
    assert sha(Path(__file__).read_bytes()) == policy['continuation_tool_sha256']
    assert sha((OUT / 'confirmation-freeze-v1.json').read_bytes()) == policy['confirmation_freeze_sha256']
    assert sha((OUT / 'runtime-amendment-v3.0.1.json').read_bytes()) == policy['prior_amendment_sha256']
    failure = ROOT / policy['failure_path']
    stop_path = ROOT / policy['stop_path']
    assert sha(failure.read_bytes()) == policy['failure_sha256']
    assert sha(stop_path.read_bytes()) == policy['stop_sha256']
    record = json.loads(failure.read_text())
    assert json.loads(stop_path.read_text())['record'] == policy['failure_path']
    assert record['job']['config'] == 'luna_chat' and record['status'] == 'failed'
    assert record['access_route'] == 'subscription' and record['paid_request'] is False
    assert record['raw_body'] == '' and record['observation']['http_status'] == 200
    assert record['observation']['transport_exit_code'] == 28
    assert record['parsed'] == {'prediction': None, 'status': 'interrupted_stream', 'termination': 'missing_terminal_event', 'valid': False}
    assert not record.get('accounting_error')
    assert len(list(stop_path.parent.glob('STOP*.json'))) <= 10
    delay = max(60., float(record['observation'].get('response_headers', {}).get('retry-after', '60')))
    receipt = {'config': 'luna_chat', 'stop_sha256': policy['stop_sha256'],
        'failure_sha256': policy['failure_sha256'],
        'not_before_epoch': datetime.fromisoformat(record['started_at']).timestamp() + record['elapsed_seconds'] + delay,
        'policy': 'Specific empty HTTP200/curl28 failure retained; continue only unattempted frozen jobs. No retry, replacement or new settings.',
        'amendment_sha256': sha(path.read_bytes()), 'prior_amendment_sha256': policy['prior_amendment_sha256']}
    target = OUT / 'continuations' / (receipt['stop_sha256'] + '.json')
    if target.exists():
        assert json.loads(target.read_text()) == receipt
    else:
        target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'failure_preserved': policy['failure_path'], 'cooldown_remaining_seconds': max(0, receipt['not_before_epoch'] - time.time())}))


if __name__ == '__main__':
    resolve()
