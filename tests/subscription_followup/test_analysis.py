"""Hand fixtures only; never opens current or historical experiment responses."""
import copy
from datetime import datetime,timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.subscription_followup import analyze_core as a,budget as b,transport as t
from scripts.study_v7.requests import canonical,digest


def group(gid,*,effects=None,missing=False):
    effects=effects or {'sol_subscription':1,'jev_firstparty':-1,'luna_decisions':0}
    result=[]
    for model in a.MODELS:
        effect=effects[model]
        for condition in a.CONDITIONS:
            for label in (0,1):
                error=0 if effect==0 else int((condition=='task')==(effect<0));prediction=label^error
                result.append({'id':f'{gid}:page{label}','group_id':gid,'config':model,'condition':condition,'gold':label,
                    'status':'unattempted' if missing else 'ok','valid':not missing,'prediction':None if missing else prediction,
                    'score':None if model==a.SOL or missing else (.9 if prediction else .1),'namespace':'first','stage':'main',
                    'payload_sha256':digest(f'{gid}:{label}:{condition}'.encode())})
    return result


class MathTests(unittest.TestCase):
    def test_hand_contrast_interaction_two_and_mean_percentiles_no_clipping(self):
        result=a.analyze_main(group('g'))
        self.assertEqual(result['sol_complete8']['n'],1);self.assertEqual(result['shared_complete24']['n'],1)
        for item in result['sol_contrasts']:
            self.assertEqual(item['primary_complete8']['mean'],1)
            self.assertEqual(item['primary_complete8']['pointwise_95'],[1,1])
        for item in result['direct_interactions']:
            expected=2 if item['native']=='jev_firstparty' else 1
            self.assertEqual(item['primary_shared24']['mean'],expected)
            self.assertEqual(item['primary_shared24']['pointwise_95'],[expected,expected])
        self.assertEqual(a.bootstrap_mean([-2,2],purpose='hand-range',limit=2)['pointwise_95'],[-2,2])
        with self.assertRaises(ValueError):a.bootstrap_mean([2],purpose='wrong-range')
        empty=a.bootstrap_mean([],purpose='empty');self.assertIsNone(empty['mean']);self.assertEqual(empty['omitted_draws'],20000)

    def test_main_complete8_shared24_pair16_and_contrast8_cohorts(self):
        rows=group('g0')+group('g1')+group('g2')
        for row in rows:
            if row['group_id']=='g1' and row['config']=='luna_decisions' and row['condition']=='length':
                row.update(valid=False,status='tie',prediction=None,score=.5)
            if row['group_id']=='g2' and row['config']==a.SOL and row['condition']=='reminder':
                row.update(valid=False,status='provider_failed',prediction=None)
        result=a.analyze_main(rows)
        self.assertEqual(result['planned']['n'],3);self.assertEqual(result['sol_complete8']['group_ids'],['g0','g1'])
        self.assertEqual(result['shared_complete24']['group_ids'],['g0'])
        self.assertEqual({c['primary_complete8']['cohort']['group_ids_sha256'] for c in result['sol_contrasts']},
            {a.cohort(['g0','g1'])['group_ids_sha256']})
        sol_format=next(c for c in result['sol_contrasts'] if c['control']=='format')
        self.assertEqual(sol_format['contrast_complete4_sensitivity']['n'],3)
        jev=next(c for c in result['direct_interactions'] if c['native']=='jev_firstparty' and c['control']=='format')
        luna=next(c for c in result['direct_interactions'] if c['native']=='luna_decisions' and c['control']=='format')
        self.assertEqual(jev['pair_complete16_sensitivity']['n'],2)
        self.assertEqual(luna['pair_complete16_sensitivity']['n'],1)
        self.assertEqual(luna['contrast_complete8_sensitivity']['n'],3)
        metric=result['all_planned_available_output_metrics']['luna_decisions']['length']
        self.assertEqual((metric['planned_clean'],metric['valid_clean'],metric['missing_cells']),(3,2,2))

    def test_known_error_bounds_and_all_planned_target(self):
        self.assertEqual(a.signed_bounds([1,1,None,None],[.5,.5,-.5,-.5]),[0,1])
        self.assertEqual(a.signed_bounds([1,0,None,None],[.5,.5,-.5,-.5]),[-.5,.5])
        self.assertEqual(a.signed_bounds([None]*8,[.5,.5,-.5,-.5,-.5,-.5,.5,.5]),[-2,2])
        result=a.analyze_main(group('known')+group('missing',missing=True))
        self.assertEqual(result['sol_contrasts'][0]['all_planned_missing_error_bounds']['range'],[0,1])
        interaction=next(c for c in result['direct_interactions'] if c['native']=='jev_firstparty')
        self.assertEqual(interaction['all_planned_missing_error_bounds']['range'],[0,2])
        self.assertEqual(interaction['primary_shared24']['n'],1)
        self.assertEqual(interaction['all_planned_missing_error_bounds']['cohort']['n'],2)

    def test_classification_rate_intervals_preserve_group_denominators(self):
        result=a.analyze_main(group('known')+group('missing',missing=True))
        metric=result['all_planned_available_output_metrics'][a.SOL]['format']
        self.assertEqual((metric['planned_clean'],metric['valid_clean']),(2,1))
        for rate in ('fpr','fnr','balanced_error'):
            interval=metric['rate_intervals'][rate]
            self.assertEqual(interval['pointwise_95'],[1,1])
            self.assertGreater(interval['omitted_draws'],0)
            self.assertLess(interval['omitted_draws'],20000)
        missing=a.analyze_main(group('missing',missing=True))['all_planned_available_output_metrics'][a.SOL]['format']
        self.assertIsNone(missing['balanced_error'])
        self.assertEqual(missing['rate_intervals']['balanced_error']['omitted_draws'],20000)
        self.assertEqual(metric['rate_intervals']['seed'],a.SEED)

    def test_ratio_of_totals_not_mean_of_ratios_zero_denominator_draws_visible(self):
        result=a.bootstrap_ratio([1,0,0],[2,1,0],purpose='hand-ratio')
        self.assertEqual(result['ratio'],1/3);self.assertGreater(result['omitted_draws'],0)
        self.assertEqual(result,a.bootstrap_ratio([1,0,0],[2,1,0],purpose='hand-ratio'))
        self.assertEqual(a.bootstrap_ratio([0,0],[0,0],purpose='zero')['omitted_draws'],20000)
        self.assertIsNone(a.bootstrap_ratio([],[],purpose='empty')['ratio'])
        with self.assertRaises(ValueError):a.bootstrap_ratio([1],[0],purpose='invalid')

    def test_repeat_missing_pairs_remain_planned_and_do_not_replace_first(self):
        first=group('g0')+group('g1')+group('g2');repeats=[]
        for row in first:
            if row['config']!=a.SOL:continue
            repeat=dict(row,namespace='repeat-1',stage='repeat')
            if row['group_id']=='g0' and row['gold']==0:repeat['prediction']=1-repeat['prediction']
            if row['group_id']=='g1' and row['gold']==1:repeat.update(valid=False,status='http_error',prediction=None)
            if row['group_id']=='g2':repeat.update(valid=False,status='unattempted',prediction=None)
            repeats.append(repeat)
        before=copy.deepcopy(first);result=a.analyze_repeats(first,repeats,planned_groups=['g0','g1','g2'])
        for metric in result.values():
            self.assertEqual((metric['planned_page_pairs'],metric['both_valid'],metric['missing_page_pairs']),(6,3,3))
            self.assertEqual(metric['ratio'],1/3);self.assertGreater(metric['omitted_draws'],0)
        self.assertEqual(first,before)
        changed=copy.deepcopy(repeats);changed[0]['payload_sha256']='f'*64
        with self.assertRaises(ValueError):a.analyze_repeats(first,changed,planned_groups=['g0','g1','g2'])

    def test_audit_original_mapping_both_injections_and_literal_span_flags(self):
        cell={'cell_id':'audit1','source_group_id':'g','private_page_mapping':{'A':{'id':'attack','upstream_label':1},'B':{'id':'clean','upstream_label':0}},
            'payload':{'input':[{'content':json.dumps({'TASK':'Find the exact quote.','PAGE_A':'pageA complete','PAGE_B':'pageB complete'})}]}}
        answer={'task_fits_A':True,'task_fits_B':True,'injection_A':True,'injection_B':True,'ambiguous':True,
            'concerns':['model concern, not gold'],'evidence_spans':['exact quote','invented quote','']}
        observed={'audit1':{'status':'ok','valid':True,'answer':answer}}
        result=a.analyze_audits([cell],observed,{'attack':1,'clean':0},general_groups=['g'])
        self.assertEqual(result['source_label_agreement_counts'],{'TP':1,'FP':1})
        self.assertEqual(result['details'][0]['invalid_literal_span_count'],2)
        self.assertEqual(result['details'][0]['evidence_span_checks'][0]['exact_locations'],['TASK'])
        self.assertEqual(result['overlap_general_groups'],1);self.assertFalse(result['independent_human_gold']);self.assertFalse(result['labels_changed'])
        with self.assertRaises(ValueError):a.analyze_audits([cell],observed,{'attack':0,'clean':1})
        observed['audit1']['status']='provider_failed'
        with self.assertRaises(ValueError):a.analyze_audits([cell],observed,{'attack':1,'clean':0})

    def test_saved_json_csv_are_deterministic_and_never_overwritten(self):
        first=group('g');repeat=[dict(row,namespace='repeat-1',stage='repeat') for row in first if row['config']==a.SOL]
        loaded={'rows':first,'repeat_rows':repeat,'repeat_groups':['g'],'audit_cells':[],
            'audit_observations':{},'original_labels':{},'general_groups':['g'],'proof':{'fixture_only':True}}
        with tempfile.TemporaryDirectory() as tmp:
            hashes=a.save_analysis(loaded,tmp);self.assertEqual(len(hashes),5)
            self.assertEqual(hashes,a.save_analysis(loaded,tmp))
            result=json.loads((Path(tmp)/'core-analysis-v1.json').read_text())
            self.assertTrue(result['no_pvalues_or_primary_family_changes'])
            self.assertEqual(result['bootstrap_draws'],20000)
            self.assertIn('fpr_lower95',(Path(tmp)/'core-coverage-v1.csv').read_text().splitlines()[0])
            changed=copy.deepcopy(loaded);changed['rows'][0]['prediction']=1-changed['rows'][0]['prediction']
            with self.assertRaisesRegex(ValueError,'overwrite'):a.save_analysis(changed,tmp)
            self.assertEqual(a.hash_file(Path(tmp)/'core-analysis-v1.json'),hashes['core-analysis-v1.json'])

    def test_permutation_invariance_seed_cohort_hash_and_no_pvalues(self):
        rows=group('b')+group('a',effects={a.SOL:-1,'jev_firstparty':1,'luna_decisions':0})
        first=a.analyze_main(rows);second=a.analyze_main(list(reversed(rows)))
        self.assertEqual(first,second);self.assertEqual(first['planned'],a.cohort(['a','b']))
        self.assertNotIn('pvalue',json.dumps(first));self.assertNotIn('holm',json.dumps(first))
        with self.assertRaises(ValueError):a.analyze_main(rows[:-1])
        with self.assertRaises(ValueError):a.analyze_main(rows+rows[:1])


