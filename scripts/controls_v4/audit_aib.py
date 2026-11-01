"""Inspect published static fixtures; do not execute the agent harness or tools."""
import json
import subprocess
from collections import Counter
from audit_sources import ROOT, OUT, sha

REVISION='d75c8ad8d255d018b75258d22ea1c78a8c37428b'


def main():
    base=ROOT/'data/raw/controls-v4/agent-injection-bench'
    assert subprocess.check_output(['git','-C',str(base),'rev-parse','HEAD'],text=True).strip()==REVISION
    path=base/'aib/data/attacks.jsonl';digest=sha(path.read_bytes())
    rows=[];excluded=[];prepared=[]
    for i,r in enumerate(map(json.loads,path.read_text().splitlines())):
        reason=None
        if r['channel'] not in ('document','web_page','tool_result'):reason='unsupported_trust_surface_or_multiturn'
        elif r.get('system_prompt') or r.get('history'):reason='additional_required_trusted_context'
        elif r['channel']=='tool_result' and not any(t.get('returns')==r['injected'] for t in r.get('tools',[])):reason='tool_response_not_exactly_aligned'
        if reason:
            excluded.append({'id':r['id'],'reason':reason});continue
        row={'source':'agent-injection-bench','revision':REVISION,'source_file':'aib/data/attacks.jsonl',
             'file_sha256':digest,'row_index':i,'source_id':r['id'],'channel':r['channel'],
             'family':r['family'],'task_sha256':sha(r['task']),'candidate_sha256':sha(r['injected']),
             'construction_label':'published_benign_control' if r['family']=='control' else 'published_intended_attack',
             'source_construction_target':int(r['family']!='control'),'semantic_label':None,
             'license':'MIT','eligibility':'pending_overlap_and_scope_review',
             'provenance_scope':'Community-authored static synthetic fixture, not a historical production trace. Citation in source is conceptual provenance, not proof of copied original paper data.'}
        rows.append(row);prepared.append(dict(row,candidate=r['injected'],trusted_task=r['task']))
    (OUT/'aib-inventory-v1.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows))
    (ROOT/'data/raw/controls-v4/aib-prepared-v1.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in prepared))
    summary={'source_revision':REVISION,'candidate_fixtures':len(rows),'distinct_texts':len({r['candidate_sha256'] for r in rows}),
             'distinct_tasks':len({r['task_sha256'] for r in rows}),'families':dict(Counter(r['family'] for r in rows)),
             'class_counts':dict(Counter(r['source_construction_target'] for r in rows)),
             'excluded':excluded,'file_sha256':digest,'license_sha256':sha((base/'LICENSE').read_bytes()),
             'model_requests':0,'approved_examples':0,
             'limitation':'Small supplemental benign-instruction stress set; cannot establish precise false-alarm rates or real-world domain transfer. Keep source-specific.'}
    (OUT/'aib-audit-v1.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n');print(json.dumps(summary))


if __name__=='__main__':main()
