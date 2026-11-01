"""V7 policy around the existing hash-chained, locked accounting infrastructure.

The v6 ledger and all old prices remain unchanged. This subclass reuses its durable
journal, dispatch/settlement state machine, Decimal money and unknown-charge holds.
Only v7 policy and arbitrary source/model group schedules are added here.
"""
from __future__ import annotations
import copy
import json
import fcntl
from decimal import Decimal
from pathlib import Path
from scripts.study_v6.accounting import (BudgetLedger as HistoricalLedger, AccountingError,
    BudgetExceeded, AlreadyDispatched, PROVIDERS, money, amount, _requests)
from scripts.study_v7.requests import PANEL, canonical, digest
from scripts.study_v7.ledger_cache import V7LedgerCacheMixin

CURRENT_CAPS = {'openai': '15', 'typesafe': '20'}
HISTORICAL = {'openai': '7.02755920', 'typesafe': '1.827584934'}
RATES = {'jev_input': '0.042', 'luna_input': '0.10', 'luna_output': '0.50',
    'luna_decisions_max_cache_write': '0.25', 'sol_input': '2', 'sol_output': '10'}


def maximum_cost(config, input_tokens=None):
    """Exact Decimal ceiling at a declared input ceiling, with max output/cache.

    Without a native count, use the route's entire accepted context capacity. A
    local byte/token proxy is never declared a Jev tokenizer upper bound. Requests
    above the short-input tier reserve 2x input/cache and 1.5x Responses output.
    """
    p = PANEL[config]
    if p['provider'] is None:
        return '0'
    n = p['context_tokens'] - p.get('output_cap', 0) if input_tokens is None else input_tokens
    if type(n) is not int or n < 1 or n + p.get('output_cap', 0) > p['context_tokens']:
        raise ValueError('Invalid accepted input ceiling')
    if config == 'jev_firstparty':
        return amount(Decimal(n) * Decimal(RATES['jev_input']) / Decimal(1000000))
    multiplier = Decimal(2 if n > 272000 else 1)
    if config == 'luna_decisions':
        return amount(Decimal(n) * Decimal('.25') * multiplier / Decimal(1000000))
    prefix = 'sol' if config == 'sol_responses' else 'luna'
    output_multiplier = Decimal('1.5') if n > 272000 else Decimal(1)
    return amount((Decimal(n) * Decimal(RATES[prefix + '_input']) * multiplier +
        Decimal(p['output_cap']) * Decimal(RATES[prefix + '_output']) * output_multiplier) / Decimal(1000000))


def usage_cost(config, usage):
    p = PANEL[config]
    if p['provider'] is None:
        return '0'
    n = usage.get('input_tokens') if isinstance(usage, dict) else None
    if type(n) is not int or not 0 < n <= p['context_tokens']:
        return None
    if config in ('jev_firstparty', 'luna_decisions'):
        from scripts.study_v6.pricing import usage_cost as native_cost
        return native_cost(p['provider'], usage).get('accounted_usd')
    output = usage.get('output_tokens')
    if type(output) is not int or not 0 <= output <= p['output_cap'] or n + output > p['context_tokens']:
        return None
    details = usage.get('input_tokens_details')
    if not isinstance(details, dict):
        return None
    # Explicit-only/no breakpoints promises no cache. Unexpected usage stops the
    # route and retains the complete reservation rather than silently repricing.
    if any(type(details.get(k, 0)) is not int or details.get(k, 0) != 0
           for k in ('cached_tokens', 'cache_write_tokens')):
        return None
    prefix = 'sol' if config == 'sol_responses' else 'luna'
    input_rate = Decimal(RATES[prefix + '_input']) * (2 if n > 272000 else 1)
    output_rate = Decimal(RATES[prefix + '_output']) * (Decimal('1.5') if n > 272000 else 1)
    return amount((Decimal(n) * input_rate + Decimal(output) * output_rate) / Decimal(1000000))


