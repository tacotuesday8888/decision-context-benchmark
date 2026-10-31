import copy
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest

from scripts.study_v5.prompts import native_payload
from scripts.study_v6 import plan, routes
from scripts.study_v6.accounting import BudgetLedger
from scripts.study_v6.common import canonical_bytes, sha256
from scripts.study_v6.evidence import exclusive, load
from scripts.study_v6.pricing import reserve, usage_cost
from scripts.study_v6.verify_execution import verify_bundle, VerificationError


class ExecutionVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'budget.jsonl'
        self.ledger = BudgetLedger(self.path, {'prior_accounted_usd': {'openai': '0', 'typesafe': '0'},
            'provider_caps_usd': {'openai': '15', 'typesafe': '20'}, 'evidence_sha256': {}})
        self.requests = []
        self.cells = []
        for config, provider in (('jev_firstparty', 'typesafe'), ('luna_decisions', 'openai')):
            row = {'candidate': 'Complete external content.', 'task': 'Summarize the page.',
                   'policy': None, 'source': 'browsesafe', 'setting': 'indirect_tool_content'}
            payload = native_payload(row, 'task', config)
            digest = sha256(canonical_bytes(payload))
            key = sha256(canonical_bytes([plan.VERSION, 'confirmation', config, digest]))
            refs = [{'id': i, 'source': 'browsesafe', 'group': 'g1', 'condition': 'task'} for i in ('a', 'b')]
            request = {'key': key, 'config': config, 'provider': provider, 'split': 'confirmation',
                'allocation': 'main', 'batch': 'main:g1', 'payload': payload,
                'request_sha256': digest, 'reserved_usd': reserve(payload, provider),
                'inference_eligible': True, 'refs': refs}
            self.requests.append(request)
            for i, gold in (('a', 0), ('b', 1)):
                self.cells.append({'split': 'confirmation', 'id': i, 'source': 'browsesafe',
                    'group': 'g1', 'gold': gold, 'config': config, 'condition': 'task',
                    'allocation': 'main', 'batch': 'main:g1', 'request_key': key,
                    'payload_sha256': digest, 'inference_eligible': True, 'coverage_supported': True})
        self.frozen = {'confirmation': {'split': 'confirmation', 'requests': self.requests,
            'cells': self.cells, 'schedules': {'main': [{'batch': 'main:g1', 'group': 'g1',
                'request_keys': [r['key'] for r in self.requests], 'all_requests_supported': True}], 'supporting': []}}}
        self.ledger.register_schedule('main', [{'group': 'main:g1', 'requests': [self.spec(r) for r in self.requests]}])
        self.ledger.register_schedule('supporting', [])

    @staticmethod
    def spec(request):
        return {k: request[k] for k in ('key', 'provider', 'reserved_usd', 'request_sha256', 'config', 'split')}

    def native(self, request):
        if request['config'] == 'jev_firstparty':
            return {'model': 'jev-1.14.0', 'answers': {'injection': {'type': 'noul', 'noul': .8}},
                    'usage': {'input_tokens': 100}}
        return {'model': 'gpt-6-luna', 'answers': [{'name': 'injection', 'type': 'predicate', 'probability': .2}],
                'usage': {'input_tokens': 200, 'input_tokens_details': {'cached_tokens': 30, 'cache_write_tokens': 20}}}

    def retain(self, request, native=None, *, parsed_override=None, cost_override=None, http=200):
        self.ledger.mark_dispatched(request['key'])
        folder = self.root / 'attempts' / request['key']
        exclusive(folder / 'request.json', canonical_bytes(request['payload']))
        exclusive(folder / 'started.json', {'config': request['config'], 'attempt_key': request['key'],
            'payload_sha256': request['request_sha256'], 'route': routes.ROUTES[request['config']]})
        raw = self.native(request) if native is None else native
        exclusive(folder / 'response.raw', canonical_bytes(raw))
        exclusive(folder / 'response.partial', canonical_bytes(raw))
        exclusive(folder / 'response-headers.partial', ('HTTP/2 '+str(http)+'\r\nx-request-id: fixture\r\n\r\n').encode())
        parsed = routes.parse_response(request['config'], json.dumps(raw))
        if parsed_override is not None:
            parsed = parsed_override
        result = {'request_sha256': request['request_sha256'], 'parsed': parsed,
            'attempt_key': request['key'], 'access_route': routes.ROUTES[request['config']],
            'paid_request': request['provider'] is not None,
            'observation': {'http_status': http, 'transport_exit_code': 0},
            'raw_hashes': {p.name: sha256(p.read_bytes()) for p in folder.iterdir()},
            'stop_required': parsed['status'] not in ('ok', 'tie', 'unsupported_over_limit')}
        exclusive(folder / 'completed.json', result)
        costs = usage_cost(request['provider'], parsed.get('usage')) if request['provider'] else {
            'accounted_usd': '0', 'actual_billed_usd': None,
            'basis': 'Existing subscription/local route; zero incremental metered API charge'}
        if cost_override is not None:
            costs = cost_override
        record = {'version': plan.VERSION, 'attempt': 0, 'first_attempt_primary': True,
            **{k: request[k] for k in ('key', 'config', 'split', 'allocation', 'batch', 'request_sha256', 'reserved_usd')},
            'charged_allocation': self.ledger.snapshot()['entries'][request['key']]['allocation'],
            'result': result, 'costs': costs}
        exclusive(folder / 'execution-record.json', record)
        self.ledger.settle(request['key'], costs['accounted_usd'], evidence_sha256=sha256((folder/'execution-record.json').read_bytes()))
        return folder

    def finish(self):
        self.ledger.reserve_next_group('main')
        for request in self.requests:
            self.retain(request)

    def audit(self, frozen=None, receipt=None):
        return verify_bundle(frozen or self.frozen, self.path, self.root, receipt)

    def test_independent_reparse_dedup_expansion_and_measured_costs(self):
        self.finish()
        summary, normalized, details = self.audit()
        self.assertTrue(summary['ready'])
        self.assertEqual(summary['first_attempt_raw_execution_records_reparsed'], 2)
        self.assertEqual(len(normalized), 4)
        self.assertEqual({(r['config'], r['prediction']) for r in normalized},
                         {('jev_firstparty', 1), ('luna_decisions', 0)})
        self.assertEqual(summary['spending']['typesafe']['settled_usage_estimate_usd'], '0.0000042')
        self.assertEqual(summary['spending']['openai']['settled_usage_estimate_usd'], '0.0000203')
        self.assertIsNone(summary['spending']['openai']['actual_billed_usd'])
        self.assertEqual(summary['main_admitted_common_prefix_groups'], 1)
        self.assertEqual(len(details['planned_cell_dispositions']), 4)
        self.assertNotIn('request_key', json.dumps(summary))

    def test_raw_mutation_or_disappearance_is_corruption_not_missing(self):
        self.finish()
        path = self.root / 'attempts' / self.requests[0]['key'] / 'response.raw'
        prior = path.read_bytes()
        path.write_bytes(b'changed')
        with self.assertRaises(VerificationError):
            self.audit()
        path.write_bytes(prior)
        path.unlink()
        with self.assertRaises(VerificationError):
            self.audit()

    def test_saved_prediction_cannot_replace_independent_native_reparse(self):
        self.ledger.reserve_next_group('main')
        fake = routes.parse_response('jev_firstparty', json.dumps(self.native(self.requests[0])))
        fake.update(prediction=0, score=.2)
        self.retain(self.requests[0], parsed_override=fake)
        self.retain(self.requests[1])
        with self.assertRaisesRegex(VerificationError, 'reparse'):
            self.audit()

    def test_independent_costs_reject_self_consistent_wrong_settlement(self):
        self.ledger.reserve_next_group('main')
        wrong = usage_cost('typesafe', {'input_tokens': 1})
        self.retain(self.requests[0], cost_override=wrong)
        self.retain(self.requests[1])
        with self.assertRaisesRegex(VerificationError, 'pricing'):
            self.audit()

    def test_incomplete_allocations_return_not_ready_without_promoting_missing(self):
        summary, normalized, details = self.audit()
        self.assertFalse(summary['ready'])
        self.assertEqual({r['status'] for r in normalized}, {'not_attempted'})
        self.assertEqual(summary['main_unrun_runnable_groups'], 1)
        self.assertIn('main_schedule_not_terminal', summary['incomplete_reasons'])

    def test_ineligible_shared_reference_is_never_expanded(self):
        self.finish()
        frozen = copy.deepcopy(self.frozen)
        frozen['confirmation']['cells'][0].update(inference_eligible=False, coverage_supported=False)
        summary, normalized, details = self.audit(frozen)
        self.assertTrue(summary['ready'])
        self.assertEqual(len(normalized), 3)
        self.assertEqual(sum(d['status'] == 'unsupported' for d in details['planned_cell_dispositions']), 1)

    def test_unplanned_attempt_or_changed_frozen_payload_rejected(self):
        self.finish()
        (self.root / 'attempts/second-attempt').mkdir()
        with self.assertRaises(VerificationError):
            self.audit()
        (self.root / 'attempts/second-attempt').rmdir()
        frozen = copy.deepcopy(self.frozen)
        frozen['confirmation']['requests'][0]['payload']['state'] = 'changed'
        with self.assertRaisesRegex(VerificationError, 'payload'):
            self.audit(frozen)

    def test_terminal_unrun_requires_exact_stop_and_explicit_scopes(self):
        exclusive(self.root / 'STOP.json', {'reason': 'fixture access failure'})
        receipt = {'version': plan.VERSION, 'reason': 'No inference after explicit fixture failure',
            'stop_sha256': sha256((self.root/'STOP.json').read_bytes()),
            'scope': [{'allocation': 'main'}, {'allocation': 'supporting'}]}
        summary, normalized, _ = self.audit(receipt=receipt)
        self.assertTrue(summary['ready'])
        self.assertEqual({r['status'] for r in normalized}, {'not_attempted'})
        with self.assertRaises(VerificationError):
            self.audit(receipt=dict(receipt, stop_sha256='0'*64))

    def test_no_schedule_cannot_silently_mean_zero_eligible_complete(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            ledger = BudgetLedger(path/'budget.jsonl', {'prior_accounted_usd': {'openai':'0','typesafe':'0'}})
            summary, _, _ = verify_bundle({'confirmation': {'split':'confirmation', 'cells':[],
                'requests':[], 'schedules': {'main':[], 'supporting':[]}}}, path/'budget.jsonl', path)
            self.assertFalse(summary['ready'])
            ledger.register_schedule('main', [])
            ledger.register_schedule('supporting', [])
            summary, _, _ = verify_bundle({'confirmation': {'split':'confirmation', 'cells':[],
                'requests':[], 'schedules': {'main':[], 'supporting':[]}}}, path/'budget.jsonl', path)
            self.assertTrue(summary['ready'])

    def test_affordable_hash_valid_cost_stop_is_rejected_independently(self):
        # A valid hash chain alone does not establish the cost-only stopping rule.
        with self.ledger._locked() as state:
            self.ledger._append(state, 'cost_stop', {'allocation': 'main', 'group': 'main:g1',
                'index': 0, 'reason': 'openai:main_allocation', 'unrun_groups': 1})
        with self.assertRaisesRegex(VerificationError, 'affordable'):
            self.audit()

    def test_real_cost_stop_retains_full_target_and_unknown_holds(self):
        second = []
        for original in list(self.requests):
            request = copy.deepcopy(original)
            request['payload']['input' if request['config'] == 'luna_decisions' else 'state'] += ' '
            request['request_sha256'] = sha256(canonical_bytes(request['payload']))
            request['key'] = sha256(canonical_bytes([plan.VERSION, 'confirmation', request['config'], request['request_sha256']]))
            request['batch'] = 'main:g2'
            request['reserved_usd'] = reserve(request['payload'], request['provider'])
            request['refs'] = [dict(r, id={'a':'c','b':'d'}[r['id']], group='g2') for r in request['refs']]
            second.append(request)
            for cell in [c for c in list(self.cells) if c['config'] == original['config']]:
                self.cells.append(dict(cell, id={'a':'c','b':'d'}[cell['id']], group='g2', batch='main:g2',
                    request_key=request['key'], payload_sha256=request['request_sha256']))
        first = list(self.requests)
        self.requests.extend(second)
        self.frozen['confirmation']['schedules']['main'].append({'batch':'main:g2', 'group':'g2',
            'request_keys':[r['key'] for r in second], 'all_requests_supported':True})
        self.path.unlink()
        bounds = {p: str(sum(Decimal(r['reserved_usd']) for r in first if r['provider'] == p) * Decimal('1.5'))
                  for p in ('openai', 'typesafe')}
        self.ledger = BudgetLedger(self.path, {'prior_accounted_usd': {'openai':'0','typesafe':'0'}},
            allocations={a:{p:bounds[p] if a == 'main' else '0' for p in ('openai','typesafe')}
                         for a in ('main','supporting','development','recovery')})
        self.ledger.register_schedule('main', [{'group':'main:g1','requests':[self.spec(r) for r in first]},
                                             {'group':'main:g2','requests':[self.spec(r) for r in second]}])
        self.ledger.register_schedule('supporting', [])
        self.ledger.reserve_next_group('main')
        for request in first:
            self.retain(request, native={'error':'context_length_exceeded'}, http=400,
                        parsed_override={'status':'unsupported_over_limit','valid':False,'prediction':None})
        self.assertEqual(self.ledger.reserve_next_group('main')['status'], 'stopped')
        summary, normalized, details = self.audit()
        self.assertTrue(summary['ready'])
        self.assertEqual(summary['main_target_runnable_groups'], 2)
        self.assertEqual(summary['main_admitted_common_prefix_groups'], 1)
        self.assertEqual(summary['main_unrun_runnable_groups'], 1)
        self.assertEqual(summary['cost_stop_allocations'], ['main'])
        self.assertEqual(sum(r['status'] == 'not_attempted' for r in normalized), 4)
        self.assertTrue(all(d['reason'] == 'budget_cost_stop' for d in details['planned_cell_dispositions'] if d['id'] in ('c','d')))
        self.assertGreater(float(summary['spending']['openai']['unknown_usage_holds_usd']), 0)

    def test_protectai_native_score_is_reparsed_without_invented_cost(self):
        self.finish()
        config = 'protectai_local'
        p = routes.PANEL[config]
        payload = routes.payload(config, {'candidate': 'Full external page.',
            'source': 'browsesafe', 'setting': 'indirect_tool_content'}, 'candidate')
        digest = sha256(canonical_bytes(payload))
        key = sha256(canonical_bytes([plan.VERSION, 'confirmation', config, digest]))
        request = {'key': key, 'config': config, 'provider': None, 'split': 'confirmation',
            'allocation': 'comparators', 'batch': 'comparators:g1', 'payload': payload,
            'request_sha256': digest, 'reserved_usd': '0', 'inference_eligible': True,
            'refs': [{'id': 'a', 'source': 'browsesafe', 'group': 'g1', 'condition': 'candidate'}]}
        self.requests.append(request)
        self.cells.append({'split': 'confirmation', 'id': 'a', 'source': 'browsesafe',
            'group': 'g1', 'gold': 0, 'config': config, 'condition': 'candidate',
            'allocation': 'comparators', 'batch': 'comparators:g1', 'request_key': key,
            'payload_sha256': digest, 'inference_eligible': True, 'coverage_supported': True})
        self.ledger.reserve_unmetered_batch('comparators:protectai_local', [self.spec(request)])
        raw = {'returned_model': p['model'], 'revision': p['revision'], 'score': .7}
        self.retain(request, native=raw, parsed_override=dict(raw, **routes.probability(.7)))
        summary, normalized, _ = self.audit()
        self.assertTrue(summary['ready'])
        self.assertEqual([r['score'] for r in normalized if r['config'] == config], [.7])
        self.assertEqual(summary['spending']['typesafe']['settled_usage_estimate_usd'], '0.0000042')

    def test_another_dispatch_after_authentication_failure_is_rejected(self):
        self.ledger.reserve_next_group('main')
        self.retain(self.requests[0], native={'error':'unauthorized'}, http=401,
                    parsed_override={'status':'authentication_error','valid':False,'prediction':None})
        self.retain(self.requests[1])
        with self.assertRaisesRegex(VerificationError, 'after a systemic failure'):
            self.audit()

    def test_accounting_only_raw_conflict_remains_unknown_without_native_reparse(self):
        self.ledger.reserve_next_group('main')
        exclusive(self.root/'STOP.json', {'reason':'Conflicting raw artifacts; no further dispatch'})
        stop_hash = sha256((self.root/'STOP.json').read_bytes())
        request = self.requests[0]
        folder = self.root/'attempts'/request['key']
        exclusive(folder/'response.partial', b'incomplete prior bytes')
        self.ledger.mark_dispatched(request['key'])
        result = {'parsed': {'status':'interrupted_unknown','valid':False,'prediction':None},
            'request_sha256':request['request_sha256'], 'stop_required':True,
            'reserved_raw_conflict_retained':True,
            'raw_hashes':{'response.partial':sha256((folder/'response.partial').read_bytes())}}
        record = {'version':plan.VERSION,'attempt':0,'first_attempt_primary':True,
            **{k:request[k] for k in ('key','config','split','allocation','batch','request_sha256','reserved_usd')},
            'charged_allocation':'main','result':result,'costs':usage_cost(request['provider'],None)}
        exclusive(folder/'execution-record.json',record)
        self.ledger.settle(request['key'],None,evidence_sha256=sha256((folder/'execution-record.json').read_bytes()))
        self.ledger.cancel_reserved(self.requests[1]['key'],stop_hash)
        summary, normalized, _ = self.audit()
        self.assertTrue(summary['ready'])
        self.assertEqual(summary['accounting_only_reserved_raw_conflicts_retained'],1)
        self.assertEqual({r['status'] for r in normalized},{'interrupted_unknown','cancelled_unsent'})
        self.assertGreater(float(summary['spending']['typesafe']['unknown_usage_holds_usd']),0)


if __name__ == '__main__':
    unittest.main()
