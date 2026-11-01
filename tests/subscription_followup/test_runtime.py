"""Offline contract tests: no provider, credential file or network is accessed."""
import contextlib
import copy
from datetime import datetime,timedelta,timezone
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from scripts.subscription_followup import budget as b,run as r,transport as t
from scripts.subscription_followup.prepare import AUDIT_SCHEMA
from scripts.study_v7 import requests as old


def payload(tag='fixed',schema=None):
    return old._responses('sol_subscription',tag,'Classify the supplied evidence.',
        schema=copy.deepcopy(schema or old.BOOL_SCHEMA),configuration_revision='v7.0.2')


def sse(final=None,*,event='response.completed',answer=None,extra=()):
    if final is None:
        final={'id':'test-provider-request','model':'gpt-6.1-sol','status':'completed',
            'reasoning':{'effort':'low'},'service_tier':'default','store':False,'truncation':'disabled',
            'usage':{'input_tokens':12,'output_tokens':4},
            'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(answer if answer is not None else {'injection':False})}]}]}
    return ''.join('data: '+json.dumps(e)+'\n\n' for e in list(extra)+[{'type':event,'response':final}])


OBS={'http_status':200,'transport_exit_code':0,'response_headers':{}}


class ParseTests(unittest.TestCase):
    def test_completed_and_audit_schema_are_technical_success(self):
        result=t.parse_structured(sse(answer={'injection':True}),payload(),OBS)
        self.assertTrue(result['valid']);self.assertEqual(result['prediction'],1)
        audit={'task_fits_A':True,'task_fits_B':False,'injection_A':True,'injection_B':True,
            'ambiguous':True,'concerns':['uncertain'],'evidence_spans':['exact quote']}
        result=t.parse_structured(sse(answer=audit),payload(schema=AUDIT_SCHEMA),OBS)
        self.assertTrue(result['valid']);self.assertEqual(result['answer'],audit);self.assertIsNone(result['prediction'])

    def test_terminal_failures_refusal_schema_and_usage_remain_invalid(self):
        base=json.loads(next(line[6:] for line in sse().splitlines() if line.startswith('data: ')))['response']
        cases=[]
        f=copy.deepcopy(base);f.update(status='failed',error={'code':'subscription_sharing_usage_limit_exceeded'})
        cases.append((sse(f,event='response.failed'),OBS,'provider_failed'))
        f=copy.deepcopy(base);f['status']='incomplete';cases.append((sse(f,event='response.incomplete'),OBS,'provider_incomplete'))
        cases.append(('data: {"type":"response.output_text.delta","delta":"{}"}\n\n',OBS,'interrupted_stream'))
        cases.append((sse()+sse(),OBS,'invalid_terminal_events'))
        f=copy.deepcopy(base);f['output'][0]['content']=[{'type':'refusal','refusal':'No'}];cases.append((sse(f),OBS,'refusal'))
        cases.append((sse(answer={'injection':False,'extra':1}),OBS,'invalid_format'))
        cases.append((sse(answer={'injection':1}),OBS,'invalid_format'))
        f=copy.deepcopy(base);f['usage']={};cases.append((sse(f),OBS,'missing_usage'))
        f=copy.deepcopy(base);f['model']='gpt-6-luna';cases.append((sse(f),OBS,'model_mismatch'))
        f=copy.deepcopy(base);f['reasoning']={'effort':'high'};cases.append((sse(f),OBS,'settings_mismatch'))
        f=copy.deepcopy(base);f['store']=True;cases.append((sse(f),OBS,'settings_mismatch'))
        f=copy.deepcopy(base);f['store']=0;cases.append((sse(f),OBS,'settings_mismatch'))
        f=copy.deepcopy(base);f['truncation']='auto';cases.append((sse(f),OBS,'truncated'))
        f=copy.deepcopy(base);f['usage']['input_tokens']=500000;cases.append((sse(f),OBS,'context_limit_mismatch'))
        cases.append((sse(),dict(OBS,transport_exit_code=28),'transport_error'))
        cases.append((sse(extra=[{'type':'error','code':'credit_balance_exhausted'}]),OBS,'provider_failed'))
        for body,obs,status in cases:
            with self.subTest(expected=status):
                result=t.parse_structured(body,payload(),obs)
                self.assertFalse(result['valid']);self.assertEqual(result['status'],status)
        result=t.parse_structured(json.dumps({'error':{'code':'credit_balance_exhausted'}}),payload(),dict(OBS,http_status=429))
        self.assertFalse(result['valid']);self.assertEqual(result['error_code'],'credit_balance_exhausted')

    def test_forbidden_models_routes_and_unsupported_fields(self):
        for config in ('sol_responses','luna_responses','luna_decisions','protectai_local'):
            with self.assertRaises((PermissionError,b.AccountingError)):t.validate_payload(config,payload())
        for changes in [{'model':'gpt-6-luna'},{'max_output_tokens':2048},{'prompt_cache_options':{'mode':'explicit'}},
                {'store':True},{'reasoning':{'effort':'high'}},{'service_tier':'priority'},{'stream':False}]:
            with self.subTest(changes=changes),self.assertRaises(PermissionError):t.validate_payload('sol_subscription',dict(payload(),**changes))

    def test_no_permit_means_no_credential_or_http(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(t,'_credential') as auth,patch.object(t,'_post') as post:
            with self.assertRaises(PermissionError):t.invoke({}, {},tmp,permit=None)
            auth.assert_not_called();post.assert_not_called();self.assertEqual(list(Path(tmp).iterdir()),[])


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
        for name in ('ROOT','CANONICAL'):
            patcher=patch.object(r,name,self.root);patcher.start();self.addCleanup(patcher.stop)
        self.now=datetime.now(timezone.utc)
        self.raw=self.root/'data/raw/subscription-followup';self.raw.mkdir(parents=True)
        self.execution=self.raw/'execution-test';self.execution.mkdir()
        self.prior=self.root/'prior.jsonl';self.prior.write_bytes(b'closed offline prior\n')
        self.receipt=self.root/'prior.json';self.receipt.write_bytes(old.canonical({'accounting':{
            'cumulative_conservative_accounted_usd':b.PRIOR,'unknown_v7_full_holds_usd':b.PRIOR_UNKNOWN},
            'journal':{'sha256':old.digest(self.prior.read_bytes()),'no_reserved_or_dispatched_entries':True}}))
        for name,path in [('PRIOR_JOURNAL_SHA256',self.prior),('PRIOR_RECEIPT_SHA256',self.receipt)]:
            patcher=patch.object(b,name,old.digest(path.read_bytes()));patcher.start();self.addCleanup(patcher.stop)
        self.groups=[]
        for stage,group,n,schema in [('preflight','preflight:canaries',2,None),('preflight','preflight:dev',8,None),
                ('main','main:g0',2,None),('main','main:g1',2,None),('repeat','repeat:g0',1,None),('audit','audit:g0',1,AUDIT_SCHEMA)]:
            cells=[]
            for i in range(n):
                body=payload(f'{group}:full-source-{i}',schema)
                cells.append({'cell_id':f'{group}:cell{i}','group_id':group,'config':'sol_subscription',
                    'configuration_revision':'v7.0.2','namespace':'repeat-1' if stage=='repeat' else 'first',
                    'payload':body,'payload_sha256':old.digest(old.canonical(body)),'upstream_label':0})
            self.groups.append({'lane':'blind_audit' if stage=='audit' else 'sol_general','stage':stage,'group_id':group,'cells':cells})
        self.planpath=self.raw/'test-plan.json';self.planpath.write_bytes(old.canonical({'groups':self.groups}))
        self.manifest=self.root/'manifest.json';self.authpath=self.root/'authorization.json';self.review=self.root/'review.json'
        lanes={name:{'enabled':name in ('sol_general','blind_audit')} for name in b.LANES}
        self.m={'run_namespace':'subscription-followup-runtime-test','routes':copy.deepcopy(b.ROUTES),'lanes':lanes,
            'execution_directory':str(self.execution.relative_to(self.root)),'workers':4,'window_seconds':18000,
            'plan':{'path':str(self.planpath.relative_to(self.root)),'sha256':old.digest(self.planpath.read_bytes())},
            'frozen_files':{},'closed_evidence':{'receipt':{'path':str(self.receipt),'sha256':old.digest(self.receipt.read_bytes())},
                'journal':{'path':str(self.prior),'sha256':old.digest(self.prior.read_bytes())}}}
        self.manifest.write_bytes(old.canonical(self.m));sha=old.digest(self.manifest.read_bytes())
        self.auth={'experimental_inference_authorized':True,'authorization_source':'explicit_owner_instruction',
            'manifest_sha256':sha,'openai_subscription_only':True,'allow_paid_openai_api':False,
            'allow_purchases_or_recharge':False,'window_seconds':18000,'owner_instruction':'offline fixture authorization',
            'max_general_calls':4410,'max_audit_calls':100}
        self.authpath.write_bytes(old.canonical(self.auth));self.review.write_bytes(old.canonical({'manifest_sha256':sha,'status':'pass','remaining_findings':[]}))
        self.called=[];self.call_lock=threading.Lock()
        self.authmock=patch.object(t,'_credential',return_value='TEST_ONLY_FAKE_TOKEN');self.authspy=self.authmock.start();self.addCleanup(self.authmock.stop)
        self.postmock=patch.object(t,'_post',side_effect=self.post);self.postspy=self.postmock.start();self.addCleanup(self.postmock.stop)
        self.silence=patch('sys.stdout',new_callable=io.StringIO);self.silence.start();self.addCleanup(self.silence.stop)

    def post(self,config,body,token,directory):
        with self.call_lock:self.called.append(body['input'][0]['content'])
        schema=body['text']['format']['schema']
        answer={'injection':True} if set(schema['properties'])=={'injection'} else {
            'task_fits_A':True,'task_fits_B':True,'injection_A':False,'injection_B':False,
            'ambiguous':False,'concerns':[],'evidence_spans':[]}
        result=sse(answer=answer);t.write_once(directory/'response.raw',result.encode())
        return copy.deepcopy(OBS),result

    def permit(self):
        p=r.Permit(self.manifest,self.authpath,self.review,self.execution)
        p.policy=b.freeze_policy(self.manifest,prior_receipt_path=self.receipt,prior_journal_path=self.prior)
        p.ledger=b.FollowupLedger(self.execution/'accounting.jsonl',p.policy,clock=lambda:self.now)
        return p

    def admit(self,p,group):
        p.ledger.reserve_group(group['lane'],group['group_id'],p.specs(group),batch_id=group['group_id'])

    def retained(self,*,post=None,settled=False):
        p=self.permit();group=self.groups[0];specs=p.specs(group)
        p.ledger.reserve_group(group['lane'],group['group_id'],specs,batch_id=group['group_id'])
        spec=specs[0];p.ledger.mark_dispatched(spec['key'])
        if post is None:result=t.invoke(group['cells'][0],spec,self.execution/'attempts',permit=p)
        else:
            with patch.object(t,'_post',side_effect=post):result=t.invoke(group['cells'][0],spec,self.execution/'attempts',permit=p)
        completed=self.execution/'attempts'/spec['key']/'completed.json'
        if settled:p.ledger.settle(spec['key'],'0',evidence_sha256=old.digest(completed.read_bytes()))
        return p,spec,result,completed

    def test_authorization_review_stop_and_deadline_prevent_auth(self):
        self.auth['experimental_inference_authorized']=False;self.authpath.write_bytes(old.canonical(self.auth))
        with self.assertRaises(PermissionError):self.permit()
        self.authspy.assert_not_called();self.postspy.assert_not_called()
        self.auth['experimental_inference_authorized']=True;self.authpath.write_bytes(old.canonical(self.auth));p=self.permit()
        group=self.groups[0];specs=p.specs(group);p.ledger.reserve_group(group['lane'],group['group_id'],specs)
        p.ledger.mark_dispatched(specs[0]['key']);self.now+=timedelta(seconds=18000)
        with self.assertRaises(b.BudgetExceeded):t.invoke(group['cells'][0],specs[0],self.execution/'attempts',permit=p)
        self.authspy.assert_not_called();self.postspy.assert_not_called()
        (self.execution/'STOP.json').write_bytes(b'{}')
        with self.assertRaises(PermissionError):self.permit()

    def test_scientific_roster_and_within_group_order_before_credentials(self):
        p=self.permit();group=self.groups[0];specs=p.specs(group)
        p.ledger.reserve_group(group['lane'],group['group_id'],specs);p.ledger.mark_dispatched(specs[1]['key'])
        with self.assertRaises(PermissionError):t.invoke(group['cells'][1],specs[1],self.execution/'attempts',permit=p)
        p.ledger.mark_dispatched(specs[0]['key'])
        bad=copy.deepcopy(group['cells'][0]);bad['namespace']='repeat-1'
        with self.assertRaises(PermissionError):t.invoke(bad,specs[0],self.execution/'attempts',permit=p)
        self.authspy.assert_not_called();self.postspy.assert_not_called()

    def test_stop_during_credential_acquisition_never_posts(self):
        p=self.permit();group=self.groups[0];spec=p.specs(group)[0]
        p.ledger.reserve_group(group['lane'],group['group_id'],p.specs(group));p.ledger.mark_dispatched(spec['key'])
        def stopped(*args):
            (self.execution/'STOP.json').write_bytes(b'{}');return 'TEST_ONLY_FAKE_TOKEN'
        with patch.object(t,'_credential',side_effect=stopped):
            result=t.invoke(group['cells'][0],spec,self.execution/'attempts',permit=p)
        self.assertFalse(result['native_request_sent']);self.assertEqual(result['parsed']['status'],'runtime_error');self.postspy.assert_not_called()

    def test_quota_failure_stops_remaining_unsent_and_close_cancels_zero(self):
        p=self.permit();runner=r.Executor(p);group=self.groups[0];self.admit(p,group)
        def quota(config,body,token,directory):
            raw=json.dumps({'error':{'code':'credit_balance_exhausted','type':'insufficient_quota'}})
            t.write_once(directory/'response.raw',raw.encode());return dict(OBS,http_status=429),raw
        with patch.object(t,'_post',side_effect=quota) as http:runner.group(group)
        self.assertEqual(http.call_count,1);self.assertTrue(runner.fatal.is_set())
        specs=p.specs(group);self.assertEqual(p.ledger.entry(specs[0]['key'])['status'],'settled')
        self.assertEqual(p.ledger.entry(specs[1]['key'])['status'],'reserved')
        runner.close();self.assertEqual(p.ledger.entry(specs[1]['key'])['status'],'cancelled_unsent')
        self.assertEqual(p.ledger.entry(specs[1]['key'])['accounted_usd'],'0')
        self.assertEqual(p.ledger.snapshot()['all_in_accounted_usd'],b.PRIOR)
        with self.assertRaises(PermissionError):self.permit()

    def test_deadline_between_cells_never_dispatches_next(self):
        p=self.permit();runner=r.Executor(p);self.admit(p,self.groups[0]);original=self.post
        def expire(*args):
            result=original(*args);self.now+=timedelta(seconds=18000);return result
        with patch.object(t,'_post',side_effect=expire) as http:
            with self.assertRaises(b.BudgetExceeded):runner.group(self.groups[0])
        self.assertEqual(http.call_count,1)
        self.assertEqual(p.ledger.entry(p.specs(self.groups[0])[1]['key'])['status'],'reserved')

    def test_valid_crash_completion_denies_automatic_restart_without_auth(self):
        p,spec,result,path=self.retained();calls=self.postspy.call_count;auth=self.authspy.call_count
        with self.assertRaises(PermissionError):r.Executor(p)
        self.assertEqual(p.ledger.entry(spec['key'])['status'],'dispatched')
        self.assertEqual(self.postspy.call_count,calls);self.assertEqual(self.authspy.call_count,auth)
        self.assertEqual(p.ledger.snapshot()['policy']['prior_unknown_holds_usd'],b.PRIOR_UNKNOWN)
        with self.assertRaises(b.AlreadyDispatched):p.ledger.mark_dispatched(spec['key'])

    def test_recovery_rejects_namespace_identity_and_terminal_evidence_substitution(self):
        p,spec,result,path=self.retained();original=path.read_bytes()
        for field,value in [('namespace','repeat-1'),('cell_id','other-cell'),('config','jev_firstparty'),
                ('request_sha256','a'*64),('key','b'*64)]:
            with self.subTest(field=field):
                changed=copy.deepcopy(result);changed[field]=value;path.write_bytes(old.canonical(changed))
                with self.assertRaises(PermissionError):r.Executor(p)
                self.assertEqual(p.ledger.entry(spec['key'])['status'],'dispatched')
                path.write_bytes(original)
        p.ledger.settle(spec['key'],'0',evidence_sha256=old.digest(original))
        changed=copy.deepcopy(result);changed['parsed']['prediction']=0;path.write_bytes(old.canonical(changed))
        with self.assertRaises(PermissionError):r.Executor(p)

    def test_retained_quota_failure_denies_restart_without_retry(self):
        def quota(config,body,token,directory):
            raw=json.dumps({'error':{'code':'credit_balance_exhausted'}});t.write_once(directory/'response.raw',raw.encode())
            return dict(OBS,http_status=429),raw
        p,spec,result,path=self.retained(post=quota);auth_calls=self.authspy.call_count
        with self.assertRaises(PermissionError):r.Executor(p)
        self.assertEqual(self.authspy.call_count,auth_calls)
        self.assertEqual(p.ledger.entry(spec['key'])['status'],'dispatched')

    def test_inprocess_service_failure_bound_and_long_retry_deferred(self):
        p=self.permit();runner=r.Executor(p)
        failure={'key':'test-key','parsed':{'status':'http_error','valid':False},
            'observation':{'http_status':503,'response_headers':{'retry-after':'120'}}}
        runner.observe(self.groups[0],failure)
        self.assertTrue(runner.pause.is_set());self.assertFalse(runner.fatal.is_set())
        self.assertEqual(len(runner.service_failures),1)
        valid={'key':'valid-key','parsed':{'status':'ok','valid':True},'observation':dict(OBS)}
        runner.observe(self.groups[0],valid);self.assertEqual(runner.consecutive_service_failures,0)
        long_result=copy.deepcopy(failure);long_result['observation']['response_headers']={'retry-after':'1200'}
        runner.observe(self.groups[0],long_result)
        self.assertTrue(runner.fatal.is_set(),'Provider wait longer than the bounded recovery limit must defer, never clamp downward')
        self.assertEqual(runner.service_failures[-1]['retry_after_seconds'],1200)
        self.postspy.assert_not_called();self.authspy.assert_not_called()

    def test_http_date_retry_beyond_bound_defers(self):
        from email.utils import format_datetime
        p=self.permit();runner=r.Executor(p)
        future=format_datetime(datetime.now(timezone.utc)+timedelta(seconds=1200),usegmt=True)
        result={'key':'test-key','parsed':{'status':'http_error','valid':False},
            'observation':{'http_status':503,'response_headers':{'retry-after':future}}}
        runner.observe(self.groups[0],result)
        self.assertTrue(runner.fatal.is_set())
        self.assertGreater(runner.service_failures[0]['retry_after_seconds'],1100)
        self.postspy.assert_not_called();self.authspy.assert_not_called()

    def test_central_producer_admits_rank_order_despite_delayed_first_worker(self):
        p=self.permit();runner=r.Executor(p);admitted=[];writers=[];second_admitted=threading.Event()
        original_reserve=p.ledger.reserve_group;original_group=runner.group
        def reserve(lane,group,specs,**kwargs):
            result=original_reserve(lane,group,specs,**kwargs)
            admitted.append(group);writers.append(threading.get_ident())
            if group=='main:g1':second_admitted.set()
            return result
        def delayed(group):
            if group['group_id']=='main:g0':
                self.assertTrue(second_admitted.wait(1),'Producer must admit next rank independently of first worker latency')
            return original_group(group)
        with patch.object(p.ledger,'reserve_group',side_effect=reserve),patch.object(runner,'group',side_effect=delayed):
            runner.stage('main',2)
        self.assertEqual(admitted,['main:g0','main:g1'])
        self.assertEqual(set(writers),{threading.get_ident()})
        self.assertEqual(self.postspy.call_count,4)

    def test_fatal_first_group_prevents_next_rank_admission(self):
        p=self.permit();runner=r.Executor(p)
        def quota(config,body,token,directory):
            raw=json.dumps({'error':{'code':'credit_balance_exhausted'}});t.write_once(directory/'response.raw',raw.encode())
            return dict(OBS,http_status=429),raw
        with patch.object(t,'_post',side_effect=quota) as post:runner.stage('main',1)
        self.assertEqual(post.call_count,1);self.assertTrue(runner.fatal.is_set())
        entries=p.ledger.snapshot()['entries']
        self.assertEqual({e['cell_id'].split(':cell')[0] for e in entries.values()},{'main:g0'})
        self.assertEqual(len(entries),2)

    def test_reserved_journal_prefix_alone_denies_process_restart(self):
        p=self.permit();group=self.groups[0];self.admit(p,group)
        with self.assertRaises(PermissionError):r.Executor(p)
        self.postspy.assert_not_called();self.authspy.assert_not_called()

    def test_interrupted_intent_without_completion_never_replays(self):
        p=self.permit();group=self.groups[0];spec=p.specs(group)[0]
        p.ledger.reserve_group(group['lane'],group['group_id'],p.specs(group));p.ledger.mark_dispatched(spec['key'])
        directory=self.execution/'attempts'/spec['key'];directory.mkdir(parents=True);(directory/'started.json').write_bytes(b'{}')
        with self.assertRaises(PermissionError):r.Executor(p)
        self.authspy.assert_not_called();self.postspy.assert_not_called()
        self.assertEqual(p.ledger.entry(spec['key'])['status'],'dispatched')

    def test_tiny_orchestrator_valid_wrong_preflight_runs_all_once_and_seals(self):
        r.execute(self.manifest,self.authpath,self.review)
        self.assertEqual(self.postspy.call_count,16)
        self.assertEqual(self.authspy.call_count,16)
        for group in self.groups:
            expected=[c['payload']['input'][0]['content'] for c in group['cells']]
            positions=[self.called.index(value) for value in expected]
            self.assertEqual(positions,sorted(positions))
        gate=json.loads((self.execution/'preflight-validation.json').read_text())
        self.assertEqual(gate['valid_technical_outputs'],10);self.assertFalse(gate['correctness_used_as_gate'])
        snapshot=json.loads((self.execution/'final-ledger-snapshot.json').read_text())
        self.assertTrue(snapshot['terminal']);self.assertEqual(len(snapshot['entries']),16)
        self.assertEqual(snapshot['all_in_accounted_usd'],b.PRIOR)
        with self.assertRaises(PermissionError):r.execute(self.manifest,self.authpath,self.review)
        self.assertEqual(self.postspy.call_count,16)


if __name__=='__main__':unittest.main()
