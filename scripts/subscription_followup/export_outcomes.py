"""Export compact first outcomes after the same strict closed-evidence barriers.

These credential-free rows permit reanalysis from the private repository. Full
raw prompts/transports stay in the ignored local store; their hashes remain in
the collection lineage and analysis provenance.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.study_v7.requests import canonical, digest
from scripts.subscription_followup.prepare import write_once


def jsonl(rows):
    return b''.join(canonical(row) + b'\n' for row in rows)


def save_core(loaded, output):
    key = lambda r: (r['group_id'], r['config'], r['condition'], r['id'])
    files = {
        'main-first-outcomes.jsonl': jsonl(sorted(loaded['rows'], key=key)),
        'repeat-outcomes.jsonl': jsonl(sorted(loaded['repeat_rows'], key=key)),
    }
    return save(files, loaded['proof'], output)


def save_extensions(loaded, output):
    from scripts.subscription_followup import pilot
    records = []
    for cell in sorted(loaded['pilot_cells'], key=lambda c: c['cell_id']):
        parsed = loaded['observations'][cell['cell_id']]
        row = {k: cell.get(k) for k in ('cell_id', 'task_id', 'condition', 'arm', 'kind', 'config', 'namespace')}
        row.update({k: parsed.get(k) for k in ('status', 'valid', 'prediction', 'score', 'answer')})
        selected = cell['payload']
        if cell.get('arm') == 'Jev_gate':
            gate = loaded['observations'][cell['gate_cell_id']]
            disposition = pilot.gate_disposition(gate.get('score'), status=gate['status'])
            row['gate_disposition'] = disposition
            selected = pilot.select_actor_payload(cell, disposition)
        row['selected_payload_sha256'] = digest(canonical(selected)) if selected is not None else None
        records.append(row)
    source = sorted(loaded['source_rows'], key=lambda r: (r['group_id'], r['config'], r['condition'], r['id']))
    return save({'source-first-outcomes.jsonl': jsonl(source), 'pilot-outcomes.jsonl': jsonl(records)},
                loaded['proof'], output)


def save(files, proof, output):
    output = Path(output)
    provenance = {'version': 'subscription-followup-compact-outcomes-1', 'no_new_estimation': True,
                  'closed_evidence_proof': proof, 'files': {name: digest(body) for name, body in files.items()}}
    for name, body in files.items():
        write_once(output / name, body)
    write_once(output / 'compact-outcomes-provenance.json', canonical(provenance) + b'\n')
    return provenance


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--core-lineage', type=Path)
    source.add_argument('--extension-manifest', type=Path)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.core_lineage:
        from scripts.subscription_followup.analyze_core import load_artifacts
        result = save_core(load_artifacts(args.core_lineage, root=args.root), args.output)
    else:
        from scripts.subscription_followup.analyze_extensions import load_artifacts
        result = save_extensions(load_artifacts(args.extension_manifest, root=args.root), args.output)
    print(json.dumps(result, indent=2, sort_keys=True))
