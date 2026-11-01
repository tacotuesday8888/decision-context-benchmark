import copy
import unittest
from scripts.subscription_followup import extension_math as m


def group(gid,*,sol_effect=1,jev_effect=-1,missing=False):
    result=[]
    for model,effect in [('sol_subscription',sol_effect),('jev_firstparty',jev_effect)]:
        for condition in m.CONDITIONS:
            for label in (0,1):
                error=int((condition=='task')==(effect<0));prediction=label^error
                result.append({'id':f'{gid}:page{label}','group_id':gid,'config':model,'condition':condition,
                    'gold':label,'status':'unattempted' if missing else 'ok','valid':not missing,
                    'prediction':None if missing else prediction,'score':None if model=='sol_subscription' or missing else (.9 if prediction else .1),
                    'namespace':'subscription-followup-extension-v1','replicate':'first','stage':'secondary'})
    return result


class SourceMathTests(unittest.TestCase):
    def test_all66_planned_shared16_interaction_range_two_not_clipped(self):
        rows=[r for i in range(66) for r in group(f'g{i}')]
        result=m.analyze_source(rows)
        self.assertEqual(result['planned']['n'],66);self.assertEqual(result['shared_complete16']['n'],66)
        self.assertEqual(len(result['contrasts']),6);self.assertEqual(len(result['direct_interactions']),3)
        for contrast in result['contrasts']:
            expected=1 if contrast['config']=='sol_subscription' else -1
            self.assertEqual(contrast['primary_shared16']['mean'],expected)
            self.assertEqual(contrast['primary_shared16']['pointwise_95'],[expected,expected])
            self.assertEqual(contrast['primary_shared16']['draws'],20000)
        for interaction in result['direct_interactions']:
            self.assertEqual(interaction['primary_shared16']['mean'],2)
            self.assertEqual(interaction['primary_shared16']['pointwise_95'],[2,2])
            self.assertEqual(interaction['all_planned_missing_error_bounds']['range'],[2,2])
        self.assertNotIn('pvalues',result);self.assertTrue(result['descriptive_only'])

    def test_known_errors_retained_in_all_planned_bounds(self):
        result=m.analyze_source(group('known')+group('missing',missing=True))
        sol=next(c for c in result['contrasts'] if c['config']=='sol_subscription' and c['control']=='format')
        self.assertEqual(sol['all_planned_missing_error_bounds']['range'],[0,1])
        interaction=next(c for c in result['direct_interactions'] if c['control']=='format')
        self.assertEqual(interaction['all_planned_missing_error_bounds']['range'],[0,2])
        self.assertEqual(interaction['primary_shared16']['n'],1)
        self.assertEqual(interaction['all_planned_missing_error_bounds']['cohort']['n'],2)

    def test_model8_contrast4_pair8_sensitivities_have_distinct_cohorts(self):
        rows=group('complete')+group('partial')
        for row in rows:
            if row['group_id']=='partial' and row['config']=='jev_firstparty' and row['condition']=='length':
                row.update(status='http_error',valid=False,prediction=None,score=None)
        result=m.analyze_source(rows)
        self.assertEqual(result['shared_complete16']['n'],1)
        self.assertEqual(result['model_complete8']['sol_subscription']['n'],2)
        self.assertEqual(result['model_complete8']['jev_firstparty']['n'],1)
        format_jev=next(c for c in result['contrasts'] if c['config']=='jev_firstparty' and c['control']=='format')
        self.assertEqual(format_jev['contrast_complete4_sensitivity']['n'],2)
        format_pair=next(c for c in result['direct_interactions'] if c['control']=='format')
        self.assertEqual(format_pair['pair_contrast_complete8_sensitivity']['n'],2)
        self.assertNotEqual(format_pair['primary_shared16']['cohort']['group_ids_sha256'],format_pair['pair_contrast_complete8_sensitivity']['cohort']['group_ids_sha256'])

    def test_native_tie_is_missing_classification_but_retained_actual_score(self):
        rows=group('g')
        row=next(r for r in rows if r['config']=='jev_firstparty' and r['condition']=='format' and r['gold']==0)
        row.update(status='tie',valid=False,prediction=None,score=.5)
        result=m.analyze_source(rows)
        self.assertEqual(result['shared_complete16']['n'],0)
        self.assertEqual(result['native_score_diagnostics']['exact_ties'],1)
        self.assertEqual(result['native_score_diagnostics']['scored_cells'],8)
        metric=result['all_planned_available_output_metrics']['jev_firstparty']['format']
        self.assertEqual((metric['planned_clean'],metric['valid_clean'],metric['valid_attack']),(1,0,1))
        self.assertIsNone(metric['fpr']);self.assertIsNone(metric['balanced_error'])
        self.assertTrue(any(r['score']==.5 and r['namespace']=='subscription-followup-extension-v1' for r in result['native_score_diagnostics']['actual_score_records']))

    def test_purpose_seed_determinism_and_original_namespaces(self):
        rows=group('g0')+group('g1',sol_effect=-1,jev_effect=1)
        first=m.analyze_source(rows);second=m.analyze_source(list(reversed(rows)))
        self.assertEqual(first,second)
        self.assertEqual(first['seed'],'subscription-followup-extension-analysis-v1-20261101')
        purposes={c['primary_shared16']['purpose'] for c in first['contrasts']+first['direct_interactions']}
        self.assertEqual(len(purposes),9)
        self.assertEqual(first['direct_interactions'][0]['primary_shared16']['pointwise_95'],[-2,2])

    def test_duplicate_incomplete_plan_replicates_and_invented_scores_rejected(self):
        rows=group('g')
        for changed in [rows+rows[:1],rows[:-1]]:
            with self.assertRaises(ValueError):m.analyze_source(changed)
        for field,value in [('replicate','repeat-1'),('stage','main'),('score',.8)]:
            changed=copy.deepcopy(rows);changed[0][field]=value
            with self.assertRaises(ValueError):m.analyze_source(changed)


if __name__=='__main__':unittest.main()
