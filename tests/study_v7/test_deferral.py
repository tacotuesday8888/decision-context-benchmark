"""Synthetic credit evidence, retained schedules and mocked transport only."""
from pathlib import Path
from datetime import datetime,timezone
import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch
from scripts.study_v7 import deferral,run,requests,routes,budget


def fixture_rows():
    location=Path(__file__).with_name('test_execution.py')
    spec=importlib.util.spec_from_file_location('v7_deferral_execution_fixture',location)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.main_rows(1),module.external_rows(1)


class Deferral(unittest.TestCase):
    def test_mixed_groups_cancel_only_unsent_paid_preserve_unknown_and_restart_without_replay(self):
        main,external=fixture_rows();plan=requests.build_plan(main,external,sol_config=None)
        lookup={r['id']:r for r in main+external};before_plan=requests.digest(requests.canonical(plan))
        names=('main_general','external_native','external_general','repeat_native','repeat_general')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);raw=root/'raw';execution=raw/'execution-v1';execution.mkdir(parents=True)
            path=root/'receipt.json';path.write_bytes(b'{}\n');sha=requests.digest(path.read_bytes())
            operation=deferral.OperationalDeferral(path,sha,{},plan)
            receipt={'historical_accounted_usd':{'openai':'0','typesafe':'0'},'caps_usd':{'openai':'100','typesafe':'100'},
                'incremental_caps_usd':{'openai':'100','typesafe':'100'},
                'allocations_usd':{a:{'openai':'10','typesafe':'10'} for a in names}}
            frozen=budget.policy(receipt['historical_accounted_usd'],receipt['caps_usd'],receipt['incremental_caps_usd'],receipt['allocations_usd'])
            ledger=budget.BudgetLedger(execution/'accounting.jsonl',frozen)
            for a in names:
                ledger.register_schedule(a,[{'group':g['group'],'requests':[budget.reservation(plan['requests'][k]) for k in g['request_keys']]} for g in plan['schedules'][a]])
            batch=ledger.reserve_next_group('main_general');old_unknown=next(k for k in batch['request_keys'] if plan['requests'][k]['config']=='luna_responses')
            ledger.mark_dispatched(old_unknown);ledger.settle(old_unknown,None,evidence_sha256='f'*64)
            original_unknown=ledger.entry(old_unknown);calls=[];materialize=run.materialize
            recover_local=next(k for k in batch['request_keys'] if plan['requests'][k]['config']=='protectai_local')
            ledger.mark_dispatched(recover_local)
            recovered_directory=execution/'attempts'/recover_local;recovered_directory.mkdir(parents=True)
            recovered_bytes=requests.canonical({'request_sha256':plan['requests'][recover_local]['payload_sha256'],
                'namespace':'first','first_attempt_primary':True,'stop_required':False,
                'parsed':{'status':'ok','valid':True,'prediction':1}})
            (recovered_directory/'completed.json').write_bytes(recovered_bytes)
            class Permit:
                operational_deferral=operation
                deferred_configurations=operation.configurations
                execution_profile='cheap-api-sol-subscription'
                allowed_allocations=names
                def check(self):operation.check()
                def admission_open(self):return True
                def check_request(self,record,body):
                    if record['config'] in self.deferred_configurations:raise PermissionError('deferred paid request')
                    if requests.digest(requests.canonical(body))!=record['payload_sha256']:raise ValueError('payload changed')
                def check_dispatch(self,record,body):
                    self.check_request(record,body)
                    if self.ledger.entry(record['key'])['status']!='dispatched':raise ValueError('no dispatch intent')
            permit=Permit();permit.receipt=receipt;permit.manifest={'historical_accounting':{'evidence_sha256':{}}};permit.plan=plan;permit.rows=lookup;permit.phase='confirmation';permit.credential_root=root
            def post(config,body,token,directory):
                self.assertEqual(config,'jev_firstparty');calls.append(directory.name)
                text=json.dumps({'model':'jev-1.14.0','usage':{'input_tokens':10},'answers':{'injection':{'type':'noul','noul':.9}}})
                routes._exclusive(directory/'response.raw',text.encode())
                return {'http_status':200,'transport_exit_code':0},text
            class Local:
                def classify(self,text):return {'score':.9,'windows':1,'input_tokens':5}
            def body(record,rows):
                self.assertNotIn(record['config'],deferral.CONFIGURATIONS)
                self.assertNotEqual(record['key'],recover_local)
                return materialize(record,rows)
            with patch.object(run,'RAW',raw),patch.object(run,'materialize',side_effect=body),patch.object(operation,'verify_evidence'),\
                 patch.object(routes,'_credential',return_value='synthetic-only'),patch.object(routes,'_post',side_effect=post),patch.object(routes,'_LocalRuntime',Local):
                result=run.execute(permit);count=len(calls);again=run.execute(permit)
            self.assertEqual(result['status'],'bounded_phase_finished')
            self.assertEqual(len(calls),count);self.assertEqual(len(calls),len(set(calls)))
            state=again['accounting'];self.assertEqual(state['entries'][old_unknown],original_unknown)
            self.assertEqual(state['schedules']['external_general']['admitted'],0)
            self.assertEqual(state['schedules']['repeat_general']['admitted'],0)
            self.assertEqual(state['schedules']['external_native']['admitted'],1)
            self.assertEqual(state['schedules']['repeat_native']['admitted'],1)
            for key,entry in state['entries'].items():
                if entry['config'] in deferral.CONFIGURATIONS and key!=old_unknown:
                    self.assertEqual(entry['status'],'cancelled_unsent');self.assertEqual(entry['accounted_usd'],'0');self.assertEqual(entry['evidence_sha256'],sha)
            self.assertEqual(requests.digest(requests.canonical(plan)),before_plan)
            self.assertEqual(state['policy'],frozen)

    def test_cancel_refuses_dispatch_intent_and_other_provider_scope(self):
        main,external=fixture_rows();plan=requests.build_plan(main,external,sol_config=None)
        row=next(r for r in plan['requests'].values() if r['config']=='luna_responses')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'receipt';path.write_bytes(b'{}');operation=deferral.OperationalDeferral(path,requests.digest(path.read_bytes()),{},plan)
            ledger=budget.BudgetLedger(root/'journal',budget.policy({'openai':'0','typesafe':'0'},{'openai':'10','typesafe':'10'},
                {'openai':'10','typesafe':'10'},{'development':{'openai':'10','typesafe':'10'}}))
            ledger.reserve_batch('one','development',[budget.reservation(row)]);ledger.mark_dispatched(row['key'])
            with self.assertRaisesRegex(PermissionError,'dispatch intent'):operation.cancel_reserved(ledger,[row['key']])
            self.assertEqual(ledger.entry(row['key'])['status'],'dispatched')
            class WrongProvider:
                def entry(self,key):return {'provider':'typesafe','config':'luna_responses','request_sha256':row['payload_sha256'],'status':'reserved'}
            with self.assertRaises(PermissionError):operation.cancel_reserved(WrongProvider(),[row['key']])
        permit=run.OwnerPermit.__new__(run.OwnerPermit);permit.check=lambda:True;permit.deferred_configurations=deferral.CONFIGURATIONS
        with self.assertRaisesRegex(PermissionError,'operationally deferred'):permit.check_request(row,{})

    def test_exact_credit_evidence_and_full_native_precondition(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);execution=root/'execution';execution.mkdir();journal=execution/'journal';journal.write_bytes(requests.canonical({'kind':'initialize','data':{}})+b'\n')
            stop=execution/'stop.json';stop.write_bytes(b'synthetic immutable stop')
            native=[{'group':'g'+str(i),'request_keys':['n'+str(i)+'-'+str(j) for j in range(16)]} for i in range(3000)]
            state={'entries':{k:{'allocation':'main_native','status':'settled'} for g in native for k in g['request_keys']},
                'schedules':{'main_native':{'admitted':3000,'groups':[{'group':g['group'],'requests':[{'key':k} for k in g['request_keys']]} for g in native]}}}
            plan={'schedules':{'main_native':native},'requests':{}};failures=[]
            for i in range(2):
                key='credit-failure-'+str(i);directory=execution/'attempts'/key;directory.mkdir(parents=True)
                body=b'data: {"type":"error","error":{"type":"insufficient_quota","code":"credit_balance_exhausted"}}\n\n'
                metadata={'request_sha256':'a'*64,'namespace':'first','first_attempt_primary':True,
                    'parsed':{'status':'missing_usage','valid':False,'prediction':None}}
                completed=requests.canonical(metadata);(directory/'completed.json').write_bytes(completed);(directory/'response.raw').write_bytes(body)
                plan['requests'][key]={'config':'luna_responses','namespace':'first','split':'confirmation','payload_sha256':'a'*64}
                state['entries'][key]={'allocation':'main_general','config':'luna_responses','provider':'openai','status':'unknown_usage','evidence_sha256':requests.digest(completed)}
                failures.append({'key':key,'completed_sha256':requests.digest(completed),'response_raw_sha256':requests.digest(body)})
            receipt={'journal_prefix_size_bytes':journal.stat().st_size,'journal_prefix_sha256':requests.digest(journal.read_bytes()),
                'stop_record_name':stop.name,'stop_sha256':requests.digest(stop.read_bytes()),'full_native_groups':3000,'full_native_requests':48000,'failure_evidence':failures}
            path=root/'receipt';path.write_bytes(requests.canonical(receipt));operation=deferral.OperationalDeferral(path,requests.digest(path.read_bytes()),receipt,plan)
            class Ledger:
                path=journal
                def snapshot(self):return state
            operation.verify_evidence(Ledger(),execution)
            state['entries']['allowed-local-after-prefix']={'allocation':'main_general','config':'protectai_local','status':'dispatched'}
            operation.verify_evidence(Ledger(),execution)
            state['entries']['allowed-local-after-prefix']['config']='luna_responses'
            with self.assertRaisesRegex(PermissionError,'deferred paid dispatch intent'):operation.verify_evidence(Ledger(),execution)
            del state['entries']['allowed-local-after-prefix']
            one=native[0]['request_keys'][0];state['entries'][one]['status']='reserved'
            with self.assertRaisesRegex(PermissionError,'all original native'):operation.verify_evidence(Ledger(),execution)
            state['entries'][one]['status']='settled'
            (execution/'attempts'/'credit-failure-0'/'response.raw').write_bytes(b'changed')
            with self.assertRaisesRegex(PermissionError,'evidence changed'):operation.verify_evidence(Ledger(),execution)

    def test_loader_bound_scope_and_receipt_mutation_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);validation=root/'validation.json';validation.write_bytes(b'{}');prior=root/'prior.json';prior.write_bytes(b'prior manifest')
            plan={'requests':{},'schedules':{}};base={'version':deferral.VERSION,'configurations':['luna_decisions','luna_responses'],'provider':'openai','access_route':'api_key','reason_code':'credit_balance_exhausted','plan_sha256':'a'*64,
                'route_validation_sha256':requests.digest(validation.read_bytes()),'prior_manifest_path':prior.name,'prior_manifest_sha256':requests.digest(prior.read_bytes())}
            receipt=root/'deferral.json'
            def load(value,owner_sha=None):
                receipt.write_bytes(requests.canonical(value));sha=requests.digest(receipt.read_bytes())
                manifest={'plan_sha256':'a'*64,'operational_deferral':{'path':receipt.name,'sha256':sha},
                    'route_validation':{'completed':True,'validated_configurations':['luna_decisions','luna_responses','jev_firstparty','protectai_local']},
                    'route_validation_receipt':{'path':validation.name,'sha256':requests.digest(validation.read_bytes())},
                    'previous_confirmation_manifest_sha256':base['prior_manifest_sha256']}
                return deferral.load_deferral(manifest,{'operational_deferral_sha256':owner_sha or sha},plan,root)
            operation=load(base);operation.check()
            for bad in ({'configurations':['jev_firstparty','luna_responses']},{'provider':'typesafe'},{'access_route':'subscription'},
                        {'reason_code':'unsupported_model'},{'plan_sha256':'f'*64}):
                with self.assertRaises(PermissionError):load(base|bad)
            with self.assertRaises(PermissionError):load(base,owner_sha='f'*64)
            operation=load(base);receipt.write_bytes(b'changed')
            with self.assertRaises(PermissionError):operation.check()


if __name__=='__main__':unittest.main()
