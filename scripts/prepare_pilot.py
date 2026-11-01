"""Deterministic extraction of existing LLMail records. No model-generated data/labels."""
import hashlib
import json
from pathlib import Path
import re
from difflib import SequenceMatcher
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
HF_REV = '1063bdf01ec8762b812d5e06ee768a06faa5a6f7'
CODE_REV = '3da2399839b285e129888161fcc8cb03169d1b43'
SPECIAL = ['<|im_start|>', '<|begin_of_text|>', '<|start_header_id|>', '<|eot_id|>',
           '<|user|>', '<|assistant|>', '<|im_end|>', '<|endoftext|>', '<|endofprompt|>',
           '<|fim_middle|>', '<|fim_prefix|>', '<|fim_suffix|>', '<|end|>', '<|start|>']
SOURCES = {
 'scenarios.json': f'https://huggingface.co/datasets/microsoft/llmail-inject-challenge/resolve/{HF_REV}/data/scenarios.json',
 'raw_submissions_phase2.jsonl': f'https://huggingface.co/datasets/microsoft/llmail-inject-challenge/resolve/{HF_REV}/data/raw_submissions_phase2.jsonl',
 'llmail-card.md': f'https://huggingface.co/datasets/microsoft/llmail-inject-challenge/resolve/{HF_REV}/README.md',
 'llmail-license.txt': f'https://raw.githubusercontent.com/microsoft/llmail-inject-challenge/{CODE_REV}/LICENSE',
 'email_retriever.py': f'https://raw.githubusercontent.com/microsoft/llmail-inject-challenge/{CODE_REV}/src/agent/workloads/email_retriever.py',
 'config.yaml': f'https://raw.githubusercontent.com/microsoft/llmail-inject-challenge/{CODE_REV}/src/agent/config.yaml',
}


def sha(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def filtered(text):
    # The source removes newlines and these special tokens before inference.
    # Selected examples are <=6000 UTF-8 bytes: cannot hit its 6000-token cutoff.
    text = text.replace('\n', ' ')
    for token in SPECIAL:
        text = text.replace(token, ' ')
    return text


def normalized(text):
    return re.sub(r'\W+', ' ', text.lower()).strip()


def related(a, b):
    return SequenceMatcher(None, normalized(a), normalized(b), autojunk=False).ratio() >= .65


def load_data():
    return [json.loads(line) for line in (ROOT / 'data/pilot.jsonl').read_text().splitlines()]


def main():
    raw = ROOT / 'data/raw'
    raw.mkdir(parents=True, exist_ok=True)
    manifest = {'dataset': 'microsoft/llmail-inject-challenge', 'revision': HF_REV,
                'code_revision': CODE_REV, 'seed': 'decision-context-pilot-v1', 'sources': {}}
    for name, url in SOURCES.items():
        path = raw / name
        if not path.exists():
            with urlopen(url, timeout=60) as response:
                path.write_bytes(response.read())
        manifest['sources'][name] = {'url': url, 'sha256': sha(path.read_bytes()), 'bytes': path.stat().st_size}
    sc = json.loads((raw / 'scenarios.json').read_text())
    eligible = {'1': [], '2': []}
    for line in (raw / 'raw_submissions_phase2.jsonl').open():
        d = json.loads(line)
        obj = json.loads(d['objectives'])
        level = d['scenario'][5:6]
        if level not in eligible or not all(obj.get(k) is True for k in
                  ['email.retrieved', 'exfil.sent', 'exfil.destination', 'exfil.content']):
            continue
        text = 'Subject of the email: ' + d['subject'] + '.   Body: ' + d['body']
        if not text.strip() or len(text.encode()) > 6000 or 'send_email_' in text:
            continue
        d['candidate'] = filtered(text)
        eligible[level].append(d)
    # Development: one team from level1. Evaluation: nine distinct other teams at level2.
    rank = lambda d: sha('decision-context-pilot-v1' + d['RowKey'])
    dev = sorted(eligible['1'], key=rank)[0]
    chosen = []
    teams = {dev['team_id']}
    for d in sorted(eligible['2'], key=rank):
        if d['team_id'] in teams or any(related(d['candidate'], x['candidate']) for x in [dev] + chosen):
            continue
        chosen.append(d)
        teams.add(d['team_id'])
        if len(chosen) == 9:
            break
    assert len(chosen) == 9
    examples = []
    for split, attacks, scenario in [('dev', [dev], 'scenario_1'), ('eval', chosen, 'scenario_2')]:
        source = sc[scenario]
        # BasicEmailRetriever(k) slices [:k-1] and inserts the attack in the middle.
        emails = source['emails'][:1 if split == 'dev' else 9]
        pos = len(emails) // 2 if len(emails) > 1 else len(emails)
        for d in attacks:
            examples.append({'id': 'phase2:' + d['RowKey'], 'gold': 1,
                'gold_basis': 'recorded retrieved tool call with correct destination and content',
                'split': split, 'group': 'team:' + d['team_id'], 'candidate': d['candidate'],
                'trusted_task': source['user_query'],
                'surrounding_before': emails[pos - 1] if pos else '', 'surrounding_after': '',
                'source_scenario': scenario, 'source_level': d['scenario'],
                'source_row': d['RowKey'], 'source_team': d['team_id'],
                'source_objectives': json.loads(d['objectives'])})
        for index, email in enumerate(emails):
            # One nearest source neighbor, excluding the candidate. Dev has no other benign
            # email; use the authentic paired attack from that development session.
            before = emails[index - 1] if index else ''
            after = emails[1] if index == 0 and len(emails) > 1 else ''
            if split == 'dev':
                after = dev['candidate']
            examples.append({'id': scenario + ':benign:' + str(index), 'gold': 0,
                'gold_basis': 'published benign scenario email (not a submission judge label)',
                'split': split, 'group': 'benign-fixture:' + scenario, 'candidate': email,
                'trusted_task': source['user_query'], 'surrounding_before': before,
                'surrounding_after': after, 'source_scenario': scenario, 'source_index': index})
    for e in examples:
        e['candidate_sha256'] = sha(e['candidate'])
        assert e['candidate'] not in e['surrounding_before'] + e['surrounding_after']
    assert not ({e['group'] for e in examples if e['split']=='dev'} &
                {e['group'] for e in examples if e['split']=='eval'})
    raw_text = ''.join(json.dumps(e, ensure_ascii=False, sort_keys=True) + '\n' for e in examples)
    (raw / 'pilot.jsonl').write_text(raw_text)
    selected = ROOT / 'data/pilot.jsonl'
    if selected.exists() and selected.read_text() != raw_text:
        raise ValueError('Frozen selection changed')
    selected.write_text(raw_text)
    manifest['selection_sha256'] = sha(raw_text)
    manifest['examples'] = [{k:v for k,v in e.items() if k not in
                           ['candidate','trusted_task','surrounding_before','surrounding_after']}
                          for e in examples]
    manifest['eligible_counts'] = {k:len(v) for k,v in eligible.items()}
    dest = ROOT / 'data/manifest.json'
    rendered = json.dumps(manifest, indent=2, sort_keys=True) + '\n'
    if dest.exists() and dest.read_text() != rendered:
        raise ValueError('Source or extraction changed: refusing to replace frozen manifest')
    dest.write_text(rendered)
    print(json.dumps({'dev':2,'eval':18,'selection_sha256':sha(raw_text)}))


if __name__ == '__main__':
    main()
