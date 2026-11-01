"""Conservative pre-inference family closure; proposals need external agent review."""
import collections,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.study_v5.prepare import ROOT,RAW,OUT,read,rank,Union
from scripts.source_discovery.prepare_review import preserve_write,canonical_bytes,sha256
# Research-agent judgments from all forty task instructions, NOT human annotations.
INFUSE_FAMILIES={
 'path_and_archive_safety':[1,24,29,37], 'dependencies':[3,7],
 'tests_and_test_reports':[5,22,40], 'authentication_and_crypto':[9,18,23,25,26],
 'service_timeout':[12,20], 'input_validation':[30,39],
 'exception_handling':[31,32,33,34,35,38],
}
def family(task):
 n=int(task.split('_')[1])
 return next((k for k,v in INFUSE_FAMILIES.items() if n in v),'task_'+str(n))
def main():
 rows=read(RAW/'prepared-review.jsonl');u=Union(len(rows));seen={};edges=[]
 def link(i,key):
  if key in seen:u.join(i,seen[key]);edges.append({'a':rows[i]['id'],'b':rows[seen[key]]['id'],'reason':key})
  seen[key]=i
 for i,r in enumerate(rows):
  link(i,r['group'])
  if r['source']=='spml':link(i,'spml_domain:'+r['coarse_domain'])
  if r['source']=='infuse':
   task=r['provenance']['pair_id'];link(i,'infuse_family:'+family(task))
   if r['provenance']['attack_id']:link(i,'infuse_attack:'+r['provenance']['attack_id'])
 components=collections.defaultdict(list)
 for i,r in enumerate(rows):components[u.find(i)].append(r)
 for members in components.values():
  gid=min(r['id'] for r in members)
  for r in members:r['split_group']=gid
 summaries={}
 for source in ['aib','spml','infuse']:
  part=[r for r in rows if r['source']==source];gs=sorted({r['split_group'] for r in part},key=rank)
  # SPML domain holdout: substantive domain families, no random policy-row split.
  if source=='spml':dev={r['split_group'] for r in part if r['coarse_domain'] in ['finance','travel']}
  else:dev=set(gs[:max(1,round(.2*len(gs)))])
  for r in part:r['split_proposal']='development' if r['split_group'] in dev else 'confirmation'
  summaries[source]={'split_groups':len(gs),'group_sizes_descending':sorted(collections.Counter(r['split_group'] for r in part).values(),reverse=True),'by_split':{s:{'rows':sum(r['split_proposal']==s for r in part),'groups':len({r['split_group'] for r in part if r['split_proposal']==s}),'upstream_labels':dict(collections.Counter(str(r['upstream_label']) for r in part if r['split_proposal']==s))} for s in ['development','confirmation']}}
 body=b''.join(canonical_bytes(r)+b'\n' for r in rows);preserve_write(RAW/'grouped-review-v2.jsonl',body)
 preserve_write(RAW/'group-edges-v2.jsonl',b''.join(canonical_bytes(e)+b'\n' for e in edges))
 report={'version':'v5-group-proposal-2','input_sha256':sha256((RAW/'prepared-review.jsonl').read_bytes()),'output_sha256':sha256(body),'sources':summaries,'infuse_research_agent_families':INFUSE_FAMILIES,'status':'pre-inference research-agent proposal, awaiting external review','limitations':['AIB lexical components do not certify semantic independence; reviewer must identify shared workflows/templates.','SPML coarse domains are a deliberately conservative split/uncertainty unit; not independently validated original seed lineage.','INFUSE connected components join task families AND reused payload templates; no variant can cross the proposed split.','No selected case has been sent to an evaluation model. No inference eligibility is granted.']}
 preserve_write(OUT/'group-audit.json',json.dumps(report,indent=2,sort_keys=True).encode()+b'\n',raw=False)
 print(json.dumps(summaries))
if __name__=='__main__':main()