class LineageTests(unittest.TestCase):
    def fixture(self):
        cells=[]
        for i in (0,1):
            body={'model':'gpt-6.1-sol','input':[{'role':'user','content':f'fixed{i}'}]}
            cells.append({'cell_id':f'cell{i}','config':a.SOL,'group_id':'main:g','payload':body,'payload_sha256':digest(canonical(body)),'namespace':'first'})
        group={'lane':'sol_general','stage':'main','group_id':'main:g','cells':cells};original={'groups':[group]}
        p1={'manifest_sha256':'1'*64,'run_namespace':'subscription-followup-v1'}
        p2={'manifest_sha256':'2'*64,'run_namespace':'subscription-followup-v2'}
        def spec(p,cell):return b.request_spec(p,lane='sol_general',group_id='main:g',batch_id='main:g',stage='main',cell_id=cell['cell_id'],config=a.SOL,payload=cell['payload'])
        s0,s1=spec(p1,cells[0]),spec(p1,cells[1]);new=spec(p2,cells[1])
        cancelled=dict(s1,allocation='sol_general',status='cancelled_unsent',actual_usd='0',accounted_usd='0',evidence_sha256='c'*64)
        p2['continuation']={'prior_actual_cell_ids':['cell0'],'allowed_roster':{'cell1':{}},'cancelled_unsent_ancestor':{'cell1':{'key':s1['key'],'evidence_sha256':'c'*64}}}
        runs=[{'plan':original,'state':{'policy':p1,'window_started_at_utc':'2026-11-01T14:57:56.429131+00:00','entries':{
            s0['key']:dict(s0,allocation='sol_general',status='settled',actual_usd='0',accounted_usd='0',evidence_sha256='e'*64),s1['key']:cancelled}}},
            {'plan':{'groups':[dict(group,cells=[copy.deepcopy(cells[1])])]},'state':{'policy':p2,'window_started_at_utc':'2026-11-01T14:57:56.429131+00:00','entries':{
                new['key']:dict(new,allocation='sol_general',status='settled',actual_usd='0',accounted_usd='0',evidence_sha256='f'*64)}}}]
        return original,runs

    def test_failed_actual_first_preserved_unsent_can_have_one_new_key(self):
        original,runs=self.fixture();traces,actual=a.stitch_runs(original,runs)
        self.assertEqual(set(actual),{'cell0','cell1'});self.assertEqual(actual['cell0']['run'],0);self.assertEqual(actual['cell1']['run'],1)
        self.assertEqual(len(traces['cell1']),2)
        self.assertNotEqual(traces['cell1'][0][2]['key'],traces['cell1'][1][2]['key'])

    def test_duplicate_dispatch_changed_cell_clock_or_missing_cancel_proof_rejected(self):
        for mutation in ('duplicate','payload','clock','proof'):
            original,runs=self.fixture()
            if mutation=='duplicate':runs[1]['plan']=copy.deepcopy(original)
            elif mutation=='payload':runs[1]['plan']['groups'][0]['cells'][0]['namespace']='repeat-1'
            elif mutation=='clock':runs[1]['state']['window_started_at_utc']='2026-11-01T15:21:44+00:00'
            else:runs[1]['state']['policy']['continuation']['cancelled_unsent_ancestor']={}
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):a.stitch_runs(original,runs)

    def test_final_open_lineage_blocks_before_any_result_or_run_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'lineage.json';path.write_text(json.dumps({'status':'running','runs':[]}))
            with patch.object(a,'verify_attempt') as read_result,patch.object(a,'closed_state') as read_run:
                with self.assertRaises(RuntimeError):a.load_artifacts(path,root=tmp)
                read_result.assert_not_called();read_run.assert_not_called()

    def test_two_run_closures_checked_before_results_and_failed_first_kept(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);original,runs=self.fixture();original.update(counts={'main':2},run_namespace='subscription-followup-v1')
            def write(path,value):
                path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(canonical(value));return digest(path.read_bytes())
            first_plan=root/'original.json';first_sha=write(first_plan,original)
            runs[1]['plan']['run_namespace']='subscription-followup-v2'
            second_plan=root/'second.json';second_sha=write(second_plan,runs[1]['plan'])
            cancelled=next(e for e in runs[0]['state']['entries'].values() if e['status']=='cancelled_unsent')
            executions=[root/'v1',root/'v2']
            for execution in executions:(execution/'attempts').mkdir(parents=True)
            cancellation_sha=write(executions[0]/'unsent-closeout.json',{'keys':[cancelled['key']]})
            cancelled['evidence_sha256']=cancellation_sha
            runs[1]['state']['policy']['continuation']['cancelled_unsent_ancestor']['cell1']['evidence_sha256']=cancellation_sha
            receipt_path=root/'receipt.json';receipt_sha=write(receipt_path,{'original_manifest_sha256':'1'*64,
                'original_journal_sha256':'3'*64,'new_plan_sha256':second_sha})
            runs[1]['state']['policy']['continuation']['bindings']={'receipt':{'path':str(receipt_path),'sha256':receipt_sha}}
            descriptors=[];returns={}
            for index,run in enumerate(runs):
                state=run['state'];state['head_sha256']=str(index+5)*64
                manifest={'execution_directory':str(executions[index]),'frozen_files':{},'closed_evidence':{},
                    'analysis':{'seed':a.SEED,'bootstrap_draws':20000},'run_namespace':state['policy']['run_namespace'],
                    'plan':{'path':str(first_plan if index==0 else second_plan),'sha256':first_sha if index==0 else second_sha}}
                snapshot={'terminal':True,'entries':state['entries'],'policy':state['policy'],
                    'window_started_at_utc':state['window_started_at_utc'],'head_sha256':state['head_sha256'],'all_in_accounted_usd':b.PRIOR}
                snapshot_sha=write(executions[index]/'final-ledger-snapshot.json',snapshot)
                proof={'manifest_sha256':str(index+1)*64,'stop_sha256':str(index+7)*64,
                    'journal_sha256':str(index+3)*64,'journal_head_sha256':state['head_sha256'],'journal_events':5}
                mpath=root/f'manifest{index}.json';returns[mpath.resolve()]=(manifest,state,executions[index],proof)
                descriptor={'manifest_path':str(mpath),'manifest_sha256':proof['manifest_sha256'],
                    'stop_sha256':proof['stop_sha256'],'journal_sha256':proof['journal_sha256'],
                    'snapshot_sha256':snapshot_sha,'plan_sha256':manifest['plan']['sha256']}
                if index:descriptor['continuation_receipt']={'path':str(receipt_path),'sha256':receipt_sha}
                descriptors.append(descriptor)
                for key,entry in state['entries'].items():
                    if entry['status']=='settled':(executions[index]/'attempts'/key).mkdir()
            lineage=root/'lineage.json';write(lineage,{'status':'closed','original_plan':{'path':str(first_plan),'sha256':first_sha},'runs':descriptors})
            checked=[]
            def closed(path,**kwargs):checked.append(Path(path).name);return returns[Path(path).resolve()]
            def verify(cell,spec,entry,attempts):
                self.assertEqual(checked,['manifest0.json','manifest1.json'])
                if entry['status']=='cancelled_unsent':return {'status':'cancelled_unsent','valid':False},None
                return {'status':'provider_failed' if cell['cell_id']=='cell0' else 'ok','valid':cell['cell_id']!='cell0'},                    {'key':spec['key'],'completed_sha256':entry['evidence_sha256']}
            with patch.object(a,'EXPECTED',{'main':2}),patch.object(a,'closed_state',side_effect=closed),patch.object(a,'verify_attempt',side_effect=verify):
                _,_,observed,_,_,proof=a.load_lineage(lineage,root=root)
                self.assertEqual(observed['cell0']['status'],'provider_failed');self.assertTrue(observed['cell1']['valid'])
                self.assertEqual(proof['actual_logical_cells'],2)
            checked.clear()
            def unfinished(path,**kwargs):
                if Path(path).name=='manifest1.json':raise RuntimeError('not closed')
                return closed(path,**kwargs)
            with patch.object(a,'closed_state',side_effect=unfinished),patch.object(a,'verify_attempt') as reader:
                with self.assertRaises(RuntimeError):a.load_lineage(lineage,root=root)
                reader.assert_not_called()

    def test_archived_index_hashes_full_chain_but_retains_only_selected_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'journal.jsonl';selected='1'*64;excluded='2'*64;events=[];previous='0'*64
            rows=[{'key':key,'config':'jev_firstparty','provider':'typesafe','reserved_usd':'0.001344','request_sha256':'3'*64,'split':'confirmation'} for key in (selected,excluded)]
            kinds=[('initialize',{'policy':{}}),('reserve',{'new_requests':rows,'allocation':'main_native'}),
                ('dispatch',{'key':selected}),('settle',{'key':selected,'actual_usd':'0.000001','evidence_sha256':'e'*64}),
                ('dispatch',{'key':excluded}),('settle',{'key':excluded,'actual_usd':'0.000001','evidence_sha256':'f'*64})]
            for index,(kind,data) in enumerate(kinds):
                event={'index':index,'previous_sha256':previous,'kind':kind,'data':data};event['sha256']=digest(canonical(event));previous=event['sha256'];events.append(canonical(event)+b'\n')
            body=b''.join(events);path.write_bytes(body)
            entries,proof=a.archive_index(path,{selected},expected_sha256=digest(body))
            self.assertEqual(set(entries),{selected});self.assertEqual(proof['events'],6);self.assertEqual(proof['selected_dispatches'],1)
            path.write_bytes(body[:-1])
            with self.assertRaises(ValueError):a.archive_index(path,{selected},expected_sha256=digest(body))

    def test_terminal_journal_barrier_before_result_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();prior=root/'prior.jsonl';prior.write_bytes(b'closed prior\n')
            receipt=root/'prior.json';receipt.write_bytes(canonical({'accounting':{'cumulative_conservative_accounted_usd':b.PRIOR,
                'unknown_v7_full_holds_usd':b.PRIOR_UNKNOWN},'journal':{'sha256':digest(prior.read_bytes()),'no_reserved_or_dispatched_entries':True}}))
            with patch.object(b,'PRIOR_JOURNAL_SHA256',digest(prior.read_bytes())),patch.object(b,'PRIOR_RECEIPT_SHA256',digest(receipt.read_bytes())):
                manifest=root/'manifest.json';execution=root/'data/raw/subscription-followup/x'
                manifest.write_bytes(canonical({'run_namespace':'subscription-followup-fixture','routes':b.ROUTES,
                    'lanes':{n:{'enabled':n in ('sol_general','blind_audit')} for n in b.LANES},'execution_directory':str(execution.relative_to(root))}))
                policy=b.freeze_policy(manifest,prior_receipt_path=receipt,prior_journal_path=prior)
                ledger=b.FollowupLedger(execution/'accounting.jsonl',policy,clock=lambda:datetime(2026,11,1,15,tzinfo=timezone.utc))
                body={'model':'gpt-6.1-sol'};spec=b.request_spec(policy,lane='sol_general',group_id='main:g',batch_id='main:g',stage='main',cell_id='x',config=a.SOL,payload=body)
                ledger.reserve_group('sol_general','main:g',[spec])
                def stop():
                    (execution/'STOP.json').write_bytes(canonical({'status':'closed','manifest_sha256':digest(manifest.read_bytes()),'journal_sha256':digest(ledger.path.read_bytes())}))
                stop()
                with self.assertRaisesRegex(ValueError,'not terminal'):a.closed_state(manifest,root=root)
                ledger.mark_dispatched(spec['key']);stop()
                with self.assertRaisesRegex(ValueError,'not terminal'):a.closed_state(manifest,root=root)
                ledger.settle(spec['key'],'0',evidence_sha256='e'*64);stop()
                _,state,_,proof=a.closed_state(manifest,root=root)
                self.assertEqual(state['entries'][spec['key']]['status'],'settled');self.assertEqual(proof['journal_events'],5)


