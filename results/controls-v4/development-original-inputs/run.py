"""Frozen, resumable v4 inference with separate evidence and all-in provider caps."""
import argparse
from datetime import datetime, timezone
import fcntl
import json
import math
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
import plan
from integrity import verify as verify_completed
from validate_collection import validate
from preserved_adapters import sha

OUT = ROOT / 'results/controls-v4'
RAW = ROOT / 'data/raw/controls-v4'
ROUTES = json.loads((OUT / 'request-plan-v1.json').read_text())['routes']


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = RAW / (path.name + '.' + str(os.getpid()) + '.tmp')
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n')
    os.replace(temp, path)


def development_rows():
    return plan.development_rows(plan.read(RAW / 'prepared-collection-v1.jsonl'))


def jobs(split):
    return plan.read(OUT / (split + '-jobs-v1.jsonl'))


def code_hashes():
    names = ('run.py', 'plan.py', 'preserved_adapters.py', 'prepare.py', 'validate_collection.py', 'validate_exposure.py', 'integrity.py', 'token_audit.py')
    paths = [ROOT / 'scripts/controls_v4' / name for name in names]
    paths += [ROOT / 'docs/controls-v4/PROTOCOL-v4.0.md']
    paths += [OUT / name for name in ('request-plan-v1.json', 'prompts-v1.json', 'confirmation-jobs-v1.jsonl',
        'development-jobs-v1.jsonl', 'collection-manifest-v1.jsonl', 'collection-summary-v1.json',
        'collection-validation-v1.json', 'exposure-validation-v1.json', 'price-verification-v1.json',
        'token-audit-v1.jsonl', 'token-audit-summary-v1.json')]
    for directory in ('expanded_v2', 'expanded_execution', 'laya_v2', 'nimble_v2'):
        paths += list((ROOT / 'scripts' / directory).glob('*.py'))
    return {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in sorted(paths)}


def freeze(split):
    verify_completed()
    validate()
    exposure = json.loads((OUT / 'exposure-validation-v1.json').read_text())
    if exposure['status'] != 'passed' or exposure['collection_sha256'] != sha((RAW / 'prepared-collection-v1.jsonl').read_bytes()):
        raise ValueError('Exposure validation stale or failed')
    frozen = {'version': 'controls-v4.0', 'split': split, 'hashes': code_hashes(), 'jobs': jobs(split)}
    if split == 'confirmation':
        frozen['development_freeze_sha256'] = sha((OUT / 'development-freeze-v1.json').read_bytes())
        frozen['development_records'] = {str(p.relative_to(ROOT)): sha(p.read_bytes())
            for p in sorted((OUT / 'development').glob('*/*.json'))}
    path = OUT / (split + '-freeze-v1.json')
    if path.exists() and json.loads(path.read_text()) != frozen:
        raise ValueError('Freeze differs; preserve old evidence and version an amendment')
    if not path.exists():
        save(path, frozen)
    return frozen


def verify_freeze(split):
    verify_completed()
    frozen = json.loads((OUT / (split + '-freeze-v1.json')).read_text())
    expected = dict(frozen['hashes'])
    if expected != code_hashes() or frozen['jobs'] != jobs(split):
        raise ValueError('Frozen configuration/code differs')
    raw = RAW / 'prepared-collection-v1.jsonl'
    summary = json.loads((OUT / 'collection-summary-v1.json').read_text())
    if sha(raw.read_bytes()) != summary['collection_sha256']:
        raise ValueError('Prepared text changed')
    if split == 'confirmation':
        for name, digest in frozen['development_records'].items():
            if sha((ROOT / name).read_bytes()) != digest:
                raise ValueError('Development evidence changed')
    return frozen


def provider(config):
    return 'typesafe' if config == 'jev_firstparty' else 'openai' if config == 'luna_decisions' else None


