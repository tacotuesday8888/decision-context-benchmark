"""Resolve base-policy transient stops while respecting prior hash-bound receipts."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import time
from source_audit import sha

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/extension-v3'


def resolve(config):
    policy_path = OUT / 'runtime-amendment-v3.0.3.json'
    policy = json.loads(policy_path.read_text())
    assert sha(Path(__file__).read_bytes()) == policy['continuation_tool_sha256']
    assert sha((OUT / 'confirmation-freeze-v1.json').read_bytes()) == policy['confirmation_freeze_sha256']
    for name, digest in policy['prior_amendments'].items():
        assert sha((OUT / name).read_bytes()) == digest
    assert config in ('jev_firstparty', 'luna_decisions', 'luna_chat', 'astra_chat')
    stops = sorted((OUT / 'confirmation' / config).glob('STOP*.json'))
    assert len(stops) <= 10, 'Ten-stop continuation limit exceeded'
    allowed_amendments = set(policy['prior_amendments'].values()) | {sha(policy_path.read_bytes())}
    for stop_path in stops:
        stop = json.loads(stop_path.read_text())
        record_path = ROOT / stop['record']
        assert record_path.parent == stop_path.parent
        record = json.loads(record_path.read_text())
        assert record['job']['config'] == config and record['status'] == 'failed'
        stop_hash, failure_hash = sha(stop_path.read_bytes()), sha(record_path.read_bytes())
        target = OUT / 'continuations' / (stop_hash + '.json')
        if target.exists():
            receipt = json.loads(target.read_text())
            assert receipt['config'] == config and receipt['stop_sha256'] == stop_hash
            assert receipt['failure_sha256'] == failure_hash
            assert receipt['amendment_sha256'] in allowed_amendments
        else:
            observation = record.get('observation', {})
            if (record.get('parsed', {}).get('status') != 'http_error'
                    or observation.get('http_status') not in (0, 500, 502, 503, 504)
                    or record.get('accounting_error')):
                raise PermissionError('Unresolved stop is outside unchanged base transient policy')
            # Do not infer permission to bypass billing/auth/quota from a bad status code.
            body = record.get('raw_body', '').lower()
            if any(word in body for word in ('insufficient_quota', 'billing', 'unauthorized', 'invalid_api_key', 'usage_limit_reached')):
                raise PermissionError('Possible billing/auth/quota signal; preserve stop')
            delay = max(60., float(observation.get('response_headers', {}).get('retry-after', '60')))
            receipt = {'config': config, 'stop_sha256': stop_hash, 'failure_sha256': failure_hash,
                'not_before_epoch': datetime.fromisoformat(record['started_at']).timestamp() + record['elapsed_seconds'] + delay,
                'policy': 'Unchanged base transient eligibility; preserve failed cell, continue only unattempted jobs. Previously resolved stops are hash-verified without replacement.',
                'amendment_sha256': sha(policy_path.read_bytes())}
            target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
        print(json.dumps({'config': config, 'preserved_failure': stop['record'],
            'cooldown_remaining_seconds': max(0, receipt['not_before_epoch'] - time.time())}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    resolve(parser.parse_args().config)