def reservation(request, *, input_ceiling=None):
    return {'key': request['key'], 'provider': PANEL[request['config']]['provider'],
        'reserved_usd': maximum_cost(request['config'], input_ceiling),
        'request_sha256': request['payload_sha256'], 'config': request['config'], 'split': request['split']}


def policy(prior, caps, incremental_caps, allocations, evidence_sha256=None):
    if set(prior) != set(PROVIDERS) or set(caps) != set(PROVIDERS) or set(incremental_caps) != set(PROVIDERS):
        raise AccountingError('Both providers required')
    prior, caps, incremental = ({p: amount(mapping[p]) for p in PROVIDERS}
                                for mapping in (prior, caps, incremental_caps))
    allocations = {a: {p: amount(v[p]) for p in PROVIDERS} for a, v in allocations.items()}
    if not allocations:
        raise AccountingError('At least one frozen allocation required')
    for p in PROVIDERS:
        if money(prior[p]) > money(caps[p]) or money(incremental[p]) + money(prior[p]) > money(caps[p]):
            raise AccountingError('Incremental authorization exceeds cumulative cap')
        if sum((money(v[p]) for v in allocations.values()), Decimal(0)) > money(incremental[p]):
            raise AccountingError('Allocation caps exceed incremental authorization')
    return {'version': 'study-v7-budget-1', 'prior_accounted_usd': prior, 'provider_caps_usd': caps,
        'v6_caps_usd': incremental, # Existing journal internal field; v6 is never opened or changed.
        'incremental_caps_usd': incremental, 'allocations_usd': allocations,
        'historical_evidence_sha256': evidence_sha256 or {}}


def _validate_subscription_supersession(state, receipt, new_schedules, receipt_sha256):
    allowed = {'development_sol_main', 'development_sol_external'}
    if (receipt.get('version') != 'study-v7.0.2-sol-subscription-amendment' or
            receipt.get('configuration_revision') != 'v7.0.2' or
            not set(new_schedules) or not set(new_schedules) <= allowed):
        raise AccountingError('Only the explicit v7.0.2 Sol development amendment is supported')
    for name in ('previous_plan_sha256', 'new_plan_sha256', 'payload_revision_sha256', 'failure_metadata_sha256'):
        value = receipt.get(name)
        if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
            raise AccountingError('Amendment must bind exact plans, payload revision and failure metadata')
    if receipt['previous_plan_sha256'] == receipt['new_plan_sha256']:
        raise AccountingError('Payload revision requires a separately preserved new plan')
    if any(e.get('split') != 'development' or e['status'] == 'dispatched' for e in state['entries'].values()):
        raise AccountingError('Supersession requires development only and no in-flight attempts')
    if not set(state['schedules']) <= {'development_main', 'development_external', *allowed}:
        raise AccountingError('Confirmation schedules must remain unregistered before supersession')
    old_keys, new_keys = set(), set()
    for allocation, groups in new_schedules.items():
        old = state['schedules'].get(allocation)
        if old is None or any(money(v) != 0 for v in state['policy']['allocations_usd'][allocation].values()):
            raise AccountingError('Affected allocation must already be a zero-cost Sol development schedule')
        if old.get('configuration_revision') == 'v7.0.2':
            raise AccountingError('Sol subscription amendment cannot be applied repeatedly')
        if ([g['group'] for g in old['groups']] != [g['group'] for g in groups] or
                [len(g['requests']) for g in old['groups']] != [len(g['requests']) for g in groups]):
            raise AccountingError('Amendment cannot change source group order or request counts')
        if (receipt.get('previous_schedules_sha256', {}).get(allocation) != digest(canonical(old['groups'])) or
                receipt.get('new_schedules_sha256', {}).get(allocation) != digest(canonical(groups))):
            raise AccountingError('Amendment schedule hashes differ')
        for schedule, keys in ((old['groups'], old_keys), (groups, new_keys)):
            for group in schedule:
                for spec in group['requests']:
                    if (spec.get('provider') is not None or money(spec['reserved_usd']) != 0 or
                            spec.get('config') != 'sol_subscription' or spec.get('split') != 'development'):
                        raise AccountingError('Only zero-cost native subscription development specifications may change')
                    if spec['key'] in keys:
                        raise AccountingError('Duplicate revised subscription attempt')
                    keys.add(spec['key'])
        for key in (r['key'] for g in old['groups'] for r in g['requests']):
            entry = state['entries'].get(key)
            if entry and entry['status'] == 'cancelled_unsent' and entry.get('evidence_sha256') != receipt_sha256:
                raise AccountingError('Existing unsent cancellation does not bind this amendment')
    if old_keys & new_keys or any(key in state['entries'] for key in new_keys):
        raise AccountingError('Revised subscription requests require fresh distinct keys')
    return old_keys


