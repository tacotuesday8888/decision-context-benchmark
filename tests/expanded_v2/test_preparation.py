import copy,json,math,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/expanded_v2'))
from common import DATA,OUT,sha,jsonl
from prepare import validate,similar
from panel import PANEL
from adapters import request,state,parse,probability,windows,paid_execute


def stream(response,kind='response.completed'):
    return 'data: '+json.dumps({'type':kind,'response':response})+'\n\n'


class DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.rows=jsonl(DATA/'collection.jsonl')
    def test_collection_counts_and_split_validation(self):
        summary=validate(self.rows)
        self.assertEqual(summary['distinct_candidates'],{'dev':60,'eval':402})
        self.assertEqual(summary['available_condition_cells'],{'dev':120,'eval':812})
        self.assertEqual(summary['unique_trusted_tasks'],{'dev':29,'eval':131})
    def test_published_assembly_is_exact_and_attributed(self):
        pairs={}
        for r in self.rows:
            if r['dataset'].startswith('bipia-'):pairs.setdefault(r['groups']['document'],{})[r['gold']]=r
        self.assertEqual(len(pairs),170)
        for members in pairs.values():
            self.assertEqual(set(members),{0,1})
            clean=members[0]['candidate'];injected=members[1]['candidate'];source=members[1]['source']
            if source['position']=='start':
                self.assertTrue(injected.endswith('\n'+clean));attack=injected[:-len(clean)-1]
            else:
                self.assertTrue(injected.startswith(clean+'\n'));attack=injected[len(clean)+1:]
            self.assertEqual(sha(attack),source['attack_sha256'])
    def test_unsupported_context_is_never_fabricated(self):
        for row in self.rows:
            if row['dataset'].startswith('bipia-') or row['dataset'] in ['llmail-task3','llmail-task4']:
                self.assertEqual(row['conditions'],['candidate','task'])
                with self.assertRaises(ValueError):state(row,'source')
            if row['dataset']=='llmail-benign-stress':
                self.assertEqual(row['conditions'],['candidate']);self.assertIsNone(row['trusted_task'])
    def test_pilot_candidates_and_teams_excluded(self):
        pilot=jsonl(ROOT/'data/pilot.jsonl');hashes={r['candidate_sha256'] for r in pilot};teams={r.get('source_team') for r in pilot}
        for row in self.rows:
            self.assertNotIn(row['candidate_sha256'],hashes)
            if row['source'].get('team_id'):self.assertNotIn(row['source']['team_id'],teams)
    def test_leakage_mutations_fail(self):
        rows=copy.deepcopy(self.rows)
        rows[0]['groups']['document']=next(r['groups']['document'] for r in rows if r['split']=='eval' and 'document' in r['groups'])
        with self.assertRaises(ValueError):validate(rows)
        with self.assertRaises(ValueError):validate(self.rows+[self.rows[0]])
    def test_manifest_and_requests_are_traceable(self):
        m=json.loads((DATA/'manifest.json').read_text())
        self.assertEqual(m['collection_sha256'],sha((DATA/'collection.jsonl').read_bytes()))
        sources=json.loads((DATA/'sources.json').read_text())['sources']
        for row in self.rows:self.assertIn(row['source']['file'],sources)
        plan=json.loads((OUT/'request-plan.json').read_text());lookup={r['id']:r for r in self.rows}
        self.assertEqual(len(plan['requests']),4190)
        for job in plan['requests']:
            payload=request(job['config'],lookup[job['id']],job['condition'])
            self.assertEqual(job['request_sha256'],sha(json.dumps(payload,ensure_ascii=False,sort_keys=True)))
    def test_metadata_cannot_enter_model_state(self):
        for row in self.rows:
            d=json.loads(state(row,'candidate'));self.assertEqual(set(d),{'CANDIDATE'})
            self.assertEqual(d['CANDIDATE'],row['candidate'])
    def test_lexical_near_document_filter(self):
        self.assertTrue(similar('a b c d e f g h','a b c d e f g h'))
        self.assertFalse(similar('a b c d e f','completely unrelated material'))


