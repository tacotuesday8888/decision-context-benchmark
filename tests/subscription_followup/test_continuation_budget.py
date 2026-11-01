"""Pure synthetic metadata tests. No auth, network or model response is read."""
import copy
from collections import Counter
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.subscription_followup import budget as b,continuation_budget as c
from scripts.study_v7.requests import canonical,digest


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(canonical(value)+b'\n')
    return {'path':str(path),'sha256':digest(path.read_bytes())}


class ContinuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup);cls.root=Path(cls.tmp.name).resolve()
        cls.patches=[]
        def bind(module,name,value):
            patcher=patch.object(module,name,value);patcher.start();cls.patches.append(patcher);cls.addClassCleanup(patcher.stop)
        bind(c,'ROOT',cls.root)
        prior=cls.root/'prior-v7.jsonl';prior.write_bytes(b'closed inherited metadata\n')
        receipt=cls.root/'prior-v7.json'
        write(receipt,{'accounting':{'cumulative_conservative_accounted_usd':b.PRIOR,'unknown_v7_full_holds_usd':b.PRIOR_UNKNOWN},
            'journal':{'sha256':digest(prior.read_bytes()),'no_reserved_or_dispatched_entries':True}})
        bind(b,'PRIOR_JOURNAL_SHA256',digest(prior.read_bytes()));bind(b,'PRIOR_RECEIPT_SHA256',digest(receipt.read_bytes()))
        cls.prior,cls.prior_receipt=prior,receipt
        groups=[]
        body={'model':'gpt-6.1-sol','instructions':'Fixed synthetic evidence only','input':[{'role':'user','content':'fixed'}],
            'store':False,'stream':True,'service_tier':'default','reasoning':{'effort':'low'},
            'text':{'format':{'type':'json_schema','name':'injection_decision','strict':True,
                'schema':{'type':'object','properties':{'injection':{'type':'boolean'}},'required':['injection'],'additionalProperties':False}}}}
        for stage,count,size in [('preflight',10,10),('main',4000,8),('repeat',400,8),('audit',100,1)]:
            for offset in range(0,count,size):
                gid=f'{stage}:g{offset//size}'
                cells=[{'cell_id':f'{stage}:cell{i}','config':'sol_subscription','group_id':gid,'payload':body,
                    'payload_sha256':digest(canonical(body)),'namespace':'repeat-1' if stage=='repeat' else 'first'} for i in range(offset,min(offset+size,count))]
                groups.append({'lane':'blind_audit' if stage=='audit' else 'sol_general','stage':stage,'group_id':gid,'cells':cells})
        cls.original_plan=cls.root/'original-plan.json';original_plan_binding=write(cls.original_plan,{'groups':groups})
        lanes={lane:{'enabled':lane in ('sol_general','blind_audit')} for lane in b.LANES}
        original_manifest=cls.root/'original-manifest.json'
        original_manifest_binding=write(original_manifest,{'run_namespace':'subscription-followup-original-test','routes':b.ROUTES,'lanes':lanes,'plan':original_plan_binding})
        original_policy=b.freeze_policy(original_manifest,prior_receipt_path=receipt,prior_journal_path=prior)
        now=b._utc(c.ORIGINAL_START)
        ledger=b.FollowupLedger(cls.root/'original-accounting.jsonl',original_policy,clock=lambda:now)
        actual=set();cancelled=set()
        for group in groups:
            if group['stage'] not in ('preflight','main'):continue
            specs=[b.request_spec(original_policy,lane=group['lane'],group_id=group['group_id'],batch_id=group['group_id'],
                stage=group['stage'],cell_id=cell['cell_id'],config='sol_subscription',payload=cell['payload']) for cell in group['cells']]
            if group['stage']=='main' and len([i for i in actual if i.startswith('main:')])>=454 and not group['group_id']=='main:g57':continue
            ledger.reserve_group(group['lane'],group['group_id'],specs)
            for spec in specs:
                if group['stage']=='preflight' or len([i for i in actual if i.startswith('main:')])<454:
                    ledger.mark_dispatched(spec['key']);ledger.settle(spec['key'],'0',evidence_sha256='a'*64)
                    actual.add(spec['cell_id']);now+=timedelta(microseconds=1)
                else:
                    ledger.cancel_reserved(spec['key'],'b'*64);cancelled.add(spec['cell_id'])
        snapshot=ledger.snapshot();cls.actual=actual;cls.cancelled=cancelled
        cls.old_sha=digest(ledger.path.read_bytes());bind(c,'ORIGINAL_JOURNAL_SHA256',cls.old_sha)
        stop=write(cls.root/'original-STOP.json',{'status':'closed','manifest_sha256':original_manifest_binding['sha256'],'journal_sha256':cls.old_sha})
        snap=write(cls.root/'original-snapshot.json',snapshot)
        continuation_groups=[]
        for group in groups:
            cells=[cell for cell in group['cells'] if cell['cell_id'] not in actual]
            if cells:continuation_groups.append(dict(group,cells=cells))
        cls.new_plan=cls.root/'new-plan.json';new_binding=write(cls.new_plan,{'groups':continuation_groups})
        allowed,_=c._roster({'groups':continuation_groups});cls.allowed=allowed
        prior_counts={s:sum(cid.startswith(s+':') for cid in actual) for s in c.STAGE_CAPS}
        record={'version':c.VERSION,'original_manifest_sha256':original_manifest_binding['sha256'],'original_stop_sha256':stop['sha256'],
            'original_journal_sha256':cls.old_sha,'original_snapshot_sha256':snap['sha256'],'original_plan_sha256':original_plan_binding['sha256'],
            'new_plan_sha256':new_binding['sha256'],'prior_actual_stage_counts':prior_counts,'prior_actual_cells':len(actual),
            'proven_unsent_cancelled_cells':len(cancelled),'never_admitted_cells':4510-len(snapshot['entries']),
            'remaining_cells':len(allowed),'original_window_started_at_utc':c.ORIGINAL_START,
            'original_deadline_utc':(b._utc(c.ORIGINAL_START)+timedelta(seconds=18000)).isoformat(),
            'continuation_cell_ids_sha256':digest(canonical(sorted(allowed))),'never_retry_dispatched':True}
        cls.receipt=cls.root/'continuation-receipt.json';receipt_binding=write(cls.receipt,record)
        cls.bindings={'original_manifest':original_manifest_binding,'original_stop':stop,
            'original_journal':{'path':str(ledger.path),'sha256':cls.old_sha},'original_snapshot':snap,'receipt':receipt_binding}
        cls.manifest=cls.root/'new-manifest.json'
        write(cls.manifest,{'run_namespace':'subscription-followup-continuation-test','routes':b.ROUTES,'lanes':lanes,
            'plan':new_binding,'continuation':{'version':c.VERSION,'bindings':cls.bindings}})
        cls.policy=c.freeze_continuation_policy(cls.manifest,prior_receipt_path=receipt,prior_journal_path=prior)
        cls.continuation_groups=continuation_groups

    def setUp(self):
        self.local=tempfile.TemporaryDirectory(dir=self.root);self.addCleanup(self.local.cleanup)
        self.now=b._utc(c.ORIGINAL_START)+timedelta(hours=1)
        self.ledger=c.ContinuationLedger(Path(self.local.name)/'new-accounting.jsonl',self.policy,clock=lambda:self.now)

    def specs(self,group):
        return [b.request_spec(self.policy,lane=group['lane'],group_id=group['group_id'],batch_id=group['group_id'],
            stage=group['stage'],cell_id=cell['cell_id'],config=cell['config'],payload=cell['payload']) for cell in group['cells']]

    def test_real_shaped464_actual10_cancel4036_unadmitted_exact4046_roster(self):
        cpolicy=self.policy['continuation']
        self.assertEqual(len(self.actual),464);self.assertEqual(len(self.cancelled),10)
        self.assertEqual(len(cpolicy['allowed_roster']),4046)
        self.assertEqual(cpolicy['prior_actual_stage_counts'],{'preflight':10,'main':454,'repeat':0,'audit':0})
        self.assertEqual(Counter(v['stage'] for v in cpolicy['allowed_roster'].values()),{'main':3546,'repeat':400,'audit':100})
        self.assertFalse(set(cpolicy['allowed_roster'])&self.actual)
        self.assertEqual(self.ledger.snapshot()['all_in_accounted_usd'],b.PRIOR)
        self.assertEqual(self.policy['prior_unknown_holds_usd'],b.PRIOR_UNKNOWN)

    def test_original_start_is_durable_and_not_reset_on_reopen(self):
        snapshot=self.ledger.snapshot();self.assertEqual(snapshot['window_started_at_utc'],c.ORIGINAL_START)
        self.assertEqual(self.ledger.remaining_seconds(),14400)
        events=[json.loads(line) for line in self.ledger.path.read_text().splitlines()]
        self.assertEqual([e['kind'] for e in events],['initialize','followup_start'])
        self.assertEqual(events[1]['data']['at_utc'],c.ORIGINAL_START)
        self.now+=timedelta(hours=1)
        again=c.ContinuationLedger(self.ledger.path,clock=lambda:self.now)
        self.assertEqual(again.remaining_seconds(),10800)
        self.assertEqual(again.snapshot()['window_started_at_utc'],c.ORIGINAL_START)

    def test_original_actual_cannot_be_replaced_even_with_fresh_key(self):
        group=copy.deepcopy(self.continuation_groups[0]);group['cells'][0]['cell_id']='main:cell0'
        before=self.ledger.path.read_bytes()
        with self.assertRaises(b.AccountingError):self.ledger.reserve_group(group['lane'],group['group_id'],self.specs(group))
        self.assertEqual(self.ledger.path.read_bytes(),before)
        self.assertEqual(self.ledger.snapshot()['entries'],{})

    def test_exact_proven_unsent_can_run_once_but_new_cancel_cannot_backfill(self):
        group=self.continuation_groups[0];specs=self.specs(group)
        self.assertTrue(all(spec['cell_id'] in self.cancelled for spec in specs))
        self.ledger.reserve_group(group['lane'],group['group_id'],specs)
        first=specs[0];self.ledger.mark_dispatched(first['key']);self.ledger.settle(first['key'],'0',evidence_sha256='c'*64)
        with self.assertRaises(b.AlreadyDispatched):self.ledger.mark_dispatched(first['key'])
        second=specs[1];self.ledger.cancel_reserved(second['key'],'d'*64)
        replacement=b.request_spec(self.policy,lane=group['lane'],group_id=group['group_id'],batch_id='fresh-batch',
            stage=group['stage'],cell_id=second['cell_id'],config='sol_subscription',payload=group['cells'][1]['payload'])
        with self.assertRaises(b.AccountingError):self.ledger.reserve_group(group['lane'],group['group_id'],[replacement],batch_id='fresh-batch')
        self.assertEqual(self.ledger.entry(second['key'])['status'],'cancelled_unsent')

    def test_exact_payload_stage_route_and_group_bindings(self):
        group=self.continuation_groups[0]
        for change in [{'split':'repeat'},{'request_sha256':'f'*64},{'config':'luna_responses'},{'provider':'openai','reserved_usd':'1'}]:
            row=dict(self.specs(group)[0],**change);before=self.ledger.path.read_bytes()
            with self.assertRaises(b.AccountingError):self.ledger.reserve_group(group['lane'],group['group_id'],[row])
            self.assertEqual(self.ledger.path.read_bytes(),before)
        with self.assertRaises(b.AccountingError):self.ledger.reserve_group('sol_general','wrong-group',self.specs(group))

    def test_original_deadline_and_last_dispatch_clock_guard(self):
        group=self.continuation_groups[0];spec=self.specs(group)[0]
        self.ledger.reserve_group(group['lane'],group['group_id'],[spec])
        self.now=b._utc(c.ORIGINAL_START)
        with self.assertRaises(b.BudgetExceeded):self.ledger.mark_dispatched(spec['key'])
        self.now=b._utc(c.ORIGINAL_START)+timedelta(seconds=18000)
        with self.assertRaises(b.BudgetExceeded):self.ledger.mark_dispatched(spec['key'])
        with self.assertRaises(b.BudgetExceeded):self.ledger.reserve_group(group['lane'],group['group_id'],[spec])

    def test_ancestor_binding_tamper_and_policy_reset_fail_closed(self):
        group=self.continuation_groups[0];path=Path(self.bindings['receipt']['path']);body=path.read_bytes()
        path.write_bytes(body+b' ')
        try:
            with self.assertRaises(b.AccountingError):self.ledger.reserve_group(group['lane'],group['group_id'],self.specs(group))
        finally:path.write_bytes(body)
        for change in [{'original_window_started_at_utc':(b._utc(c.ORIGINAL_START)+timedelta(hours=1)).isoformat()},
                {'prior_actual_stage_counts':{'preflight':10,'main':0,'repeat':0,'audit':0}}]:
            policy=copy.deepcopy(self.policy);policy['continuation'].update(change)
            with self.assertRaises(b.AccountingError):c.ContinuationLedger(Path(self.local.name)/'bad.jsonl',policy)
        with self.assertRaises(b.AccountingError):c.ContinuationLedger(self.bindings['original_journal']['path'],self.policy)


if __name__=='__main__':unittest.main()