class BudgetLedger(V7LedgerCacheMixin, HistoricalLedger):
    def __init__(self, path, frozen_policy=None, *, guard=None, history_root=None):
        self.path = Path(path); self.lock_path = self.path.with_name(self.path.name + '.lock')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.history_root, self.guard, self._cache = history_root, guard, None
        with self._locked() as state:
            if state is None:
                if frozen_policy is None:
                    raise AccountingError('No initialized v7 budget')
                self._append(None, 'initialize', {'policy': frozen_policy})
            elif frozen_policy is not None and state['policy'] != frozen_policy:
                raise AccountingError('V7 budget policy is immutable')

    @staticmethod
    def _apply(state, kind, data):
        if state is None:
            if kind != 'initialize':
                raise AccountingError('Missing initialization')
            p = data['policy']
            checked = policy(p['prior_accounted_usd'], p['provider_caps_usd'],
                p['incremental_caps_usd'], p['allocations_usd'], p['historical_evidence_sha256'])
            if p != checked:
                raise AccountingError('Invalid frozen v7 policy')
            return {'policy': checked, 'entries': {}, 'batches': {}, 'schedules': {},
                    'continuations': {}, 'development_amendments': {}}
        if kind == 'supersede_subscription_development':
            receipt, groups, sha = data['receipt'], data['new_schedules'], data['receipt_sha256']
            _validate_subscription_supersession(state, receipt, groups, sha)
            archives = state.setdefault('subscription_schedule_supersessions', {})
            if sha in archives or data['previous_schedules'] != {a: state['schedules'][a] for a in groups}:
                raise AccountingError('Supersession archive changed or event repeated')
            archives[sha] = copy.deepcopy(data)
            for allocation, new_groups in groups.items():
                state['schedules'][allocation] = {'groups': new_groups, 'admitted': 0, 'stopped': None,
                    'configuration_revision': 'v7.0.2', 'supersession_receipt_sha256': sha}
            return state
        return HistoricalLedger._apply(state, kind, data)

    def _check_guard(self, state):
        if self.history_root is not None:
            for name, sha in state['policy']['historical_evidence_sha256'].items():
                self.verify_historical_file(Path(self.history_root) / name, sha)
        if self.guard is not None:
            self.guard()

    def supersede_subscription_development(self, receipt_path, new_schedules):
        """Explicit offline amendment only; never inferred from changed requests.

        Preserve all completed/unknown entries and old schedules. Only positively
        never-dispatched zero-cost old reservations are cancelled, with the exact
        amendment-file hash as evidence. Confirmation and provider policies cannot
        change. No executor may hold the process lock during this operation.
        """
        receipt_bytes = Path(receipt_path).read_bytes()
        receipt, sha = json.loads(receipt_bytes), digest(receipt_bytes)
        groups = {a: [{'group': g['group'], 'requests': _requests(g['requests'])} for g in values]
                  for a, values in new_schedules.items()}
        with (self.path.parent / 'executor.lock').open('a+b') as executor_lock:
            try:
                fcntl.flock(executor_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise AccountingError('Executor must finish before the explicit subscription amendment') from None
            with self._locked() as state:
                self._check_guard(state)
                previous = state.get('subscription_schedule_supersessions', {}).get(sha)
                if previous is not None:
                    if previous['receipt'] != receipt or previous['new_schedules'] != groups:
                        raise AccountingError('Retained supersession receipt changed')
                    return copy.deepcopy(previous)
                old_keys = _validate_subscription_supersession(state, receipt, groups, sha)
                for key in sorted(old_keys):
                    if state['entries'].get(key, {}).get('status') == 'reserved':
                        state = self._append(state, 'cancel_reserved', {'key': key, 'evidence_sha256': sha,
                            'reason': 'explicit_zero_cost_subscription_development_revision_never_dispatched'})
                data = {'receipt': receipt, 'receipt_sha256': sha, 'new_schedules': groups,
                    'previous_schedules': {a: copy.deepcopy(state['schedules'][a]) for a in groups}}
                self._append(state, 'supersede_subscription_development', data)
                return copy.deepcopy(data)

    def entry(self, key):
        """Read one immutable copy, without copying every frozen schedule/entry."""
        with self._locked() as state:
            value = state['entries'].get(key)
            return None if value is None else copy.deepcopy(value)

    def progress(self, allocation):
        """Read one allocation's position and last admitted whole group only."""
        with self._locked() as state:
            schedule = state['schedules'][allocation]
            index = schedule['admitted']
            previous = schedule['groups'][index-1] if index else None
            unfinished = [r['key'] for r in previous['requests']
                if state['entries'][r['key']]['status'] in ('reserved', 'dispatched')] if previous else []
            return {'admitted': index, 'total_groups': len(schedule['groups']),
                'unfinished_request_keys': unfinished,
                'stopped': copy.deepcopy(schedule['stopped']),
                'previous_group': copy.deepcopy(schedule['groups'][index-1]) if index else None}

    def register_schedule(self, allocation, groups):
        groups = [{'group': g['group'], 'requests': _requests(g['requests'])} for g in groups]
        if len({g['group'] for g in groups}) != len(groups):
            raise AccountingError('Duplicate scheduled source/model group')
        with self._locked() as state:
            self._check_guard(state)
            if allocation not in state['policy']['allocations_usd']:
                raise AccountingError('Unbudgeted allocation')
            if allocation in state['schedules']:
                if state['schedules'][allocation]['groups'] != groups:
                    raise AccountingError('Frozen schedule changed')
                return copy.deepcopy(state['schedules'][allocation])
            return copy.deepcopy(self._append(state, 'register_schedule',
                {'allocation': allocation, 'groups': groups})['schedules'][allocation])

    def reserve_next_group(self, allocation, *, admission_open=True):
        self.verify_full_journal()
        with self._locked() as state:
            self._check_guard(state)
            schedule = state['schedules'][allocation]
            if schedule['stopped'] is not None:
                return {'status': 'stopped', **copy.deepcopy(schedule['stopped'])}
            index = schedule['admitted']
            if index and any(state['entries'][r['key']]['status'] in ('reserved', 'dispatched')
                    for r in schedule['groups'][index-1]['requests']):
                raise AccountingError('Finish the admitted whole group before another admission')
            if index == len(schedule['groups']):
                return {'status': 'complete', 'admitted_groups': index}
            group = schedule['groups'][index]
            try:
                if not admission_open:
                    raise BudgetExceeded('predeclared_time_cutoff')
                batch_id = allocation + ':group:' + group['group']
                if schedule.get('configuration_revision'):
                    batch_id += ':revision:' + schedule['configuration_revision']
                batch = self._reserve(state, batch_id, allocation,
                                      group['requests'], group['group'])
            except BudgetExceeded as error:
                stop = {'allocation': allocation, 'group': group['group'], 'index': index,
                    'reason': str(error), 'unrun_groups': len(schedule['groups'])-index}
                self._append(state, 'cost_stop', stop)
                return {'status': 'stopped', **stop}
            return {'status': 'admitted', 'index': index, **batch}