class AdapterTests(unittest.TestCase):
    def test_invalid_scores_and_ties(self):
        for p in [True,'0.5',float('nan'),float('inf'),-1,1.1]:
            with self.assertRaises(ValueError):probability(p)
        self.assertEqual(probability(.5)['status'],'tie')
        self.assertIsNone(probability(.5)['prediction'])
    def test_incomplete_budget_is_not_semantic_error(self):
        body=stream({'status':'incomplete','model':'gpt-6-astra','usage':{'output_tokens':2048},
            'incomplete_details':{'reason':'max_output_tokens'}},'response.incomplete')
        r=parse('astra_chat',body);self.assertEqual(r['status'],'truncated');self.assertFalse(r['valid'])
        self.assertIsNone(r['prediction']);self.assertEqual(r['usage']['output_tokens'],2048)
    def test_strict_chat_output_and_refusal(self):
        for text,valid in [('{"injection":true}',True),('{"injection":1}',False),('{"injection":false,"extra":1}',False),('YES',False)]:
            body=stream({'status':'completed','model':'gpt-6-luna','output':[{'content':[{'type':'output_text','text':text}]}]})
            self.assertEqual(parse('luna_chat',body)['valid'],valid)
        body=stream({'status':'completed','model':'gpt-6-luna','output':[{'content':[{'type':'refusal','refusal':'cannot answer'}]}]})
        self.assertEqual(parse('luna_chat',body)['status'],'refusal')
    def test_different_model_and_interrupted_stream(self):
        body=stream({'status':'completed','model':'gpt-6-luna-alias','output':[]})
        self.assertEqual(parse('luna_chat',body)['status'],'model_mismatch')
        self.assertEqual(parse('luna_chat','data: [DONE]\n\n')['status'],'interrupted_stream')
    def test_native_decision_shapes(self):
        self.assertEqual(parse('jev_firstparty',json.dumps({'model':'jev-1.14.0','answers':{'injection':{'noul':.9}}}))['prediction'],1)
        self.assertEqual(parse('luna_decisions',json.dumps({'model':'gpt-6-luna','answers':[{'name':'injection','type':'predicate','probability':.1}]}))['prediction'],0)
    def test_windows_cover_all_tokens_and_overlap(self):
        ids=list(range(1600));parts=list(windows(ids))
        self.assertTrue(all(len(p)<=510 for p in parts))
        self.assertEqual(set(sum(parts,[])),set(ids))
        for a,b in zip(parts,parts[1:]):self.assertEqual(a[-64:],b[:64])
        with self.assertRaises(ValueError):list(windows(ids,510,510))
    def test_paid_execution_blocked_and_local_condition_not_duplicated(self):
        with self.assertRaises(PermissionError):paid_execute()
        row=jsonl(DATA/'collection.jsonl')[0]
        with self.assertRaises(ValueError):request('protectai_local',row,'task')
        self.assertEqual(len({p['model'] for p in PANEL.values()}),4)

if __name__=='__main__':unittest.main()

class EvidenceTests(unittest.TestCase):
    def test_saved_development_is_not_evaluation(self):
        rows={r['id']:r for r in jsonl(DATA/'collection.jsonl')}
        records=[json.loads(p.read_text()) for p in (OUT/'development').glob('*.json')]
        self.assertEqual(len(records),12)
        for r in records:
            self.assertEqual(rows[r['id']]['split'],'dev')
            self.assertEqual(r['paid_requests'],0)
            self.assertTrue(parse(r['config'],r['raw_body'])['valid'])
    def test_real_development_includes_long_windows(self):
        d=json.loads((OUT/'local-window-development.json').read_text())
        self.assertEqual(len(d['records']),2)
        for r in d['records']:
            self.assertGreater(r['result']['input_tokens'],512)
            self.assertGreater(r['result']['windows'],1)
    def test_non_budget_incomplete_is_not_called_truncation(self):
        body=stream({'status':'incomplete','model':'gpt-6-luna','incomplete_details':{'reason':'content_filter'}},'response.incomplete')
        self.assertEqual(parse('luna_chat',body)['status'],'provider_incomplete')
