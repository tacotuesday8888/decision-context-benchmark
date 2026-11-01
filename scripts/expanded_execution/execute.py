"""Versioned execution over immutable v2 preparation; secrets never enter records."""
import argparse
import fcntl
import json
import math
import os
from pathlib import Path
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/expanded_v2'))
from common import DATA, sha, jsonl
from panel import PANEL as PREPARED_PANEL
from adapters import request as prepared_request, parse, LocalDetector
from development import dev_rows
from provider_access import subscription_credentials
from smoke_access import env_secret
from transport import post
from spending import provider_for_key, totals as provider_totals, caps as provider_caps

OUT = ROOT / 'results/expanded-execution'
VERSION = 'expanded-execution-v2.3.2'
sys.path.insert(0, str(ROOT/'scripts/laya_v2'))
from adapter import CONFIG as LAYA_CONFIG, request as laya_request
sys.path.insert(0, str(ROOT/'scripts/nimble_v2'))
from local import CONFIG as NIMBLE_CONFIG, request as nimble_request
PANEL = dict(PREPARED_PANEL, laya_local=LAYA_CONFIG, nimble_local=NIMBLE_CONFIG)
CONFIGS = tuple(PANEL)


def request(config, row, condition):
    if config == 'laya_local':return laya_request(row, condition)
    if config == 'nimble_local':return nimble_request(row, condition)
    return prepared_request(config, row, condition)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n')
    os.replace(temp, path)


def verify_preparation():
    frozen = json.loads((ROOT / 'results/expanded-v2/preparation-freeze.json').read_text())
    pilot = json.loads((ROOT / 'results/expanded-v2/pilot-integrity.json').read_text())
    for name, digest in dict(frozen['hashes'], **pilot).items():
        if sha((ROOT / name).read_bytes()) != digest:
            raise ValueError('Protected artifact changed: ' + name)


def route(config, routes):
    if config in ('protectai_local', 'laya_local', 'nimble_local'):
        return 'local'
    return routes[config]


def reserve_usd(config, payload, access):
    if access in ('local', 'subscription'):
        return 0.0
    p = PANEL[config]
    # UTF-8 bytes + framing allowance, 2x input rate covers cache writes.
    # Reserve output at its full configured cap, never at observed mean length.
    input_bound = len(canonical(payload).encode()) + 4096
    return (2 * input_bound * p['input_usd_per_million'] +
            (p['output_cap'] or 0) * p['output_usd_per_million']) / 1e6


