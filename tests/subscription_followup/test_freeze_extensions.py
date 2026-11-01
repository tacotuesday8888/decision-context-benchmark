"""Pure synthetic metadata freeze tests. No current response/auth/network reads."""
import copy
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.subscription_followup import freeze_extensions as f, extensions, budget
from scripts.study_v7.requests import canonical, digest


def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(value if isinstance(value,bytes) else canonical(value)+b"\n")
    return {"path":str(path),"sha256":digest(path.read_bytes())}


class FreezeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.patch=patch.object(extensions,"ROOT",self.root);self.patch.start();self.addCleanup(self.patch.stop)
        self.closure=patch.object(extensions,"verify_closed_core",return_value={"actual_cells":4510,
            "anchor":extensions.GLOBAL_ANCHOR,"deadline":extensions.GLOBAL_DEADLINE})
        self.verify=self.closure.start();self.addCleanup(self.closure.stop)
        self.now=budget._utc(extensions.GLOBAL_ANCHOR)+timedelta(hours=2)
        for name in f.STATIC_DOCS:write(self.root/name,b"Synthetic prospective document fixture\n")
        for name in f.SOURCE_PROVENANCE:
            path=self.root/"data/raw/subscription-followup/second-source"/name
            source=write(path,b"Synthetic licence/inventory fixture\n")
            write(path.with_suffix(path.suffix+".receipt.json"),{"sha256":source["sha256"],"authenticated":False,"repository_code_executed":False})
        write(self.root/"legacy.py",b"# frozen synthetic legacy dependency\n")
        dependency=digest((self.root/"legacy.py").read_bytes())
        failed=write(self.root/"closed-failure-evidence.json",b"Synthetic failed technical metadata bytes\n")
        continuation=write(self.root/"continuation.json",{"failed_request_key":f.OVERLOAD_KEY,"failure_code":"server_is_overloaded",
            "failure_http_status":200,"failure_type":"service_unavailable_error","failed_first_outcome":failed})
        self.core0=self.root/"core0.json"
        c0=write(self.core0,{"execution_directory":"data/raw/subscription-followup/closed0"})
        self.core1=self.root/f.CORE_MANIFEST
        self.core={"execution_directory":"data/raw/subscription-followup/closed1","frozen_files":{"legacy.py":dependency},
                   "closed_evidence":{"core_v1_receipt":continuation}}
        c1=write(self.core1,self.core)
        patcher=patch.object(extensions,"CORE_MANIFESTS",(c0["sha256"],c1["sha256"]));patcher.start();self.addCleanup(patcher.stop)
        self.lineage={"status":"closed","runs":[{"manifest_path":str(self.core0),"manifest_sha256":c0["sha256"]},
                     {"manifest_path":str(self.core1),"manifest_sha256":c1["sha256"]}]}
        self.lineage_path=self.root/"closed-lineage.json";write(self.lineage_path,self.lineage)
        events0=[{"kind":"fatal_failure","key":f.OVERLOAD_KEY,"http_status":200,"error_code":"server_is_overloaded"},
                 {"kind":"valid_response","key":"synthetic-valid-after-old"}]
        events1=[{"kind":"service_failure","key":"new-synthetic-503","http_status":503,"retry_after_seconds":120.},
                 {"kind":"valid_response","key":"synthetic-recovered"}]
        self.events0=self.root/"data/raw/subscription-followup/closed0/runtime-events.jsonl"
        self.events1=self.root/"data/raw/subscription-followup/closed1/runtime-events.jsonl"
        for path,events in ((self.events0,events0),(self.events1,events1)):
            write(path,b"".join(canonical(e)+b"\n" for e in events))
        self.owner={"experimental_inference_authorized":True,"authorization_source":"explicit_owner_instruction",
            "manifest_sha256":c0["sha256"],"human_turn":f.OWNER_TURN,"trusted_source_chat":f.OWNER_CHAT,
            "owner_instruction":f.OWNER_INSTRUCTION,"openai_subscription_only":True,"allow_paid_openai_api":False,
            "allow_purchases_or_recharge":False,"prior_typesafe_conservative_accounted_usd":budget.PRIOR["typesafe"],
            "typesafe_cumulative_cap_usd":budget.CAPS["typesafe"]}
        write(self.root/f.OWNER_FILE,self.owner)
        self.plan={"run_namespace":f.NAMESPACE,"total_cells":1128,"counts":{"sol_subscription":576,"jev_firstparty":552},
                   "group_counts":{"second_source":66,"isolated_agent":12},"pilot":{"version":"subscription-followup-isolated-agent-4"}}
        plan=write(self.root/"data/raw/subscription-followup/extensions-plan-v1.json",self.plan)
        rows=write(self.root/f.INPUTS["source_rows"],b"Synthetic complete selected source bytes\n")
        schedule=write(self.root/f.INPUTS["source_schedule"],{"groups":"fixed-counterbalanced-fixture"})
        pilot=write(self.root/f.INPUTS["pilot_plan"],{"version":"subscription-followup-isolated-agent-4"})
        for key in ("source_capacity","source_audit","source_precision"):
            write(self.root/f.INPUTS[key],{"synthetic_fixture":True})
        selection={"selection_manifest_sha256":"a"*64,"selected_groups":66,"selected_rows":132,
                   "historically_exposed_components":0,"preparation_code_sha256":{"legacy.py":dependency},"source_file_proofs":[]}
        write(self.root/f.INPUTS["source_selection"],selection)
        write(self.root/f.INPUTS["pilot_preparation"],{"plan":{"sha256":pilot["sha256"]}})
        prep={"plan":{"path":str(Path(plan["path"]).relative_to(self.root)),"sha256":plan["sha256"]},
              "code_sha256":{"legacy.py":dependency},"inputs":{"source_rows":rows}}
        write(self.root/f.INPUTS["extension_preparation"],prep)
        review={"status":"pass","remaining_preparation_findings":[],"execution_not_authorized_by_this_review":True,
                "inputs":{Path(path).name:digest((self.root/path).read_bytes()) for key,path in f.INPUTS.items() if key in
                    ("extension_preparation","source_selection","source_capacity","source_audit","source_precision","pilot_preparation")}}
        write(self.root/f.INPUTS["preparation_review"],review)
        patcher=patch.multiple(f,PLAN_SHA=plan["sha256"],SOURCE_ROWS_SHA=rows["sha256"],SOURCE_MANIFEST_SHA="a"*64,
                              SOURCE_SCHEDULE_SHA=schedule["sha256"],PILOT_PLAN_SHA=pilot["sha256"])
        patcher.start();self.addCleanup(patcher.stop)

    def freeze(self):return f.freeze(self.lineage_path,root=self.root,now=self.now)

    def test_exact_scope_owner_binding_analysis_and_two_prior_failures_no_self_review(self):
        result=self.freeze();m=json.loads(Path(result["manifest"]["path"]).read_text());a=json.loads(Path(result["owner_authorization"]["path"]).read_text())
        self.assertEqual(a["manifest_sha256"],result["manifest"]["sha256"])
        self.assertEqual((a["max_sol_calls"],a["max_jev_calls"]),(576,552));self.assertEqual(m["plan_cells"],1128)
        self.assertEqual(m["maximum_jev_full_context_reservation_usd"],"0.741888")
        self.assertFalse(m["lanes"]["sol_general"]["enabled"]);self.assertFalse(m["lanes"]["blind_audit"]["enabled"])
        self.assertTrue(m["lanes"]["second_source"]["enabled"]);self.assertTrue(m["lanes"]["isolated_agent"]["enabled"])
        self.assertEqual(m["analysis"]["seed"],f.SEED);self.assertEqual(m["analysis"]["bootstrap_draws"],20000)
        self.assertEqual(m["global_clock_anchor_utc"],extensions.GLOBAL_ANCHOR);self.assertEqual(m["global_deadline_utc"],extensions.GLOBAL_DEADLINE)
        self.assertEqual(len(m["prior_transient_failure_events"]),2)
        self.assertEqual([e["http_status"] for e in m["prior_transient_failure_events"]],[200,503])
        self.assertEqual(m["prior_consecutive_service_failures"],0)
        self.assertEqual(a["owner_instruction"],f.OWNER_INSTRUCTION)
        self.assertTrue(a["independent_review_still_required"]);self.assertFalse(result["review_created"])
        self.assertFalse(result["inference_performed"])
        self.assertEqual(len(list((self.root/"results/subscription-followup").glob("*pre-execution-review*"))),0)
        self.assertEqual(self.freeze(),result)

    def test_closed_core_verifier_is_first_gate_and_cannot_create_partial_outputs(self):
        self.verify.side_effect=PermissionError("Core still active")
        with self.assertRaises(PermissionError):self.freeze()
        self.assertFalse((self.root/"results/subscription-followup/run-manifest-extensions-v1.json").exists())
        self.assertFalse((self.root/"results/subscription-followup/owner-authorization-extensions-v1.json").exists())

    def test_preserve_trailing_consecutive_event_and_reject_exhausted_bound(self):
        write(self.events1,canonical({"kind":"service_failure","key":"new-503","http_status":503,"retry_after_seconds":120})+b"\n")
        result=self.freeze();m=json.loads(Path(result["manifest"]["path"]).read_text())
        self.assertEqual(m["prior_consecutive_service_failures"],1)
        self.assertEqual(len(m["prior_transient_failure_events"]),2)

    def test_derive_three_or_more_final_events_instead_of_static_count(self):
        events=[]
        for i in range(2):
            events.extend([{"kind":"service_failure","key":f"new-503-{i}","http_status":503,"retry_after_seconds":120},
                           {"kind":"valid_response","key":f"recovered-{i}"}])
        write(self.events1,b"".join(canonical(e)+b"\n" for e in events))
        result=self.freeze();m=json.loads(Path(result["manifest"]["path"]).read_text())
        self.assertEqual(len(m["prior_transient_failure_events"]),3)
        self.assertEqual(m["prior_consecutive_service_failures"],0)

    def test_changed_owner_plan_or_dependency_fails_before_new_permit(self):
        self.owner["allow_paid_openai_api"]=True;write(self.root/f.OWNER_FILE,self.owner)
        with self.assertRaises(ValueError):self.freeze()
        self.owner["allow_paid_openai_api"]=False;write(self.root/f.OWNER_FILE,self.owner)
        write(self.root/"legacy.py",b"changed")
        with self.assertRaises(ValueError):self.freeze()
        self.assertFalse((self.root/"results/subscription-followup/run-manifest-extensions-v1.json").exists())

    def test_duplicate_or_long_retry_event_and_expired_clock_refuse_freeze(self):
        duplicate={"kind":"service_failure","key":"same-key","http_status":503,"retry_after_seconds":120}
        write(self.events1,canonical(duplicate)+b"\n"+canonical(duplicate)+b"\n")
        with self.assertRaises(ValueError):self.freeze()
        write(self.events1,canonical(dict(duplicate,retry_after_seconds=601))+b"\n")
        with self.assertRaises(ValueError):self.freeze()
        write(self.events1,canonical({"kind":"valid_response","key":"good"})+b"\n")
        self.now=budget._utc(extensions.GLOBAL_DEADLINE)
        with self.assertRaises(ValueError):self.freeze()

    def test_existing_different_output_is_never_replaced(self):
        path=self.root/"results/subscription-followup/owner-authorization-extensions-v1.json"
        write(path,b"existing immutable object")
        with self.assertRaises(ValueError):self.freeze()
        self.assertEqual(path.read_bytes(),b"existing immutable object")
        self.assertFalse((self.root/"results/subscription-followup/run-manifest-extensions-v1.json").exists())


if __name__=="__main__":unittest.main()
