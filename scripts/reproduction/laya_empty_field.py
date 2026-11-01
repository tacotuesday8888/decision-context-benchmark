"""Bounded post-hoc reproduction; never edits the historical experiment."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/laya-empty-field-reproduction'
SOURCES={'A':'614aac425fd608ee16de97c0','B':'55c5090952021e24b1635f6d'}
sys.path.insert(0,str(ROOT/'scripts/laya_v2'))
import adapter

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def inputs():
 records={k:json.loads((ROOT/'results/extension-v3/confirmation/laya_local'/f'{v}.json').read_text()) for k,v in SOURCES.items()}
 a,b=[records[k]['request'].copy() for k in 'AB'];sa,sb=[json.loads(q.pop('state')) for q in [a,b]]
 assert a==b and sb.pop('TRUSTED_USER_TASK')=='' and sa==sb
 return records

def worker(method,order,repeat):
 import torch,laya
 records=inputs();torch.set_num_threads(2)
 if method=='adapter':
  wrapper=adapter.LocalDecision();agent=wrapper.agent
 else:
  manifest=json.loads((ROOT/'results/laya-v2/model-artifacts.json').read_text())
  assert manifest['files_sha256']==adapter.artifact_hashes()
  assert laya.__version__==adapter.SDK
  agent=laya.load(str(adapter.MODEL_DIR),device='cpu',backend='eager',expected_sha256=manifest['files_sha256'])
  agent.model.eval()
 results=[]
 for condition in order*2:
  q=records[condition]['request'];start=time.perf_counter()
  if method=='adapter':raw,parsed,audit=wrapper.predict(q)
  else:
   raw=agent.system_one(q['state'],q['questions'],max_len=8192,head_max_len=256)
   parsed=adapter.parse(raw);audit=None
  assert parsed['status']=='ok' and not raw['usage']['truncated'] and raw['usage']['state_tokens_dropped']==0
  results.append({'condition':condition,'request':q,'raw_response':raw,'parsed':parsed,'token_audit':audit,'elapsed_seconds':time.perf_counter()-start})
 save(OUT/f'{method}-{order}-{repeat}.json',{'method':method,'order':order,'restart':repeat,'pid':os.getpid(),'torch':torch.__version__,'sdk':laya.__version__,'training':agent.model.training,'parameter_dtypes':sorted({str(p.dtype) for p in agent.model.parameters()}),'cpu_amp_env':os.getenv('LAYA_CPU_AMP'),'results':results})
 print(json.dumps({'method':method,'order':order,'restart':repeat,'scores':[r['parsed']['score'] for r in results]}),flush=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('--worker',choices=['adapter','sdk']);p.add_argument('--order');p.add_argument('--repeat',type=int);args=p.parse_args()
 if args.worker:return worker(args.worker,args.order,args.repeat)
 assert not (OUT/'plan.json').exists(),'New output version required; no overwrites'
 sources={str((ROOT/'results/extension-v3/confirmation/laya_local'/f'{v}.json').relative_to(ROOT)):sha(ROOT/'results/extension-v3/confirmation/laya_local'/f'{v}.json') for v in SOURCES.values()}
 inputs()
 save(OUT/'plan.json',{'purpose':'Post-hoc reproducibility of one selected historical formatting flip, not a new accuracy estimate','source_hashes':sources,'script_sha256':sha(Path(__file__)),'design':'Two independent process restarts per adapter/SDK and AB/BA ordering; repeat the pair twice within each process; 32 forward calls total','conditions':{'A':'Historical candidate-only exact request','B':'Historical exact request with empty TRUSTED_USER_TASK'},'cost_usd':0,'environment':'CPU eager, two threads, evaluation mode; CPU AMP disabled explicitly for repeatability. Historical per-forward dtype was not recorded.'})
 env=os.environ.copy();env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',USE_TF='0',LAYA_CPU_AMP='0')
 for method in ['adapter','sdk']:
  for order in ['AB','BA']:
   for repeat in [1,2]:subprocess.run([sys.executable,__file__,'--worker',method,'--order',order,'--repeat',str(repeat)],env=env,check=True)
 for name,digest in sources.items():assert sha(ROOT/name)==digest
 rows=[r for f in OUT.glob('*-*-*.json') for r in json.loads(f.read_text())['results']]
 summary={'calls':len(rows),'historical_files_unchanged':True,'by_condition':{k:{'scores':sorted({r['parsed']['score'] for r in rows if r['condition']==k}),'predictions':sorted({r['parsed']['prediction'] for r in rows if r['condition']==k}),'n':sum(r['condition']==k for r in rows)} for k in 'AB'}}
 assert len(rows)==32
 save(OUT/'summary.json',summary);print(json.dumps(summary))
if __name__=='__main__':main()
