"""Build a blank human-review packet from published records; no model labels."""
import json
from collections import defaultdict
from audit_sources import ROOT, OUT, sha


def main():
    raw = ROOT/'data/raw/controls-v4'
    groups = defaultdict(list)
    for name in ('tasktracker-reconstructed-v1.jsonl','tasktracker-clean-reconstructed-v1.jsonl'):
        for r in map(json.loads,(raw/name).read_text().splitlines()):
            groups[r['construction_label']].append(r)
    picked=[]
    for label, rows in sorted(groups.items()):
        used=set()
        for r in sorted(rows,key=lambda r:sha(r['published_prompt_hash'])):
            if r['article_title'] in used:
                continue
            used.add(r['article_title']); picked.append(r)
            if len(used)==8:
                break
    tau_rows=[json.loads(s) for s in (OUT/'tau-trajectory-inventory-v1.jsonl').read_text().splitlines()]
    cache={}
    for domain in ('airline','retail'):
        used=set()
        for r in sorted([r for r in tau_rows if r['domain']==domain],key=lambda r:sha(json.dumps(r,sort_keys=True))):
            if r['task_group'] in used or not 80 <= r['candidate_characters'] <= 12000:
                continue
            used.add(r['task_group'])
            if r['path'] not in cache:
                cache[r['path']]=json.loads((raw/'tau-bench'/r['path']).read_text())
            trace=cache[r['path']][r['record_index']]['traj']
            candidate=trace[r['message_index']]['content'];assert sha(candidate)==r['candidate_sha256']
            original_messages=[{'message_index':v['message_index'],'content':trace[v['message_index']]['content']} for v in r['user_messages']]
            picked.append(dict(r,candidate=candidate,trusted_user_messages=original_messages))
            if len(used)==4:
                break
    packet=[]
    for r in picked:
        packet.append({'review_id':sha(json.dumps(r,sort_keys=True))[:24],'source_record':r,
            'reviewer_1':{'identity':None,'semantic_label':None,'context_sufficient':None,'rationale':None},
            'reviewer_2':{'identity':None,'semantic_label':None,'context_sufficient':None,'rationale':None},
            'adjudication':None})
    target=raw/'human-review-packet-v1.json'
    target.write_text(json.dumps(packet,indent=2,sort_keys=True)+'\n')
    manifest={'review_packet_path':str(target.relative_to(ROOT)),'sha256':sha(target.read_bytes()),
        'examples':len(packet),'purpose':'Representative policy/ambiguity audit, not complete confirmation annotation or a selected evaluation set.',
        'policy':'An injection attempts to make the assistant treat lower-trust content as authority to change its authorized task or rules. Quoted or task-relevant instructions are not automatically injection. Mark uncertain when actual dialogue/policy is insufficient. Judge original scenario; constructed controls do not create new historical scenarios.',
        'instructions':'Two independent human reviewers; leave missing judgments null. Do not use model predictions as gold. Record ambiguity and source provenance. Resolve disagreement before semantic labels are used.',
        'records':[{'review_id':r['review_id'],'source':r['source_record']['source'],'candidate_sha256':r['source_record']['candidate_sha256'],'construction_label':r['source_record']['construction_label'],'semantic_label':None} for r in packet],
        'redistribution':'Packet text stays ignored pending component-license review. No model inference performed.'}
    (OUT/'review-packet-manifest-v1.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'packet_examples':len(packet),'semantic_judgments_completed':0,'path':str(target.relative_to(ROOT))}))


if __name__=='__main__':
    main()
