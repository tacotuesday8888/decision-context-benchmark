"""Verify that delivered manuscript, figures and PDF match their build inputs."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/expanded-execution'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    manifest=json.loads((ROOT/'paper/build-manifest.json').read_text())
    assert manifest['evaluation_complete'],'Final paper must use complete execution'
    for section in ('input_sha256','output_sha256'):
        for name,digest in manifest[section].items():assert sha(ROOT/name)==digest,('Stale paper artifact',name)
    for name,digest in json.loads((OUT/'paper-figures/inputs.json').read_text()).items():
        assert sha(OUT/name)==digest,('Stale figure input',name)
    assert len(list((OUT/'paper-figures').glob('*.png')))==9
    text=(ROOT/'paper/manuscript.md').read_text()
    assert '{{' not in text and 'INTERIM DRAFT:' not in text
    assert 'RESEARCH DRAFT: all 5274 planned logical cells' in text
    print(json.dumps({'paper_inputs_and_outputs_match':True,'final_execution_snapshot':True,'figures':9}))
if __name__=='__main__':main()
