"""Post-freeze descriptive audit; prints no fixture values and changes no selection."""
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    rows = map(json.loads, (ROOT / 'data/raw/extension-v3/prepared-collection-v1.jsonl').read_text().splitlines())
    matched = [dict(id=r['id'], dataset=r['dataset'], candidate_sha256=r['candidate_sha256'], task_group=r['groups']['task'])
               for r in rows if re.search(r'(?i)\b(?:password|otp|api_key|private key)\b', r['candidate'])]
    report = {'scope': 'Post-freeze descriptive audit only; no exclusion, relabeling or inference changes. Keyword mentions are not evidence of live credentials. Original narrow filter excludes colon/equal assignments and SSH keys, not prose or serialized strings.',
        'matched_task_candidate_pairs': len(matched),
        'distinct_candidate_hashes': len({r['candidate_sha256'] for r in matched}),
        'by_source': dict(Counter(r['dataset'] for r in matched)), 'rows': matched}
    (ROOT / 'results/extension-v3/fixture-keyword-audit-v1.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'rows'}))


if __name__ == '__main__':
    main()
