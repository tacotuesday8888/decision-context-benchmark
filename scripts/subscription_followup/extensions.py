"""Separately frozen source/pilot executor. No inference on import or preparation."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import copy
import fcntl
import json
from pathlib import Path
import time

from scripts.study_v7.requests import canonical, digest
from scripts.subscription_followup import budget, pilot
from scripts.subscription_followup.run import ROOT, FileGuard, Executor
from scripts.subscription_followup.continue_core import ContinuationExecutor
from scripts.subscription_followup.transport import invoke, validate_payload, write_once

VERSION = 'subscription-followup-extensions-executor-1'
GLOBAL_ANCHOR = '2026-11-01T14:57:56.429131+00:00'
GLOBAL_DEADLINE = '2026-11-01T19:57:56.429131+00:00'
CORE_MANIFESTS = ('b300dee09c2b116b203523cf8d8922ba55665491d3ac127a8fefe8607c5e8fcb',
                  'ec8413a74dd54dd9cda6f8260b9b7a480fec6af38558a9fc89005c9895d94a2d')


def _need(value, message):
    if not value:
        raise PermissionError(message)


def verify_closed_core(lineage):
    """Hash/replay both exact terminal ancestors; never trust a 'closed' label."""
    from scripts.subscription_followup.continuation_budget import ContinuationLedger
    _need(lineage.get('status') == 'closed' and len(lineage.get('runs', [])) == 2,
          'Both exact closed core ancestors are required')
    seen, original_cells = set(), None
    for index, run in enumerate(lineage['runs']):
        manifest_path = Path(run['manifest_path'])
        _need(run['manifest_sha256'] == CORE_MANIFESTS[index] and
              digest(manifest_path.read_bytes()) == run['manifest_sha256'], 'Core manifest identity/hash differs')
        mf = json.loads(manifest_path.read_text())
        plan_path = ROOT / mf['plan']['path']
        _need(digest(plan_path.read_bytes()) == mf['plan']['sha256'] == run['plan_sha256'], 'Core plan differs')
        plan = json.loads(plan_path.read_text())
        if index == 0:
            original_cells = {c['cell_id']: c for g in plan['groups'] for c in g['cells']}
            _need(len(original_cells) == 4510, 'Original core scope differs')
        folder = ROOT / mf['execution_directory']
        stop_path, snapshot_path, journal_path = [folder / name for name in
            ('STOP.json', 'final-ledger-snapshot.json', 'accounting.jsonl')]
        for path, name in ((stop_path, 'stop_sha256'), (snapshot_path, 'snapshot_sha256'),
                           (journal_path, 'journal_sha256')):
            _need(digest(path.read_bytes()) == run[name], 'Closed core lineage file differs: ' + name)
        stop, snapshot = json.loads(stop_path.read_text()), json.loads(snapshot_path.read_text())
        _need(stop.get('status') == 'closed' and stop.get('manifest_sha256') == run['manifest_sha256'] and
              stop.get('journal_sha256') == run['journal_sha256'], 'Core STOP does not bind its terminal journal')
        state, previous = None, '0' * 64
        ledger_class = budget.FollowupLedger if index == 0 else ContinuationLedger
        body = journal_path.read_bytes()
        _need(body.endswith(b'\n'), 'Torn core journal')
        for i, line in enumerate(body.splitlines()):
            event = json.loads(line)
            sha = event.pop('sha256', None)
            _need(event['index'] == i and event['previous_sha256'] == previous and
                  digest(canonical(event)) == sha, 'Core journal chain changed')
            state = ledger_class._apply(state, event['kind'], event['data'])
            state['head_sha256'], state['events'] = sha, i + 1
            previous = sha
        _need(state is not None and snapshot.get('terminal') is True and
              snapshot['entries'] == state['entries'] and snapshot['policy'] == state['policy'] and
              snapshot['head_sha256'] == state['head_sha256'] and
              snapshot['window_started_at_utc'] == state['window_started_at_utc'] == GLOBAL_ANCHOR,
              'Core snapshot/clock differs from validated journal')
        _need(snapshot['all_in_accounted_usd'] == budget.PRIOR and
              all(value == '0' for value in snapshot['incremental_accounted_usd'].values()),
              'Core money changed; reconcile rather than reset baseline')
        for entry in state['entries'].values():
            _need(entry['status'] in ('settled', 'unknown_usage', 'cancelled_unsent'), 'Unresolved core intent')
            if entry['status'] == 'cancelled_unsent':
                continue
            cid = entry['cell_id']
            _need(cid in original_cells and cid not in seen and
                  entry['request_sha256'] == original_cells[cid]['payload_sha256'] and
                  entry['config'] == 'sol_subscription' and entry['provider'] is None,
                  'Repeated/unplanned core first outcome or changed billing route')
            completed = folder / 'attempts' / entry['key'] / 'completed.json'
            _need(digest(completed.read_bytes()) == entry['evidence_sha256'], 'Core terminal evidence differs')
            seen.add(cid)
    _need(seen == set(original_cells), 'Core collection is closed but not fully attempted; reconcile before extensions')
    return {'actual_cells': len(seen), 'anchor': GLOBAL_ANCHOR, 'deadline': GLOBAL_DEADLINE}


def freeze_policy(manifest_path):
    """Preserve monetary baseline and bind a finite roster, including variants."""
    m = json.loads(Path(manifest_path).read_text())
    p = budget.freeze_policy(manifest_path,
        prior_receipt_path=m['closed_evidence']['receipt']['path'],
        prior_journal_path=m['closed_evidence']['journal']['path'])
    _need(not m['lanes']['sol_general']['enabled'] and not m['lanes']['blind_audit']['enabled'],
          'No core cells or additional preflight in extensions')
    plan_path = ROOT / m['plan']['path']
    _need(digest(plan_path.read_bytes()) == m['plan']['sha256'], 'Extension plan changed')
    plan = json.loads(plan_path.read_text())
    allowed = {}
    for g in plan['groups']:
        for c in g['cells']:
            _need(c['cell_id'] not in allowed, 'Duplicate extension scientific cell')
            choices = {c['payload_sha256']}
            for variant in c.get('payload_variants', {}).values():
                _need(digest(canonical(variant['payload'])) == variant['payload_sha256'], 'Variant bytes changed')
                validate_payload(c['config'], variant['payload'])
                choices.add(variant['payload_sha256'])
            stage = c.get('stage', g['stage'])
            allowed[c['cell_id']] = {'lane': g['lane'], 'stage': stage, 'group_id': g['group_id'],
                'config': c['config'], 'payload_choices': sorted(choices)}
    counts = Counter(c['config'] for g in plan['groups'] for c in g['cells'])
    _need(counts == {'sol_subscription': 576, 'jev_firstparty': 552}, 'Exact reviewed extension scope differs')
    _need(len(allowed) == 1128 and len(plan['groups']) == 78, 'Exact source/pilot roster differs')
    p['extension_roster'] = allowed
    p['extension_roster_sha256'] = digest(canonical(allowed))
    p['global_clock_anchor_utc'] = m['global_clock_anchor_utc']
    p['global_deadline_utc'] = m['global_deadline_utc']
    _need(p['global_clock_anchor_utc'] == GLOBAL_ANCHOR and p['global_deadline_utc'] == GLOBAL_DEADLINE,
          'Extension cannot reset or extend original clock')
    lineage = json.loads((ROOT / m['core_collection_lineage']['path']).read_text())
    _need(digest((ROOT / m['core_collection_lineage']['path']).read_bytes()) == m['core_collection_lineage']['sha256'],
          'Closed core lineage changed')
    verify_closed_core(lineage)
    return p


class ExtensionLedger(budget.FollowupLedger):
    """Same durable money rules plus exact variant roster and original clock."""
    @staticmethod
    def _admit(state, batch_id, rows):
        p = state['policy']
        _need(digest(canonical(p['extension_roster'])) == p['extension_roster_sha256'], 'Extension roster changed')
        lane, group, _ = budget._unbatch(p, batch_id)
        for r in rows:
            item = p['extension_roster'].get(r['cell_id'])
            _need(item is not None and (lane, group, r['split'], r['config']) ==
                  (item['lane'], item['group_id'], item['stage'], item['config']) and
                  r['request_sha256'] in item['payload_choices'], 'Reservation is outside frozen extension roster')

    @staticmethod
    def _apply(state, kind, data):
        p = data['policy'] if state is None else state['policy']
        _need(digest(canonical(p['extension_roster'])) == p['extension_roster_sha256'], 'Extension roster changed')
        _need(p['global_clock_anchor_utc'] == GLOBAL_ANCHOR and p['global_deadline_utc'] == GLOBAL_DEADLINE,
              'Original global clock cannot shift')
        if kind == 'followup_start':
            _need(data['at_utc'] == p['global_clock_anchor_utc'], 'Global clock cannot reset')
        if kind == 'reserve':
            ExtensionLedger._admit(state, data['batch_id'], data['new_requests'])
        return budget.FollowupLedger._apply(state, kind, data)

    def __init__(self, path, policy, **kwargs):
        _need(canonical(freeze_policy(policy['manifest_path'])) == canonical(policy), 'Extension policy differs from freeze')
        super().__init__(path, policy, **kwargs)
        with self._locked() as state:
            if state['window_started_at_utc'] is None:
                self._append(state, 'followup_start', {'at_utc': policy['global_clock_anchor_utc']})

    def reserve_group(self, lane, group_id, requests, *, batch_id=None):
        self.verify_full_journal()
        rows = budget._specs(requests)
        with self._locked() as state:
            self._check_guard(state)
            if self._now() >= budget._utc(state['policy']['global_deadline_utc']):
                raise budget.BudgetExceeded('Original global deadline ended')
            batch = budget._batch(state['policy'], lane, group_id, batch_id or group_id)
            self._admit(state, batch, rows)
            budget._validate_specs(state, batch, rows)
            return self._reserve(state, batch, lane, rows)


class ExtensionPermit:
    def __init__(self, manifest, authorization, review):
        self.manifest_path, self.authorization_path, self.review_path = map(Path, (manifest, authorization, review))
        self.manifest = json.loads(self.manifest_path.read_text())
        self.manifest_sha256 = digest(self.manifest_path.read_bytes())
        self.authorization = json.loads(self.authorization_path.read_text())
        self.authorization_sha256 = digest(self.authorization_path.read_bytes())
        self.review = json.loads(self.review_path.read_text())
        self.review_sha256 = digest(self.review_path.read_bytes())
        self.execution = (ROOT / self.manifest['execution_directory']).resolve()
        _need(self.execution.is_relative_to(ROOT / 'data/raw/subscription-followup'), 'Extension raw namespace only')
        self.guard = FileGuard()
        self.plan_path = ROOT / self.manifest['plan']['path']
        self.guard.check(self.plan_path, self.manifest['plan']['sha256'])
        self.plan = json.loads(self.plan_path.read_text())
        self.groups = self.plan['groups']
        self.records, self.cell_group = {}, {}
        self.cell_identity_sha256 = {}
        for g in self.groups:
            for c in g['cells']:
                _need(c['cell_id'] not in self.records and c['group_id'] == g['group_id'], 'Cell/group identity differs')
                _need(digest(canonical(c['payload'])) == c['payload_sha256'], 'Payload differs')
                validate_payload(c['config'], c['payload'])
                self.records[c['cell_id']] = c
                self.cell_group[c['cell_id']] = g
                self.cell_identity_sha256[c['cell_id']] = digest(canonical(c))
        self.cells = self.records  # Inherited closeout counts the complete planned roster.
        self.credential_root = ROOT.parent / 'Decision Context Benchmark'
        self.ledger = None
        self.monotonic_start = None
        self.monotonic_remaining = 18000
        self.check()

    def check(self):
        self.guard.check(self.manifest_path, self.manifest_sha256)
        self.guard.check(self.authorization_path, self.authorization_sha256)
        self.guard.check(self.review_path, self.review_sha256)
        self.guard.check(self.plan_path, self.manifest['plan']['sha256'])
        for n, sha in self.manifest['frozen_files'].items():
            self.guard.check(ROOT / n, sha)
        for item in self.manifest['closed_evidence'].values():
            self.guard.check(item['path'], item['sha256'])
        _need(not (self.execution / 'STOP.json').exists(), 'Extension stop seal present')
        a = self.authorization
        _need(a.get('experimental_inference_authorized') is True and
              a.get('authorization_source') == 'explicit_owner_instruction' and
              a.get('manifest_sha256') == self.manifest_sha256 and
              a.get('openai_subscription_only') is True and
              a.get('allow_paid_openai_api') is False and a.get('allow_purchases_or_recharge') is False and
              a.get('max_sol_calls') == 576 and a.get('max_jev_calls') == 552,
              'Exact bounded extension authorization required')
        _need(self.review.get('status') == 'pass' and not self.review.get('remaining_findings') and
              self.review.get('manifest_sha256') == self.manifest_sha256, 'Exact extension review required')
        _need(datetime.now(timezone.utc) < budget._utc(self.manifest['global_deadline_utc']), 'Original global deadline ended')
        if self.ledger is not None:
            _need(self.ledger.remaining_seconds() > 0, 'Durable global deadline ended')
        if self.monotonic_start is not None:
            _need(time.monotonic() - self.monotonic_start < self.monotonic_remaining, 'Monotonic deadline ended')
        return True

    def spec(self, g, c):
        stage = c.get('stage', g['stage'])
        batch = g['group_id'] + ':' + stage if g['lane'] == 'isolated_agent' else g['group_id']
        return budget.request_spec(self.policy, lane=g['lane'], group_id=g['group_id'], batch_id=batch,
                                   stage=stage, cell_id=c['cell_id'], config=c['config'], payload=c['payload'])

    def specs(self, g):
        return [self.spec(g, c) for c in g['cells']]

    def retained(self, c):
        g = self.cell_group[c['cell_id']]
        spec = self.spec(g, c)
        path = self.execution / 'attempts' / spec['key'] / 'completed.json'
        result = json.loads(path.read_text())
        entry = self.ledger.entry(spec['key'])
        _need(entry is not None and entry['status'] in ('settled', 'unknown_usage') and
              digest(path.read_bytes()) == entry['evidence_sha256'], 'Exact settled gate evidence required')
        _need(all(result.get(k) == v for k, v in {'key': spec['key'], 'cell_id': c['cell_id'],
              'config': c['config'], 'namespace': c['namespace'], 'request_sha256': c['payload_sha256']}.items()),
              'Gate identity differs')
        for name, sha in result['raw_hashes'].items():
            _need(Path(name).name == name and digest((path.parent / name).read_bytes()) == sha, 'Gate raw evidence changed')
        return result

    def selected(self, c):
        if c.get('arm') != 'Jev_gate':
            return copy.deepcopy(c)
        gate = self.records[c['gate_cell_id']]
        result = self.retained(gate)
        parsed = result['parsed']
        disposition = pilot.gate_disposition(parsed.get('score'), status=parsed['status'])
        body = pilot.select_actor_payload(c, disposition)
        if body is None:
            return None
        actual = copy.deepcopy(c)
        actual.update(payload=body, payload_sha256=digest(canonical(body)))
        return actual

    def check_dispatch(self, c, spec):
        self.check()
        original = self.records.get(c.get('cell_id'))
        _need(original is not None, 'Unplanned extension cell')
        _need(digest(canonical(original)) == self.cell_identity_sha256[c['cell_id']], 'In-memory frozen cell changed')
        expected = self.selected(original)
        _need(expected is not None and canonical(c) == canonical(expected), 'Gate-conditioned payload or cell differs')
        g = self.cell_group[c['cell_id']]
        _need(spec == self.spec(g, c), 'Dispatch spec differs from selected frozen variant')
        entry = self.ledger.entry(spec['key'])
        _need(entry is not None and entry['status'] == 'dispatched' and
              all(entry.get(k) == v for k, v in spec.items()), 'Exact durable dispatch intent required')
        for prior in g['cells']:
            if prior['cell_id'] == c['cell_id']:
                break
            actual = self.selected(prior)
            _need(actual is not None, 'Missing conditional predecessor cannot be skipped into protection')
            e = self.ledger.entry(self.spec(g, actual)['key'])
            _need(e is not None and e['status'] in ('settled', 'unknown_usage'), 'Frozen within-group order violated')


class ExtensionExecutor(ContinuationExecutor):
    def __init__(self, p):
        Executor.__init__(self, p)
        self.service_failures = list(p.manifest.get('prior_transient_failure_events', []))
        self.consecutive_service_failures = 0

    def restore(self):
        snapshot = self.permit.ledger.snapshot()
        _need(not any(self.attempts.iterdir()) and not snapshot['entries'] and
              snapshot['window_started_at_utc'] == self.permit.manifest['global_clock_anchor_utc'],
              'Extension restart denied; no intent may replay')

    def observe(self, g, result):
        if result['config'] == 'jev_firstparty' and result['parsed']['status'] == 'tie' and result['parsed'].get('score') == .5:
            with self.lock:
                self.completed['tie'] += 1
                self.consecutive_service_failures = 0
                self.event('native_abstention', key=result['key'], stage=g['stage'])
            return
        super().observe(g, result)
        if g['lane'] == 'isolated_agent' and not result['parsed'].get('valid'):
            self.reason = 'pilot_provider_failure_missing_not_protection'
            self.fatal.set()

    def call(self, g, c):
        spec = self.permit.spec(g, c)
        with self.lock:
            if self.fatal.is_set() or self.pause.is_set():
                return None
            self.permit.check()
            self.permit.ledger.mark_dispatched(spec['key'])
            if self.permit.monotonic_start is None:
                self.permit.monotonic_remaining = self.permit.ledger.remaining_seconds()
                self.permit.monotonic_start = time.monotonic()
        result = invoke(c, spec, self.attempts, permit=self.permit)
        cost = budget.usage_cost(c['config'], result['parsed'].get('usage'))
        if result.get('native_request_sent') is False:
            cost = '0'
        path = self.attempts / spec['key'] / 'completed.json'
        self.permit.ledger.settle(spec['key'], cost, evidence_sha256=digest(path.read_bytes()))
        self.observe(g, result)
        return result

    def pilot_stage(self):
        for g in (g for g in self.permit.groups if g['lane'] == 'isolated_agent'):
            if self.fatal.is_set() or self.pause.is_set():
                return
            gates = [c for c in g['cells'] if c['kind'] == 'gate']
            self.permit.check()
            self.permit.ledger.reserve_group(g['lane'], g['group_id'], [self.permit.spec(g, c) for c in gates],
                                             batch_id=g['group_id'] + ':gate')
            for c in gates:
                self.call(g, c)
                if self.fatal.is_set() or self.pause.is_set():
                    return
            actors = [self.permit.selected(c) for c in g['cells'] if c['kind'] == 'actor']
            if any(c is None for c in actors):
                self.reason = 'missing_gate_actor_not_admitted'
                self.fatal.set()
                return
            self.permit.ledger.reserve_group(g['lane'], g['group_id'], [self.permit.spec(g, c) for c in actors],
                                             batch_id=g['group_id'] + ':actor')
            for c in actors:
                result = self.call(g, c)
                if result is not None and result['parsed'].get('valid'):
                    task = next(t for t in pilot.TASKS if t['task_id'] == c['task_id'])
                    try:
                        scored = pilot.evaluate(task, result['parsed']['answer'])
                    except ValueError:
                        scored = {'status': 'invalid_action_packet', 'legitimate_completion': None, 'attacker_success': None}
                    write_once(self.attempts / result['key'] / 'simulated-execution.json',
                               {'cell_id': c['cell_id'], 'result': scored, 'no_external_actions': True})
                if self.fatal.is_set() or self.pause.is_set():
                    return


def execute(manifest, authorization, review):
    p = ExtensionPermit(manifest, authorization, review)
    p.execution.mkdir(parents=True, exist_ok=True)
    with (p.execution / '.sole-executor.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        p.policy = freeze_policy(manifest)
        p.ledger = ExtensionLedger(p.execution / 'accounting.jsonl', p.policy)
        p.monotonic_remaining = p.ledger.remaining_seconds()
        runner = ExtensionExecutor(p)
        try:
            runner.stage('secondary', p.manifest['workers'])
            if not runner.fatal.is_set():
                runner.pilot_stage()
        except Exception as error:
            runner.reason = 'extension_stop:' + type(error).__name__
            runner.event('executor_stop', error_type=type(error).__name__)
            raise
        finally:
            runner.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--authorization', required=True)
    parser.add_argument('--review', required=True)
    args = parser.parse_args()
    execute(args.manifest, args.authorization, args.review)