def ledger_transaction(method):
    def locked(self, *args, **kwargs):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with (self.path.parent / '.budget.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if self.path.exists():
                self.data = json.loads(self.path.read_text())
                if self.data['cap_usd'] != self.cap:
                    raise ValueError('Cannot silently change saved cap')
            return method(self, *args, **kwargs)
    return locked


class Ledger:
    """Caller holds run lock. Pending/crashed requests retain their full reservation."""
    def __init__(self, path, cap):
        if not math.isfinite(cap) or cap < 0:
            raise ValueError('Finite nonnegative cap required')
        self.path, self.cap = path, cap
        self.data = json.loads(path.read_text()) if path.exists() else {'entries': []}
        if 'cap_usd' in self.data and self.data['cap_usd'] != cap:
            raise ValueError('Cannot silently change saved cap')
        self.data['cap_usd'] = cap

    @ledger_transaction
    def begin(self, key, amount):
        if any(e['key'] == key for e in self.data['entries']):
            raise ValueError('Attempt already reserved; inspect pending evidence')
        provider = provider_for_key(key)
        if provider:
            if self.cap > provider_caps()[provider]:raise PermissionError('Ledger cap exceeds owner provider cap')
            # Include the in-memory current ledger exactly once, and every old/new
            # ledger for this provider. TypeSafe cannot consume OpenAI's allowance.
            total = sum(e['accounted_usd'] for e in self.data['entries'] if provider_for_key(e['key']) == provider)
            for path in self.path.parent.glob('*ledger*.json'):
                if path != self.path:
                    total += sum(e['accounted_usd'] for e in json.loads(path.read_text())['entries'] if provider_for_key(e['key']) == provider)
        else:
            total = sum(e['accounted_usd'] for e in self.data['entries'])
            if self.path.name.startswith('execution-ledger'):
                for path in self.path.parent.glob('execution-ledger*.json'):
                    if path != self.path:
                        total += sum(e['accounted_usd'] for e in json.loads(path.read_text())['entries'])
        if total + amount > self.cap + 1e-12:
            raise PermissionError('Execution spending cap reached before request')
        self.data['entries'].append({'key': key, 'reserved_usd': amount,
                                     'accounted_usd': amount, 'state': 'pending'})
        save(self.path, self.data)

    @ledger_transaction
    def finish(self, key, observed):
        e = next(e for e in self.data['entries'] if e['key'] == key)
        # Unknown billing remains reserved, including failed/ambiguous attempts.
        if observed is not None:
            e['accounted_usd'] = observed
        e['state'] = 'recorded'
        save(self.path, self.data)
        if observed is not None and observed > e['reserved_usd'] + 1e-12:
            raise RuntimeError('Provider usage exceeded reservation; stop and review rates')


def metered_cost(config, parsed, access):
    if access in ('subscription', 'local'):
        return 0.0
    u = parsed.get('usage') or {}
    n = u.get('input_tokens')
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        return None
    p = PANEL[config]
    out = u.get('output_tokens', 0) if p['kind'] != 'chat' else u.get('output_tokens')
    if isinstance(out, bool) or not isinstance(out, int) or out < 0:
        return None
    # Conservative accounting: no discounts; includes up to 2x input for cache writes.
    return (n * 2 * p['input_usd_per_million'] + out * p['output_usd_per_million']) / 1e6


def safe_parse(config, body):
    # Some streaming failures arrive as standalone error events without a terminal
    # response object. Stop the route on those, including subscription quota gates.
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
        return parse(config, body)
    except (ValueError, KeyError, TypeError, IndexError):
        return {'status': 'parse_error', 'valid': False, 'prediction': None}


def has_usage(parsed):
    u = parsed.get('usage') or {}
    return isinstance(u.get('input_tokens'), int) and not isinstance(u.get('input_tokens'), bool)


def development_passed(config, access):
    records = [json.loads(p.read_text()) for p in (OUT / 'checks' / config).glob('*.json') if p.name != 'STOP.json']
    return len(records) == 2 and all(r['access_route'] == access and r['parsed']['valid'] and
                                    has_usage(r['parsed']) for r in records)


def run(config, split, routes, ledger, config_hash):
    if config == 'nimble_local':
        from run import run as run_nimble
        return run_nimble(split)
    if config == 'laya_local':
        from runner import run as run_laya
        return run_laya(split)
    access = route(config, routes)
    paid = access == 'api_key'
    if split == 'eval' and access != 'local' and not development_passed(config, access):
        raise PermissionError('Two successful development checks with usage required: ' + config)
    rows = dev_rows()[:2] if split == 'dev' else [r for r in jsonl(DATA/'collection.jsonl') if r['split'] == 'eval']
    model = LocalDetector() if access == 'local' else None
    directory = OUT / ('checks' if split == 'dev' else 'evaluation') / config
    directory.mkdir(parents=True, exist_ok=True)
    stop_path = directory / 'STOP.json'
    if stop_path.exists():
        from stop_resolution import resolved
        if not resolved(directory, access):
            raise PermissionError('Provider stopped previously; resolve saved STOP before any new calls')
    completed = 0
    for row in rows:
        conditions = ['candidate'] if split == 'dev' or access == 'local' else row['conditions']
        for condition in conditions:
            payload = request(config, row, condition)
            key = sha(config + row['id'] + condition)[:24]
            paths = sorted(directory.glob(key + '-*.json'))
            if paths:
                previous = json.loads(paths[-1].read_text())
                if previous['access_route'] != access or previous['request_sha256'] != sha(canonical(payload)):
                    raise ValueError('Saved cell route/payload differs; new version required')
                # Every completed logical cell, including invalid output, is retained and skipped.
                continue
            for attempt in range(2 if split == 'eval' else 1):
                attempt_key = f'{split}:{config}:{key}:{attempt}'
                amount = reserve_usd(config, payload, access)
                credential = None
                if access == 'api_key':
                    credential = env_secret(PANEL[config]['credential'] if PANEL[config]['kind'] != 'chat' else 'OPENAI_API_KEY')
                elif access == 'subscription':
                    credential = subscription_credentials()['access_token']
                if attempt:
                    retries = sum('-1.json' in p.name for p in directory.glob('*.json'))
                    if retries >= 41:
                        break
                ledger.begin(attempt_key, amount)
                start = time.perf_counter()
                if access == 'local':
                    parsed = model.classify(row['candidate'])
                    body, observation = None, {'http_status': None}
                else:
                    observation, body = post(PANEL[config]['endpoint'], payload, {'Authorization': 'Bearer ' + credential})
                    body = (body or '').replace(credential, '[redacted]')
                    parsed = safe_parse(config, body) if observation['http_status'] == 200 else {
                        'status': 'http_error', 'valid': False, 'prediction': None}
                record = {'version': VERSION, 'execution_config_sha256': config_hash, 'config': config,
                          'id': row['id'], 'split': split, 'condition': condition, 'attempt': attempt,
                          'candidate_sha256': row['candidate_sha256'], 'request': payload,
                          'request_sha256': sha(canonical(payload)), 'access_route': access,
                          'paid_request': paid, 'started_at': datetime.now(timezone.utc).isoformat(),
                          'elapsed_seconds': round(time.perf_counter()-start, 3), 'observation': observation,
                          'raw_body': body, 'parsed': parsed, 'reserved_usd': amount}
                cost = metered_cost(config, parsed, access)
                record['conservative_usage_cost_usd'] = cost
                save(directory / f'{key}-{attempt}.json', record)
                ledger.finish(attempt_key, cost)
                status = observation.get('http_status')
                transient = status in (0, 500, 502, 503, 504) or bool(observation.get('transport_exit_code'))
                stop = access != 'local' and ((status != 200 and not transient) or
                    parsed['status'] in ('provider_failed', 'model_mismatch') or
                    (paid and status == 200 and not has_usage(parsed)))
                if split == 'dev' and not parsed['valid']:
                    stop = True
                if stop:
                    save(directory/'STOP.json', {'id': row['id'], 'http_status': status, 'status': parsed['status']})
                    print(json.dumps({'config': config, 'stopped': True, 'status': parsed['status'], 'http_status': status}), flush=True)
                    return
                if not transient or attempt == 1 or split == 'dev':
                    break
                delay = observation.get('response_headers', {}).get('retry-after', '1')
                try:
                    delay = float(delay)
                except ValueError:
                    delay = 60
                if delay > 60:
                    save(directory/'STOP.json', {'reason': 'Long Retry-After; manual resume required', 'retry_after': delay})
                    return
                time.sleep(max(0, delay))
            completed += 1
            if completed % 25 == 0:
                print(json.dumps({'config': config, 'split': split, 'completed': completed}), flush=True)
    print(json.dumps({'config': config, 'split': split, 'new_cells': completed}), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('mode', choices=['check', 'local', 'eval', 'estimate'])
    p.add_argument('--config', choices=CONFIGS)
    args = p.parse_args()
    verify_preparation()
    if args.config == 'nimble_local' and args.mode in ('check', 'eval', 'local'):
        from run import run as run_nimble
        run_nimble('dev' if args.mode == 'check' else 'eval')
        return
    if args.config == 'laya_local' and args.mode in ('check', 'eval', 'local'):
        from runner import run as run_laya
        run_laya('dev' if args.mode == 'check' else 'eval')
        return
    config = json.loads((OUT/'execution-config-v2.3.json').read_text())
    routes = config['routes']
    digest = sha(canonical(config))
    if args.mode == 'estimate':
        rows = [r for r in jsonl(DATA/'collection.jsonl') if r['split'] == 'eval']
        estimates = {}
        for c in CONFIGS:
            costs = [reserve_usd(c, request(c,r,k), route(c,routes)) for r in rows
                     for k in (['candidate'] if c == 'protectai_local' else r['conditions'])]
            estimates[c] = {'cells': len(costs), 'no_retry_reservation_usd': sum(costs),
                            'including_retry_reservation_usd': sum(costs)+sum(sorted(costs,reverse=True)[:41])}
        print(json.dumps(estimates, indent=2)); return
    OUT.mkdir(exist_ok=True)
    with (OUT/('.'+args.mode+'-'+(args.config or 'all')+'.run.lock')).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.mode == 'local':
            configs, split, cap, ledger_path = ['protectai_local'], 'eval', 0, OUT/'local-ledger.json'
        elif args.mode == 'check':
            configs = [args.config] if args.config else [c for c in CONFIGS if c != 'protectai_local']
            split, cap, ledger_path = 'dev', .99, OUT/'check-ledger.json'
        else:
            configs, split = [args.config] if args.config else list(CONFIGS), 'eval'
            cap, ledger_path = 0, OUT/'local-ledger-v2.3.json'
        for c in configs:
            provider = 'typesafe' if c == 'jev_firstparty' else ('openai' if c in ('luna_decisions','luna_chat','astra_chat') else None)
            ledger = Ledger(OUT/(provider+'-ledger-v2.3.json'), config['provider_spending_caps_usd'][provider]) if provider else Ledger(OUT/'local-ledger-v2.3.json',0)
            run(c, split, routes, ledger, digest)

if __name__ == '__main__':
    main()
