import unittest
from scripts.study_v6.common import rank
from scripts.study_v6.reviews import validate_complete
from scripts.study_v6.feasibility import group_prefix, PRIMARY_CONDITIONS

def record(key='a'):
    return {'id': key, 'source': 'browsesafe', 'group': key, 'setting': 'indirect_tool_content',
            'task': 'Summarize this notice.', 'policy': None, 'candidate': 'The museum opens at noon.'}

def review_fixture():
    packet = [{'review_id': 'a', 'candidate': 'The museum opens at noon.', 'task': 'Summarize.', 'policy': None}]
    session = {'reviewer_id': 'A', 'model_version': 'fixture-model', 'session_identifier': 'fixture',
               'blinding_declaration': 'Synthetic test only.', 'limitations': 'Not a real review.'}
    review = {'review_id': 'a', 'reviewer_id': 'A', 'reviewer_kind': 'agent',
              'reviewer_model_version': 'fixture-model', 'verdict': 'allowed',
              'rationale': 'This is ordinary opening-time information.', 'evidence_span': 'opens at noon',
              'context_needed': 'no', 'task_relation': 'related', 'instruction_type': 'ordinary_data',
              'ambiguity': 'none', 'group_merge_ids': ''}
    return packet, [review], session

class ReviewBudgetTests(unittest.TestCase):
    def test_complete_valid_review_and_unclear_are_lockable(self):
        packet, reviews, session = review_fixture()
        self.assertTrue(validate_complete(packet, reviews, session))
        reviews[0].update(verdict='unclear', evidence_span='', ambiguity='Insufficient context')
        self.assertTrue(validate_complete(packet, reviews, session))

    def test_incomplete_unknown_and_duplicate_ids_cannot_lock(self):
        packet, reviews, session = review_fixture()
        for rows in [[], reviews * 2, [{**reviews[0], 'review_id': 'unknown'}]]:
            with self.assertRaises(ValueError):
                validate_complete(packet, rows, session)

    def test_fabricated_evidence_and_unknown_group_are_rejected(self):
        packet, reviews, session = review_fixture()
        for update in [{'evidence_span': 'not actually there'}, {'group_merge_ids': 'unseen'},
                       {'context_needed': 'probably'}, {'reviewer_model_version': 'different'}]:
            with self.assertRaises(ValueError):
                validate_complete(packet, [{**reviews[0], **update}], session)

    def test_budget_keeps_whole_groups_and_same_provider_cohort(self):
        rows = [record('a'), {**record('b'), 'group': 'a'}]
        groups, spent, costs = group_prefix(rows, .1, lambda _: PRIMARY_CONDITIONS)
        self.assertEqual(groups, ['a'])
        self.assertEqual(set(spent), {'openai', 'typesafe'})
        # Identical payloads in one group are charged once per condition.
        _, single, _ = group_prefix(rows[:1], .1, lambda _: PRIMARY_CONDITIONS)
        self.assertEqual(spent, single)

    def test_budget_does_not_skip_expensive_first_group(self):
        ids = sorted(['a', 'b'], key=lambda g: rank('budget-order:' + g))
        rows = [record(i) for i in ids]
        rows[0]['candidate'] = 'Long complete page. ' * 10000
        groups, spent, _ = group_prefix(rows, .01, lambda _: PRIMARY_CONDITIONS)
        self.assertEqual(groups, [])
        self.assertTrue(all(v == 0 for v in spent.values()))
        self.assertTrue(group_prefix(rows[1:], .01, lambda _: PRIMARY_CONDITIONS)[0])

if __name__ == '__main__':
    unittest.main()
