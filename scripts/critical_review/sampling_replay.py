"""Archive the original 20,000 multinomial draws for one nonportable rate table.

Generation is permitted only if the draws reproduce all original endpoints
exactly. This is an offline replay capsule, not a changed bootstrap analysis.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path

import numpy as np

from scripts.subscription_followup import analyze_core as core

ROOT = Path(__file__).resolve().parents[2]
PURPOSE = 'all_planned_available/jev_firstparty/task/classification-rates'


def sampling_inputs():
    path = ROOT / 'results/subscription-followup-execution/main-first-outcomes.jsonl'
    groups = core.index_main([json.loads(x) for x in path.read_text().splitlines()])
    vectors = []
    for gid in sorted(groups):
        clean, attack = (groups[gid]['jev_firstparty', 'task', label] for label in (0, 1))
        vectors.append([core._error(clean) or 0, int(core._valid(clean)), core._error(attack) or 0, int(core._valid(attack))])
    support, counts = np.unique(np.asarray(vectors, dtype=float), axis=0, return_counts=True)
    seed = int.from_bytes(hashlib.sha256(f'{core.SEED}\0{PURPOSE}'.encode()).digest()[:8], 'big')
    return support, counts, seed


def intervals(draws, support):
    totals = draws @ support
    assert np.all(totals[:, 1] > 0) and np.all(totals[:, 3] > 0)
    clean = totals[:, 0] / totals[:, 1]
    attack = totals[:, 2] / totals[:, 3]
    return {name: np.quantile(value, [.025, .975], method='linear').tolist()
            for name, value in [('fpr', clean), ('fnr', attack), ('balanced_error', (clean + attack) / 2)]}


def numeric_hash(array):
    return hashlib.sha256(array.astype('<u8').tobytes()).hexdigest()


def generate(output):
    from scripts.critical_review.verify import read, sha, write_new
    support, counts, seed = sampling_inputs()
    draws = np.random.default_rng(seed).multinomial(500, counts / 500, size=20000)
    saved = read(ROOT / 'results/subscription-followup-execution/core-analysis-v1.json')['main']['all_planned_available_output_metrics']['jev_firstparty']['task']['rate_intervals']
    for name, value in intervals(draws, support).items():
        if value != saved[name]['pointwise_95']:
            raise ValueError('This environment does not regenerate the original draws; use the committed replay capsule.')
    buffer = io.BytesIO()
    np.savez_compressed(buffer, draws=draws.astype('<u2'), support=support, counts=counts)
    output.mkdir(parents=True, exist_ok=True)
    target = output / 'core-rate-sampling-v1.npz'
    with target.open('xb') as stream:
        stream.write(buffer.getvalue())
    write_new(output / 'core-rate-sampling-v1.json', {
        'version': 'core-rate-sampling-replay-1', 'draws': 20000, 'groups': 500,
        'purpose': PURPOSE, 'seed': core.SEED, 'derived_seed': seed,
        'support': support.tolist(), 'counts': counts.tolist(),
        'probabilities_hex': [x.hex() for x in counts / 500],
        'original_endpoint_check': 'exact', 'draws_sha256': numeric_hash(draws),
        'pcg64_first64_raw_sha256': numeric_hash(np.random.default_rng(seed).bit_generator.random_raw(64)),
        'npz_sha256': sha(target), 'numpy': np.__version__,
        'input_sha256': sha(ROOT / 'results/subscription-followup-execution/main-first-outcomes.jsonl'),
        'frozen_analysis_code_sha256': sha(Path(core.__file__)),
        'scope': 'One archived-native available-output rate table; no primary effects or outcomes changed'})


def replay():
    from scripts.critical_review.verify import read, sha
    base = ROOT / 'results/critical-review'
    metadata = read(base / 'core-rate-sampling-v1.json')
    assert sha(base / 'core-rate-sampling-v1.npz') == metadata['npz_sha256']
    assert sha(Path(core.__file__)) == metadata['frozen_analysis_code_sha256']
    assert sha(ROOT / 'results/subscription-followup-execution/main-first-outcomes.jsonl') == metadata['input_sha256']
    support, counts, seed = sampling_inputs()
    with np.load(base / 'core-rate-sampling-v1.npz', allow_pickle=False) as saved:
        draws = saved['draws'].astype(np.int64)
        assert np.array_equal(support, saved['support']) and np.array_equal(counts, saved['counts'])
    assert draws.shape == (20000, len(counts)) and np.all(draws.sum(axis=1) == 500)
    assert numeric_hash(draws) == metadata['draws_sha256']
    assert [x.hex() for x in counts / 500] == metadata['probabilities_hex']
    raw_hash = numeric_hash(np.random.default_rng(seed).bit_generator.random_raw(64))
    current = np.random.default_rng(seed).multinomial(500, counts / 500, size=20000)
    return intervals(draws, support), {
        'original_draws_sha256': metadata['draws_sha256'], 'current_draws_sha256': numeric_hash(current),
        'same_multinomial_draws': np.array_equal(draws, current),
        'same_pcg64_first64_raw': raw_hash == metadata['pcg64_first64_raw_sha256'],
        'identical_support_counts_and_probability_bits': True,
        'replay_from_archived_draws': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    generate(parser.parse_args().output)
