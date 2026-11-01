"""Deterministic examples for qualitative inspection; never relabels or tunes."""
import json
from execute import OUT,ROOT,DATA,PANEL,jsonl,save,sha


def main():
    rows=sorted([r for r in jsonl(DATA/'collection.jsonl') if r['split']=='eval'],key=lambda r:r['id'])
    actual={};paths={}
    for config in PANEL:
        for path in sorted((OUT/'evaluation'/config).glob('*-*.json')):
            r=json.loads(path.read_text())
            if 'parsed' not in r:continue
            key=(config,r['id'],r['condition'])
            if key not in actual or r['attempt']>actual[key]['attempt']:actual[key]=r;paths[key]=str(path.relative_to(ROOT))
    examples=[]
    for config in PANEL:
        selected=set()
        for row in rows:
            a=actual.get((config,row['id'],'candidate'));b=actual.get((config,row['id'],'task'))
            if not a or not b or not a['parsed']['valid'] or not b['parsed']['valid']:continue
            pa=a['parsed']['prediction'];pb=b['parsed']['prediction'];gold=row['gold']
            category='corrected' if pa!=gold and pb==gold else 'regressed' if pa==gold and pb!=gold else 'persistent_false_alarm' if pa==pb==1 and gold==0 else 'persistent_missed_attack' if pa==pb==0 and gold==1 else None
            if category is None or category in selected:continue
            selected.add(category)
            examples.append({'config':config,'category':category,'id':row['id'],'dataset':row['dataset'],'gold':gold,'gold_basis':row['gold_basis'],'source':row['source'],'groups':row['groups'],'candidate_sha256':row['candidate_sha256'],
                'candidate_prediction':pa,'task_prediction':pb,'candidate_score':a['parsed'].get('score'),'task_score':b['parsed'].get('score'),
                'candidate_record':paths[config,row['id'],'candidate'],'task_record':paths[config,row['id'],'task']})
    failures=[{'config':c,'id':i,'condition':k,'status':r['parsed']['status'],'record':paths[c,i,k]} for (c,i,k),r in sorted(actual.items()) if r['parsed']['status'] not in ('ok','tie')]
    save(OUT/'error-review.json',{'selection':'First lexicographic candidate ID per model and category among currently available valid pairs. Examples illustrate disagreements with inherited gold; they are not representative frequency estimates or new labels. Regenerate after execution ends.','examples':examples,'operational_failures':failures})
    print(json.dumps({'examples':len(examples),'operational_failures':len(failures)}))

if __name__=='__main__':main()
