"""Independently audit retained v6 execution, without any model or network calls.

The frozen plan supplies all denominators. The append-only journal supplies the
reservation order. Raw responses are parsed again rather than trusting saved
predictions. Only aggregate receipts may be tracked; normalized rows and detailed
dispositions remain under the ignored execution directory.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v6 import plan, routes
from scripts.study_v6.accounting import BudgetLedger, canonical, money, amount
from scripts.study_v6.common import ROOT, canonical_bytes, sha256
from scripts.study_v6.evidence import immutable, load
from scripts.study_v6.pricing import reserve, usage_cost


class VerificationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise VerificationError(message)


def _spec(request):
    result = {k: request[k] for k in ('key', 'provider', 'reserved_usd', 'request_sha256', 'config', 'split')}
    result['reserved_usd'] = amount(result['reserved_usd'])
    return result


def _decimal_equal(a, b):
    return (a is None and b is None) or (a is not None and b is not None and money(a) == money(b))


def _failure(status):
    return {'status': status, 'valid': False, 'prediction': None}


def _reparse(request, result, folder):
    """Reparse complete native bytes; interrupted intent remains primary missing."""
    raw_path = folder / 'response.raw'
    if result.get('interrupted_dispatch_intent_preserved') is True or result.get('reserved_raw_conflict_retained') is True:
        require(result['parsed'] == _failure('interrupted_unknown'), 'Interrupted primary was promoted to a prediction')
        return _failure('interrupted_unknown')
    if not raw_path.exists():
        require(result.get('error_type') and result['parsed'] == _failure('runtime_error'),
                'A completed attempt lacks native response evidence')
        return _failure('runtime_error')
    body = raw_path.read_text()
    config = request['config']
    if config == 'protectai_local':
        raw = json.loads(body)
        p = routes.PANEL[config]
        if raw.get('returned_model') != p['model'] or raw.get('revision') != p['revision']:
            return _failure('model_mismatch')
        return dict(raw, **routes.probability(raw['score']))
    if config == 'laya_local':
        return routes.parse_response(config, json.loads(body))
    observation = result['observation']
    http, exit_code = observation['http_status'], observation['transport_exit_code']
    require(type(http) is int and type(exit_code) is int, 'Invalid retained transport disposition')
    headers = folder / 'response-headers.partial'
    if http and headers.exists():
        statuses = re.findall(r'^HTTP/\d(?:\.\d)?\s+(\d{3})\b', headers.read_text(), re.MULTILINE)
        require(statuses and int(statuses[-1]) == http, 'Retained HTTP headers disagree with terminal transport status')
    if http == 200:
        parsed = routes.parse_response(config, body)
        if exit_code and parsed['status'] != 'model_mismatch':
            return dict(_failure('transport_error'), usage=parsed.get('usage') or {},
                        returned_model=parsed.get('returned_model'))
        return parsed
    if http in (401, 403):
        return _failure('authentication_error')
    if http == 400 and any(s in body.lower() for s in (
            'max_tokens_exceeded', 'context_length_exceeded', 'context length', 'too long', 'context window')):
        return _failure('unsupported_over_limit')
    return _failure('transport_error' if exit_code else 'http_error')


def _audit_attempt(request, entry, directory, stop_hash):
    folder = directory / 'attempts' / request['key']
    if entry['status'] == 'cancelled_unsent':
        require(not folder.exists(), 'Cancelled-unsent reservation has possibly sent attempt artifacts')
        require(stop_hash is not None and entry['evidence_sha256'] == stop_hash,
                'Cancelled-unsent entry lacks its exact immutable stop')
        require(money(entry['accounted_usd']) == money(entry['actual_usd']) == 0,
                'Cancelled-unsent reservation was charged')
        return _failure('cancelled_unsent'), None
    require(entry['status'] in ('settled', 'unknown_usage'), 'Attempt remains nonterminal')
    record_path = folder / 'execution-record.json'
    require(record_path.is_file() and sha256(record_path.read_bytes()) == entry['evidence_sha256'],
            'Execution record does not match the accounting evidence hash')
    record = load(record_path)
    require(record['version'] == plan.VERSION and record['attempt'] == 0 and
            record['first_attempt_primary'] is True, 'Unversioned or recovery evidence entered the primary run')
    for key in ('key', 'config', 'split', 'allocation', 'batch', 'request_sha256'):
        require(record[key] == request[key], 'Execution metadata changed: ' + key)
    require(record.get('charged_allocation', record['allocation']) == entry['allocation'],
            'Charged allocation differs from first owning reservation')
    require(_decimal_equal(record['reserved_usd'], request['reserved_usd']), 'Raw reservation differs from freeze')
    result = record['result']
    ambiguous = (result.get('interrupted_dispatch_intent_preserved') is True or
                 result.get('reserved_raw_conflict_retained') is True)
    conflict = result.get('reserved_raw_conflict_retained') is True
    require(result['request_sha256'] == request['request_sha256'], 'Raw request hash differs from frozen payload')
    require(isinstance(result['raw_hashes'], dict), 'Missing retained-byte hash inventory')
    for name, digest in result['raw_hashes'].items():
        require(Path(name).name == name and name != 'execution-record.json' and
                (name != 'completed.json' or conflict),
                'Unsafe or recursive raw evidence path')
        path = folder / name
        require(path.is_file() and sha256(path.read_bytes()) == digest, 'Retained native bytes changed or disappeared')
    actual_names = {p.name for p in folder.iterdir() if p.is_file()}
    expected_names = set(result['raw_hashes']) | {'execution-record.json'}
    completed = folder / 'completed.json'
    if completed.exists() and not conflict:
        require(load(completed) == result, 'Completed native result differs from charged result')
        expected_names.add('completed.json')
    else:
        require(ambiguous,
                'Ordinary first attempt lacks its immutable completion receipt')
    require(actual_names == expected_names and not any(p.is_dir() for p in folder.iterdir()),
            'Uninventoried attempt artifact or hidden second attempt')
    request_path = folder / 'request.json'
    if not ambiguous:
        require(request_path.is_file() and request_path.read_bytes() == canonical_bytes(request['payload']),
                'Native dispatched request bytes differ from exact freeze')
        started = load(folder / 'started.json')
        require(started['config'] == request['config'] and started['attempt_key'] == request['key'] and
                started['payload_sha256'] == request['request_sha256'] and
                started['route'] == routes.ROUTES[request['config']], 'Started request provenance changed')
        require(result['attempt_key'] == request['key'] and
                result['access_route'] == routes.ROUTES[request['config']] and
                result['paid_request'] == (request['provider'] is not None), 'Actual request route changed')
    elif request_path.exists():
        require(request_path.read_bytes() == canonical_bytes(request['payload']), 'Interrupted request bytes differ')
    parsed = _reparse(request, result, folder)
    require(parsed == result['parsed'], 'Independent native reparse disagrees with retained prediction')
    require(result['stop_required'] is (parsed['status'] not in ('ok', 'tie', 'unsupported_over_limit')),
            'Systemic route failure did not require a global stop')
    if request['config'] == 'laya_local' and parsed['status'] in ('ok', 'tie'):
        audit = result.get('token_audit') or {}
        require(audit.get('truncated') is False and audit.get('state_tokens_dropped') == 0 and
                audit.get('input_tokens') == parsed['usage']['input_tokens'] and
                type(audit.get('head_tokens')) is int and audit['head_tokens'] <= routes.PANEL['laya_local']['head_max_len'],
                'Native Laya forward differs from full-input token audit')
    expected_cost = usage_cost(request['provider'], parsed.get('usage')) if request['provider'] else {
        'accounted_usd': '0', 'actual_billed_usd': None,
        'basis': 'Existing subscription/local route; zero incremental metered API charge'}
    require(record['costs'] == expected_cost, 'Independent measured-usage pricing disagrees with execution record')
    expected_actual = expected_cost['accounted_usd']
    require(_decimal_equal(entry['actual_usd'], expected_actual), 'Journal settlement differs from native measured usage')
    if expected_actual is None:
        require(entry['status'] == 'unknown_usage' and
                _decimal_equal(entry['accounted_usd'], entry['reserved_usd']), 'Unknown usage reservation was released')
    else:
        require(entry['status'] == 'settled' and _decimal_equal(entry['accounted_usd'], expected_actual),
                'Known usage does not match terminal settlement')
    return parsed, record


def _expected_schedules(frozen, requests):
    expected = {}
    for allocation in ('main', 'supporting'):
        expected[allocation] = []
        for group in frozen.get('schedules', {}).get(allocation, []):
            if group['all_requests_supported']:
                require(all(k in requests for k in group['request_keys']), 'Runnable whole group has an omitted request')
                expected[allocation].append({'group': group['batch'],
                    'requests': [_spec(requests[k]) for k in group['request_keys']]})
    return expected


def _audit_cost_order(journal_path, requests, expected_schedules):
    """Replay reservations independently: each admission fits; each cost stop cannot.

    This proof reads no predictions. Settlement amounts are checked independently
    against native evidence by _audit_attempt, then joined to this replay.
    """
    events = [json.loads(line) for line in Path(journal_path).read_text().splitlines()]
    policy = events[0]['data']['policy']
    entries, schedules, admitted, cost_stops = {}, {}, defaultdict(int), {}

    def cap_reasons(allocation, specs):
        reasons = []
        for provider in ('openai', 'typesafe'):
            used = sum((money(e['accounted_usd']) for e in entries.values() if e['provider'] == provider), Decimal(0))
            bucket = sum((money(e['accounted_usd']) for e in entries.values()
                          if e['provider'] == provider and e['allocation'] == allocation), Decimal(0))
            added = sum((money(s['reserved_usd']) for s in specs
                         if s['key'] not in entries and s['provider'] == provider), Decimal(0))
            if money(policy['prior_accounted_usd'][provider]) + used + added > money(policy['provider_caps_usd'][provider]):
                reasons.append(provider + ':global_cap')
            if used + added > money(policy['v6_caps_usd'][provider]):
                reasons.append(provider + ':v6_cap')
            if bucket + added > money(policy['allocations_usd'][allocation][provider]):
                reasons.append(provider + ':' + allocation + '_allocation')
        return reasons

    for event in events[1:]:
        kind, data = event['kind'], event['data']
        if kind == 'register_schedule':
            allocation = data['allocation']
            require(data['groups'] == expected_schedules[allocation], 'Paid schedule differs from frozen whole-group order')
            schedules[allocation] = data['groups']
        elif kind == 'reserve':
            allocation, keys = data['allocation'], data['request_keys']
            require(all(k in requests for k in keys), 'Unplanned/recovery request entered first-attempt ledger')
            specs = [_spec(requests[k]) for k in keys]
            require(sha256(canonical(specs)) == data['requests_sha256'], 'Reservation refers to changed exact request specs')
            require(not cap_reasons(allocation, specs), 'Admitted requests exceeded a frozen budget at admission')
            if data.get('group') is not None:
                index = admitted[allocation]
                require(allocation in schedules and index < len(schedules[allocation]), 'Admission lies outside registered schedule')
                group = schedules[allocation][index]
                require(data['group'] == group['group'] and keys == [r['key'] for r in group['requests']],
                        'Admission skipped/reordered a whole group')
                require(allocation not in cost_stops, 'Inference advanced after its cost-only stopping point')
                if index:
                    require(all(entries[r['key']]['status'] in ('settled', 'unknown_usage')
                                for r in schedules[allocation][index-1]['requests']),
                            'Next group advanced before the previous whole group was terminal')
                admitted[allocation] += 1
            else:
                require(allocation == 'development' or (allocation == 'supporting' and
                        all(s['provider'] is None and money(s['reserved_usd']) == 0 for s in specs)),
                        'Paid confirmation reservation bypassed the atomic whole-group schedule')
            expected_new = [s for s in specs if s['key'] not in entries]
            require(data['new_requests'] == expected_new, 'Atomic reservation omitted or duplicated provider holds')
            for spec in data['new_requests']:
                entries[spec['key']] = dict(spec, allocation=allocation, accounted_usd=spec['reserved_usd'], status='reserved')
        elif kind == 'dispatch':
            entry = entries[data['key']]
            require(entry['status'] == 'reserved', 'Second dispatch entered the first-attempt journal')
            entry['status'] = 'dispatched'
        elif kind == 'settle':
            entry = entries[data['key']]
            require(entry['status'] == 'dispatched', 'Settlement lacks a unique dispatch intent')
            require(data['actual_usd'] is None or money(data['actual_usd']) <= money(entry['reserved_usd']),
                    'Native settlement exceeds its pre-dispatch reservation')
            entry['accounted_usd'] = entry['reserved_usd'] if data['actual_usd'] is None else data['actual_usd']
            entry['status'] = 'unknown_usage' if data['actual_usd'] is None else 'settled'
        elif kind == 'cancel_reserved':
            entry = entries[data['key']]
            require(entry['status'] == 'reserved', 'Dispatched reservation was cancelled as unsent')
            entry.update(accounted_usd='0', status='cancelled_unsent')
        elif kind == 'cost_stop':
            allocation, index = data['allocation'], admitted[data['allocation']]
            require(allocation in schedules and index < len(schedules[allocation]), 'Cost stop does not name the next group')
            group = schedules[allocation][index]
            require(data['index'] == index and data['group'] == group['group'], 'Cost stop skipped the next group')
            if index:
                require(all(entries[r['key']]['status'] in ('settled', 'unknown_usage')
                            for r in schedules[allocation][index-1]['requests']),
                        'Cost stopping decision preceded previous whole-group settlement')
            reasons = cap_reasons(allocation, group['requests'])
            require(reasons and data['reason'] == ', '.join(reasons), 'Saved cost stop was affordable or had incorrect cap reasons')
            require(data['unrun_groups'] == len(schedules[allocation]) - index, 'Saved unrun-group denominator changed')
            cost_stops[allocation] = data
        else:
            raise VerificationError('Unknown primary accounting event')
    return entries, dict(admitted), cost_stops


def _unrun_scopes(directory, supplied):
    path = directory / 'terminal-unrun.json'
    receipt = load(path) if supplied is None and path.exists() else supplied
    if receipt is None:
        return []
    stop = directory / 'STOP.json'
    require(receipt.get('version') == plan.VERSION and isinstance(receipt.get('reason'), str) and receipt['reason'],
            'Terminal unrun receipt lacks a version/reason')
    require(stop.exists() and receipt.get('stop_sha256') == sha256(stop.read_bytes()),
            'Terminal unrun receipt must bind the exact immutable systemic stop')
    scopes = receipt.get('scope')
    require(isinstance(scopes, list) and scopes, 'Terminal unrun receipt needs explicit allocation/config scopes')
    for scope in scopes:
        require(set(scope) <= {'allocation', 'config'} and scope.get('allocation') in
                ('development', 'main', 'supporting', 'comparators'), 'Invalid terminal-unrun scope')
        require(scope.get('config') in (None, *plan.CONFIGS), 'Unknown terminal-unrun configuration')
    return scopes


def _covered(scopes, allocation, config=None):
    return any(s['allocation'] == allocation and (s.get('config') is None or s['config'] == config) for s in scopes)


def _token_diagnostics(requests, parsed, eligible_cells):
    """Aggregate actual native input-count differences without exposing any text."""
    cells = defaultdict(dict)
    eligible = {(c['split'], c['id'], c['config'], c['condition']) for c in eligible_cells}
    for request in requests.values():
        if request['key'] not in parsed:
            continue
        usage = parsed[request['key']].get('usage') or {}
        n = usage.get('input_tokens')
        if type(n) is not int or n < 1:
            continue
        payload = request['payload']
        state = payload.get('state', payload.get('input'))
        if isinstance(state, list):
            state = state[0]['content']
        try:
            evidence = json.loads(state)
        except (TypeError, ValueError):
            continue
        task = evidence.get('TRUSTED_USER_TASK')
        for ref in request['refs']:
            if (request['split'], ref['id'], request['config'], ref['condition']) not in eligible:
                continue
            cells[(request['split'], request['config'], ref['source'], ref['id'])][ref['condition']] = (n, len(task) if isinstance(task, str) else None)
    grouped = defaultdict(list)
    for (split, config, source, _), conditions in cells.items():
        for control in ('format', 'reminder', 'length'):
            if 'task' in conditions and control in conditions:
                task, other = conditions['task'], conditions[control]
                grouped[(split, config, source, control)].append((task[0]-other[0], task[1], other[1]))
    result = []
    for (split, config, source, control), values in sorted(grouped.items()):
        result.append({'split': split, 'config': config, 'source': source, 'control': control,
            'paired_rows': len(values), 'mean_task_minus_control_input_tokens': sum(v[0] for v in values)/len(values),
            'min_task_minus_control_input_tokens': min(v[0] for v in values),
            'max_task_minus_control_input_tokens': max(v[0] for v in values),
            'equal_task_control_character_rows': sum(a is not None and a == b for _, a, b in values),
            'character_interpretation': 'Exact trusted-task-field character counts; filler is character-matched, not token-matched.'})
    return result


def verify_bundle(frozen_by_split, ledger_path, directory, terminal_receipts=None):
    """Read-only audit returning aggregate receipt, normalized records, raw detail.

    Incomplete (but intact) execution returns ready=False. Corrupt evidence raises
    VerificationError; it must never become a missing observation or be repaired.
    Caller must first validate actual freezes with freeze.verify; fixtures pass
    synthetic frozen plans directly and never acquire credentials or model access.
    """
    directory = Path(directory)
    require(set(frozen_by_split) <= {'development', 'confirmation'} and frozen_by_split,
            'Unknown or missing frozen splits')
    requests, cells = {}, []
    for split, frozen in frozen_by_split.items():
        require(frozen.get('split', split) == split, 'Frozen split changed')
        for request in frozen['requests']:
            require(request['split'] == split and request.get('inference_eligible') is True,
                    'Frozen request is ineligible or in a different split')
            require(request['key'] not in requests, 'Request cache crossed split boundaries')
            require(request['request_sha256'] == sha256(canonical_bytes(request['payload'])), 'Frozen payload bytes changed')
            expected_provider = plan.PROVIDERS.get(request['config'])
            require(request['provider'] == expected_provider, 'Frozen paid route/provider changed')
            expected_hold = reserve(request['payload'], expected_provider) if expected_provider else '0'
            require(_decimal_equal(request['reserved_usd'], expected_hold), 'Frozen reservation differs from exact frozen price rule')
            requests[request['key']] = request
        cells.extend(frozen['cells'])
    identities = [(c['split'], c['id'], c['config'], c['condition']) for c in cells]
    require(len(set(identities)) == len(cells), 'Duplicate frozen planned cell')
    for cell in cells:
        if cell['inference_eligible']:
            require(cell['coverage_supported'] and cell['request_key'] in requests, 'Eligible cell lacks full-input request')
            request = requests[cell['request_key']]
            require(request['split'] == cell['split'] and request['config'] == cell['config'] and
                    request['request_sha256'] == cell['payload_sha256'], 'Frozen cell payload/cache binding changed')
            require(any(ref['id'] == cell['id'] and ref['condition'] == cell['condition'] and
                        ref['source'] == cell['source'] and ref['group'] == cell['group'] for ref in request['refs']),
                    'Deduplicated request lost a frozen cell reference')
    ledger = BudgetLedger(ledger_path).snapshot()
    require(set(ledger['entries']) <= set(requests), 'Unplanned/recovery attempt exists in primary accounting')
    confirmation = frozen_by_split.get('confirmation', {'schedules': {}})
    expected_schedules = _expected_schedules(confirmation, requests)
    replayed, admitted, cost_stops = _audit_cost_order(ledger_path, requests, expected_schedules)
    require(set(replayed) == set(ledger['entries']), 'Independent journal replay has different attempts')
    for key, entry in replayed.items():
        actual = ledger['entries'][key]
        require(entry['status'] == actual['status'] and _decimal_equal(entry['accounted_usd'], actual['accounted_usd']),
                'Independent replay differs from journal accounting')
    stop = directory / 'STOP.json'
    stop_hash = sha256(stop.read_bytes()) if stop.exists() else None
    scopes = _unrun_scopes(directory, terminal_receipts)
    attempt_root = directory / 'attempts'
    if attempt_root.exists():
        require(all(p.is_dir() and p.name in requests and p.name in ledger['entries'] for p in attempt_root.iterdir()),
                'Unplanned raw attempt exists outside reserved frozen requests')
    incomplete, parsed, records = [], {}, {}
    for key, entry in ledger['entries'].items():
        request = requests[key]
        require(all(entry.get(k) == v for k, v in _spec(request).items() if k != 'reserved_usd') and
                _decimal_equal(entry['reserved_usd'], request['reserved_usd']), 'Journal request binding differs from freeze')
        if entry['status'] in ('reserved', 'dispatched'):
            incomplete.append('nonterminal_attempt')
            continue
        parsed[key], record = _audit_attempt(request, entry, directory, stop_hash)
        if record is not None:
            records[key] = record
    dispatch_order = [e['data']['key'] for e in (json.loads(line) for line in Path(ledger_path).read_text().splitlines())
                      if e['kind'] == 'dispatch' and not records.get(e['data']['key'], {}).get('result', {}).get('reserved_raw_conflict_retained')]
    for i, key in enumerate(dispatch_order):
        if key in records and (records[key]['result']['stop_required'] or
                               records[key]['costs'].get('unexpected_pricing_tier')):
            require(i == len(dispatch_order)-1, 'Another native first attempt was dispatched after a systemic failure')
    # Every scheduled allocation/config must finish, cost-stop, or have an exact
    # STOP-linked unrun receipt. Absence of an attempted route is never completion.
    for allocation in ('main', 'supporting'):
        if 'confirmation' not in frozen_by_split:
            incomplete.append('confirmation_freeze_missing')
            continue
        schedule = ledger['schedules'].get(allocation)
        if schedule is None:
            if not _covered(scopes, allocation):
                incomplete.append(allocation + '_schedule_not_registered')
        elif schedule['admitted'] < len(schedule['groups']) and allocation not in cost_stops and not _covered(scopes, allocation):
            incomplete.append(allocation + '_schedule_not_terminal')
    for config in plan.COMPARATORS + ('protectai_local',):
        selected = [r for r in requests.values() if r['split'] == 'confirmation' and r['config'] == config]
        if any(r['key'] not in parsed for r in selected) and not _covered(scopes, 'comparators', config):
            incomplete.append(config + '_comparator_not_terminal')
    dev = [r for r in requests.values() if r['split'] == 'development']
    if any(r['key'] not in parsed for r in dev) and not _covered(scopes, 'development'):
        incomplete.append('development_not_terminal')
    normalized, dispositions = [], []
    for cell in cells:
        key = cell['request_key']
        if not cell['inference_eligible']:
            outcome, reason = _failure('unsupported'), 'frozen_full_input_or_whole_group_exclusion'
        elif key in parsed:
            outcome, reason = parsed[key], 'retained_first_attempt' if key in records else 'positive_unsent_cancellation'
        else:
            outcome = _failure('not_attempted')
            allocation = cell['allocation']
            reason = 'budget_cost_stop' if allocation in cost_stops else 'explicit_systemic_stop_unrun' if _covered(scopes, allocation, cell['config']) else 'incomplete_execution'
            if reason == 'incomplete_execution':
                incomplete.append('unexplained_unattempted_cell')
        detail = {k: cell[k] for k in ('split', 'id', 'source', 'group', 'config', 'condition', 'request_key')}
        dispositions.append(dict(detail, status=outcome['status'], reason=reason))
        if cell['split'] == 'confirmation' and cell['inference_eligible']:
            normalized.append({k: cell[k] for k in ('id', 'config', 'condition')} | {
                'request_key': key, 'attempt': 0,
                **{k: outcome[k] for k in ('status', 'valid', 'prediction', 'score') if k in outcome}})
    by_source = []
    for source in sorted({c['source'] for c in cells if c['split'] == 'confirmation'}):
        part = [c for c in cells if c['split'] == 'confirmation' and c['source'] == source]
        by_source.append({'source': source, 'planned_rows': len({c['id'] for c in part}),
            'planned_groups': len({c['group'] for c in part}),
            'class_rows': dict(Counter(str(v) for v in {c['id']: c['gold'] for c in part}.values())),
            'planned_cells': len(part), 'eligible_cells': sum(c['inference_eligible'] for c in part),
            'dispositions': dict(Counter(d['status'] for d in dispositions if d['split'] == 'confirmation' and d['source'] == source))})
    spending = {}
    for provider in ('openai', 'typesafe'):
        entries = [e for e in ledger['entries'].values() if e['provider'] == provider]
        spending[provider] = {'inherited_accounted_usd': ledger['policy']['prior_accounted_usd'][provider],
            'incremental_conservative_accounted_usd': ledger['incremental_accounted_usd'][provider],
            'cumulative_conservative_accounted_usd': ledger['all_in_accounted_usd'][provider],
            'settled_usage_estimate_usd': str(sum((money(e['actual_usd']) for e in entries if e['status'] == 'settled'), Decimal(0))),
            'unknown_usage_holds_usd': str(sum((money(e['reserved_usd']) for e in entries if e['status'] == 'unknown_usage'), Decimal(0))),
            'pending_holds_usd': str(sum((money(e['reserved_usd']) for e in entries if e['status'] in ('reserved', 'dispatched')), Decimal(0))),
            'initial_reservations_usd': str(sum((money(e['reserved_usd']) for e in entries), Decimal(0))),
            'cancelled_unsent_requests': sum(e['status'] == 'cancelled_unsent' for e in entries),
            'global_cap_usd': ledger['policy']['provider_caps_usd'][provider],
            'v6_cap_usd': ledger['policy']['v6_caps_usd'][provider], 'actual_billed_usd': None,
            'meaning': 'Usage-derived estimates and retained reservations; not provider invoice or balance.'}
    main_target = confirmation.get('schedules', {}).get('main', [])
    summary = {'version': 'v6-independent-execution-verification-1',
        'ready': not incomplete and ledger['terminal'], 'integrity_checks_passed': True,
        'incomplete_reasons': dict(Counter(incomplete)), 'journal_terminal': ledger['terminal'],
        'journal_sha256': sha256(Path(ledger_path).read_bytes()), 'journal_bytes': Path(ledger_path).stat().st_size,
        'first_attempt_unique_reserved_requests': len(ledger['entries']),
        'first_attempt_raw_execution_records_reparsed': len(records),
        'accounting_only_reserved_raw_conflicts_retained': sum(r['result'].get('reserved_raw_conflict_retained') is True for r in records.values()),
        'confirmation_normalized_eligible_cells': len(normalized), 'source_denominators': by_source,
        'main_target_reviewed_groups': len(main_target),
        'main_target_runnable_groups': len(expected_schedules['main']),
        'main_preflight_unsupported_groups': len(main_target)-len(expected_schedules['main']),
        'main_admitted_common_prefix_groups': admitted.get('main', 0),
        'main_unrun_runnable_groups': len(expected_schedules['main'])-admitted.get('main', 0),
        'supporting_admitted_groups': admitted.get('supporting', 0),
        'cost_stop_allocations': sorted(cost_stops), 'terminal_unrun_scope_count': len(scopes),
        'spending': spending, 'token_contrast_diagnostics': _token_diagnostics(requests, parsed,
            [c for c in cells if c['inference_eligible']]),
        'configuration_dispositions': [{'split': split, 'config': config,
            'planned_cells': len(part), 'eligible_cells': sum(c['inference_eligible'] for c in part),
            'dispositions': dict(Counter(d['status'] for d in dispositions if d['split'] == split and d['config'] == config))}
            for (split, config), part in sorted(_parts(cells).items())],
        'new_model_calls': 0, 'new_inference_spend_usd': 0,
        'requires_scientific_analysis_before_paper': True,
        'limitations': ['Agent-reviewed source agreement is not human gold.',
            'Execution readiness does not establish statistical power, population FPR, agent resistance or novelty.',
            'Closed-model token counts and monetary estimates are provider-reported measurements, not invoice verification.']}
    details = {'planned_cell_dispositions': dispositions,
        'cost_stops': cost_stops, 'journal_head_sha256': ledger['head_sha256'],
        'unrun_request_keys': sorted(set(requests)-set(parsed)),
        'normalized_records_sha256': sha256(b''.join(canonical_bytes(r)+b'\n' for r in normalized))}
    return summary, normalized, details


def _parts(cells):
    parts = defaultdict(list)
    for cell in cells:
        parts[(cell['split'], cell['config'])].append(cell)
    return parts


def verify(*, write=False):
    """Production entry point: validate actual committed freezes before raw audit."""
    from scripts.study_v6.freeze import verify as verify_freeze
    frozen = {}
    receipts = {}
    for split in ('development', 'confirmation'):
        path = plan.RESULTS / (split + '-freeze-v1.json')
        if path.exists():
            receipts[split], frozen[split] = verify_freeze(split)
    require(frozen, 'No actual frozen execution exists')
    summary, normalized, details = verify_bundle(frozen, plan.DEST / 'budget.jsonl', plan.DEST)
    summary['freeze_sha256'] = {split: sha256((plan.RESULTS / (split+'-freeze-v1.json')).read_bytes()) for split in frozen}
    if write:
        require(summary['ready'], 'Do not write final normalized evidence from incomplete execution')
        immutable(plan.DEST / 'normalized-records.jsonl', b''.join(canonical_bytes(r)+b'\n' for r in normalized))
        immutable(plan.DEST / 'raw-execution-verification.json', details)
        immutable(plan.RESULTS / 'execution-verification-v1.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true', help='Write immutable receipts only after all execution gates pass')
    args = parser.parse_args()
    print(json.dumps(verify(write=args.write), sort_keys=True))
