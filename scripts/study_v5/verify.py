"""Offline consistency verifier; --require-cache adds exact source/payload checks."""
import argparse,collections,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.study_v5.prepare import ROOT,RAW,OUT,read,wrap,place
from scripts.study_v5.prompts import conditions,evidence
from scripts.source_discovery.prepare_review import sha256

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--require-cache',action='store_true');args=ap.parse_args()
 prep=json.loads((OUT/'preparation.json').read_text());group=json.loads((OUT/'group-audit.json').read_text());scope=json.loads((OUT/'scope-pairs.json').read_text());cost=json.loads((OUT/'feasibility.json').read_text());tokens=json.loads((OUT/'token-audit.json').read_text())
 assert prep['prepared_rows']==428 and scope['rows']==48
 assert prep['semantic_gold_assigned']==prep['agent_reviews_completed']==prep['inference_eligible']==0
 assert sum(sum(v['rows'] for v in s['by_split'].values()) for s in group['sources'].values())==428
 assert cost['new_inference_spend_usd']==0 and not cost['accounting']['is_provider_balance']
 assert tokens['audited_payloads']==3268 and tokens['truncated_payloads']==0
 checked=0
 if args.require_cache:
  for r in json.loads((OUT/'source-receipts.json').read_text())['files']+prep['infuse']['static_file_receipts']:
   p=ROOT/r['cache'];b=p.read_bytes();assert sha256(b)==r['sha256'] and len(b)==r['bytes'];checked+=1
  rows=read(RAW/'grouped-review-v2.jsonl')+read(RAW/'scope-pairs.jsonl');assert len(rows)==476
  assert sha256((RAW/'grouped-review-v2.jsonl').read_bytes())==group['output_sha256']
  assert sha256((RAW/'scope-pairs.jsonl').read_bytes())==scope['raw_sha256']
  for name,receipt in prep['review_artifacts'].items():
   b=(RAW/name).read_bytes();assert sha256(b)==receipt['sha256'] and len(b)==receipt['bytes']
  audit=json.loads((OUT/'source-code-audit.json').read_text())
  assert sha256((RAW/'aib-seed-links-v2.json').read_bytes())==audit['aib']['links_sha256']
  for receipt in audit['inputs']:assert sha256((ROOT/receipt['path']).read_bytes())==receipt['sha256']
  aib={r['source']['row_id']:r for r in read(ROOT/'data/raw/source-discovery/aib-review-v1.jsonl')}
  spml={str(r['source']['row_number_1based']):r for r in read(ROOT/'data/raw/source-discovery/spml-review-v1.jsonl')}
  for r in rows:
   assert r['semantic_gold'] is None and not r['inference_eligible']
   if r['source']=='aib':
    orig=aib[r['id'].split(':')[1]]['detector_payload'];assert r['candidate']==orig['source_conversation_inputs'][1]['content'];assert r['task']==orig['actual_user_task'] and r['policy']==orig['trusted_policy']
   if r['source']=='spml':
    orig=spml[r['id'].split(':')[1]]['detector_payload'];assert r['candidate']==orig['submitted_user_prompt'] and r['policy']==orig['trusted_policy'] and r['task'] is None
   for c in conditions(r):assert evidence(r,c).get('CANDIDATE',evidence(r,c).get('USER_MESSAGE'))==r['candidate']
  for source in ['aib','spml','infuse','scope']:
   part=[r for r in rows if r['source']==source];dev={r['split_group'] for r in part if r['split_proposal']=='development'};test={r['split_group'] for r in part if r['split_proposal']=='confirmation'};assert not dev&test
  inf=[r for r in rows if r['source']=='infuse'];by=collections.defaultdict(list)
  for r in inf:by[r['provenance']['pair_id']].append(r)
  attack_splits=collections.defaultdict(set)
  import tomllib
  for pair in by.values():
   clean=next(r for r in pair if r['upstream_label']==0);attack=next(r for r in pair if r['upstream_label']==1);pr=attack['provenance'];a=tomllib.loads((RAW/'infuse'/pr['attack_config']).read_text())['attack']
   original=(RAW/'infuse'/pr['candidate_path']).read_text();assert original==clean['candidate']
   payload=a['target'].get('inject_prefix','')+a['payload']['template'];assert attack['candidate']==place(original,wrap(pr['candidate_path'],payload),a['target'].get('inject_position','append'))
   assert clean['split_proposal']==attack['split_proposal'];attack_splits[pr['attack_id']].add(attack['split_proposal'])
  assert all(len(v)==1 for v in attack_splits.values())
  for name in ['review-packet','scope-review-packet']:
   for r in read(RAW/(name+'.jsonl')):assert set(r)=={'review_id','setting','task','policy','candidate'}
  assert sha256((RAW/'token-audit.jsonl').read_bytes())==tokens['audit_sha256']
 print(json.dumps({'status':'pass','cache_required':args.require_cache,'source_files_checked':checked,'source_review_rows':428,'constructed_review_rows':48,'no_semantic_gold_or_inference_admission':True}))
if __name__=='__main__':main()
