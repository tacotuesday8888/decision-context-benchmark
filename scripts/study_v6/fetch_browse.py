"""Pinned, resumable training-only Parquet column reads. Never reads screenshots/test.

Use the approved local Hugging Face credential cache; no token arguments or output.
No upstream executable code is imported. Partial output cannot become a review set.
"""
from __future__ import annotations
import argparse
import collections
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v6.common import (
    ROOT, RAW, OUT, BROWSE_REPO, BROWSE_REV, read, write_rows,
    report, sha256, browse_selection,
)

META_COLUMNS = ['entry_id', 'arm', 'label', 'split', 'benign_task',
                'injection_text_fragments_json', 'attack_quotes_json', 'domain',
                'page_type', 'attack_type', 'language_page', 'language_payload']

def train_paths(names):
    return sorted(n for n in names if re.fullmatch(r'data/members-train-\d{4}\.parquet', n))

def selected_groups(metadata, ids):
    result = collections.defaultdict(set)
    for row in metadata:
        if row['entry_id'].rsplit('_', 1)[0] in ids:
            result[row['_file']].add(row['_row_group'])
    return result

def main():
    import huggingface_hub
    import pyarrow
    import pyarrow.parquet as pq
    from huggingface_hub import HfApi, HfFileSystem, get_token
    ap = argparse.ArgumentParser()
    ap.add_argument('--pairs', type=int, default=1000)
    args = ap.parse_args()
    if args.pairs != 1000:
        raise ValueError('This version fixes selection at 1000 pairs; version any amendment')
    if not get_token():
        raise SystemExit('Approved local Hugging Face login required; no credentials are printed.')
    info = HfApi().dataset_info(BROWSE_REPO, revision=BROWSE_REV, files_metadata=True)
    if info.sha != BROWSE_REV:
        raise ValueError('Revision mismatch')
    paths = train_paths(s.rfilename for s in info.siblings)
    if len(paths) != 21:
        raise ValueError('Pinned training shard inventory changed')
    receipts, metadata = [], []
    def fetch_metadata(path):
        cached = RAW / 'browse-metadata' / (Path(path).stem + '.jsonl')
        if not cached.exists():
            rows = []
            fs = HfFileSystem(token=True, block_size=65536)
            with fs.open(f'datasets/{BROWSE_REPO}@{BROWSE_REV}/{path}', 'rb') as f:
                parquet = pq.ParquetFile(f)
                if set(META_COLUMNS + ['content_markdown']) - set(parquet.schema_arrow.names):
                    raise ValueError('Required columns absent')
                table = parquet.read(columns=META_COLUMNS)
                position = 0
                for group in range(parquet.num_row_groups):
                    size = parquet.metadata.row_group(group).num_rows
                    for offset, row in enumerate(table.slice(position, size).to_pylist()):
                        rows.append({**row, '_file': path, '_row_group': group, '_group_offset': offset})
                    position += size
            write_rows(cached, rows)
        print('Metadata shard complete:', Path(path).name, flush=True)
        return cached
    with ThreadPoolExecutor(max_workers=4) as executor:
        for cached in executor.map(fetch_metadata, paths):
            metadata.extend(read(cached))
            receipts.append({'path': str(cached.relative_to(ROOT)), 'sha256': sha256(cached.read_bytes())})
    if len(metadata) != 59000:
        raise ValueError('Expected 59000 labeled train pages')
    chosen, groups, excluded = browse_selection(metadata, args.pairs)
    write_rows(RAW / 'browse-pool-groups.jsonl', [{'pair_id': k, 'group': v} for k, v in sorted(groups.items())])
    wanted = set(chosen)
    locations = selected_groups(metadata, wanted)
    texts = []
    def fetch_text(location):
        path, group_ids = location
        cached = RAW / 'browse-selected' / (Path(path).stem + '.jsonl')
        if not cached.exists():
            rows = []
            fs = HfFileSystem(token=True, block_size=65536)
            with fs.open(f'datasets/{BROWSE_REPO}@{BROWSE_REV}/{path}', 'rb') as f:
                parquet = pq.ParquetFile(f)
                for row in parquet.read_row_groups(sorted(group_ids), columns=['entry_id', 'content_markdown']).to_pylist():
                    if row['entry_id'].rsplit('_', 1)[0] in wanted:
                        rows.append(row)
            write_rows(cached, rows)
        print('Text shard complete:', Path(path).name, flush=True)
        return cached
    with ThreadPoolExecutor(max_workers=4) as executor:
        for cached in executor.map(fetch_text, sorted(locations.items())):
            texts.extend(read(cached))
            receipts.append({'path': str(cached.relative_to(ROOT)), 'sha256': sha256(cached.read_bytes())})
    index = {r['entry_id']: r for r in metadata}
    if len(texts) != 2 * len(chosen) or len({r['entry_id'] for r in texts}) != len(texts):
        raise ValueError('Incomplete or duplicated selected text export')
    rows = [{**index[r['entry_id']], **r} for r in texts]
    write_rows(RAW / 'browse-train-selected.jsonl', sorted(rows, key=lambda r: r['entry_id']))
    record = {'version': 'browse-column-acquisition-v1', 'repository': BROWSE_REPO,
              'revision': BROWSE_REV, 'source_training_pages': len(metadata),
              'eligible_pairs': len(groups), 'exact_pool_components': len(set(groups.values())),
              'selected_pairs': len(chosen), 'selected_pages': len(rows),
              'metadata_exclusions': excluded, 'receipts': receipts,
              'output_sha256': sha256((RAW / 'browse-train-selected.jsonl').read_bytes()),
              'selection': 'One hash-ranked pair per exact task/reference component; 1000 hash-ranked components',
              'test_data_read': False, 'screenshot_columns_read': False,
              'pyarrow_version': pyarrow.__version__, 'huggingface_hub_version': huggingface_hub.__version__}
    report(OUT / 'browse-acquisition.json', record)
    print(json.dumps({k: record[k] for k in ['source_training_pages', 'exact_pool_components', 'selected_pairs']}))

if __name__ == '__main__':
    main()
