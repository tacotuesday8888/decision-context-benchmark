"""Recompute bounded construction-code findings using inert data only.

Run with the existing .venv Python (PyYAML). Never import upstream source code.
"""
import collections,json,sys,tomllib
from pathlib import Path
import yaml
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.study_v5.prepare import ROOT,RAW,OUT,read,norm,shingles
from scripts.source_discovery.prepare_review import preserve_write,sha256

def input_key(messages):
 return tuple((m['role'],m.get('content',''),m.get('tool')) for m in messages if m['role'] in ['user','tool_result'])

def main():
 seeds=[];files=sorted((RAW/'aib/generation/templates').glob('*.yaml'))
 for path in files:
  data=yaml.safe_load(path.read_text())
  for seed in data['seeds']:
   messages=seed.get('conversation')
   if messages is None:
    messages=[{'role':'user','content':seed.get('user_message','')},{'role':'tool_result','tool':(seed.get('tools',[{}])[0] or {}).get('name','tool'),'content':seed.get('injected_tool_output','')}]
   seeds.append((input_key(messages),seed['id'],data['category']))
 rows=read(ROOT/'data/raw/source-discovery/aib-cases.jsonl');links=[]
 for row in rows:
  for key,sid,category in seeds:
   if input_key(row['conversation'])==key:links.append({'id':row['id'],'seed_id':sid,'category':category})
 body=(json.dumps(links,indent=2)+'\n').encode()
 preserve_write(RAW/'aib-seed-links-v2.json',body)
 configs=[tomllib.loads(p.read_text())['attack'] for p in sorted((RAW/'infuse/benchmark/attacks').glob('*/config.toml'))]
 report={'version':'v5-source-code-audit-1','executed_upstream_code':False,'aib':{'yaml_files':len(files),'seed_entries':len(seeds),'released_rows':len(rows),'exact_input_message_links':len(links),'matched_release_rows':len({r['id'] for r in links}),'unmatched_release_rows':len(rows)-len({r['id'] for r in links}),'links_sha256':sha256(body),'matching_rule':'Exact user/tool_result role, content and tool sequence; assistant reference replies excluded; not proof of independent authorship or template families.'},'infuse':{'attack_configs':len(configs),'positions':dict(collections.Counter(a['target'].get('inject_position','append') for a in configs))},'inputs':[{'path':str(p.relative_to(ROOT)),'sha256':sha256(p.read_bytes())} for p in files]+[{'path':'data/raw/source-discovery/aib-cases.jsonl','sha256':sha256((ROOT/'data/raw/source-discovery/aib-cases.jsonl').read_bytes())}]}
 preserve_write(OUT/'source-code-audit.json',json.dumps(report,indent=2,sort_keys=True).encode()+b'\n',raw=False)
 # Source-pair overlap supplements historical exposure screening. A zero lexical
 # match count cannot certify independence from common semantic templates.
 selected=read(RAW/'grouped-review-v2.jsonl')+read(RAW/'scope-pairs.jsonl')
 features=[(norm(r['candidate']),norm(r['task']),shingles(r['candidate'])) for r in selected]
 hits=[];compared=0
 for i,a in enumerate(selected):
  for j,b in enumerate(selected[:i]):
   if a['source']==b['source']:continue
   compared+=1;ac,at,ash=features[i];bc,bt,bsh=features[j];flags=[]
   if ac==bc:flags.append('normalized_candidate_match')
   if at and at==bt:flags.append('normalized_task_match')
   if min(len(ash),len(bsh))>=10 and len(ash&bsh)/len(ash|bsh)>=.5:flags.append('candidate_jaccard_ge_0.5')
   if flags:hits.append({'a':a['id'],'b':b['id'],'flags':flags})
 overlap={'version':'v5-cross-source-overlap-1','rows':len(selected),'cross_source_pairs_compared':compared,'hits':hits,'threshold':.5,'limitations':'Lexical screen only; cross-source semantic families still require external review. Within-source closures and historical exposure have separate receipts.'}
 preserve_write(OUT/'overlap-audit.json',json.dumps(overlap,indent=2,sort_keys=True).encode()+b'\n',raw=False)
 print(json.dumps({k:report[k] for k in ['aib','infuse']}))
 print(json.dumps(overlap))
if __name__=='__main__':main()
