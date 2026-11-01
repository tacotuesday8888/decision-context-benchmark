"""Offline complete-arm raw-request, parser, model metadata and accounting audit."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path
import plan
from source_audit import sha
from adapter import parse as parse_laya
from adapters import probability

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/extension-v3'


def safe_parse(config, body):
    for line in body.splitlines():
        if line.startswith('data:'):
            try:
                event = json.loads(line[5:].strip())
            except ValueError:
                continue
            if isinstance(event, dict) and event.get('type') == 'error':
                return {'status': 'provider_failed', 'valid': False, 'prediction': None,
                        'provider_error_code': event.get('code') or (event.get('error') or {}).get('code')}
    try:
        return plan.preserved.parse(config, body)
    except (ValueError, KeyError, TypeError, IndexError):
        return {'status': 'parse_error', 'valid': False, 'prediction': None}


def metered_cost(config, parsed, route):
    if route in ('subscription', 'local'):
        return 0.0
    usage = parsed.get('usage') or {}
    settings = plan.preserved.PANEL[config]
    incoming = usage.get('input_tokens')
    outgoing = usage.get('output_tokens', 0) if settings['kind'] != 'chat' else usage.get('output_tokens')
    if type(incoming) is not int or type(outgoing) is not int or min(incoming, outgoing) < 0:
        return None
    return (2 * incoming * settings['input_usd_per_million'] + outgoing * settings['output_usd_per_million']) / 1e6


def state(config, payload):
    if config == 'protectai_local':
        return {'CANDIDATE': payload['candidate']}
    if 'state' in payload:
        return json.loads(payload['state'])
    if isinstance(payload['input'], str):
        return json.loads(payload['input'])
    return json.loads(payload['input'][0]['content'])


def audit(config):
    frozen_path = OUT / 'confirmation-freeze-v1.json'
    frozen = json.loads(frozen_path.read_text())
    amendment_path = OUT / 'runtime-amendment-v3.0.1.json'
    amendment = json.loads(amendment_path.read_text())
    assert amendment['prior_confirmation_freeze_sha256'] == sha(frozen_path.read_bytes())
    assert set(amendment['implementation_hashes']) == {'scripts/extension_v3/run.py'}
    expected_hashes = dict(frozen['hashes'], **amendment['implementation_hashes'])
    for filename, digest in expected_hashes.items():
        assert sha((ROOT / filename).read_bytes()) == digest, filename
    for filename, digest in frozen['development_records'].items():
        assert sha((ROOT / filename).read_bytes()) == digest, filename
    manifest = {r['id']: r for r in plan.read(OUT / 'collection-manifest-v1.jsonl')}
    request_plan = json.loads((OUT / 'request-plan-v1.json').read_text())
    settings, route = request_plan['models'][config], request_plan['routes'][config]
    jobs = [j for j in frozen['jobs'] if j['config'] == config]
    ledger = json.loads((OUT / 'analysis' / (config + '-ledger.json')).read_text())['entries']
    entries = {r['key']: r for r in ledger}
    assert len(entries) == len(ledger) == len(jobs)
    records, tasks = [], {}
    for job in jobs:
        key = sha(json.dumps(job, sort_keys=True))[:24]
        path = OUT / 'confirmation' / config / (key + '.json')
        record = json.loads(path.read_text())
        assert record['status'] in ('completed', 'failed') and record['attempt'] == 0
        assert record['job'] == job and record['split'] == 'confirmation'
        evidence = state(config, record['request'])
        assert sha(evidence['CANDIDATE']) == manifest[job['id']]['candidate_sha256']
        if job['condition'] == 'task':
            assert sha(evidence['TRUSTED_USER_TASK']) == manifest[job['id']]['task_sha256']
            tasks[job['id']] = evidence['TRUSTED_USER_TASK']
        records.append((key, path, record, evidence))
    counts, used_tokens, window_count, hashes, cost = Counter(), [], 0, {}, 0.0
    preflight = {(r['id'], r['condition']): r for r in plan.read(OUT / 'token-audit-v1.jsonl')}
    for key, path, record, evidence in records:
        job = record['job']
        row = dict(manifest[job['id']], candidate=evidence['CANDIDATE'], trusted_task=tasks.get(job['id']))
        expected_request = plan.request(config, row, job['condition'])
        assert record['request'] == expected_request
        assert record['request_sha256'] == sha(plan.preserved.canonical(expected_request))
        assert record['access_route'] == route and record['paid_request'] == (route == 'api_key')
        assert record['freeze_sha256'] == sha(frozen_path.read_bytes())
        if 'runtime_amendment_sha256' in record:
            assert record['runtime_amendment_sha256'] == sha(amendment_path.read_bytes())
        metadata = record['model_metadata']
        if config == 'nimble_local':
            assert metadata['model']['digest'] == settings['revision']
            assert metadata['model']['details']['quantization_level'] == 'Q4_K_M'
            assert metadata['runtime'] == '0.40.11'
        else:
            assert metadata == settings
        parsed = record.get('parsed')
        if config == 'laya_local' and 'raw_response' in record:
            recomputed = parse_laya(record['raw_response'])
            actual = record['token_audit']
            expected = preflight[(job['id'], job['condition'])]
            for name, value in actual.items():
                assert expected[name] == value
            assert not actual['truncated'] and actual['state_tokens_dropped'] == 0
            assert recomputed['usage']['input_tokens'] == actual['input_tokens']
        elif config == 'protectai_local':
            raw = record['raw_response']
            assert raw['returned_model'] == settings['model'] and raw['revision'] == settings['revision']
            assert raw['windows'] == len(raw['window_scores']) and raw['windows'] > 0
            assert all(type(p) in (int, float) and 0 <= p <= 1 for p in raw['window_scores'])
            assert type(raw['input_tokens']) is int and raw['input_tokens'] > 0
            width, overlap = settings['window_tokens'], settings['overlap_tokens']
            expected_windows = 1 + math.ceil(max(0, raw['input_tokens'] - width) / (width - overlap))
            assert raw['windows'] == expected_windows, 'Detector window coverage mismatch'
            assert raw['score'] == max(raw['window_scores'])
            recomputed = dict(raw, **probability(raw['score']))
            window_count += raw['windows']
        elif 'raw_body' in record:
            if record['observation']['http_status'] != 200:
                recomputed = {'status': 'http_error', 'valid': False}
            elif config == 'nimble_local':
                recomputed = plan.preserved.nimble.parse(json.loads(record['raw_body']))
            else:
                recomputed = safe_parse(config, record['raw_body'])
        else:
            assert record['status'] == 'failed' and 'error_type' in record
            recomputed = parsed
        assert recomputed == parsed, str(path)
        assert record['status'] == ('completed' if parsed and parsed['status'] in ('ok', 'tie') else 'failed')
        if record['status'] == 'completed' and config != 'protectai_local':
            usage = parsed['usage']
            assert type(usage['input_tokens']) is int and usage['input_tokens'] > 0
            assert not usage.get('truncated') and not usage.get('state_tokens_dropped', 0)
            if config == 'nimble_local':
                assert usage['input_tokens'] <= settings['context_tokens'], 'Native input exceeds declared bound'
            used_tokens.append(usage['input_tokens'])
        entry = entries['confirmation:' + config + ':' + key]
        assert entry['status'] == 'settled' and entry['config'] == config
        reserve = plan.preserved.reserve_usd(config, expected_request, route)
        assert reserve == record['reserved_usd'] == entry['reserved_usd']
        expected_cost = metered_cost(config, parsed or {}, route)
        if expected_cost is None:
            expected_cost = reserve
        assert math.isclose(entry['accounted_usd'], expected_cost, abs_tol=1e-12)
        cost += entry['accounted_usd']
        counts[parsed.get('status', 'runtime_error') if parsed else 'runtime_error'] += 1
        hashes[str(path.relative_to(ROOT))] = sha(path.read_bytes())
    receipt = {'status': 'passed', 'config': config, 'planned_and_terminal_cells': len(jobs),
        'parsed_statuses': dict(counts), 'record_sha256': hashes, 'accounted_usd': cost,
        'input_tokens': {'records': len(used_tokens), 'sum': sum(used_tokens), 'max': max(used_tokens) if used_tokens else None},
        'detector_forward_windows': window_count, 'verifier_sha256': sha(Path(__file__).read_bytes()),
        'scope': 'Frozen request reconstruction from hash-bound recorded source text/task, raw reparse, startup model identity, Laya preflight, detector windows, settled ledger. No new inference. Nimble per-request loaded context and Laya per-forward dtype were not captured by runner.'}
    (OUT / 'analysis' / (config + '-record-audit.json')).write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: receipt[k] for k in ['status', 'config', 'planned_and_terminal_cells', 'parsed_statuses', 'accounted_usd', 'detector_forward_windows']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    audit(parser.parse_args().config)
