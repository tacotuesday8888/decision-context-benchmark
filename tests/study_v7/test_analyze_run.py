"""Synthetic retained raw evidence; never real predictions, credentials or calls."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.study_v7 import analyze_run,requests


def fixture():
    main=[dict(id=f"m-{i}-{label}",group_id=f"g{i}",pair_id=f"p{i}",source="browsesafe",
        task=f"Synthetic task {i}",candidate=f"Synthetic page {i} {label}",upstream_label=label,
        partition="confirmation",input_sha256=requests.digest(f"m{i}{label}".encode()))
        for i in range(3) for label in (0,1)]
    external=[dict(id=f"e-{label}-{i}",group_id=f"eg-{label}-{i}",source="promptshield",
        candidate=f"Synthetic original request {label} {i}",upstream_label=label,partition="confirmation",
        general_subset=i==0,input_sha256=requests.digest(f"e{label}{i}".encode())) for label in (0,1) for i in range(2)]
    selection={"general_groups":["g0","g1"],"native_repeat_groups":["g0"],"general_repeat_groups":["g0"],
        "audit_groups":[],"external_general_ids":["e-0-0","e-1-0"]}
    plan=requests.build_plan(main,external,selection,sol_config="sol_subscription",sol_subscription_revision="v7.0.2")
    return plan,{r["id"]:r for r in main+external}


def write_attempt(root,request,rows,prediction=None):
    row=rows[request["id"]];pred=row["upstream_label"] if prediction is None else prediction
    directory=root/request["key"];directory.mkdir(parents=True)
    payload=requests.materialize(request,rows)
    (directory/"request.json").write_bytes(requests.canonical(payload))
    started=dict(key=request["key"],config=request["config"],namespace=request["namespace"],
        payload_sha256=request["payload_sha256"],route=requests.PANEL[request["config"]]["route"])
    (directory/"started.json").write_bytes(requests.canonical(started))
    (directory/"response.raw").write_text('Synthetic retained body; parser output is separately frozen.')
    parsed=dict(status="ok",valid=True,prediction=pred,returned_model=requests.PANEL[request["config"]]["model"])
    if request["config"]=="protectai_local":parsed["revision"]=requests.PANEL["protectai_local"]["revision"]
    if request.get("configuration_revision") is not None:parsed["configuration_revision"]=request["configuration_revision"]
    if request["config"] not in analyze_run.BOOLEAN:
        parsed["score"]=.9 if pred else .1
    result=dict(parsed=parsed,request_sha256=request["payload_sha256"],namespace=request["namespace"],
        first_attempt_primary=request["namespace"]=="first",configuration_revision=request.get("configuration_revision"),
        elapsed_seconds=.01,raw_hashes={p.name:requests.digest(p.read_bytes()) for p in directory.iterdir()})
    (directory/"completed.json").write_bytes(requests.canonical(result))


def populate(root,plan,rows):
    missing=set()
    for key,r in plan["requests"].items():
        if r["split"]!="confirmation" or r["namespace"]!="first":continue
        omit=(r["config"]=="jev_firstparty" and r["id"]=="m-0-0" and r["condition"]=="format" or
              r["config"]=="sol_subscription" and r["id"]=="m-1-1" and r["condition"]=="task" or
              r["config"]=="sol_subscription" and r["id"]=="e-1-0")
        if omit:
            missing.add(key)
            if r["id"]=="e-1-0":
                directory=root/key;directory.mkdir(parents=True)
                (directory/"interrupted.json").write_bytes(requests.canonical(dict(key=key,namespace="first",first_attempt_primary=True,payload_sha256=r["payload_sha256"])))
            continue
        wrong=r["config"]=="sol_subscription" and (r["id"]=="e-0-0" or r["group_id"]=="g0" and r["condition"]=="task")
        write_attempt(root,r,rows,1-rows[r["id"]]["upstream_label"] if wrong else None)
    # Repeat has a valid answer where the first native attempt is missing.
    repeat=next(r for r in plan["requests"].values() if r["namespace"]=="repeat-1" and r["config"]=="jev_firstparty" and r["id"]=="m-0-0" and r["condition"]=="format")
    write_attempt(root,repeat,rows)
    # Unknown legacy Sol result is intentionally not parseable: only directory
    # counts, never its output, may enter current-plan analysis.
    legacy=root/("f"*64);legacy.mkdir();(legacy/"completed.json").write_text("not read as a model result")
    return missing


class AnalyzeRunTests(unittest.TestCase):
    def test_first_attempt_missingness_subsets_and_matched_denominators(self):
        plan,source_rows=fixture()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);populate(root,plan,source_rows)
            rows,metadata=analyze_run.reconstruct_confirmation(plan,root)
            self.assertEqual(metadata["ignored_legacy_directories"],1)
            self.assertEqual(metadata["current_plan_nonconfirmation_or_repeat_directories"],1)
            missing=next(r for r in rows if r["config"]=="jev_firstparty" and r["id"]=="m-0-0" and r["condition"]=="format")
            self.assertEqual(missing["status"],"unattempted")
            self.assertFalse(missing["valid"])
            interrupted=next(r for r in rows if r["config"]=="sol_subscription" and r["id"]=="e-1-0")
            self.assertEqual(interrupted["status"],"interrupted_unknown")
            matched=analyze_run.matched_comparisons(plan,rows,draws=100)
            self.assertEqual(len(matched),34)
            main=next(r for r in matched if r["source"]=="browsesafe" and r["condition"]=="task" and r["left_config"]=="luna_responses" and r["right_config"]=="sol_subscription")
            self.assertEqual([main["planned_groups"],main["complete_groups"],main["planned_rows"],main["complete_rows"]],[2,1,4,2])
            self.assertEqual(main["complete_class_rows"],{"0":1,"1":1})
            self.assertEqual(main["mean_error_difference"],-1)
            external=next(r for r in matched if r["source"]=="promptshield" and r["left_config"]=="luna_responses" and r["right_config"]=="sol_subscription")
            self.assertEqual(external["planned_class_rows"],{"0":1,"1":1})
            self.assertEqual(external["complete_class_rows"],{"0":1,"1":0})
            self.assertEqual(external["mean_error_difference"],-1)
            self.assertEqual(external["interval_95"],[-1,-1])
            self.assertIn("not balanced error",external["estimand"])

    def test_driver_writes_saved_analysis_and_report_schemas_without_new_formulas(self):
        plan,source_rows=fixture()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);attempts=root/"attempts";populate(attempts,plan,source_rows)
            output=root/"output"
            receipt=analyze_run.analyze_run(plan,attempts,plan_sha256="a"*64,output_dir=output,draws=100,synthetic_fixture=True)
            self.assertEqual(receipt["network_or_model_calls"],0)
            primary=json.loads((output/"primary-analysis.json").read_text())
            self.assertEqual(primary["planned_groups"],3)
            self.assertEqual(primary["primary_complete_groups"],2)
            self.assertTrue(all(r["primary"]["test"]["n"]==2 for r in primary["contrasts"]))
            descriptive=json.loads((output/"descriptive-analysis.json").read_text())
            self.assertTrue(all(r["source"]=="promptshield" or r["config"] not in ("jev_firstparty","luna_decisions") for r in descriptive))
            sol=next(r for r in descriptive if r["source"]=="promptshield" and r["config"]=="sol_subscription")
            self.assertEqual(sol["score_diagnostics"]["n"],0)
            self.assertIsNone(sol["score_diagnostics"]["auroc"])
            self.assertTrue((output/"tables/analysis-tables.json").is_file())
            self.assertTrue((output/"figures/primary-contrasts.png").is_file())
            self.assertTrue((output/"matched-comparisons.csv").is_file())
            with self.assertRaisesRegex(ValueError,"explicitly synthetic"):
                analyze_run.analyze_run(plan,attempts,plan_sha256="a"*64,output_dir=output,draws=100)

    def test_started_revision_hash_and_original_labels_are_checked(self):
        plan,source_rows=fixture()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            request=next(r for r in plan["requests"].values() if r["namespace"]=="first" and r["config"]=="sol_subscription")
            write_attempt(root,request,source_rows)
            completed=root/request["key"]/"completed.json";result=json.loads(completed.read_text())
            result["configuration_revision"]="legacy"
            completed.write_bytes(requests.canonical(result))
            with self.assertRaisesRegex(ValueError,"configuration revision"):
                analyze_run.reconstruct_confirmation(plan,root)
            result["configuration_revision"]=request["configuration_revision"];completed.write_bytes(requests.canonical(result))
            started=root/request["key"]/"started.json";start=json.loads(started.read_text());start["config"]="luna_responses"
            started.write_bytes(requests.canonical(start))
            with self.assertRaisesRegex(ValueError,"Started first-attempt identity"):
                analyze_run.reconstruct_confirmation(plan,root)


if __name__=="__main__":unittest.main()
