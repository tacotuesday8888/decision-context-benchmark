"""Resolve base transients plus one hash-bound nonterminal stream timeout."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import time
from source_audit import sha

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/extension-v3'


def nonterminal_timeout(record):
    """No answer, refusal, terminal event, usage or provider error may be bypassed."""
    if (record.get('access_route') != 'subscription' or record.get('paid_request') is not False
            or record.get('accounting_error')
            or record.get('observation', {}).get('http_status') != 200
            or record.get('observation', {}).get('transport_exit_code') != 28
            or record.get('parsed') != {'prediction': None, 'status': 'interrupted_stream',
                'termination': 'missing_terminal_event', 'valid': False}):
        return False
    events = []
    for line in record.get('raw_body', '').splitlines():
        if line.startswith('event:'):
            if line.split(':', 1)[1].strip() not in ('response.created', 'response.in_progress'):
                return False
        elif line.startswith('data:'):
            try:
                event = json.loads(line.split(':', 1)[1])
            except ValueError:
                return False
            response = event.get('response', {})
            if (event.get('type') not in ('response.created', 'response.in_progress')
                    or response.get('model') != 'gpt-6-astra'
                    or response.get('status') != 'in_progress'
                    or response.get('output') != []
                    or response.get('error') is not None
                    or response.get('incomplete_details') is not None
                    or response.get('usage') is not None):
                return False
            events.append(event['type'])
        elif line.strip():
            return False
    return events == ['response.created', 'response.in_progress']


def resolve(config):
    policy_path = OUT / 'runtime-amendment-v3.0.4.json'
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
            exception = policy['specific_nonterminal_timeout']
            exact_exception = (str(record_path.relative_to(ROOT)) == exception['failure_path']
                and failure_hash == exception['failure_sha256'] and stop_hash == exception['stop_sha256']
                and config == 'astra_chat' and nonterminal_timeout(record))
            base_transient = (record.get('parsed', {}).get('status') == 'http_error'
                and observation.get('http_status') in (0, 500, 502, 503, 504)
                and not record.get('accounting_error'))
            if not (base_transient or exact_exception):
                raise PermissionError('Unresolved stop outside base policy or exact reviewed exception')
            # Base HTTP failures keep the conservative keyword guard. The exact SSE
            # exception checks structured provider errors above; its echoed prompt
            # itself contains the word unauthorized.
            body = record.get('raw_body', '').lower()
            if not exact_exception and any(word in body for word in ('insufficient_quota', 'billing', 'unauthorized', 'invalid_api_key', 'usage_limit_reached')):
                raise PermissionError('Possible billing/auth/quota signal; preserve stop')
            delay = max(60., float(observation.get('response_headers', {}).get('retry-after', '60')))
            receipt = {'config': config, 'stop_sha256': stop_hash, 'failure_sha256': failure_hash,
                'not_before_epoch': datetime.fromisoformat(record['started_at']).timestamp() + record['elapsed_seconds'] + delay,
                'policy': 'Base transient eligibility or exact hash-bound nonterminal timeout; preserve failure, continue only unattempted jobs. Prior receipts verified unchanged.',
                'amendment_sha256': sha(policy_path.read_bytes())}
            target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
        print(json.dumps({'config': config, 'preserved_failure': stop['record'],
            'cooldown_remaining_seconds': max(0, receipt['not_before_epoch'] - time.time())}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    resolve(parser.parse_args().config)
