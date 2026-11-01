import copy
import unittest
from scripts.study_v6.resolve_review import resolve, source_label
from scripts.study_v6.common import canonical_bytes, sha256
from scripts.study_v6.resolved_plan import plan
from scripts.study_v5.prompts import conditions, native_payload


def fixture():
    rows = [{'id': 's:' + str(i), 'source': 'browsesafe', 'group': 'g:' + str(i//2),
             'pair_id': str(i//2), 'split_proposal': 'confirmation', 'upstream_label': i % 2,
             'candidate': 'Example content ' + str(i), 'task': 'Read this page', 'policy': None,
             'setting': 'indirect_tool_content', 'provenance': {}, 'semantic_gold': None,
             'inference_eligible': False} for i in range(6)]
    mapping = [{**row, 'review_id': 'r:' + str(i)} for i, row in enumerate(rows)]
    packet = [{k: r[k] for k in ('review_id', 'candidate', 'task', 'policy', 'setting')} for r in mapping]
    reviews = [{'review_id': r['review_id'], 'verdict': 'violation' if r['upstream_label'] else 'allowed',
                'group_merge_ids': '', 'ambiguity': 'none'} for r in mapping]
    return dict(rows=rows, mapping=mapping, packet=packet, reviews=reviews, group_records=[],
                links=[], edges=[], policy={'proposals': {}, 'cross_source_links': {}, 'limitations': []})


def proposal(args, pid, members, action='merge'):
    args['group_records'].append({'kind': 'merge_proposal', 'proposal_id': pid, 'proposal': 'merge',
        'source_ids': ['s:' + str(i) for i in members], 'review_ids': ['r:' + str(i) for i in members]})
    args['policy']['proposals'][pid] = {'action': action, 'reason': 'fixture decision'}


def link(args, a, b):
    args['links'].append({'source_ids': ['s:' + str(a), 's:' + str(b)]})
    args['reviews'][a]['group_merge_ids'] += ';r:' + str(b)


class ResolutionTests(unittest.TestCase):
    def test_dispute_quarantines_pair_without_relabeling(self):
        a = fixture(); a['reviews'][1]['verdict'] = 'allowed'
        before = copy.deepcopy(a)
        outputs, summary = resolve(**a)
        self.assertEqual(summary['quarantined_rows'], 2)
        self.assertIsNone(outputs['resolved'][1]['semantic_gold'])
        self.assertEqual(outputs['resolved'][1]['reviewed_verdict'], 'allowed')
        self.assertEqual(outputs['resolved'][0]['exclusion_reasons'], ['paired_member_excluded'])
        self.assertEqual(a, before)

    def test_unclear_and_exposure_fail_closed(self):
        a = fixture(); a['reviews'][0]['verdict'] = 'unclear'; a['exposure_ids'] = {'s:4'}
        outputs, summary = resolve(**a)
        self.assertEqual(summary['review_eligible_rows'], 2)
        self.assertTrue(all(not r['inference_eligible'] for r in outputs['resolved']))

    def test_transitive_merge_preserves_pair_and_split(self):
        a = fixture(); proposal(a, 'a', [0, 2]); proposal(a, 'b', [3, 4])
        outputs, summary = resolve(**a)
        self.assertEqual(summary['final_groups_all_rows'], 1)
        self.assertEqual(len({r['split_proposal'] for r in outputs['resolved']}), 1)

    def test_hold_excludes_entire_closed_component(self):
        a = fixture(); proposal(a, 'merge', [0, 2]); proposal(a, 'hold', [3], 'quarantine_component')
        outputs, summary = resolve(**a)
        self.assertEqual(summary['quarantined_rows'], 4)
        self.assertEqual([r['review_eligible'] for r in outputs['resolved']], [False]*4+[True]*2)

    def test_stale_id_repaired_only_in_derived_output(self):
        a = fixture(); a['rows'][0]['review_id'] = 'obsolete'
        outputs, summary = resolve(**a)
        self.assertEqual(summary['id_corrections'], 1)
        self.assertEqual(outputs['resolved'][0]['review_id'], 'r:0')
        self.assertEqual(a['rows'][0]['review_id'], 'obsolete')

    def test_content_join_mismatch_rejected(self):
        a = fixture(); a['mapping'][0]['candidate'] = 'different'
        with self.assertRaisesRegex(ValueError, 'Changed source fields'):
            resolve(**a)

    def test_incomplete_proposal_decisions_rejected(self):
        a = fixture(); proposal(a, 'a', [0, 2]); a['policy']['proposals'] = {}
        with self.assertRaisesRegex(ValueError, 'Every proposal'):
            resolve(**a)

    def test_dropped_or_unresolved_blinded_links_rejected(self):
        a = fixture(); link(a, 0, 2)
        with self.assertRaisesRegex(ValueError, 'Unresolved blinded'):
            resolve(**a)
        a['links'] = []
        with self.assertRaisesRegex(ValueError, 'locked review CSV'):
            resolve(**a)

    def test_explicit_weak_bridge_rejection_does_not_merge(self):
        a = fixture(); link(a, 0, 2)
        a['group_records'].append({'kind': 'cross_source_bridge_review', 'source_ids': ['s:0', 's:2'],
                                  'post_lock_disposition': 'weak'})
        a['policy']['cross_source_links']['weak'] = 'reject'
        outputs, summary = resolve(**a)
        self.assertEqual(summary['final_groups_all_rows'], 3)
        self.assertEqual(outputs['link-resolutions'][0]['disposition'], 'rejected_broad_or_unsupported_relation')

    def test_locked_self_link_is_retained_as_noop(self):
        a = fixture(); link(a, 0, 0)
        outputs, summary = resolve(**a)
        self.assertEqual(summary['final_groups_all_rows'], 3)
        self.assertEqual(outputs['link-resolutions'][0]['disposition'], 'same_final_component')

    def test_additional_link_quarantine(self):
        a = fixture(); link(a, 0, 2)
        key = sha256(canonical_bytes(['s:0', 's:2']))
        a['policy']['additional_links'] = {key: {'action': 'quarantine_component'}}
        _, summary = resolve(**a)
        self.assertEqual(summary['quarantined_rows'], 4)

    def test_group_assignment_independent_of_labels_and_row_order(self):
        a = fixture(); proposal(a, 'a', [0, 2]); out, _ = resolve(**a)
        a['rows'].reverse(); a['reviews'][3]['verdict'] = 'unclear'
        other, _ = resolve(**a)
        fields = lambda rs: {r['id']: (r['group'], r['split_proposal']) for r in rs}
        self.assertEqual(fields(out['resolved']), fields(other['resolved']))

    def test_labels_do_not_accept_unknown_conventions(self):
        self.assertEqual([source_label(x) for x in (0, 1, 'safe', 'unsafe')], [0, 1, 0, 1])
        for value in ('benign', 2, None, True):
            with self.assertRaises(ValueError): source_label(value)

    def test_binary_caveat_requires_distinct_complete_adjudication(self):
        a = fixture(); a['reviews'][0]['ambiguity'] = 'Only factual details may be missing.'
        outputs, summary = resolve(**a)
        self.assertEqual(summary['unresolved_review_actions'], 1)
        self.assertFalse(summary['review_resolution_complete'])
        self.assertFalse(outputs['resolved'][0]['review_eligible'])
        self.assertFalse(outputs['resolved'][1]['review_eligible'])
        a['adjudications'] = []
        with self.assertRaisesRegex(ValueError, 'complete caveat packet'): resolve(**a)
        a['adjudications'] = [{'review_id': 'r:0', 'verdict': 'allowed', 'ambiguity': 'none', 'group_merge_ids': ''}]
        outputs, summary = resolve(**a)
        self.assertTrue(summary['review_resolution_complete'])
        self.assertEqual(summary['review_eligible_rows'], 6)

    def test_disagreed_or_uncertain_adjudication_is_excluded(self):
        a = fixture(); a['reviews'][0]['ambiguity'] = 'Missing authority'
        for verdict, ambiguity, links in [('violation', 'none', ''), ('allowed', 'uncertain', ''), ('allowed', 'none', 'r:2')]:
            a['adjudications'] = [{'review_id': 'r:0', 'verdict': verdict, 'ambiguity': ambiguity, 'group_merge_ids': links}]
            outputs, summary = resolve(**a)
            self.assertTrue(summary['review_resolution_complete'])
            self.assertEqual(summary['quarantined_rows'], 4 if links else 2)

    def test_plan_checks_cached_exact_payload_and_keeps_group_prefix(self):
        a = fixture(); outputs, _ = resolve(**a); rows = outputs['resolved']
        # A planning fixture only: assign all complete groups to confirmation.
        for r in rows: r['split_proposal'] = 'confirmation'
        audit = [{'id': r['id'], 'condition': c, 'coverage_status': 'supported',
                  'payload_sha256': sha256(canonical_bytes(native_payload(r, c, 'laya_local'))),
                  'state_tokens': 10, 'head_tokens': 10, 'truncated': False}
                 for r in rows for c in conditions(r)]
        result, manifests = plan(rows, audit)
        self.assertEqual(result['primary_review_cleared_target_groups_before_route_coverage'], 3)
        self.assertEqual(sum(len(g['ids']) for g in manifests['primary-target']), 6)
        audit[0]['payload_sha256'] = 'bad'
        with self.assertRaisesRegex(ValueError, 'exact current request'): plan(rows, audit)


if __name__ == '__main__': unittest.main()
