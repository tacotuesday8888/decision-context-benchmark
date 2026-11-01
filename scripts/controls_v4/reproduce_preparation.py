"""Isolated source-artifact reconstruction; no network or model inference."""
import hashlib,json,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/'data/raw/controls-v4'
OUT=ROOT/'results/controls-v4'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    commands=['audit_tasktracker_advbench.py','audit_tasktracker_clean.py','audit_aib.py','draft_selection_v2.py','prepare.py','validate_collection.py']
    compare=['tasktracker-advbench-inventory-v1.jsonl','tasktracker-advbench-audit-v1.json','tasktracker-clean-inventory-v1.jsonl','tasktracker-clean-audit-v1.json','aib-inventory-v1.jsonl','aib-audit-v1.json','draft-selection-v2.jsonl','draft-selection-summary-v2.json','reused-development-v2.jsonl','collection-manifest-v1.jsonl','collection-summary-v1.json','collection-validation-v1.json']
    with tempfile.TemporaryDirectory(prefix='reproduce-',dir=RAW) as folder:
        isolated=Path(folder);isolated_raw=isolated/'data/raw/controls-v4';isolated_raw.mkdir(parents=True)
        (isolated/'results/controls-v4').mkdir(parents=True)
        shutil.copytree(ROOT/'scripts/controls_v4',isolated/'scripts/controls_v4',ignore=shutil.ignore_patterns('__pycache__'))
        old=isolated/'data/expanded-v2';old.mkdir(parents=True);shutil.copy2(ROOT/'data/expanded-v2/collection.jsonl',old/'collection.jsonl')
        copied={}
        for name in ['squad-dev-v2.0.json','advbench-harmful-behaviors.csv','advbench-LICENSE']:
            shutil.copy2(RAW/name,isolated_raw/name);copied[name]=sha(RAW/name)
        for name in ['TaskTracker','agent-injection-bench']:
            subprocess.run(['git','clone','--quiet','--no-hardlinks',str(RAW/name),str(isolated_raw/name)],check=True,capture_output=True)
            copied[name]=subprocess.check_output(['git','-C',str(isolated_raw/name),'rev-parse','HEAD'],text=True).strip()
        for command in commands:
            result=subprocess.run([sys.executable,str(isolated/'scripts/controls_v4'/command)],cwd=isolated,capture_output=True,text=True)
            if result.returncode:raise RuntimeError(command+' failed: '+result.stderr[-1000:])
        identical={}
        for name in compare:
            expected=sha(OUT/name);assert sha(isolated/'results/controls-v4'/name)==expected,name;identical[name]=expected
        expected=sha(RAW/'prepared-collection-v1.jsonl');assert sha(isolated_raw/'prepared-collection-v1.jsonl')==expected
        identical['ignored_full_prepared_collection']=expected
    receipt={'status':'passed','commands':commands,'source_artifacts':copied,'identical_outputs':identical,'script_sha256':sha(Path(__file__)),
        'scope':'Rebuild from pinned local source clones and original published data in isolated directory; no network, inference or upstream harness execution. Six deterministic adapters/checks; full prepared text also byte-identical.'}
    (OUT/'preparation-reproduction-v1.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':'passed','commands':len(commands),'identical_outputs':len(identical)}))
if __name__=='__main__':main()
