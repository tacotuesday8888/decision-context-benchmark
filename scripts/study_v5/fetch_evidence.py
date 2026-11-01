"""Pinned, bounded inert source acquisition. Never imports or executes upstream code."""
from pathlib import Path
import concurrent.futures
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data/raw/study-v5'
REPOS = {
 'infuse': ('judydnguyen/infuse','d4ed0634c7d94979da9d91c0db5e2aba11a3dff2'),
 'authorization': ('PEACH-Research-Lab/AuthorizationBench','c48d2da60f207ad2664feebda516b1cc72f4fa98'),
 'aib': ('ppradyoth/AgentInjectionBench','540669a836e98063278fb0586e5e178818a20d88'),
 'asb': ('agiresearch/ASB','544540ff0788998072f7df463056fd17e62cc9f4'),
}
def fetch(item):
 name,path=item; repo,rev=REPOS[name]
 url=f'https://raw.githubusercontent.com/{repo}/{rev}/{path}'
 dst=RAW/name/path
 if not dst.resolve().is_relative_to((RAW/name).resolve()):raise ValueError('Source path escapes cache')
 if dst.exists(): b=dst.read_bytes()
 else:
  with urllib.request.urlopen(url,timeout=40) as r:b=r.read(2_000_001)
  if len(b)>2_000_000:raise ValueError('Oversize source')
  dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(b);dst.chmod(0o600)
 tree=json.loads((RAW/f'{name}-tree.json').read_text())
 expected=next(x['sha'] for x in tree['tree'] if x['path']==path and x['type']=='blob')
 actual=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
 if actual!=expected:raise ValueError('Pinned Git blob mismatch: '+path)
 return dict(repository=repo,revision=rev,path=path,url=url,cache=str(dst.relative_to(ROOT)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
 wanted=[]
 for name,(repo,rev) in REPOS.items():
  treepath=RAW/f'{name}-tree.json'
  if not treepath.exists():
   with urllib.request.urlopen(f'https://api.github.com/repos/{repo}/git/trees/{rev}?recursive=1',timeout=40) as r:b=r.read(8_000_001)
   if len(b)>8_000_000:raise ValueError('Oversize tree')
   treepath.parent.mkdir(parents=True,exist_ok=True);treepath.write_bytes(b)
  tree=json.loads(treepath.read_text())
  if tree['sha']!=rev or tree.get('truncated'):raise ValueError('Wrong or incomplete tree')
  for x in tree['tree']:
   p=x['path']
   if x['type']!='blob':continue
   use=p in ['README.md','LICENSE']
   if name=='infuse':use |= (p.startswith('infuse/injection/') and p.endswith('.py')) or p in ['docs/INJECTION.md','infuse/envs/surface_attack_prompts.py','infuse/envs/surface_detector.py','benchmark/attacks/verifier_lib.sh'] or (p.startswith('benchmark/tasks/') and p.endswith(('instruction.md','benign.toml','tests/test.sh'))) or (p.startswith('benchmark/attacks/') and p.endswith('config.toml'))
   if name=='aib':use |= p.startswith('generation/') and p.endswith(('.py','.yaml')) or p=='runtime/cases.py'
   if name=='asb':use |= p in ['pyopenagi/agents/react_agent_attack.py','scripts/agent_attack.py']
   if name=='authorization':use |= p in ['docs/CONSTRUCTION.md','authorization_eva_sandbox/seeds/seed.json','authorization_eva_sandbox/services/contracts.py'] or any(p==f'authorization_eva_sandbox/tasks/{task}/{file}' for task in ['T0013-j-c-h','T0013-n-c-h'] for file in ['task_config.json','vignette.json','system_prompt.txt','workspace/README.md'])
   if use:wanted.append((name,p))
 with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:receipts=list(pool.map(fetch,wanted))
 out=ROOT/'results/study-v5/source-receipts.json';out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps({'version':'v5-evidence-1','executed_upstream_code':False,'files':sorted(receipts,key=lambda r:(r['repository'],r['path']))},indent=2)+'\n')
 print(json.dumps({'files':len(receipts),'bytes':sum(r['bytes'] for r in receipts)}))
if __name__=='__main__':main()
