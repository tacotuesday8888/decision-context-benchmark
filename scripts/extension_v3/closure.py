"""Reconcile all frozen cells, attempts and provider reservations without inference.

A live snapshot is written only under ignored raw data. A tracked terminal receipt
is written only with --require-terminal and no missing/in-flight cells.
"""
import argparse
from collections import Counter, defaultdict
import fcntl
import json
import math
from pathlib import Path
from source_audit import sha

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/extension-v3'
RAW = ROOT / 'data/raw/extension-v3'


def closure(require_terminal=False):
    expected = {}
    for split in ('development', 'confirmation'):
        freeze = json.loads((OUT / (split + '-freeze-v1.json')).read_text())
        for job in freeze['jobs']:
            key = sha(json.dumps(job, sort_keys=True))[:24]
            identity = split + ':' + job['config'] + ':' + key
            assert identity not in expected
            expected[identity] = (split, job, key)
    with (RAW / 'inference-budget.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ledger_path = OUT / 'inference-ledger-v1.json'
        ledger_bytes = ledger_path.read_bytes()
        entries = json.loads(ledger_bytes)['entries']
        ledger = {e['key']: e for e in entries}
        assert len(ledger) == len(entries), 'Duplicate ledger key'
        assert set(ledger) <= set(expected), 'Unplanned reservation'
        actual = {}
        for split in ('development', 'confirmation'):
            for path in (OUT / split).glob('*/*.json'):
                if path.name.startswith('STOP'):
                    continue
                record = json.loads(path.read_text())
                identity = split + ':' + path.parent.name + ':' + path.stem
                assert identity in expected and identity in ledger, 'Unplanned/unreserved record'
                assert identity not in actual
                assert record['job'] == expected[identity][1]
                assert record['attempt'] == 0 and record['split'] == split
                assert record['status'] in ('reserved', 'completed', 'failed')
                actual[identity] = (record, sha(path.read_bytes()))
        pending, unknown, values, counts = [], [], defaultdict(list), Counter()
        for identity, entry in ledger.items():
            assert entry['status'] in ('pending', 'settled', 'unknown_usage')
            assert all(type(entry[k]) in (int, float) and math.isfinite(entry[k]) and entry[k] >= 0 for k in ('reserved_usd', 'accounted_usd'))
            assert entry['accounted_usd'] <= entry['reserved_usd'] + 1e-12
            config = expected[identity][1]['config']
            provider = 'typesafe' if config == 'jev_firstparty' else 'openai' if config == 'luna_decisions' else None
            assert entry['provider'] == provider and entry['config'] == config
            if provider:
                values[provider].append(entry['accounted_usd'])
            else:
                assert entry['accounted_usd'] == entry['reserved_usd'] == 0
            if entry['status'] == 'pending':
                assert entry['accounted_usd'] == entry['reserved_usd']
                pending.append(identity)
            elif entry['status'] == 'unknown_usage':
                assert entry['accounted_usd'] == entry['reserved_usd']
                unknown.append(identity)
            if identity in actual:
                record = actual[identity][0]
                assert record['reserved_usd'] == entry['reserved_usd']
                if entry['status'] == 'settled':
                    assert record['status'] in ('completed', 'failed')
                    assert record['conservative_usage_cost_usd'] is not None
                    assert math.isclose(record['conservative_usage_cost_usd'], entry['accounted_usd'], abs_tol=1e-12)
                counts[identity.split(':')[0] + ':' + config + ':' + record['status']] += 1
            else:
                assert entry['status'] == 'pending', 'Settled entry lacks raw evidence'
        plan = json.loads((OUT / 'request-plan-v1.json').read_text())
        totals = {provider: math.fsum([prior, *values[provider]]) for provider, prior in plan['prior_accounted_usd'].items()}
        assert all(totals[p] <= plan['provider_caps_usd'][p] for p in totals)
        missing = sorted(set(expected) - set(actual))
        in_flight = sorted(k for k, (r, _) in actual.items() if r['status'] == 'reserved')
        terminal = not missing and not pending and not in_flight
        if require_terminal:
            assert terminal, f'Incomplete: {len(missing)} missing, {len(pending)} pending, {len(in_flight)} reserved records'
            assert set(ledger) == set(expected)
        result = {'status': 'terminal' if terminal else 'incomplete', 'terminal_required': require_terminal,
            'planned_cells_including_development': len(expected), 'raw_records': len(actual),
            'status_counts': dict(counts), 'unattempted_or_missing': missing,
            'pending_reservations': pending, 'in_flight_records': in_flight,
            'unknown_usage_reservations_retained': unknown,
            'prior_accounted_usd': plan['prior_accounted_usd'], 'extension_accounted_usd': {p: math.fsum(v) for p, v in values.items()},
            'all_in_conservative_accounted_usd': totals, 'provider_caps_usd': plan['provider_caps_usd'],
            'ledger_sha256': sha(ledger_bytes), 'record_sha256': {k: digest for k, (_, digest) in actual.items()},
            'script_sha256': sha(Path(__file__).read_bytes()),
            'scope': 'Every frozen development/confirmation cell and ledger entry. Earlier costs inherited from preserved frozen plan. Conservative usage/reservations, not provider invoice or refreshed balance. Zero subscription metering excludes subscription fees/electricity.'}
    target = OUT / 'execution-closure-v1.json' if require_terminal else RAW / 'live-accounting-snapshot.json'
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: result[k] for k in ('status', 'planned_cells_including_development', 'raw_records', 'all_in_conservative_accounted_usd')}))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--require-terminal', action='store_true')
    closure(parser.parse_args().require_terminal)
