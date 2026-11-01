"""Read-only protection for completed v3 and previous evidence."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE='d929836982347374695a0d38797623f8276a1cd5'
def verify():
    closure=ROOT/'results/extension-v3/execution-closure-v1.json'
    plan=ROOT/'results/controls-v4/request-plan-v1.json'
    if plan.exists():
        assert hashlib.sha256(closure.read_bytes()).hexdigest()==json.loads(plan.read_text())['prior_closure_sha256']
    changed=subprocess.check_output(['git','diff',BASE,'--','scripts/extension_v3','results/extension-v3','docs/extension-v3'],cwd=ROOT,text=True)
    if changed:raise ValueError('Completed v3 artifacts changed')
    receipt=json.loads((ROOT/'results/extension-v3/completed-study-freeze.json').read_text())
    for name,digest in receipt['hashes'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Earlier evidence changed: '+name)
    return {'baseline_commit':BASE,'unchanged_earlier_files':len(receipt['hashes'])}
if __name__=='__main__':print(json.dumps(verify()))
