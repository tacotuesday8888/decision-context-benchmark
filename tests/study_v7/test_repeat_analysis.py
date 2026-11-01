"""Synthetic fresh-namespace repeat fixtures; no real outputs or model calls."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.study_v7 import repeat_analysis as repeat
from scripts.study_v7 import requests


def fixture():
    rows=[dict(id=f"page-{i}-{gold}",group_id=f"g{i}",pair_id=f"p{i}",source="browsesafe",
        task=f"Synthetic task {i}",candidate=f"Synthetic complete page {i} {gold}",upstream_label=gold,
        partition="confirmation",input_sha256=requests.digest(f"{i}-{gold}".encode())) for i in range(2) for gold in (0,1)]
    selection=dict(general_groups=["g0","g1"],native_repeat_groups=["g0","g1"],general_repeat_groups=["g0"],audit_groups=[],external_general_ids=[])
    plan=requests.build_plan(rows,[],selection,sol_config="sol_subscription",sol_subscription_revision="v7.0.2")
    return plan,{r["id"]:r for r in rows}


def write_attempt(root,request,rows, *, prediction=False,tie=False):
    directory=root/request["key"];directory.mkdir(parents=True)
    payload=requests.materialize(request,rows)
    (directory/"request.json").write_bytes(requests.canonical(payload))
    (directory/"started.json").write_bytes(requests.canonical(dict(key=request["key"],config=request["config"],
        namespace=request["namespace"],payload_sha256=request["payload_sha256"],route=requests.PANEL[request["config"]]["route"])))
    (directory/"response.raw").write_text("Synthetic retained response")
    parsed=dict(status="tie" if tie else "ok",valid=not tie,prediction=None if tie else int(prediction),
        returned_model=requests.PANEL[request["config"]]["model"])
    if request["config"] in repeat.NATIVE:parsed["score"]=.5 if tie else .9 if prediction else .1
    if request.get("configuration_revision") is not None:parsed["configuration_revision"]=request["configuration_revision"]
    result=dict(parsed=parsed,request_sha256=request["payload_sha256"],namespace=request["namespace"],
        first_attempt_primary=request["namespace"]=="first",configuration_revision=request.get("configuration_revision"),
        elapsed_seconds=.1,raw_hashes={p.name:requests.digest(p.read_bytes()) for p in directory.iterdir()})
    (directory/"completed.json").write_bytes(requests.canonical(result))


def populate(root,plan,rows):
    for request in plan["requests"].values():
        if request["namespace"] not in {"first","repeat-1"}:continue
        c,i,condition,namespace=(request[k] for k in ("config","id","condition","namespace"))
        if (c=="jev_firstparty" and i=="page-1-0" and condition=="format" and namespace=="repeat-1" or
            c=="luna_decisions" and i=="page-1-0" and condition=="task" and namespace=="first" or
            c=="luna_responses" and i=="page-0-0" and condition=="format" and namespace=="first"):
            continue
        prediction=False;tie=False
        if c=="jev_firstparty" and condition=="format":
            prediction=i=="page-0-1" or i=="page-0-0" and namespace=="repeat-1" or i=="page-1-0"
        if c=="luna_decisions" and condition=="task":
            tie=i=="page-0-0" and namespace=="first" or i=="page-0-1" and namespace=="repeat-1"
            prediction=i=="page-0-1" or namespace=="repeat-1"
        write_attempt(root,request,rows,prediction=prediction,tie=tie)


class RepeatAnalysisTests(unittest.TestCase):
    def test_page_ratio_group_bootstrap_and_complete_group_denominators(self):
        plan,rows=fixture()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);populate(root,plan,rows)
            result=repeat.analyze_repeats(plan,root,draws=1000,synthetic_fixture=True)
            self.assertEqual(len(result["summaries"]),16)
            row=next(r for r in result["summaries"] if r["config"]=="jev_firstparty" and r["condition"]=="format")
            self.assertEqual(row["planned_page_pairs"],4)
            self.assertEqual(row["both_valid_page_pairs"],3)
            self.assertEqual(row["both_valid_class_rows"],{"0":1,"1":2})
            self.assertEqual(row["first_valid_class_rows"],{"0":2,"1":2})
            self.assertEqual(row["repeat_valid_class_rows"],{"0":1,"1":2})
            self.assertEqual(row["disagreements"],1)
            self.assertAlmostEqual(row["paired_page_disagreement"]["mean"],1/3)
            self.assertEqual(row["paired_page_disagreement"]["interval_95"],[0,.5])
            self.assertEqual(row["complete_two_page_groups"],1)
            self.assertEqual(row["complete_group_mean_disagreement"],.5)
            self.assertEqual(row["complete_group_interval_95"],[.5,.5])
            self.assertAlmostEqual(row["native_absolute_score_change"]["mean"],.8/3)
            self.assertFalse(result["first_attempts_replaced"])
            self.assertFalse(result["p_values_calculated"])

    def test_ties_score_pairs_and_missing_first_never_replaced(self):
        plan,rows=fixture()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);populate(root,plan,rows)
            output=repeat.analyze_repeats(plan,root,draws=100,synthetic_fixture=True)
            native=next(r for r in output["summaries"] if r["config"]=="luna_decisions" and r["condition"]=="task")
            self.assertEqual(native["first_status_counts"],{"tie":1,"ok":2,"unattempted":1})
            self.assertEqual(native["first_tie_class_rows"],{"0":1,"1":0})
            self.assertEqual(native["repeat_tie_class_rows"],{"0":0,"1":1})
            self.assertEqual(native["both_valid_page_pairs"],1)
            self.assertEqual(native["native_scored_page_pairs_including_ties"],3)
            self.assertAlmostEqual(native["native_absolute_score_change"]["mean"],1.6/3)
            boolean=next(r for r in output["summaries"] if r["config"]=="luna_responses" and r["condition"]=="format")
            self.assertEqual(boolean["valid_first_pages"],1)
            self.assertEqual(boolean["valid_repeat_pages"],2)
            self.assertEqual(boolean["both_valid_page_pairs"],1)
            self.assertIsNone(boolean["native_absolute_score_change"])
            self.assertEqual(boolean["native_scored_page_pairs_including_ties"],0)

    def test_exact_payload_namespace_hash_and_production_draws(self):
        plan,rows=fixture()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);populate(root,plan,rows)
            with self.assertRaisesRegex(ValueError,"Reduced draws"):
                repeat.analyze_repeats(plan,root,draws=100)
            request=next(r for r in plan["requests"].values() if r["namespace"]=="repeat-1")
            (root/request["key"]/"response.raw").write_text("changed raw bytes")
            with self.assertRaisesRegex(ValueError,"raw evidence hash"):
                repeat.analyze_repeats(plan,root,draws=100,synthetic_fixture=True)
            request["payload_sha256"]="f"*64
            with self.assertRaisesRegex(ValueError,"exact first payload"):
                repeat.analyze_repeats(plan,root,draws=100,synthetic_fixture=True)

    def test_recorded_provider_ids_timestamps_and_duplicate_diagnostics(self):
        plan,rows=fixture()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);populate(root,plan,rows)
            for namespace in ("first","repeat-1"):
                request=next(r for r in plan["requests"].values() if r["config"]=="luna_responses" and r["id"]=="page-0-1" and r["condition"]=="format" and r["namespace"]==namespace)
                directory=root/request["key"]
                started=json.loads((directory/"started.json").read_text());started["started_at"]="2026-11-01T12:00:00+00:00"
                (directory/"started.json").write_bytes(requests.canonical(started))
                completed=json.loads((directory/"completed.json").read_text())
                completed["parsed"]["provider_request_id"]="synthetic-same-response-id"
                completed["observation"]={"response_headers":{"x-request-id":"synthetic-transport-"+namespace}}
                completed["finished_at"]="2026-11-01T12:00:01+00:00"
                completed["raw_hashes"]["started.json"]=requests.digest((directory/"started.json").read_bytes())
                (directory/"completed.json").write_bytes(requests.canonical(completed))
            result=repeat.analyze_repeats(plan,root,draws=100,synthetic_fixture=True)
            summary=next(r for r in result["summaries"] if r["config"]=="luna_responses" and r["condition"]=="format")
            self.assertEqual(summary["fresh_evidence_diagnostics"]["duplicate_provider_response_id_pairs"],1)
            self.assertEqual(summary["fresh_evidence_diagnostics"]["duplicate_provider_transport_request_id_pairs"],0)
            evidence=next(r for r in result["recorded_fresh_evidence"] if r["config"]=="luna_responses" and r["source_id"]=="page-0-1" and r["condition"]=="format")
            self.assertTrue(evidence["distinct_attempt_keys"])
            self.assertEqual(evidence["first"]["namespace"],"first")
            self.assertEqual(evidence["repeat"]["namespace"],"repeat-1")
            self.assertEqual(evidence["first"]["provider_response_id"],"synthetic-same-response-id")
            self.assertEqual(evidence["repeat"]["finished_at"],"2026-11-01T12:00:01+00:00")
            self.assertFalse(result["provider_ids_or_timestamps_invented"])


if __name__=="__main__":unittest.main()
