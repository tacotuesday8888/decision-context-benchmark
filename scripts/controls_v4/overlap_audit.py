"""Conservative exact/lexical exposure checks before model selection or inference."""
import json
import re
from collections import defaultdict
from audit_sources import ROOT, OUT, sha


def read(path):
    return [json.loads(s) for s in path.read_text().splitlines()]


def shingles(text):
    words=re.findall(r'\w+',text.casefold())
    return {tuple(words[i:i+5]) for i in range(max(0,len(words)-4))}


def overlaps(left, right, threshold=.8):
    # Cardinality bound rejects impossible pairs before set intersection.
    output=[]
    cached=[(key,shingles(text)) for key,text in right.items()]
    for key,text in left.items():
        s=shingles(text)
        if not s:
            continue
        for old_id,t in cached:
            if not t or min(len(s),len(t))/max(len(s),len(t)) < threshold:
                continue
            intersection=len(s&t)
            score=intersection/(len(s)+len(t)-intersection)
            if score >= threshold:
                output.append({'new':key,'previous':old_id,'jaccard':score})
    return output


def main():
    raw=ROOT/'data/raw/controls-v4'
    old=read(ROOT/'data/pilot.jsonl')+read(ROOT/'data/expanded-v2/collection.jsonl')+read(ROOT/'data/raw/extension-v3/prepared-collection-v1.jsonl')
    old_texts={r['id']:r['candidate'] for r in old}
    old_tasks={sha(r['trusted_task']) for r in old if r.get('trusted_task')}
    attack=read(raw/'tasktracker-advbench-reconstructed-v1.jsonl')
    clean=read(raw/'tasktracker-clean-reconstructed-v1.jsonl')
    unique={r['candidate_sha256']:r['candidate'] for r in attack+clean}
    # Check clean original paragraphs as well, even when only an injected version is selected later.
    documents={r['original_document_sha256']:r['original_document'] for r in attack}
    near=overlaps(dict(unique,**documents),old_texts)
    prior_attacks={}
    for kind in ('dh','ds'):
        for r in json.loads((ROOT/f'data/raw/extension-v3/InjecAgent/data/test_cases_{kind}_base.json').read_text()):
            prior_attacks[sha(r['Attacker Instruction'])]=r['Attacker Instruction']
    # Every published BIPIA string is conservatively checked, including unselected variants.
    def strings(value):
        if isinstance(value,str):
            yield value
        elif isinstance(value,list):
            for item in value: yield from strings(item)
        elif isinstance(value,dict):
            for item in value.values(): yield from strings(item)
    for path in (ROOT/'data/raw/expanded-v2').glob('benchmark__*attack_*.json'):
        for text in strings(json.loads(path.read_text())):
            prior_attacks[sha(text)]=text
    import csv
    new_attacks={sha(r['goal']):r['goal'] for r in csv.DictReader((raw/'advbench-harmful-behaviors.csv').open())}
    attack_overlap=overlaps(new_attacks,prior_attacks)
    report={'source':'TaskTracker QA/AdvBench and clean QA audit',
            'prior_rows':len(old),'new_unique_candidates':len(unique),'original_paragraphs_checked':len(documents),
            'prior_exact_task_hash_overlap':sorted({h for r in attack+clean for h in (r['task_sha256'],r['question_sha256'])}&old_tasks),
            'candidate_or_original_paragraph_near_overlaps':near,
            'previous_attack_strings_screened':len(prior_attacks),
            'attack_prompt_near_overlaps':attack_overlap,
            'attack_prompt_exact_overlaps':sorted(set(new_attacks)&set(prior_attacks)),
            'threshold':.8,'definition':'casefolded 5-word shingle Jaccard',
            'limitations':'Does not establish semantic novelty, unseen broad harm categories, or absence of pretraining exposure. Shared article/document and same/near attack groups still require separate split validation.',
            'model_requests':0}
    (OUT/'tasktracker-overlap-audit-v1.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'new_candidates':len(unique),'near_text_overlaps':len(near),'near_attack_overlaps':len(attack_overlap),'exact_task_overlaps':len(report['prior_exact_task_hash_overlap'])}))


if __name__=='__main__':
    main()
