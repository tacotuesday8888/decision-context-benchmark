"""Rebuild final analyses from the staged Git tree without credentials or inference."""
import hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/controls-v4'
RAW=ROOT/'data/raw/controls-v4'
CONFIGS=['jev_firstparty','luna_decisions','laya_local','nimble_local','luna_chat','astra_chat','protectai_local']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert json.loads((OUT/'execution-closure-v1.json').read_text())['status']=='terminal'
    tree=subprocess.check_output(['git','write-tree'],cwd=ROOT,text=True).strip()
    outputs=list((OUT/'analysis').glob('*'))+list((OUT/'figures').glob('*'))+list((OUT/'tables').glob('*'))+[OUT/'execution-closure-v1.json',OUT/'report-inputs-v1.json',ROOT/'docs/controls-v4/RESULTS.md']
    expected={str(p.relative_to(ROOT)):sha(p) for p in outputs if p.is_file()}
    commands=[]
    with tempfile.TemporaryDirectory(prefix='offline-reproduce-',dir=RAW) as folder:
        isolated=Path(folder)
        subprocess.run(['git','checkout-index','--all','--prefix='+str(isolated)+os.sep],cwd=ROOT,check=True,capture_output=True)
        assert not (isolated/'.env.local').exists() and not (isolated/'.secrets').exists()
        baseline=json.loads((isolated/'results/extension-v3/completed-study-freeze.json').read_text())
        for path,digest in baseline['hashes'].items():assert sha(isolated/path)==digest,path
        for config in CONFIGS:
            for script in ['analyze.py','verify_analysis.py','verify_bootstrap.py','audit_records.py']:
                commands.append([sys.executable,'scripts/controls_v4/'+script,'--config',config])
        commands += [[sys.executable,'scripts/controls_v4/tables.py'],[sys.executable,'scripts/controls_v4/figures.py'],[sys.executable,'scripts/controls_v4/closure.py','--require-terminal'],[sys.executable,'scripts/controls_v4/report.py']]
        for command in commands:
            result=subprocess.run(command,cwd=isolated,capture_output=True,text=True)
            if result.returncode:raise RuntimeError(str(command[1:])+' failed: '+result.stderr[-1500:])
        for path,digest in expected.items():assert sha(isolated/path)==digest,path
    receipt={'status':'passed','staged_tree':tree,'commands':[c[1:] for c in commands],
        'identical_outputs':expected,'prior_files_preserved':len(baseline['hashes']),'script_sha256':sha(Path(__file__)),
        'scope':'Isolated staged-tree analysis reconstruction using installed numerical runtime. No credentials, model weights, external network, new inference or source downloads.'}
    (OUT/'offline-reproduction-v1.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':'passed','commands':len(commands),'identical_outputs':len(expected)}))
if __name__=='__main__':main()
