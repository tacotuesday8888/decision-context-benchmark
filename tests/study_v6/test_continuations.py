"""Reviewed continuation is explicit, crash-safe and never retries a failed key."""
import json
from pathlib import Path
import subprocess
import unittest

from scripts.study_v6 import continuations as c, plan
from scripts.study_v6.accounting import AlreadyDispatched, AccountingError
from scripts.study_v6.common import canonical_bytes, sha256
from scripts.study_v6.evidence import exclusive, immutable, load
from scripts.study_v6.verify_execution import verify_bundle, VerificationError
from scripts.study_v6.pricing import usage_cost
from tests.study_v6 import test_execution_verification as fixtures


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ExecutionVerificationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.ledger = self.fixture.ledger
        self.failed, self.other = self.fixture.requests
        self.ledger.reserve_next_group('main')
        self.fixture.retain(self.failed, native={'error': 'upstream temporarily unavailable'}, http=503,
            parsed_override={'status':'http_error','valid':False,'prediction':None})
        exclusive(self.root/'STOP.json', {'reason':'Preserved first-attempt route failure',
            'request_key':self.failed['key'],'created_at_utc':'1970-01-01T00:16:40+00:00'})
        self.raw_plan = self.root/'confirmation-frozen-plan.json'
        immutable(self.raw_plan,self.fixture.frozen['confirmation'])
        self.freeze_path = self.root/'results/study-v6-execution/confirmation-freeze-v1.json'
        immutable(self.freeze_path,{'split':'confirmation','raw_plan':str(self.raw_plan.relative_to(self.root))})
        subprocess.run(['git','init','-q'],cwd=self.root,check=True,capture_output=True)

    @staticmethod
    def checker(split, root):
        receipt=load(root/'results/study-v6-execution'/(split+'-freeze-v1.json'))
        return receipt,load(root/receipt['raw_plan'])

    def prepare(self, **kwargs):
        return c.prepare(reason='Reviewed transient upstream service failure; retain original failed attempt.',
            directory=self.root,project_root=self.root,now_epoch=1000,freeze_checker=self.checker,**kwargs)

    def commit(self, prepared):
        relative=str(Path(prepared['receipt_path']).relative_to(self.root))
        subprocess.run(['git','add',relative],cwd=self.root,check=True,capture_output=True)
        subprocess.run(['git','-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
                        'commit','-qm','Review inert continuation receipt'],cwd=self.root,check=True,capture_output=True)

    def activate(self, prepared, **kwargs):
        return c.activate(prepared['manifest_path'],directory=self.root,project_root=self.root,
                          now_epoch=1060,freeze_checker=self.checker,**kwargs)

    def reset_interruption(self, partial=False, http_timeout=False):
        self.fixture = fixtures.ExecutionVerificationTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root,self.ledger=self.fixture.root,self.fixture.ledger
        self.failed,self.other=self.fixture.requests
        self.ledger.reserve_next_group('main');self.ledger.mark_dispatched(self.failed['key'])
        request=self.failed;folder=self.root/'attempts'/request['key']
        exclusive(folder/'request.json',canonical_bytes(request['payload']))
        exclusive(folder/'started.json',{'config':request['config'],'attempt_key':request['key'],
            'payload_sha256':request['request_sha256'],'route':'api_key','started_at':'1970-01-01T00:15:00+00:00'})
        if partial or http_timeout:exclusive(folder/'response.partial',b'{"model":"jev-1.14.0","answers":')
        if http_timeout:
            exclusive(folder/'response.raw',(folder/'response.partial').read_bytes())
            exclusive(folder/'response-headers.partial',b'HTTP/2 200\r\n\r\n')
            result={'parsed':{'status':'transport_error','valid':False,'prediction':None,'usage':{},'returned_model':None},
                'request_sha256':request['request_sha256'],'stop_required':True,
                'attempt_key':request['key'],'access_route':'api_key','paid_request':True,
                'observation':{'http_status':200,'transport_exit_code':28}}
        else:
            result={'parsed':{'status':'interrupted_unknown','valid':False,'prediction':None},
                'request_sha256':request['request_sha256'],'stop_required':True,'interrupted_dispatch_intent_preserved':True}
        result['raw_hashes']={p.name:sha256(p.read_bytes()) for p in folder.iterdir()}
        if http_timeout:exclusive(folder/'completed.json',result)
        costs=usage_cost(request['provider'],result['parsed'].get('usage'))
        record={'version':plan.VERSION,'attempt':0,'first_attempt_primary':True,'charged_allocation':'main',
            **{k:request[k] for k in ('key','config','split','allocation','batch','request_sha256','reserved_usd')},
            'result':result,'costs':costs}
        exclusive(folder/'execution-record.json',record)
        self.ledger.settle(request['key'],costs['accounted_usd'],evidence_sha256=sha256((folder/'execution-record.json').read_bytes()))
        exclusive(self.root/'STOP.json',{'request_key':request['key'],
            'reason':'Preserved first-attempt route failure' if http_timeout else 'Interrupted first attempt retained; no resend'})
        self.raw_plan=self.root/'confirmation-frozen-plan.json';immutable(self.raw_plan,self.fixture.frozen['confirmation'])
        self.freeze_path=self.root/'results/study-v6-execution/confirmation-freeze-v1.json'
        immutable(self.freeze_path,{'split':'confirmation','raw_plan':str(self.raw_plan.relative_to(self.root))})
        subprocess.run(['git','init','-q'],cwd=self.root,check=True,capture_output=True)

    def test_prepare_is_inert_and_scope_caps_hold_original_failure(self):
        before=self.ledger.snapshot()
        prepared=self.prepare()
        self.assertEqual(self.ledger.snapshot(),before)
        self.assertTrue((self.root/'STOP.json').exists())
        manifest=load(prepared['manifest_path'])
        self.assertEqual(manifest['remaining_request_keys'],[self.other['key']])
        self.assertNotIn(self.failed['key'],manifest['remaining_request_keys'])
        self.assertEqual(manifest['unchanged_caps']['provider_caps_usd'],{'openai':'15','typesafe':'20'})
        self.assertEqual(before['entries'][self.failed['key']]['status'],'unknown_usage')
        self.assertEqual(before['entries'][self.other['key']]['status'],'reserved')
        receipt=load(prepared['receipt_path'])
        self.assertNotIn('remaining_request_keys',receipt)
        self.assertNotIn(self.failed['key'],json.dumps(receipt))

    def test_activation_requires_exact_committed_receipt_and_cooldown(self):
        prepared=self.prepare()
        before=(self.root/'budget.jsonl').read_bytes()
        with self.assertRaisesRegex(c.ContinuationError,'committed'):
            self.activate(prepared)
        self.assertEqual((self.root/'budget.jsonl').read_bytes(),before)
        self.commit(prepared)
        with self.assertRaisesRegex(c.ContinuationError,'cooldown'):
            c.activate(prepared['manifest_path'],directory=self.root,project_root=self.root,
                now_epoch=1059,freeze_checker=self.checker)
        self.assertEqual((self.root/'budget.jsonl').read_bytes(),before)
        self.assertTrue((self.root/'STOP.json').exists())

    def test_activation_archives_after_journal_and_is_idempotent(self):
        prepared=self.prepare();self.commit(prepared)
        before=self.ledger.snapshot()
        result=self.activate(prepared)
        self.assertTrue(result['activated'])
        self.assertFalse((self.root/'STOP.json').exists())
        event=self.ledger.snapshot()['continuations'][self.failed['key']]
        archived=self.root/'stops'/(event['stop_sha256']+'.json')
        self.assertTrue(archived.is_file())
        self.assertEqual(sha256(archived.read_bytes()),event['stop_sha256'])
        self.assertEqual(before['entries'],self.ledger.snapshot()['entries'])
        body=(self.root/'budget.jsonl').read_bytes()
        self.activate(prepared)
        self.assertEqual((self.root/'budget.jsonl').read_bytes(),body)
        self.assertTrue(c.approved_failure(self.failed['key'],self.ledger,self.root,
            project_root=self.root,freeze_checker=self.checker))
        with self.assertRaises(AlreadyDispatched):
            self.ledger.mark_dispatched(self.failed['key'])

    def test_crash_between_journal_and_archive_never_opens_dispatch_gate(self):
        prepared=self.prepare();self.commit(prepared)
        def crash():raise RuntimeError('Injected crash after durable continuation journal')
        with self.assertRaises(RuntimeError):self.activate(prepared,after_journal=crash)
        self.assertTrue((self.root/'STOP.json').exists())
        self.assertEqual(len(self.ledger.snapshot()['continuations']),1)
        with self.assertRaises(c.ContinuationError):
            c.approved_failure(self.failed['key'],self.ledger,self.root,
                project_root=self.root,freeze_checker=self.checker)
        events=self.ledger.snapshot()['events']
        self.activate(prepared)
        self.assertFalse((self.root/'STOP.json').exists())
        self.assertEqual(self.ledger.snapshot()['events'],events)

    def test_verified_remaining_attempt_runs_once_and_failed_primary_stays_missing(self):
        prepared=self.prepare();self.commit(prepared);self.activate(prepared)
        self.fixture.retain(self.other)
        summary,records,_=verify_bundle(self.fixture.frozen,self.root/'budget.jsonl',self.root,
            project_root=self.root,continuation_freeze_checker=self.checker)
        self.assertTrue(summary['ready'])
        self.assertEqual(summary['reviewed_remaining_first_attempt_continuations'],1)
        self.assertEqual(sum(r['status']=='http_error' for r in records),2)
        self.assertEqual(sum(r['status']=='ok' for r in records),2)
        events=[json.loads(s) for s in (self.root/'budget.jsonl').read_text().splitlines()]
        self.assertEqual(sum(e['kind']=='dispatch' and e['data']['key']==self.failed['key'] for e in events),1)
        self.assertEqual(self.ledger.snapshot()['entries'][self.failed['key']]['status'],'unknown_usage')

    def test_closed_cohort_or_changed_freeze_cannot_activate(self):
        prepared=self.prepare();self.commit(prepared)
        stop_hash=sha256((self.root/'STOP.json').read_bytes())
        self.ledger.cancel_reserved(self.other['key'],stop_hash)
        with self.assertRaisesRegex(c.ContinuationError,'changed since preparation'):
            self.activate(prepared)
        self.assertTrue((self.root/'STOP.json').exists())
        self.assertFalse(self.ledger.snapshot()['continuations'])

    def test_quota_and_valid_predictions_are_not_transient_continuations(self):
        raw=self.root/'attempts'/self.failed['key']/'response.raw'
        raw.write_text('{"error":"insufficient_quota"}')
        with self.assertRaisesRegex(c.ContinuationError,'quota'):
            self.prepare()
        record_path=self.root/'attempts'/self.failed['key']/'execution-record.json'
        record=load(record_path)
        record['result']['parsed']={'status':'ok','valid':True,'prediction':1,'score':.8}
        record_path.write_bytes(canonical_bytes(record)+b'\n')
        with self.assertRaisesRegex(c.ContinuationError,'Only an invalid transient'):
            self.prepare()

    def test_committed_receipt_and_archive_cannot_be_changed_after_activation(self):
        prepared=self.prepare();self.commit(prepared);self.activate(prepared)
        receipt=Path(prepared['receipt_path'])
        receipt.write_text('{"changed":true}\n')
        with self.assertRaises(c.ContinuationError):
            c.approved_failure(self.failed['key'],self.ledger,self.root,
                project_root=self.root,freeze_checker=self.checker)

    def test_ledger_rejects_valid_prediction_even_with_exact_external_hash(self):
        record=load(self.root/'attempts'/self.failed['key']/'execution-record.json')
        record['result']['parsed']={'status':'ok','valid':True,'prediction':0,'score':.1}
        with self.assertRaisesRegex(AccountingError,'Only an invalid transient'):
            self.ledger.record_continuation(self.failed['key'],failure_record=record,
                failure_evidence_sha256=sha256(canonical_bytes(record)+b'\n'),stop_sha256='a'*64,
                manifest_sha256='b'*64,manifest_path='data/raw/manifest.json',receipt_path='results/receipt.json',
                receipt_sha256='c'*64,activated_at_epoch=1060)

    def test_intact_bodyless_interruption_keeps_hold_and_never_resends(self):
        self.reset_interruption()
        prepared=self.prepare();self.commit(prepared);self.activate(prepared)
        manifest=load(prepared['manifest_path'])
        self.assertEqual(manifest['eligibility_basis'],'preserved_dispatch_intent_with_no_response_received')
        self.assertEqual(self.ledger.snapshot()['entries'][self.failed['key']]['status'],'unknown_usage')
        with self.assertRaises(AlreadyDispatched):self.ledger.mark_dispatched(self.failed['key'])
        self.fixture.retain(self.other)
        summary,records,_=verify_bundle(self.fixture.frozen,self.root/'budget.jsonl',self.root,
            project_root=self.root,continuation_freeze_checker=self.checker)
        self.assertTrue(summary['ready'])
        self.assertEqual(sum(r['status']=='interrupted_unknown' for r in records),2)

    def test_partial_unknown_crash_is_not_mistaken_for_no_response(self):
        self.reset_interruption(partial=True)
        with self.assertRaisesRegex(c.ContinuationError,'Only a no-response interruption'):
            self.prepare()

    def test_observed_http200_partial_transport_timeout_can_continue_others(self):
        self.reset_interruption(http_timeout=True)
        partial=self.root/'attempts'/self.failed['key']/'response.partial';before=partial.read_bytes()
        prepared=self.prepare();self.commit(prepared);self.activate(prepared)
        self.assertEqual(partial.read_bytes(),before)
        self.fixture.retain(self.other)
        summary,records,_=verify_bundle(self.fixture.frozen,self.root/'budget.jsonl',self.root,
            project_root=self.root,continuation_freeze_checker=self.checker)
        self.assertTrue(summary['ready'])
        self.assertEqual(sum(r['status']=='transport_error' for r in records),2)


if __name__=='__main__':unittest.main()
