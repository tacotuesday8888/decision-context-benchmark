"""Small lexical fixtures; source text and model calls are never required."""
import collections
import hashlib
import random
import unittest

from scripts.study_v6.common import Union, near_links, shingles
from scripts.study_v7.main_data import (
    compact_near_links, compact_shingles, component_map, english, exact_text_edges,
    metadata_components, rank,
)


def test_rank_is_exact_null_delimited_protocol():
    expected = hashlib.sha256('\0'.join(('study-v7-plan-20261101', 'browsesafe', 'audit', '123')).encode()).hexdigest()
    assert rank('browsesafe', 'audit', '123') == expected
    assert rank('browsesafe', 'audit', '123') != rank('browsesafe', 'partition', '123')


def check_compact_exact_join_matches_independent_brute_force(threshold):
    rng = random.Random(73)
    base = 'one two three four five six seven eight nine ten eleven twelve'.split()
    texts = ['', 'one two', ' '.join(base), ' '.join(base).upper()]
    for _ in range(40):
        words = base.copy()
        for __ in range(rng.randrange(6)):
            words[rng.randrange(len(words))] = rng.choice(['apple', 'pear', 'orange', 'banana'])
        texts.append(' '.join(words))
    sets = [shingles(t) for t in texts]
    expected = []
    for i, group in enumerate(sets):
        for j in range(i):
            other = sets[j]
            if min(len(group), len(other)) < 5:
                continue
            score = len(group & other)/len(group | other)
            if score >= threshold:
                expected.append((j, i, score))
    assert compact_near_links(texts, threshold) == expected
    assert compact_near_links(texts, threshold) == near_links(texts, threshold)


def test_compact_exact_join_matches_independent_brute_force():
    for threshold in (.5, .8):
        check_compact_exact_join_matches_independent_brute_force(threshold)


def test_cross_history_join_finds_only_cross_edges():
    texts = ['one two three four five six seven eight nine'] * 2
    texts += ['one two three four five six seven eight ten'] * 2
    whole = compact_near_links(texts, .5)
    expected = [r for r in whole if r[0] < 2 <= r[1]]
    assert compact_near_links(texts, .5, historical_count=2) == expected


def test_packed_shingles_preserve_exact_unique_trigram_sizes():
    values = ['Ａ one TWO three one two three four five', 'one TWO three one two three four five']
    result = compact_shingles(values)
    assert [len(v) for v in result] == [len(shingles(v)) for v in values]


def pair(key, task, reference=''):
    rows = []
    for suffix, arm, label in [('benign', 'control', 'no'), ('malicious', 'attack', 'yes')]:
        rows.append({'entry_id': f'{key}_{suffix}', 'split': 'train', 'arm': arm,
                     'label': label, 'benign_task': task,
                     'injection_text_fragments_json': [reference] if reference else [],
                     'attack_quotes_json': []})
    return rows


def test_metadata_component_closes_prior_rejected_relatives_transitively():
    rows = pair('1', 'task a', 'one two three four five six')
    rows += pair('2', 'task b', 'one two three four five six')
    rows += pair('3', 'task b')
    rows += pair('4', 'separate task')
    pairs, ids, positions, union, edges, excluded = metadata_components(rows)
    groups = component_map(ids, positions, union)
    held = {groups['1']}  # Rejected or accepted historical selection makes no difference.
    assert {key for key in ids if groups[key] in held} == {'1', '2', '3'}
    assert groups['4'] not in held
    assert not excluded
    assert collections.Counter(e['axis'] for e in edges) == {'reference': 1, 'task': 1}


def test_exact_historical_hits_hold_all_members_and_closure_propagates():
    union, positions, edges = Union(3), {'1': 0, '2': 1, '3': 2}, []
    held = exact_text_edges(['old text', 'OLD TEXT', 'same candidate', 'same candidate'],
                            ['historical:1', '1', '2', '3'], 'candidate',
                            union, positions, edges, old_count=1)
    assert held == {'1'}
    assert union.find(1) == union.find(2)
    assert union.find(0) != union.find(1)
    assert len(edges) == 2


def test_unselected_prior_component_document_can_exclude_fresh_task():
    # Pair2 was never selected, but shares the prior pair1 metadata component.
    rows = pair('1', 'old unrelated task', 'shared reference one two three four five')
    rows += pair('2', 'second unrelated task', 'shared reference one two three four five')
    rows += pair('3', 'fresh task on another topic')
    _, ids, positions, union, _, _ = metadata_components(rows)
    groups = component_map(ids, positions, union)
    relatives = {key for key in ids if groups[key] == groups['1']}
    assert relatives == {'1', '2'}
    document_a = 'red green blue yellow purple orange white black silver gold'
    document_b = 'train station timetable departure arrival platform passenger ticket conductor engine'
    fresh_document = document_b + ' notice'
    # Screening only the actually selected document misses this fresh relative.
    assert compact_near_links([document_a, fresh_document], .5, historical_count=1) == []
    # Complete prior-component document acquisition catches it with a different task.
    hits = compact_near_links([document_a, document_b, fresh_document], .5, historical_count=2)
    assert [(j, i) for j, i, _ in hits] == [(1, 2)]
    assert hits[0][2] >= .5


def test_english_requires_both_pages_and_payload_without_invented_control_payload():
    arms = {'benign': {'language_page': ['en'], 'language_payload': None},
            'malicious': {'language_page': ['en'], 'language_payload': ['en']}}
    assert english(arms)
    arms['malicious']['language_payload'] = ['en', 'es']
    assert not english(arms)


def test_mislabeled_source_arm_fails_before_selection():
    rows = pair('1', 'task')
    rows[1]['label'] = 'no'
    with unittest.TestCase().assertRaisesRegex(ValueError, 'inconsistent arm/label'):
        metadata_components(rows)


def load_tests(loader, suite, pattern):
    return unittest.TestSuite(unittest.FunctionTestCase(function) for name, function
                              in sorted(globals().items()) if name.startswith('test_'))
