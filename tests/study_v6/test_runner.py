import json
from pathlib import Path
import tempfile
import unittest

from scripts.study_v6.accounting import BudgetLedger
from scripts.study_v6.common import canonical_bytes, sha256
from scripts.study_v6.evidence import exclusive, load
from scripts.study_v6.run import Executor, spec


def request(key='a', config='jev_firstparty', provider='typesafe', split='development'):
    payload = {'model': 'fixture', 'state': 'Unchanged complete input'}
    return {'key': key, 'config': config, 'provider': provider, 'split': split,
        'allocation': 'development' if split == 'development' else 'main', 'batch': 'fixture',
        'payload': payload, 'request_sha256': sha256(canonical_bytes(payload)),
        'reserved_usd': '.01' if provider else '0', 'inference_eligible': True}


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.ledger = BudgetLedger(self.root / 'budget.jsonl', {
            'prior_accounted_usd': {'openai': '0', 'typesafe': '0'},
            'provider_caps_usd': {'openai': '15', 'typesafe': '20'}, 'evidence_sha256': {}})
        self.calls = 0

    def tearDown(self):
        self.temp.cleanup()

    def fake(self, config, payload, raw, key, runtime=None):
        self.calls += 1
        folder = raw / key
        folder.mkdir(parents=True, exist_ok=False)
        exclusive(folder / 'request.json', canonical_bytes(payload))
        exclusive(folder / 'response.raw', b'{"fixture":"retained"}')
        result = {'request_sha256': sha256(canonical_bytes(payload)),
            'parsed': {'status': 'ok', 'valid': True, 'prediction': 1, 'score': .8,
                       'usage': {'input_tokens': 100}}, 'stop_required': False,
            'raw_hashes': {p.name: sha256(p.read_bytes()) for p in folder.iterdir()}}
        exclusive(folder / 'completed.json', result)
        return result

    def executor(self, reqs, invoke=None, schedules=None):
        return Executor({'requests': reqs, 'schedules': schedules or {}}, self.ledger,
                        self.root, invoke=invoke or self.fake, runtime_factory=lambda c: None)

    def test_exactly_once_and_crash_after_response_before_settlement(self):
        req = request()
        self.ledger.reserve_batch('dev', 'development', [spec(req)])
        self.ledger.mark_dispatched(req['key'])
        self.fake(req['config'], req['payload'], self.root / 'attempts', req['key'])
        executor = self.executor([req])
        record = executor.dispatch(req['key'])
        self.assertEqual(record['result']['parsed']['prediction'], 1)
        self.assertEqual(self.calls, 1)
        executor.dispatch(req['key'])
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.ledger.snapshot()['entries']['a']['status'], 'settled')

    def test_interrupted_intent_never_resent_and_unknown_retained(self):
        req, other = request(), request('b')
        self.ledger.reserve_batch('dev', 'development', [spec(req), spec(other)])
        self.ledger.mark_dispatched(req['key'])
        folder = self.root / 'attempts' / req['key']
        exclusive(folder / 'response.partial', b'data: {"partial":')
        with self.assertRaises(PermissionError):
            self.executor([req, other]).dispatch(req['key'])
        self.assertEqual(self.calls, 0)
        entries = self.ledger.snapshot()['entries']
        self.assertEqual(entries['a']['status'], 'unknown_usage')
        self.assertEqual(entries['a']['accounted_usd'], '0.01')
        self.assertEqual(entries['b']['status'], 'cancelled_unsent')
        self.assertEqual((folder / 'response.partial').read_bytes(), b'data: {"partial":')
        with self.assertRaises(PermissionError):
            self.executor([req, other]).dispatch('b')

    def test_no_unreserved_or_ineligible_dispatch(self):
        req = request()
        with self.assertRaises(PermissionError):
            self.executor([req]).dispatch('a')
        self.ledger.reserve_batch('dev', 'development', [spec(req)])
        req['inference_eligible'] = False
        with self.assertRaises(PermissionError):
            self.executor([req]).dispatch('a')
        self.assertEqual(self.calls, 0)

    def test_failure_preserved_and_remaining_positive_unsent_cancelled(self):
        first, second = request(), request('b')
        self.ledger.reserve_batch('dev', 'development', [spec(first), spec(second)])
        def fail(config, payload, raw, key, runtime=None):
            result = self.fake(config, payload, raw, key)
            result['parsed'] = {'status': 'authentication_error', 'valid': False, 'prediction': None}
            result['stop_required'] = True
            return result
        with self.assertRaises(PermissionError):
            self.executor([first, second], fail).dispatch('a')
        self.assertEqual(self.calls, 1)
        self.assertEqual(self.ledger.snapshot()['entries']['b']['status'], 'cancelled_unsent')
        self.assertIsNone(load(self.root / 'attempts/a/execution-record.json')['costs']['accounted_usd'])

    def test_tampered_raw_cannot_resume(self):
        req = request()
        executor = self.executor([req])
        self.ledger.reserve_batch('dev', 'development', [spec(req)])
        self.ledger.mark_dispatched(req['key'])
        self.fake(req['config'], req['payload'], self.root / 'attempts', req['key'])
        (self.root / 'attempts/a/response.raw').write_text('changed')
        with self.assertRaises(PermissionError):
            executor.dispatch('a')
        self.assertTrue((self.root / 'STOP.json').exists())

    def test_stopped_exception_can_close_without_dispatch_and_cannot_reserve_more(self):
        first, second = request(), request('b')
        self.ledger.reserve_batch('dev', 'development', [spec(first), spec(second)])
        def crash(*args, **kwargs):
            raise TimeoutError('fixture')
        executor = self.executor([first, second], crash)
        with self.assertRaises(PermissionError):
            executor.dispatch('a')
        self.assertEqual(self.ledger.snapshot()['entries']['a']['status'], 'dispatched')
        with self.assertRaises(PermissionError):
            executor.development()
        state = executor.close_stopped()
        self.assertTrue(state['terminal'])
        self.assertEqual(state['entries']['a']['status'], 'unknown_usage')
        self.assertEqual(state['entries']['b']['status'], 'cancelled_unsent')
        self.assertEqual(self.calls, 0)

    def test_missing_raw_creates_stop_before_any_other_request(self):
        first, second = request(), request('b')
        executor = self.executor([first, second])
        self.ledger.reserve_batch('dev', 'development', [spec(first), spec(second)])
        executor.dispatch('a')
        (self.root / 'attempts/a/response.raw').unlink()
        with self.assertRaises(PermissionError):
            executor.dispatch('a')
        with self.assertRaises(PermissionError):
            executor.dispatch('b')
        self.assertEqual(self.calls, 1)
        self.assertTrue((self.root / 'STOP.json').exists())

    def test_reserved_with_artifacts_keeps_hold_until_accounting_only_closure(self):
        req = request()
        self.ledger.reserve_batch('dev', 'development', [spec(req)])
        exclusive(self.root / 'attempts/a/response.partial', b'possibly sent')
        executor = self.executor([req])
        with self.assertRaises(PermissionError):
            executor.dispatch('a')
        self.assertEqual(self.ledger.snapshot()['entries']['a']['status'], 'reserved')
        state = executor.close_stopped()
        self.assertEqual(state['entries']['a']['status'], 'unknown_usage')
        self.assertEqual(state['entries']['a']['accounted_usd'], '0.01')
        self.assertEqual(self.calls, 0)


if __name__ == '__main__':
    unittest.main()
