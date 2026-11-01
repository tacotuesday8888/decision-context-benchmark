import hashlib
import unittest

from scripts.study_v7.external_data import close, rank, select, validate


class ExternalSelectionTests(unittest.TestCase):
    def test_rank_has_frozen_nul_separated_identity(self):
        self.assertEqual(rank('x','y','z'), hashlib.sha256(b'study-v7-plan-20261101\0x\0y\0z').hexdigest())

    def test_actual_schema_and_labels_are_preserved(self):
        self.assertEqual(validate([{'prompt':'raw\n text','label':1}], 'test')[0]['prompt'],'raw\n text')
        for row in ({'prompt':'x','label':True},{'prompt':'x','label':2},{'prompt':'x','label':0,'task':'invented'}):
            with self.assertRaises(ValueError):
                validate([row],'test')

    def test_global_closure_quarantines_cross_split_and_contradictory(self):
        rows = validate([{'prompt':'one shared request','label':0},
                         {'prompt':'contradictory request','label':0},
                         {'prompt':'contradictory request','label':1}], 'test')
        rows += validate([{'prompt':'one shared request','label':0}], 'validation')
        eligible, edges, excluded, mixed = close(rows, [])
        self.assertFalse(eligible['test'])
        self.assertFalse(eligible['validation'])
        reasons={reason for x in excluded for reason in x['reasons']}
        self.assertEqual(reasons, {'cross_split_component','exact_contradictory_labels'})
        self.assertEqual(len(mixed),1)
        self.assertEqual(len(edges),2)

    def test_near_component_has_one_representative_before_label_sampling(self):
        text='alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike'
        rows=validate([{'prompt':text,'label':0},{'prompt':text+' november','label':1}], 'test')
        eligible, _, _, mixed=close(rows, [])
        self.assertEqual(len(eligible['test']),1)
        self.assertEqual(len(mixed),1)
        # A mixed-label component can never fill both class quotas.
        with self.assertRaises(ValueError):
            select(eligible,test_per_label=1,validation_per_label=0)

    def test_transitive_historical_touch_excludes_entire_component(self):
        text='alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo lima mike'
        rows=validate([{'prompt':text+' november','label':1}], 'test')
        eligible, _, excluded, _=close(rows,[{'id':'old','prompt':text,'split':'historical'}])
        self.assertFalse(eligible['test'])
        self.assertEqual(excluded[0]['reasons'],['historical_component'])


if __name__ == '__main__':
    unittest.main()
