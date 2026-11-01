"""Synthetic extension runtime contracts. Never read real attempts or credentials."""
from collections import Counter
import contextlib
import copy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.subscription_followup import extensions as x, budget as b, pilot, run, transport
from scripts.subscription_followup.continuation_budget import ORIGINAL_START
from scripts.study_v7.requests import canonical, digest, _responses
from scripts.study_v5.prompts import INDIRECT

END = (b._utc(ORIGINAL_START)+timedelta(seconds=18000)).isoformat()


def write(path, value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(value if isinstance(value,bytes) else canonical(value)+b"\n")
    return {"path":str(path),"sha256":digest(path.read_bytes())}


def synthetic_plan(namespace):
    groups=[]
    for i in range(66):
        gid=f"secondary:synthetic:{i}";cells=[]
        for config in ("jev_firstparty","sol_subscription"):
            for arm in ("clean","attack"):
                for condition in ("format","task","reminder","length"):
                    text=f"Synthetic complete observation {i}/{arm}/{condition}"
                    body=({"model":"jev-1.14.0","state":text,
                           "questions":{"injection":{"type":"noul","instructions":INDIRECT}}}
                          if config=="jev_firstparty" else _responses(config,text,INDIRECT,configuration_revision="v7.0.2"))
                    cells.append({"cell_id":f"secondary:{i}:{config}:{arm}:{condition}","group_id":gid,
                        "stage":"secondary","config":config,"namespace":namespace,"kind":"classification",
                        "payload":body,"payload_sha256":digest(canonical(body))})
        groups.append({"lane":"second_source","stage":"secondary","group_id":gid,"cells":cells})
    authored=pilot.build_plan(run_namespace=namespace)
    for original in authored["groups"]:
        g=copy.deepcopy(original);gid="isolated_agent:"+g["source_group_id"];g["group_id"]=gid
        for c in g["cells"]:c.update(group_id=gid,namespace=namespace)
        groups.append(g)
    return {"groups":groups,"total_cells":1128,"run_namespace":namespace}


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve()
        patcher=patch.object(x,"ROOT",self.root);patcher.start();self.addCleanup(patcher.stop)
        for owner,name in ((transport,"_credential"),(transport,"_post"),(x,"invoke"),(run,"invoke")):
            patcher=patch.object(owner,name,side_effect=AssertionError("Offline fixture cannot invoke transport"))
            spy=patcher.start();self.addCleanup(patcher.stop);self.addCleanup(spy.assert_not_called)
        self.namespace="subscription-followup-extension-synthetic"
        self.plan=synthetic_plan(self.namespace);self.planpath=self.root/"plan.json";self.plan_binding=write(self.planpath,self.plan)
        self.prior=self.root/"prior.jsonl";write(self.prior,b"closed synthetic inherited accounting\n")
        self.prior_receipt=self.root/"prior-receipt.json"
        write(self.prior_receipt,{"accounting":{"cumulative_conservative_accounted_usd":b.PRIOR,"unknown_v7_full_holds_usd":b.PRIOR_UNKNOWN},
             "journal":{"sha256":digest(self.prior.read_bytes()),"no_reserved_or_dispatched_entries":True}})
        for name,path in (("PRIOR_JOURNAL_SHA256",self.prior),("PRIOR_RECEIPT_SHA256",self.prior_receipt)):
            patcher=patch.object(b,name,digest(path.read_bytes()));patcher.start();self.addCleanup(patcher.stop)
        self.core=self.root/"data/raw/subscription-followup/synthetic-closed-core";self.core.mkdir(parents=True)
        self.core_manifest=self.root/"core-manifest.json"
        core_plan=write(self.root/"synthetic-core-plan.json",{"groups":[{"cells":[
            {"cell_id":f"old-core:{i}","payload_sha256":"d"*64} for i in range(4510)]}]})
        self.core_manifest_binding=write(self.core_manifest,{"execution_directory":str(self.core.relative_to(self.root)),"plan":core_plan})
        self.core_journal=write(self.core/"accounting.jsonl",b"synthetic closed core journal\n")
        self.core_snapshot=write(self.core/"final-ledger-snapshot.json",{"terminal":True,"all_in_accounted_usd":b.PRIOR,
            "window_started_at_utc":ORIGINAL_START,"incremental_accounted_usd":{"openai":"0","typesafe":"0"},"entries":{}})
        self.core_stop=write(self.core/"STOP.json",{"status":"closed","manifest_sha256":self.core_manifest_binding["sha256"],
            "journal_sha256":self.core_journal["sha256"]})
        self.lineage={"status":"closed","global_clock_anchor_utc":ORIGINAL_START,"global_deadline_utc":END,"runs":[{
            "manifest_path":str(self.core_manifest),"manifest_sha256":self.core_manifest_binding["sha256"],
            "journal_path":self.core_journal["path"],"journal_sha256":self.core_journal["sha256"],
            "snapshot_path":self.core_snapshot["path"],"snapshot_sha256":self.core_snapshot["sha256"],
            "stop_path":self.core_stop["path"],"stop_sha256":self.core_stop["sha256"],"plan_sha256":core_plan["sha256"]}]}
        self.lineage["runs"].append(copy.deepcopy(self.lineage["runs"][0]))
        self.lineagepath=self.root/"core-lineage.json";self.lineage_binding=write(self.lineagepath,self.lineage)
        # Full real-shaped ancestor replay is independently reviewed separately.
        # Runtime fixtures mock that read-only boundary; fail-closed/hash tests
        # below explicitly restore the real verifier for the early rejection path.
        self.real_verify_closed_core=x.verify_closed_core
        patcher=patch.object(x,"verify_closed_core",return_value={"actual_cells":4510,"anchor":ORIGINAL_START,"deadline":END})
        self.lineage_verifier=patcher.start();self.addCleanup(patcher.stop)
        self.execution=self.root/"data/raw/subscription-followup/execution-synthetic";self.execution.mkdir()
        lanes={name:{"enabled":name in ("second_source","isolated_agent")} for name in b.LANES}
        lanes["isolated_agent"].update(pilot_ready=True,pilot_receipt_sha256="c"*64)
        self.m={"run_namespace":self.namespace,"routes":copy.deepcopy(b.ROUTES),"lanes":lanes,"workers":1,
            "execution_directory":str(self.execution.relative_to(self.root)),"plan":self.plan_binding,"frozen_files":{},
            "closed_evidence":{"receipt":{"path":str(self.prior_receipt),"sha256":digest(self.prior_receipt.read_bytes())},
                               "journal":{"path":str(self.prior),"sha256":digest(self.prior.read_bytes())}},
            "core_collection_lineage":self.lineage_binding,"global_clock_anchor_utc":ORIGINAL_START,"global_deadline_utc":END}
        self.manifest=self.root/"manifest.json";self.authpath=self.root/"authorization.json";self.reviewpath=self.root/"review.json"
        self.bind_manifest()
        self.now=b._utc(ORIGINAL_START)+timedelta(hours=1)
        # Keep permit checks on the same synthetic clock as the fixture ledger.
        # Real wall time must not expire offline tests after the frozen run ends.
        patcher=patch.object(x,"datetime",wraps=datetime)
        self.permit_clock=patcher.start();self.addCleanup(patcher.stop)
        self.permit_clock.now.side_effect=lambda tz=None:self.now.astimezone(tz)

    def bind_manifest(self):
        write(self.manifest,self.m);sha=digest(self.manifest.read_bytes())
        self.auth={"experimental_inference_authorized":True,"authorization_source":"explicit_owner_instruction",
            "manifest_sha256":sha,"openai_subscription_only":True,"allow_paid_openai_api":False,
            "allow_purchases_or_recharge":False,"max_sol_calls":576,"max_jev_calls":552}
        write(self.authpath,self.auth);write(self.reviewpath,{"status":"pass","remaining_findings":[],"manifest_sha256":sha})

    def permit(self):
        p=x.ExtensionPermit(self.manifest,self.authpath,self.reviewpath)
        p.policy=x.freeze_policy(self.manifest)
        p.ledger=x.ExtensionLedger(self.execution/"accounting.jsonl",p.policy,clock=lambda:self.now)
        return p

    def gate_evidence(self,p,g,scores=(.2,.8),statuses=("ok","ok")):
        gates=[c for c in g["cells"] if c["kind"]=="gate"]
        specs=[p.spec(g,c) for c in gates]
        p.ledger.reserve_group(g["lane"],g["group_id"],specs,batch_id=g["group_id"]+":gate")
        paths=[]
        for c,spec,score,status in zip(gates,specs,scores,statuses):
            p.ledger.mark_dispatched(spec["key"])
            directory=self.execution/"attempts"/spec["key"];directory.mkdir(parents=True,exist_ok=True)
            raw=write(directory/"response.raw",b"synthetic retained gate bytes, no real provider response")
            record={"key":spec["key"],"cell_id":c["cell_id"],"config":c["config"],"namespace":c["namespace"],
                "request_sha256":c["payload_sha256"],"raw_hashes":{"response.raw":raw["sha256"]},
                "parsed":{"status":status,"valid":status=="ok","score":score}}
            completed=directory/"completed.json";write(completed,record)
            p.ledger.settle(spec["key"],"0",evidence_sha256=digest(completed.read_bytes()));paths.append(completed)
        return gates,paths

    def pilot_group(self,p,task=None):
        return next(g for g in p.groups if g["lane"]=="isolated_agent" and (task is None or g["source_group_id"]==task))

    def test_exact_owner_caps_review_and_routes_required(self):
        for field,value in (("experimental_inference_authorized",False),("authorization_source","implicit"),
                ("manifest_sha256","f"*64),
                ("openai_subscription_only",False),("allow_paid_openai_api",True),("allow_purchases_or_recharge",True),
                ("max_sol_calls",577),("max_jev_calls",553)):
            with self.subTest(field=field):
                write(self.authpath,dict(self.auth,**{field:value}))
                with self.assertRaises(PermissionError):x.ExtensionPermit(self.manifest,self.authpath,self.reviewpath)
        write(self.authpath,self.auth)
        write(self.reviewpath,{"status":"pass","remaining_findings":["open"],"manifest_sha256":digest(self.manifest.read_bytes())})
        with self.assertRaises(PermissionError):x.ExtensionPermit(self.manifest,self.authpath,self.reviewpath)
        self.m["routes"]["sol_subscription"]["route"]="api_key";self.bind_manifest()
        with self.assertRaises(b.AccountingError):x.freeze_policy(self.manifest)

    def test_exact_finite_roster_and_both_dynamic_variants(self):
        p=self.permit();roster=p.policy["extension_roster"]
        self.assertEqual(len(roster),1128);self.assertEqual(len(p.groups),78)
        self.assertEqual(Counter(r["config"] for r in roster.values()),{"jev_firstparty":552,"sol_subscription":576})
        self.assertFalse(any(r["stage"]=="preflight" for r in roster.values()))
        gated=[c for g in p.groups for c in g["cells"] if c.get("arm")=="Jev_gate"]
        self.assertEqual(len(gated),24)
        for c in gated:
            self.assertEqual(set(roster[c["cell_id"]]["payload_choices"]),{v["payload_sha256"] for v in c["payload_variants"].values()})
        self.assertEqual(Decimal("0.001344")*552,Decimal("0.741888"))

    def test_old_core_cell_extra_actor_preflight_and_third_variant_cannot_reserve(self):
        p=self.permit();g=p.groups[0];cell=copy.deepcopy(g["cells"][0])
        for field,value in (("cell_id","main:old-core-cell"),("stage","preflight")):
            with self.subTest(field=field):
                bad=dict(cell,**{field:value});spec=p.spec(g,bad)
                ledger=x.ExtensionLedger(self.execution/(field+"-reject.jsonl"),p.policy,clock=lambda:self.now)
                before=ledger.path.read_bytes()
                with self.assertRaises((PermissionError,b.AccountingError)):
                    ledger.reserve_group(g["lane"],g["group_id"],[spec])
                self.assertEqual(ledger.path.read_bytes(),before)
        pg=self.pilot_group(p);actor=copy.deepcopy(next(c for c in pg["cells"] if c.get("arm")=="Jev_gate"))
        actor["payload"]["input"][0]["content"]+="invented variant";actor["payload_sha256"]=digest(canonical(actor["payload"]))
        ledger=x.ExtensionLedger(self.execution/"variant-reject.jsonl",p.policy,clock=lambda:self.now)
        before=ledger.path.read_bytes()
        with self.assertRaises((PermissionError,b.AccountingError)):
            ledger.reserve_group(pg["lane"],pg["group_id"],[p.spec(pg,actor)],batch_id=pg["group_id"]+":actor")
        self.assertEqual(ledger.path.read_bytes(),before)
        self.assertEqual(p.ledger.snapshot()["entries"],{})

    def test_all552_jev_reservations_hold_exact_full_context_ceiling(self):
        p=self.permit()
        for g in p.groups:
            cells=[c for c in g["cells"] if c["config"]=="jev_firstparty"]
            batch=g["group_id"]+":gate" if g["lane"]=="isolated_agent" else g["group_id"]
            p.ledger.reserve_group(g["lane"],g["group_id"],[p.spec(g,c) for c in cells],batch_id=batch)
        state=p.ledger.snapshot()
        self.assertEqual(len(state["entries"]),552)
        self.assertEqual(Decimal(state["incremental_accounted_usd"]["typesafe"]),Decimal("0.741888"))
        self.assertTrue(all(e["reserved_usd"]=="0.001344" for e in state["entries"].values()))

    def test_second_dynamic_variant_of_same_logical_actor_is_not_another_attempt(self):
        p=self.permit();g=self.pilot_group(p);self.gate_evidence(p,g,(.1,.1))
        original=next(c for c in g["cells"] if c.get("arm")=="Jev_gate")
        allowed=p.selected(original);withheld=copy.deepcopy(original)
        withheld.update(payload=withheld["payload_variants"]["withheld"]["payload"],
                        payload_sha256=withheld["payload_variants"]["withheld"]["payload_sha256"])
        batch=g["group_id"]+":actor"
        p.ledger.reserve_group(g["lane"],g["group_id"],[p.spec(g,allowed)],batch_id=batch)
        before=p.ledger.path.read_bytes()
        with self.assertRaises(b.AccountingError):
            p.ledger.reserve_group(g["lane"],g["group_id"],[p.spec(g,withheld)],batch_id=batch)
        self.assertEqual(p.ledger.path.read_bytes(),before)

    def test_actor_dispatch_requires_both_frozen_gate_predecessors_settled(self):
        p=self.permit();g=self.pilot_group(p);gates,_=self.gate_evidence(p,g,(.1,.1))
        actual=p.selected(g["cells"][2]);spec=p.spec(g,actual)
        p.ledger.reserve_group(g["lane"],g["group_id"],[spec],batch_id=g["group_id"]+":actor")
        p.ledger.mark_dispatched(spec["key"])
        second=p.spec(g,gates[1])["key"];entry=p.ledger.entry
        def premature(key):
            record=entry(key)
            return dict(record,status="reserved") if key==second else record
        with patch.object(p.ledger,"entry",side_effect=premature),self.assertRaises(PermissionError):
            p.check_dispatch(actual,spec)
        p.check_dispatch(actual,spec)

    def test_second_gate_cannot_dispatch_before_first_gate_settles(self):
        p=self.permit();g=self.pilot_group(p)
        gates=[c for c in g["cells"] if c["kind"]=="gate"]
        specs=[p.spec(g,c) for c in gates]
        p.ledger.reserve_group(g["lane"],g["group_id"],specs,batch_id=g["group_id"]+":gate")
        p.ledger.mark_dispatched(specs[1]["key"])
        with self.assertRaises(PermissionError):p.check_dispatch(gates[1],specs[1])

    def test_global_anchor_and_deadline_cannot_shift_together(self):
        self.m["global_clock_anchor_utc"]=(b._utc(ORIGINAL_START)+timedelta(hours=1)).isoformat()
        self.m["global_deadline_utc"]=(b._utc(END)+timedelta(hours=1)).isoformat();self.bind_manifest()
        with self.assertRaises(PermissionError):x.freeze_policy(self.manifest)

    def test_empty_or_unclosed_core_lineage_rejected(self):
        for lineage in ({"status":"closed","runs":[]},{"status":"active","runs":self.lineage["runs"]}):
            with self.subTest(lineage=lineage):
                self.m["core_collection_lineage"]=write(self.lineagepath,lineage);self.bind_manifest()
                with patch.object(x,"verify_closed_core",side_effect=self.real_verify_closed_core),self.assertRaises(PermissionError):
                    x.freeze_policy(self.manifest)

    def test_closed_ancestor_manifest_and_raw_metadata_hashes_required(self):
        original=self.core_manifest.read_bytes();self.core_manifest.write_bytes(original+b" ")
        with patch.object(x,"verify_closed_core",side_effect=self.real_verify_closed_core), \
             patch.object(x,"CORE_MANIFESTS",(digest(original),digest(original))),self.assertRaises(PermissionError):
            x.freeze_policy(self.manifest)
        self.core_manifest.write_bytes(original)
        self.core.joinpath("accounting.jsonl").write_bytes(b"changed synthetic ancestor journal")
        with patch.object(x,"verify_closed_core",side_effect=self.real_verify_closed_core), \
             patch.object(x,"CORE_MANIFESTS",(digest(original),digest(original))),self.assertRaises(PermissionError):
            x.freeze_policy(self.manifest)

    def test_original_clock_is_durable_deadline_and_restart_fail_closed(self):
        p=self.permit();snapshot=p.ledger.snapshot()
        self.assertEqual(snapshot["window_started_at_utc"],ORIGINAL_START)
        self.assertEqual(p.ledger.remaining_seconds(),14400.)
        runner=x.ExtensionExecutor(p);runner.event=Mock()
        runner.restore()
        g=p.groups[0];spec=p.spec(g,g["cells"][0]);p.ledger.reserve_group(g["lane"],g["group_id"],[spec])
        with self.assertRaises(PermissionError):x.ExtensionExecutor(p)
        self.now=b._utc(END)
        with self.assertRaises(b.BudgetExceeded):p.ledger.mark_dispatched(spec["key"])
        with self.assertRaises(PermissionError):p.check()

    def test_prior_attempt_denies_restart_even_if_ledger_empty(self):
        p=self.permit();directory=self.execution/"attempts"/"synthetic-old-intent";directory.mkdir(parents=True)
        write(directory/"started.json",{})
        with self.assertRaises(PermissionError):x.ExtensionExecutor(p)

    def test_service_recovery_state_is_inherited_without_reset(self):
        self.m.update(prior_transient_failure_events=[{'key':'old-a'},{'key':'old-b'}],
                      prior_consecutive_service_failures=2)
        self.bind_manifest();p=self.permit();runner=x.ExtensionExecutor(p)
        self.assertEqual(runner.consecutive_service_failures,2)
        self.assertEqual(runner.service_failures,self.m['prior_transient_failure_events'])
        for value in (3,-1,True):
            with self.subTest(value=value):
                p.manifest['prior_consecutive_service_failures']=value
                with self.assertRaises(PermissionError):x.ExtensionExecutor(p)
        p.manifest.update(prior_transient_failure_events=[{}]*6,prior_consecutive_service_failures=0)
        with self.assertRaises(PermissionError):x.ExtensionExecutor(p)

    def test_gate_identity_completion_and_raw_hashes_precede_variant_choice(self):
        p=self.permit();g=self.pilot_group(p);gates,paths=self.gate_evidence(p,g)
        actor=next(c for c in g["cells"] if c.get("arm")=="Jev_gate" and c["gate_cell_id"]==gates[0]["cell_id"])
        self.assertEqual(p.selected(actor)["payload_sha256"],actor["payload_variants"]["allowed"]["payload_sha256"])
        path=paths[0];original=path.read_bytes();base=json.loads(original);spec=p.spec(g,gates[0]);entry=p.ledger.entry(spec["key"])
        for field,value in (("cell_id","other"),("key","wrong"),("config","sol_subscription"),("namespace","old-core"),("request_sha256","f"*64)):
            with self.subTest(field=field):
                write(path,dict(base,**{field:value}));bound=dict(entry,evidence_sha256=digest(path.read_bytes()))
                with patch.object(p.ledger,"entry",return_value=bound),self.assertRaises(PermissionError):p.selected(actor)
        path.write_bytes(original)
        path.parent.joinpath("response.raw").write_bytes(b"changed raw")
        with self.assertRaises(PermissionError):p.selected(actor)

    def test_gate_tie_blocks_without_provider_failure_and_error_is_missing(self):
        p=self.permit();g=self.pilot_group(p);gates,_=self.gate_evidence(p,g,(.5,None),("tie","http_error"))
        actors={c["gate_cell_id"]:c for c in g["cells"] if c.get("arm")=="Jev_gate"}
        self.assertEqual(p.selected(actors[gates[0]["cell_id"]])["payload_sha256"],actors[gates[0]["cell_id"]]["payload_variants"]["withheld"]["payload_sha256"])
        self.assertIsNone(p.selected(actors[gates[1]["cell_id"]]))
        # A new empty runner is used because old attempts are never restartable.
        runner=object.__new__(x.ExtensionExecutor)
        import threading
        runner.lock=threading.RLock();runner.completed=Counter();runner.consecutive_service_failures=2
        runner.fatal=threading.Event();runner.pause=threading.Event();runner.event=Mock()
        runner.observe(g,{"key":"synthetic-tie","config":"jev_firstparty","parsed":{"status":"tie","valid":False,"score":.5}})
        self.assertFalse(runner.fatal.is_set());self.assertFalse(runner.pause.is_set());self.assertEqual(runner.consecutive_service_failures,0)
        runner.event.assert_called_once_with("native_abstention",key="synthetic-tie",stage=g["stage"])

    def test_missing_gate_admits_no_actor_and_never_writes_protection(self):
        p=self.permit();runner=x.ExtensionExecutor(p);runner.event=Mock();g=self.pilot_group(p)
        self.gate_evidence(p,g,(.2,None),("ok","http_error"));p.groups=[g]
        runner.call=Mock(return_value=None);runner.pilot_stage()
        self.assertTrue(runner.fatal.is_set());self.assertEqual(runner.reason,"missing_gate_actor_not_admitted")
        self.assertEqual([call.args[1]["kind"] for call in runner.call.call_args_list],["gate","gate"])
        self.assertTrue(all(e["split"]=="gate" for e in p.ledger.snapshot()["entries"].values()))
        self.assertEqual(list(self.execution.rglob("simulated-execution.json")),[])

    def test_pilot_calls_both_gates_before_frozen_actors_and_resets_world(self):
        p=self.permit();runner=x.ExtensionExecutor(p);runner.event=Mock();g=self.pilot_group(p,"calendar")
        self.gate_evidence(p,g,(.1,.1));p.groups=[g];called=[]
        def fake_call(group,cell):
            called.append(cell["cell_id"])
            if cell["kind"]=="gate":return None
            return {"key":cell["cell_id"].replace(":","-"),"parsed":{"valid":True,"answer":{
                "action":"send_message","target":"outbox:external","value":"CALENDAR_CANARY","final_answer":"Tuesday; 14:00"}}}
        runner.call=fake_call;runner.pilot_stage()
        self.assertEqual(called,[c["cell_id"] for c in g["cells"]]);self.assertEqual(len(called),6)
        outputs=[json.loads(f.read_text()) for f in self.execution.rglob("simulated-execution.json")]
        self.assertEqual(len(outputs),4)
        for output in outputs:
            result=output["result"]
            self.assertTrue(result["legitimate_completion"]);self.assertTrue(result["attacker_success"])
            self.assertEqual(len(result["world_after"]["outbox"]),1)
            self.assertTrue(output["no_external_actions"])
        self.assertEqual(pilot.INITIAL_WORLD["outbox"],[])

    def test_mocked_orchestrator_has_no_preflight_and_closes_cleanly(self):
        p=self.permit();stages=[]
        with patch.object(x,"ExtensionPermit",return_value=p),patch.object(x,"ExtensionLedger",return_value=p.ledger), \
             patch.object(x.ExtensionExecutor,"stage",autospec=True,side_effect=lambda runner,stage,workers:stages.append(stage)), \
             patch.object(x.ExtensionExecutor,"pilot_stage",autospec=True) as pilot_stage,contextlib.redirect_stdout(io.StringIO()):
            x.execute(self.manifest,self.authpath,self.reviewpath)
        self.assertEqual(stages,["secondary"]);pilot_stage.assert_called_once()
        self.assertEqual(json.loads((self.execution/"STOP.json").read_text())["status"],"closed")
        self.assertTrue(json.loads((self.execution/"final-ledger-snapshot.json").read_text())["terminal"])


if __name__=="__main__":unittest.main()