def transact(key, config, amount=None, settled=None):
    path = OUT / 'inference-ledger-v1.json'
    with (RAW / 'inference-budget.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ledger = json.loads(path.read_text()) if path.exists() else {'entries': []}
        matched = [e for e in ledger['entries'] if e['key'] == key]
        if amount is not None:
            if matched or not math.isfinite(amount) or amount < 0:
                raise ValueError('Duplicate or invalid reservation')
            name = provider(config)
            if name:
                used = json.loads((OUT / 'request-plan-v1.json').read_text())['prior_accounted_usd'][name]
                used += sum(e['accounted_usd'] for e in ledger['entries'] if e['provider'] == name)
                if used + amount > json.loads((OUT / 'request-plan-v1.json').read_text())['provider_caps_usd'][name] + 1e-12:
                    raise PermissionError('All-in provider cap would be exceeded')
            ledger['entries'].append({'key': key, 'provider': name, 'config': config,
                'reserved_usd': amount, 'accounted_usd': amount, 'status': 'pending'})
        else:
            if len(matched) != 1:
                raise ValueError('Missing reservation')
            entry = matched[0]
            if settled is not None and (not math.isfinite(settled) or not 0 <= settled <= entry['reserved_usd'] + 1e-12):
                raise ValueError('Usage exceeds bound; stop and preserve reservation')
            entry['accounted_usd'] = entry['reserved_usd'] if settled is None else settled
            entry['status'] = 'unknown_usage' if settled is None else 'settled'
        save(path, ledger)


def run(config, split):
    frozen = verify_freeze(split)
    directory = OUT / split / config
    directory.mkdir(parents=True, exist_ok=True)
    for stop_path in directory.glob('STOP*.json'):
        resolution = OUT / 'continuations' / (sha(stop_path.read_bytes()) + '.json')
        if split != 'confirmation' or not resolution.exists():
            raise PermissionError('Saved route failure requires documented resolution; no automatic retry')
        receipt = json.loads(resolution.read_text())
        stop = json.loads(stop_path.read_text())
        if (receipt['config'] != config or receipt['stop_sha256'] != sha(stop_path.read_bytes())
            or receipt['failure_sha256'] != sha((ROOT / stop['record']).read_bytes())
            or time.time() < receipt['not_before_epoch']):
            raise PermissionError('Continuation receipt mismatch or cooldown incomplete')
    if split == 'confirmation':
        expected = [j for j in jobs('development') if j['config'] == config]
        for job in expected:
            key = sha(json.dumps(job, sort_keys=True))[:24]
            record = json.loads((OUT / 'development' / config / (key + '.json')).read_text())
            if record.get('status') != 'completed' or record['parsed']['status'] not in ('ok', 'tie'):
                raise PermissionError('Development operational gate incomplete')
    lookup = {r['id']: r for r in (development_rows() if split == 'development' else plan.read(RAW / 'prepared-collection-v1.jsonl'))}
    with (RAW / ('run-' + config + '.lock')).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        model = plan.preserved.LocalDecision() if config == 'laya_local' else plan.preserved.LocalDetector() if config == 'protectai_local' else None
        metadata = plan.preserved.nimble.verify_model() if config == 'nimble_local' else plan.preserved.PANEL[config]
        selected = [j for j in frozen['jobs'] if j['config'] == config]
        for index, job in enumerate(selected):
            key = sha(json.dumps(job, sort_keys=True))[:24]
            path = directory / (key + '.json')
            payload = plan.request(config, lookup[job['id']], job['condition'])
            payload_hash = sha(plan.preserved.canonical(payload))
            if path.exists():
                old = json.loads(path.read_text())
                if old['request_sha256'] != payload_hash or old['access_route'] != ROUTES[config]:
                    raise ValueError('Existing request changed')
                if old['status'] == 'reserved':
                    raise PermissionError('Interrupted attempt retained; do not resend')
                continue
            amount = plan.preserved.reserve_usd(config, payload, ROUTES[config])
            attempt_key = split + ':' + config + ':' + key
            transact(attempt_key, config, amount=amount)
            record = {'job': job, 'split': split, 'status': 'reserved', 'attempt': 0,
                'access_route': ROUTES[config], 'paid_request': ROUTES[config] == 'api_key',
                'request': payload, 'request_sha256': payload_hash, 'reserved_usd': amount,
                'model_metadata': metadata, 'started_at': datetime.now(timezone.utc).isoformat(),
                'freeze_sha256': sha((OUT / (split + '-freeze-v1.json')).read_bytes())}
            save(path, record)
            start = time.perf_counter()
            cost = None
            try:
                if config == 'laya_local':
                    raw, parsed, audit = model.predict(payload)
                    record.update(raw_response=raw, token_audit=audit)
                    cost = 0.0
                elif config == 'nimble_local':
                    status, body = plan.preserved.nimble.call('/v1/systemone', payload)
                    record.update(raw_body=body, observation={'http_status': status})
                    parsed = plan.preserved.nimble.parse(json.loads(body)) if status == 200 else {'status': 'http_error', 'valid': False}
                    cost = 0.0
                elif config == 'protectai_local':
                    parsed = model.classify(lookup[job['id']]['candidate'])
                    record['raw_response'] = parsed
                    cost = 0.0
                else:
                    # Import operational helpers only here; old runner is never invoked.
                    from execute import safe_parse, metered_cost
                    from smoke_access import env_secret
                    from provider_access import subscription_credentials
                    from transport import post
                    credential = env_secret(plan.preserved.PANEL[config]['credential']) if ROUTES[config] == 'api_key' else subscription_credentials()['access_token']
                    observation, body = post(plan.preserved.PANEL[config]['endpoint'], payload, {'Authorization': 'Bearer ' + credential})
                    body = (body or '').replace(credential, '[redacted]')
                    record.update(raw_body=body, observation=observation)
                    parsed = safe_parse(config, body) if observation['http_status'] == 200 else {'status': 'http_error', 'valid': False}
                    cost = metered_cost(config, parsed, ROUTES[config])
                record['parsed'] = parsed
                record['status'] = 'completed' if parsed['status'] in ('ok', 'tie') else 'failed'
                if record['paid_request'] and cost is None:
                    record['status'] = 'failed'
                    record['accounting_error'] = 'missing_usage'
            except Exception as error:
                record.update(status='failed', error_type=type(error).__name__)
            record.update(elapsed_seconds=round(time.perf_counter() - start, 4), conservative_usage_cost_usd=cost)
            save(path, record)
            try:
                transact(attempt_key, config, settled=cost)
            except Exception as error:
                stop_target = directory / ('STOP-' + key + '.json' if (directory / 'STOP.json').exists() else 'STOP.json')
                save(stop_target, {'job': job, 'record': str(path.relative_to(ROOT)),
                    'reason': 'Accounting settlement failed; reservation preserved',
                    'error_type': type(error).__name__})
                raise
            print(json.dumps({'split': split, 'config': config, 'completed_index': index + 1,
                              'planned': len(selected), 'status': record['status']}), flush=True)
            if record['status'] != 'completed':
                stop_target = directory / ('STOP-' + key + '.json' if (directory / 'STOP.json').exists() else 'STOP.json')
                save(stop_target, {'job': job, 'record': str(path.relative_to(ROOT)),
                    'reason': 'Preserved failure; no automatic retries or fallback'})
                return


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['freeze-development', 'freeze-confirmation', 'development', 'confirmation'])
    parser.add_argument('--config', choices=list(plan.preserved.PANEL))
    args = parser.parse_args()
    if args.action.startswith('freeze-'):
        print(json.dumps({'frozen_jobs': len(freeze(args.action.split('-', 1)[1])['jobs'])}))
    else:
        if not args.config:
            parser.error('--config required')
        run(args.config, args.action)