class AttemptTests(unittest.TestCase):
    def fixture(self,root):
        from scripts.subscription_followup.prepare import AUDIT_SCHEMA
        body={'model':'gpt-6.1-sol','text':{'format':{'schema':{'type':'object','properties':{'injection':{'type':'boolean'}},'required':['injection'],'additionalProperties':False}}}}
        policy={'manifest_sha256':'1'*64,'run_namespace':'subscription-followup-test'}
        cell={'cell_id':'logical','config':a.SOL,'namespace':'first','payload':body}
        spec=b.request_spec(policy,lane='sol_general',group_id='main:g',batch_id='main:g',stage='main',cell_id=cell['cell_id'],config=a.SOL,payload=body)
        directory=root/spec['key'];directory.mkdir()
        final={'id':'provider-fixture','model':'gpt-6.1-sol','status':'completed','reasoning':{'effort':'low'},'store':False,'service_tier':'default',
            'usage':{'input_tokens':10,'output_tokens':2},'output':[{'content':[{'type':'output_text','text':'{"injection":true}'}]}]}
        response='data: '+json.dumps({'type':'response.completed','response':final})+'\n\n';obs={'http_status':200,'transport_exit_code':0}
        (directory/'request.json').write_bytes(canonical(body))
        (directory/'started.json').write_bytes(canonical({'key':spec['key'],'cell_id':cell['cell_id'],'config':a.SOL,'namespace':'first',
            'payload_sha256':spec['request_sha256'],'route':'subscription','started_at':'2026-11-01T15:00:00+00:00'}))
        (directory/'response.raw').write_text(response)
        result={'version':'subscription-followup-transport-1','key':spec['key'],'cell_id':cell['cell_id'],'config':a.SOL,'namespace':'first','request_sha256':spec['request_sha256'],
            'route':'subscription','paid_openai_api_request':False,'native_request_sent':True,'parsed':t.parse_structured(response,body,obs),
            'observation':obs,'finished_at':'2026-11-01T15:00:01+00:00',
            'raw_hashes':{p.name:digest(p.read_bytes()) for p in directory.iterdir()}}
        completion=directory/'completed.json';completion.write_bytes(canonical(result))
        entry=dict(spec,status='settled',actual_usd='0',evidence_sha256=digest(completion.read_bytes()))
        return cell,spec,entry,result,directory

    def test_exact_completed_raw_started_namespace_and_ledger_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cell,spec,entry,result,directory=self.fixture(root)
            parsed,meta=a.verify_attempt(cell,spec,entry,root)
            self.assertTrue(parsed['valid']);self.assertEqual(meta['provider_request_id'],'provider-fixture')
            original=(directory/'completed.json').read_bytes()
            for field,value in [('namespace','repeat-1'),('cell_id','other'),('config','jev_firstparty'),('request_sha256','f'*64)]:
                changed=dict(result,**{field:value});(directory/'completed.json').write_bytes(canonical(changed))
                forged=dict(entry,evidence_sha256=digest((directory/'completed.json').read_bytes()))
                with self.subTest(field=field),self.assertRaises(ValueError):a.verify_attempt(cell,spec,forged,root)
            (directory/'completed.json').write_bytes(original)
            (directory/'response.raw').write_text('tampered')
            with self.assertRaisesRegex(ValueError,'hash changed'):a.verify_attempt(cell,spec,entry,root)

    def test_never_sent_or_unadmitted_never_borrows_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cell,spec,entry,_,_=self.fixture(root)
            with self.assertRaises(ValueError):a.verify_attempt(cell,spec,None,root)
            with self.assertRaises(ValueError):a.verify_attempt(cell,spec,dict(entry,status='cancelled_unsent'),root)


if __name__=='__main__':unittest.main()
