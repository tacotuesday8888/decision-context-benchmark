"""Hand-computable synthetic tables/charts; no real predictions or source text."""
import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest

from scripts.study_v7 import report


def fixture():
    primary={"planned_groups":4,"primary_complete_groups":3,"primary_complete_group_ids":["g1","g2","g3"],
             "contrasts":[],"coverage":[],"raw_source_snippet":"excluded synthetic restricted text"}
    for model in ("jev_firstparty","luna_decisions"):
        for control in ("format","reminder","length"):
            primary["contrasts"].append({"config":model,"control":control,"task":"task",
                "primary":{"test":{"n":3,"mean":.25,"t":1.5,"df":2,"p":.2},
                    "intervals":{"pointwise_95":[.1,.4],"conservative_six_99_166667":[.05,.45],"draws":20000,"omitted_draws":0},
                    "holm6":{"adjusted_p":.8,"reject":False}},
                "contrast_complete_sensitivity":{"test":{"n":4,"mean":1/3}},
                "all_planned_error_difference_bounds":[-.125,.625]})
    descriptive=[{"source":"promptshield","config":"jev_firstparty","condition":"external",
        "planned_rows":100,"valid_rows":80,"coverage":.8,"confusion":{"tn":30,"fp":10,"fn":20,"tp":20},
        "fpr":.25,"fnr":.5,"balanced_error":.375,"status_counts":{"ok":80,"tie":10,"unsupported_over_limit":10},
        "intervals":{"fpr":[.1,.4],"fnr":[.3,.7],"balanced_error":[.2,.55],"brier":[.1,.3]},
        "score_diagnostics":{"n":90,"auroc":.75,"brier":.2,"reliability_10_fixed_bins":[
            {"lower":i/10,"upper":(i+1)/10,"n":9,"mean_score":(i+.5)/10,"attack_frequency":i/10} for i in range(10)]},
        "payload_text":"excluded synthetic restricted text"}]
    general=[{"source":"browsesafe","condition":"task","left_config":"luna_responses","right_config":"sol_subscription",
        "matched_cohort":True,"cohort_id":"synthetic-shared-cohort","planned_groups":4,"complete_groups":2,
        "planned_rows":8,"complete_rows":4,"mean_error_difference":.125,"interval_95":[-.25,.5]}]
    return primary,descriptive,general


class ReportTests(unittest.TestCase):
    def test_hand_values_units_and_explicit_denominators(self):
        primary,descriptive,general=fixture()
        output=report.build_tables(primary,descriptive,general)
        row=output["tables"]["primary_contrasts"][0]
        self.assertEqual(row["estimate_fraction"],.25)
        self.assertEqual(row["estimate_pp"],25)
        self.assertEqual(row["pointwise_95_lower_pp"],10)
        self.assertEqual(row["conservative_99_166667_upper_pp"],45)
        self.assertEqual(row["primary_complete_groups"],3)
        self.assertEqual(row["contrast_complete_groups"],4)
        self.assertEqual(row["contrast_complete_estimate_fraction"],1/3)
        bounds=output["tables"]["planned_bounds"][0]
        self.assertEqual([bounds["lower_pp"],bounds["upper_pp"]],[-12.5,62.5])
        self.assertFalse(bounds["is_confidence_interval"])
        external=output["tables"]["descriptive"][0]
        self.assertEqual(external["balanced_error"],.375)
        self.assertEqual(external["valid_benign_rows"],40)
        self.assertEqual(external["valid_attack_rows"],40)
        self.assertEqual(external["valid_rows"],80)
        self.assertEqual(external["scored_rows"],90)
        self.assertFalse(output["metadata"]["sources_pooled"])
        self.assertNotIn("excluded synthetic restricted text",json.dumps(output))
        self.assertEqual(output["tables"]["general_comparisons"][0]["complete_rows"],4)

    def test_rejects_changed_cohorts_invented_scores_or_unmatched_comparisons(self):
        primary,descriptive,general=fixture()
        primary["contrasts"][0]["primary"]["test"]["n"]=2
        with self.assertRaisesRegex(ValueError,"same complete-group cohort"):
            report.build_tables(primary)
        primary,descriptive,general=fixture()
        descriptive[0]["config"]="sol_subscription"
        with self.assertRaisesRegex(ValueError,"invented confidence"):
            report.build_tables(primary,descriptive)
        primary,descriptive,general=fixture()
        general[0]["matched_cohort"]=False
        with self.assertRaisesRegex(ValueError,"same-source matched cohort"):
            report.build_tables(primary,descriptive,general)
        with self.assertRaisesRegex(ValueError,"Duplicate descriptive"):
            report.build_tables(primary,descriptive+descriptive)

    def test_deterministic_csv_json_figures_and_chart_labels(self):
        primary,descriptive,general=fixture()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            left=report.write_report(primary,descriptive_summaries=descriptive,general_comparisons=general,output_dir=root/"left")
            right=report.write_report(primary,descriptive_summaries=descriptive,general_comparisons=general,output_dir=root/"right")
            self.assertEqual(left,right)
            with (root/"left/tables/primary-contrasts.csv").open() as handle:
                row=next(csv.DictReader(handle))
                self.assertEqual(float(row["estimate_pp"]),25)
                self.assertEqual(int(row["primary_complete_groups"]),3)
                self.assertEqual(int(row["planned_groups"]),4)
            svg=(root/"left/figures/primary-contrasts.svg").read_text()
            for label in ("95% pointwise","99.1667% per comparison","N=3","BrowseSafe++"):
                self.assertIn(label,svg)
            bounds=(root/"left/figures/planned-missingness-bounds.svg").read_text()
            self.assertIn("not confidence intervals",bounds)
            self.assertIn("planned N=4",bounds)
            external=(root/"left/figures/promptshield-error-coverage.svg").read_text()
            self.assertIn("PromptShield",external)
            self.assertIn("rows 80/100",external)
            self.assertNotIn("BrowseSafe++",external)
            self.assertTrue(all((root/"left"/name).is_file() for name in left["artifacts"]))


if __name__=="__main__":
    unittest.main()
