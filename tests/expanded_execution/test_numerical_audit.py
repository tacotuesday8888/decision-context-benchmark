import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/expanded_execution'))
from verify_analysis import check_interval

class NumericalAuditTests(unittest.TestCase):
    def test_cluster_pair_members_stay_together(self):
        rows=[{'gold':g,'groups':{'document':d}} for d in ('a','b') for g in (0,1)]
        for balanced in (False,True):
            check_interval(rows,[1,1,-1,-1],'document',[-1,1],balanced)
            with self.assertRaises(AssertionError):
                check_interval(rows,[1,1,-1,-1],'document',[-.5,.5],balanced)
    def test_one_fixture_cannot_support_population_interval(self):
        rows=[{'gold':0,'groups':{'fixture':'one'}},{'gold':1,'groups':{'team':'a'}},{'gold':1,'groups':{'team':'b'}}]
        check_interval(rows,[0,1,0],'class_clusters',None,True)
        with self.assertRaises(AssertionError):check_interval(rows,[0,1,0],'class_clusters',[0,1],True)

    def test_figure_uses_named_document_interval_not_dictionary_order(self):
        from paper_figures import document_interval
        self.assertEqual(document_interval({'intervals':{'attack_family':{'interval':[-1,1]},'document':{'interval':[.1,.2]}}}),[.1,.2])
        self.assertEqual(document_interval({'intervals':[{'axis':'attack_family','interval':[-1,1]},{'axis':'document','interval':[.1,.2]}]}),[.1,.2])
