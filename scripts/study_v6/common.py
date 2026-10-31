"""V6 preparation primitives. No inference and no semantic label assignment."""
from __future__ import annotations
import collections
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from scripts.source_discovery.prepare_review import canonical_bytes, preserve_write, sha256

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data/raw/study-v6'
OUT = ROOT / 'results/study-v6'
SEED = 'DCB-v6-20261030'
BROWSE_REPO = 'perplexity-ai/browsesafe-plus-plus'
BROWSE_REV = '3e9f4b3cef9295a1928ddfb33675eafd8bb68259'
NVIDIA_REV = 'd738d4f361cc38bb4d7a42b9066776dade5332f5'
NVIDIA_SHA = '3329da17564a7eb287e2730fc7d6956e1f4fe51e8950ac4f110b3c37e78cf3b9'

def read(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]

def write_rows(path, rows):
    preserve_write(path, b''.join(canonical_bytes(r) + b'\n' for r in rows))

def report(path, value):
    preserve_write(path, json.dumps(value, indent=2, sort_keys=True).encode() + b'\n', raw=False)

def rank(value):
    return hashlib.sha256((SEED + ':' + str(value)).encode()).hexdigest()

def norm(value):
    return ' '.join(re.findall(r'\w+', unicodedata.normalize('NFKC', value or '').casefold()))

class Union:
    def __init__(self, n):
        self.p = list(range(n))
    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x
    def join(self, a, b):
        self.p[self.find(a)] = self.find(b)

def exact_groups(items, key_lists):
    """Each key list is an axis; empty keys never connect unrelated examples."""
    u = Union(len(items))
    for values in key_lists:
        seen = {}
        for i, keys in enumerate(values):
            for key in keys:
                if not key:
                    continue
                if key in seen:
                    u.join(i, seen[key])
                else:
                    seen[key] = i
    members = collections.defaultdict(list)
    for i, item in enumerate(items):
        members[u.find(i)].append(str(item))
    return {item: min(group, key=rank) for group in members.values() for item in group}

def references(row):
    result = []
    for key in ('injection_text_fragments_json', 'attack_quotes_json'):
        value = row.get(key)
        if value in (None, ''):
            continue
        value = json.loads(value) if isinstance(value, str) else value
        if not isinstance(value, list) or any(not isinstance(s, str) for s in value):
            raise ValueError('Malformed injection references')
        result.extend(s for s in value if s.strip())
    return sorted(set(result))

def index_browse(rows):
    """Only labeled training pairs; duplicate or inconsistent entries fail closed."""
    pairs = collections.defaultdict(dict)
    for row in rows:
        match = re.fullmatch(r'(\d+)_(malicious|benign)', row.get('entry_id', ''))
        if not match or row.get('split') != 'train':
            raise ValueError('Not a labeled training entry')
        key, arm = match.groups()
        expected = ('attack', 'yes') if arm == 'malicious' else ('control', 'no')
        if (row.get('arm'), row.get('label')) != expected or arm in pairs[key]:
            raise ValueError('Duplicate entry or inconsistent arm/label')
        pairs[key][arm] = row
    eligible, excluded = {}, []
    for key, arms in sorted(pairs.items()):
        if set(arms) != {'malicious', 'benign'}:
            excluded.append({'pair': key, 'reason': 'incomplete_pair'})
        elif not isinstance(arms['benign'].get('benign_task'), str) or not arms['benign']['benign_task'].strip():
            excluded.append({'pair': key, 'reason': 'missing_task'})
        elif arms['benign']['benign_task'] != arms['malicious'].get('benign_task'):
            excluded.append({'pair': key, 'reason': 'tasks_differ'})
        else:
            try:
                references(arms['malicious'])
                eligible[key] = arms
            except (ValueError, TypeError):
                excluded.append({'pair': key, 'reason': 'malformed_references'})
    return eligible, excluded

def browse_selection(rows, n=1000):
    pairs, excluded = index_browse(rows)
    ids = sorted(pairs)
    groups = exact_groups(ids, [
        [[norm(pairs[k]['benign']['benign_task'])] for k in ids],
        [[norm(s) for s in references(pairs[k]['malicious']) if len(norm(s).split()) >= 5] for k in ids],
    ])
    by_group = collections.defaultdict(list)
    for key in ids:
        by_group[groups[key]].append(key)
    # One pair per exact task/injection component. Sample before reading outcomes.
    chosen_groups = sorted(by_group, key=lambda g: rank('browse-group:' + g))[:n]
    chosen = [min(by_group[g], key=lambda k: rank('browse-pair:' + k)) for g in chosen_groups]
    return chosen, groups, excluded

def shingles(value):
    words = norm(value).split()
    return set(zip(words, words[1:], words[2:]))

def near_links(texts, threshold=.5):
    """Exact 3-word Jaccard join using prefix filtering, no probabilistic misses.

    Short texts use normalized exact matching elsewhere. This is a lexical audit,
    not a claim that all semantic template relatives have been discovered.
    """
    import math
    sets = [shingles(t) for t in texts]
    frequency = collections.Counter(s for group in sets for s in group)
    postings = collections.defaultdict(list)
    links = []
    for i, group in enumerate(sets):
        if len(group) < 5:
            continue
        ordered = sorted(group, key=lambda s: (frequency[s], s))
        prefix = ordered[:len(group) - math.ceil(threshold * len(group)) + 1]
        candidates = {j for s in prefix for j in postings[s]}
        for j in sorted(candidates):
            other = sets[j]
            if min(len(group), len(other)) < threshold * max(len(group), len(other)):
                continue
            score = len(group & other) / len(group | other)
            if score >= threshold:
                links.append((j, i, score))
        for s in prefix:
            postings[s].append(i)
    return links
