import copy
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.subscription_followup import budget as b


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.prior=self.root/'prior.jsonl';self.prior.write_bytes(b'closed prior journal\n')
        self.receipt=self.root/'prior.json'
        self.receipt.write_bytes(b.canonical({'accounting':{'cumulative_conservative_accounted_usd':b.PRIOR,
            'unknown_v7_full_holds_usd':b.PRIOR_UNKNOWN},'journal':{'sha256':b.digest(self.prior.read_bytes()),
            'no_reserved_or_dispatched_entries':True}}))
        for name,path in [('PRIOR_JOURNAL_SHA256',self.prior),('PRIOR_RECEIPT_SHA256',self.receipt)]:
            p=patch.object(b,name,b.digest(path.read_bytes()));p.start();self.addCleanup(p.stop)
        self.manifest=self.root/'manifest.json';self.write_manifest()
        self.policy=self.freeze()
        self.now=datetime(2026,11,1,14,30,tzinfo=timezone.utc)
        self.path=self.root/'new'/'accounting.jsonl'
        self.ledger=b.FollowupLedger(self.path,self.policy,clock=lambda:self.now)

    def write_manifest(self,isolated=False):
        lanes={name:{'enabled':name!='isolated_agent'} for name in b.LANES}
        if isolated:lanes['isolated_agent']={'enabled':True,'pilot_ready':True,'pilot_receipt_sha256':'a'*64}
        self.manifest.write_bytes(b.canonical({'run_namespace':'subscription-followup-test-v1','routes':b.ROUTES,'lanes':lanes}))

    def freeze(self):
        return b.freeze_policy(self.manifest,prior_receipt_path=self.receipt,prior_journal_path=self.prior)

    def spec(self,i=0,*,lane='second_source',group='g0',batch=None,stage='secondary',config='jev_firstparty',policy=None):
        payload={'model':b.ROUTES[config]['model']}
        if config=='jev_firstparty':payload.update(state='synthetic',questions={'injection':{'type':'noul','instructions':'fixed'}})
        else:payload.update(input='synthetic',store=False)
        return b.request_spec(policy or self.policy,lane=lane,group_id=group,batch_id=batch or group,
            stage=stage,cell_id=f'{group}:cell{i}',config=config,payload=payload)

    def reserve(self,rows,*,lane='second_source',group='g0',batch=None,ledger=None):
        return (ledger or self.ledger).reserve_group(lane,group,rows,batch_id=batch or group)

    def test_exact_inherited_total_cap_and_full_context_prices(self):
        s=self.ledger.snapshot()
        self.assertEqual(s['all_in_accounted_usd'],b.PRIOR)
        self.assertEqual(Decimal(b.CAPS['typesafe'])-Decimal(b.PRIOR['typesafe']),Decimal('14.048575808'))
        self.assertEqual(self.policy['prior_unknown_holds_usd'],{'openai':'1.9952816','typesafe':'0'})
        self.assertEqual(self.policy['allocations_usd']['second_source']['typesafe'],'1.0752')
        self.assertEqual(self.policy['allocations_usd']['isolated_agent']['typesafe'],'0')
        self.assertEqual(b.maximum_cost('jev_firstparty'),'0.001344')
        self.assertEqual(b.usage_cost('jev_firstparty',{'input_tokens':32000}),'0.001344')
        self.assertIsNone(b.usage_cost('jev_firstparty',{'input_tokens':32001}))
        self.assertEqual(b.usage_cost('sol_subscription',None),'0')

    def test_route_model_and_multiple_questions_fail_closed(self):
        for config in ('luna_decisions','luna_responses','sol_responses'):
            with self.assertRaises(b.AccountingError):b.maximum_cost(config)
        for fields in [dict(route='api_key',credential_source='OPENAI_API_KEY',endpoint=b.ROUTES['sol_subscription']['endpoint']),
                dict(route='subscription',credential_source='current_codex_auth',endpoint=b.ROUTES['sol_subscription']['endpoint']),
                dict(route='subscription',credential_source='existing_project_oauth',endpoint='https://example.invalid')]:
            with self.assertRaises(b.AccountingError):b.validate_route('sol_subscription',**fields)
        for payload in [{'model':'wrong'}, {'model':'jev-1.14.0','state':'x','questions':{'a':{},'b':{}}},
                {'model':'jev-1.14.0','state':'x','questions':{'a':{}},'long_context':True}]:
            with self.assertRaises(b.AccountingError):b.request_spec(self.policy,lane='second_source',group_id='g',batch_id='g',
                stage='secondary',cell_id='a',config='jev_firstparty',payload=payload)

    def test_identical_payloads_separate_cells_but_batches_idempotent(self):
        rows=[self.spec(0),self.spec(1),self.spec(2,config='sol_subscription')]
        self.assertEqual(rows[0]['request_sha256'],rows[1]['request_sha256'])
        self.assertNotEqual(rows[0]['key'],rows[1]['key'])
        self.reserve(rows);before=self.path.read_bytes()
        self.reserve(rows);self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(len(self.ledger.snapshot()['entries']),3)
        with self.assertRaises(b.AccountingError):self.reserve([dict(rows[0],request_sha256='b'*64)],batch='different')
        self.assertEqual(self.path.read_bytes(),before)

    def test_same_cell_cannot_be_retried_under_fresh_batch(self):
        row=self.spec();self.reserve([row]);self.ledger.mark_dispatched(row['key'])
        self.ledger.settle(row['key'],None,evidence_sha256='a'*64)
        before=self.path.read_bytes()
        retry=self.spec(batch='new-attempt')
        with self.assertRaises(b.AccountingError):self.reserve([retry],batch='new-attempt')
        self.assertEqual(self.path.read_bytes(),before)

    def test_whole_group_cap_rejection_is_atomic(self):
        rows=[self.spec(i) for i in range(9)]+[self.spec(20,config='sol_subscription')]
        before=self.path.read_bytes()
        with self.assertRaises(b.BudgetExceeded):self.reserve(rows)
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(self.ledger.snapshot()['entries'],{})

    def test_disabled_and_pilot_guard(self):
        row=self.spec(lane='isolated_agent',stage='actor',config='sol_subscription')
        with self.assertRaises(b.AccountingError):self.reserve([row],lane='isolated_agent')
        obj=json.loads(self.manifest.read_bytes());obj['lanes']['isolated_agent']={'enabled':True}
        self.manifest.write_bytes(b.canonical(obj))
        with self.assertRaises(b.AccountingError):self.freeze()
        self.write_manifest(isolated=True);p=self.freeze()
        other=b.FollowupLedger(self.root/'isolated.jsonl',p,clock=lambda:self.now)
        self.assertEqual(p['allocations_usd']['isolated_agent']['typesafe'],'0.032256')
        for i in range(12):
            g=f'task{i}'
            rows=[self.spec(j,lane='isolated_agent',group=g,stage='actor',config='sol_subscription',policy=p) for j in range(4)]
            rows += [self.spec(j,lane='isolated_agent',group=g,stage='gate',policy=p) for j in range(2)]
            self.reserve(rows,lane='isolated_agent',group=g,ledger=other)
        with self.assertRaises(b.BudgetExceeded):
            self.reserve([self.spec(lane='isolated_agent',group='task13',stage='actor',config='sol_subscription',policy=p)],
                lane='isolated_agent',group='task13',ledger=other)

    def test_second_source_group_limit_and_unknown_hold_no_replacement(self):
        for i in range(100):
            g=f'g{i}';self.reserve([self.spec(j,group=g) for j in range(8)],group=g)
        with self.assertRaises(b.BudgetExceeded):self.reserve([self.spec(group='g100')],group='g100')
        row=self.spec();self.ledger.mark_dispatched(row['key'])
        self.ledger.settle(row['key'],None,evidence_sha256='e'*64)
        other=self.spec(99,batch='replacement')
        with self.assertRaises(b.BudgetExceeded):self.reserve([other],batch='replacement')
        s=self.ledger.snapshot()
        self.assertEqual(s['incremental_accounted_usd']['typesafe'],'1.0752')
        self.assertEqual(s['entries'][row['key']]['accounted_usd'],'0.001344')
        self.assertEqual(s['entries'][row['key']]['status'],'unknown_usage')

    def test_cancel_never_dispatched_zero_preserves_consumed_call_slot(self):
        rows=[self.spec(i) for i in range(8)];self.reserve(rows)
        self.ledger.cancel_reserved(rows[0]['key'],'a'*64)
        self.assertEqual(self.ledger.entry(rows[0]['key'])['accounted_usd'],'0')
        with self.assertRaises(b.BudgetExceeded):self.reserve([self.spec(99,batch='extra')],batch='extra')
        self.ledger.mark_dispatched(rows[1]['key'])
        with self.assertRaises(b.AccountingError):self.ledger.cancel_reserved(rows[1]['key'],'a'*64)
        self.ledger.settle(rows[1]['key'],None,evidence_sha256='f'*64)
        with self.assertRaises(b.AccountingError):self.ledger.cancel_reserved(rows[1]['key'],'a'*64)

    def test_preflight_stage_limit_no_backfill(self):
        rows=[self.spec(i,lane='sol_general',group='preflight',stage='preflight',config='sol_subscription') for i in range(10)]
        self.reserve(rows,lane='sol_general',group='preflight')
        self.ledger.cancel_reserved(rows[0]['key'],'a'*64)
        extra=self.spec(11,lane='sol_general',group='preflight2',stage='preflight',config='sol_subscription')
        before=self.path.read_bytes()
        with self.assertRaises(b.BudgetExceeded):self.reserve([extra],lane='sol_general',group='preflight2')
        self.assertEqual(self.path.read_bytes(),before)

    def test_dispatch_once_reopen_unknown_hold_and_evidence_immutable(self):
        row=self.spec();self.reserve([row]);self.ledger.mark_dispatched(row['key'])
        other=b.FollowupLedger(self.path,clock=lambda:self.now)
        with self.assertRaises(b.AlreadyDispatched):other.mark_dispatched(row['key'])
        other.settle(row['key'],None,evidence_sha256='c'*64)
        self.assertEqual(other.entry(row['key'])['accounted_usd'],'0.001344')
        with self.assertRaises(b.AccountingError):other.settle(row['key'],'0',evidence_sha256='d'*64)
        with self.assertRaises(b.AlreadyDispatched):other.mark_dispatched(row['key'])
        self.assertEqual(other.snapshot()['all_in_accounted_usd']['typesafe'],'7.78035312600000006')

    def test_one_window_all_lanes_restart_and_settle_after_deadline(self):
        a=self.spec();self.reserve([a]);self.assertEqual(self.ledger.remaining_seconds(),18000)
        self.now+=timedelta(hours=2);self.ledger.mark_dispatched(a['key']);start=self.now
        z=self.spec(lane='sol_general',group='main:g',stage='main',config='sol_subscription')
        self.reserve([z],lane='sol_general',group='main:g')
        self.now+=timedelta(hours=4);other=b.FollowupLedger(self.path,clock=lambda:self.now)
        self.assertEqual(other.remaining_seconds(),3600)
        self.assertEqual(other.snapshot()['window_started_at_utc'],start.isoformat())
        self.now+=timedelta(hours=1)
        with self.assertRaises(b.BudgetExceeded):other.mark_dispatched(z['key'])
        with self.assertRaises(b.BudgetExceeded):self.reserve([self.spec(group='next')],group='next',ledger=other)
        other.settle(a['key'],None,evidence_sha256='a'*64)
        self.assertEqual(other.remaining_seconds(),0)
        self.assertEqual(other.entry(a['key'])['status'],'unknown_usage')

    def test_backward_clock_and_elevated_policy_rejected(self):
        rows=[self.spec(i) for i in range(2)];self.reserve(rows)
        self.ledger.mark_dispatched(rows[0]['key']);self.now-=timedelta(seconds=1)
        with self.assertRaises(b.BudgetExceeded):self.ledger.mark_dispatched(rows[1]['key'])
        for change in [dict(provider_caps_usd=dict(b.CAPS,typesafe='22')),dict(prior_accounted_usd=dict(b.PRIOR,typesafe='0')),
                dict(window_seconds=18001),dict(routes={})]:
            p=dict(self.policy,**change)
            with self.assertRaises(b.AccountingError):b.FollowupLedger(self.root/'bad.jsonl',p)

    def test_policy_does_not_alias_mutable_expected_rules(self):
        p=self.freeze()
        p['routes']['sol_subscription']['route']='api_key'
        p['lanes']['sol_general']['limits']['stages']['main']['sol_subscription']=4001
        p['prior_unknown_holds_usd']['openai']='0'
        p['pricing']['jev_usd_per_million']='0'
        self.assertEqual(b.ROUTES['sol_subscription']['route'],'subscription')
        self.assertEqual(b.LANES['sol_general']['stages']['main']['sol_subscription'],4000)
        self.assertEqual(b.PRIOR_UNKNOWN['openai'],'1.9952816')
        self.assertEqual(b.PRICING['jev_usd_per_million'],'0.042')
        with self.assertRaises(b.AccountingError):b.FollowupLedger(self.root/'mutated.jsonl',p)

    def test_prior_manifest_hash_guards_and_journal_tamper(self):
        row=self.spec();self.reserve([row])
        for target in [self.prior,self.receipt,self.manifest]:
            original=target.read_bytes();st=target.stat()
            target.write_bytes(bytes([original[0]^1])+original[1:]);os.utime(target,ns=(st.st_atime_ns,st.st_mtime_ns))
            with self.assertRaises(b.AccountingError):self.ledger.mark_dispatched(row['key'])
            target.write_bytes(original)
        original=self.path.read_bytes();self.path.write_bytes(original[:-1])
        with self.assertRaises(b.AccountingError):b.FollowupLedger(self.path)
        self.path.write_bytes(original)
        with self.assertRaises(b.AccountingError):b.FollowupLedger(self.prior,self.policy)
        p=copy.deepcopy(self.policy);p['manifest_sha256']='a'*64
        with self.assertRaises(b.AccountingError):b.FollowupLedger(self.path,p)


if __name__=='__main__':unittest.main()
