"""Synthetic evidence only; no credential, network or model access."""
from collections import defaultdict
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.study_v7 import operational as op
from scripts.study_v7.budget import policy, usage_cost
from scripts.study_v7.requests import PANEL, CONDITIONS, canonical, digest, payload, audit_payload

CONFIGS=("jev_firstparty","luna_decisions","luna_responses","sol_subscription","protectai_local")
USAGE={"input_tokens":100,"output_tokens":1,"input_tokens_details":{"cached_tokens":0,"cache_write_tokens":0}}


def write_attempt(root, request, body, *, audit=None):
    directory=root/request["key"]
    directory.mkdir(parents=True)
    request_bytes=canonical(body)
    (directory/"request.json").write_bytes(request_bytes)
    (directory/"response.raw").write_text("Synthetic retained response")
    parsed={"status":"ok","valid":True,"returned_model":PANEL[request["config"]]["model"],"usage":USAGE}
    if request.get("configuration_revision") is not None:
        parsed["configuration_revision"]=request["configuration_revision"]
    if request["config"] == "protectai_local":
        parsed["revision"]=PANEL["protectai_local"]["revision"]
    if PANEL[request["config"]]["kind"] == "responses":
        parsed["returned_settings"]={k:body.get(k) for k in ("reasoning","max_output_tokens","service_tier","prompt_cache_options","store")}
    if audit is not None:
        parsed["audit"]=audit
    result={"parsed":parsed,"request_sha256":digest(request_bytes),"namespace":request["namespace"],
            "configuration_revision":request.get("configuration_revision"),
            "first_attempt_primary":request["namespace"]=="first","elapsed_seconds":.01,
            "raw_hashes":{"request.json":digest(request_bytes),"response.raw":digest((directory/"response.raw").read_bytes())}}
    (directory/"completed.json").write_bytes(canonical(result))
    return result


def write_journal(path,plan,attempts):
    allocations={r["allocation"] for r in plan["requests"].values()}
    pol=policy({p:"0" for p in op.PROVIDERS},{p:"20" for p in op.PROVIDERS},
               {p:"20" for p in op.PROVIDERS},{a:{p:"1" for p in op.PROVIDERS} for a in allocations})
    events=[]
    def append(kind,data):
        event={"index":len(events),"previous_sha256":events[-1]["sha256"] if events else "0"*64,
               "kind":kind,"data":data}
        event["sha256"]=digest(canonical(event));events.append(event)
    append("initialize",{"policy":pol})
    parts=defaultdict(list)
    for r in plan["requests"].values():
        if (attempts/r["key"]/"completed.json").exists():
            parts[r["allocation"]].append(r)
    for allocation,requests in parts.items():
        specs=[{"key":r["key"],"provider":PANEL[r["config"]]["provider"],
                "reserved_usd":".001" if PANEL[r["config"]]["provider"] else "0",
                "request_sha256":r["payload_sha256"],"config":r["config"],"split":r["split"]} for r in requests]
        append("reserve",{"batch_id":allocation,"allocation":allocation,"new_requests":specs})
        for r in requests:
            body=(attempts/r["key"]/"completed.json").read_bytes();retained=json.loads(body)
            append("dispatch",{"key":r["key"]})
            append("settle",{"key":r["key"],"actual_usd":usage_cost(r["config"],retained["parsed"].get("usage") or {}),
                              "evidence_sha256":digest(body)})
    path.write_bytes(b"".join(canonical(e)+b"\n" for e in events))


def development_plan(sol_revision=None):
    from scripts.study_v7.requests import model_configuration
    plan={"requests":{},"active_configurations":list(CONFIGS),"model_configurations":{
        c:model_configuration(c,sol_revision if c=="sol_subscription" else None) for c in CONFIGS}}
    bodies={}
    for config in CONFIGS:
        for source,n in (("browsesafe",100),("promptshield",100)):
            for i in range(n):
                row={"source":source,"candidate":f"Synthetic page {source} {i}","task":f"Synthetic task {i//2}"}
                for condition in (("candidate",) if config=="protectai_local" else CONDITIONS) if source=="browsesafe" else ("external",):
                    revision=sol_revision if config=="sol_subscription" else None
                    body=payload(config,row,condition,configuration_revision=revision); sha=digest(canonical(body))
                    key=digest(f"{config}/{source}/{i}/{condition}".encode())
                    request={"key":key,"source":source,"config":config,"split":"development","namespace":"first",
                        "id":f"{source}:{i}","group_id":f"{source}:{i//2 if source=='browsesafe' else i}",
                        "condition":condition,"payload_sha256":sha,"allocation":"development_"+source}
                    if revision is not None:request["configuration_revision"]=revision
                    plan["requests"][key]=request;bodies[key]=body
    return plan,bodies


class OperationalTests(unittest.TestCase):
    def test_one_bounded_service_recovery_keeps_failed_first_attempt_invalid(self):
        plan,bodies=development_plan("v7.0.2")
        sol=[r for r in plan["requests"].values() if r["config"]=="sol_subscription"]
        failed,unsent=sol[-9],sol[-8:];unsent_keys={r["key"] for r in unsent}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);attempts=root/"attempts"
            for r in plan["requests"].values():
                if r["key"] not in unsent_keys:write_attempt(attempts,r,bodies[r["key"]])
            directory=attempts/failed["key"]
            result=json.loads((directory/"completed.json").read_text())
            raw=canonical({"error":{"code":"subscription_sharing_user_unavailable","message":"ChatGPT user temporarily unavailable"}})
            (directory/"response.raw").write_bytes(raw)
            result.update(parsed={"status":"http_error","valid":False,"prediction":None},
                observation={"http_status":503,"transport_exit_code":0})
            result["raw_hashes"]["response.raw"]=digest(raw)
            (directory/"completed.json").write_bytes(canonical(result))
            failure_bytes=(directory/"completed.json").read_bytes()
            journal=root/"journal.jsonl";write_journal(journal,plan,attempts)
            before=journal.read_bytes();pause=root/"raw/pause.json";pause.parent.mkdir()
            pause.write_bytes(canonical({"configuration":"sol_subscription","request_key":failed["key"]}))
            recovery={"version":"study-v7-sol-service-recovery-1","configuration":"sol_subscription", "configuration_revision":"v7.0.2",
                "plan_sha256":"a"*64,"failed_request_key":failed["key"],"failed_completed_sha256":digest(failure_bytes),
                "failed_response_raw_sha256":digest(raw),"pause_record_path":str(pause),"pause_record_sha256":digest(pause.read_bytes()),
                "http_status":503,"error_code":"subscription_sharing_user_unavailable","maximum_continuations":1,"retry_failed_request":False,
                "expected_unsent_request_keys":sorted(unsent_keys),"pre_continuation_journal_sha256":digest(before),
                "pre_continuation_journal_size_bytes":len(before)}
            receipt=root/"recovery.json";receipt.write_bytes(canonical(recovery))
            with patch.object(op,"RAW",root/"raw"):
                pending=op.development_receipt(plan,attempts,plan_sha256="a"*64,journal_path=journal,service_recovery=receipt)
                self.assertEqual(pending["service_recovery"]["disposition"],"operationally_deferred")
                self.assertTrue(pending["core_readiness"]["completed"])
                for r in unsent:write_attempt(attempts,r,bodies[r["key"]])
                # Append new reservations/dispatches/settlements while preserving
                # the exact old prefix that proves these8keys were never sent.
                events=[json.loads(line) for line in before.splitlines()]
                def append(kind,data):
                    event=dict(index=len(events),previous_sha256=events[-1]["sha256"],kind=kind,data=data)
                    event["sha256"]=digest(canonical(event));events.append(event)
                allocation=unsent[0]["allocation"]
                append("reserve",{"batch_id":"availability-continuation","allocation":allocation,"new_requests":[
                    {"key":r["key"],"provider":None,"reserved_usd":"0","request_sha256":r["payload_sha256"],
                     "config":"sol_subscription","split":"development"} for r in unsent]})
                for r in unsent:
                    append("dispatch",{"key":r["key"]})
                    append("settle",{"key":r["key"],"actual_usd":"0","evidence_sha256":digest((attempts/r["key"]/"completed.json").read_bytes())})
                journal.write_bytes(b"".join(canonical(e)+b"\n" for e in events))
                self.assertEqual(journal.read_bytes()[:len(before)],before)
                final=op.development_receipt(plan,attempts,plan_sha256="a"*64,journal_path=journal,service_recovery=receipt)
                self.assertTrue(final["completed"])
                self.assertIn("sol_subscription",final["validated_configurations"])
                self.assertNotIn("sol_subscription",final["unsupported_configurations"])
                self.assertEqual(final["service_recovery"]["new_valid_responses"],8)
                self.assertEqual(final["service_recovery"]["preserved_invalid_first_attempts"],1)
                self.assertEqual(sum(p["status_counts"].get("http_error",0) for p in final["source_config_coverage"] if p["config"]=="sol_subscription"),1)
                self.assertEqual((directory/"completed.json").read_bytes(),failure_bytes)
                state,accounting=op.read_journal(journal,plan,plan_sha256="a"*64)
                retained={r["key"]:op.retained_attempt(r,attempts,state) for r in sol}
                retained[unsent[0]["key"]]=dict(retained[unsent[0]["key"]],status="http_error",valid=False)
                repeated=op.validate_service_recovery(receipt,plan,attempts,state,accounting,plan_sha256="a"*64,journal_path=journal,retained_records=retained)
                self.assertFalse(repeated["completed"])
                self.assertEqual(repeated["disposition"],"operationally_deferred")
                recovery["pre_continuation_journal_sha256"]="f"*64;receipt.write_bytes(canonical(recovery))
                with self.assertRaisesRegex(ValueError,"journal prefix changed"):
                    op.development_receipt(plan,attempts,plan_sha256="a"*64,journal_path=journal,service_recovery=receipt)

    def test_development_receipt_complete_counts_costs_and_no_accuracy(self):
        plan,bodies=development_plan()
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);attempts=root/"attempts"
            for request in plan["requests"].values():
                write_attempt(attempts,request,bodies[request["key"]])
            journal=root/"accounting.jsonl";write_journal(journal,plan,attempts)
            original=journal.read_bytes()
            result=op.development_receipt(plan,attempts,plan_sha256="a"*64,journal_path=journal)
            self.assertTrue(result["completed"])
            self.assertTrue(result["core_readiness"]["completed"])
            self.assertEqual(result["validated_configurations"],sorted(CONFIGS))
            self.assertFalse(result["accuracy_calculated"])
            self.assertTrue(result["accounting"]["read_only_replay"])
            self.assertEqual(journal.read_bytes(),original)
            self.assertFalse((root/"accounting.jsonl.lock").exists())
            self.assertEqual(sum(p["planned_requests"] for p in result["source_config_coverage"]),2200)
            self.assertNotIn("prediction",json.dumps(result))
            subscription=next(p for p in result["source_config_coverage"] if p["config"]=="sol_subscription")
            self.assertIsNone(subscription["requested_configurations"][0]["max_output_tokens"])
            # Changed raw bytes cannot be silently accepted.
            key=next(iter(plan["requests"]))
            (attempts/key/"response.raw").write_text("changed")
            with self.assertRaisesRegex(ValueError,"raw evidence hash"):
                op.development_receipt(plan,attempts,plan_sha256="a"*64,journal_path=journal)

    def test_incomplete_and_wrong_development_counts_fail_readiness(self):
        plan,_=development_plan()
        with tempfile.TemporaryDirectory() as temp:
            result=op.development_receipt(plan,Path(temp),plan_sha256="b"*64)
            self.assertFalse(result["completed"])
            self.assertEqual(result["validated_configurations"],[])
            self.assertEqual(len(result["blockers"]),5)
            plan["requests"].pop(next(iter(plan["requests"])))
            with self.assertRaisesRegex(ValueError,"exact frozen counts"):
                op.development_receipt(plan,Path(temp),plan_sha256="b"*64)

    def test_fixed_paid_settings_and_explicit_subscription_default(self):
        row={"source":"promptshield","candidate":"Synthetic ordinary request"}
        paid=payload("luna_responses",row,"external")
        self.assertEqual(paid["max_output_tokens"],256)
        paid["reasoning"]={"effort":"low"}
        checked=op.settings_check("luna_responses",paid,{},False)
        self.assertIn("requested_reasoning",checked["problems"])
        subscription=payload("sol_subscription",row,"external")
        subscription["max_output_tokens"]=2048
        checked=op.settings_check("sol_subscription",subscription,{},False)
        self.assertIn("subscription_unsupported_output_cap_requested",checked["problems"])

    def test_explicit_subscription_v702_cache_default_and_catalogue_capacity(self):
        from scripts.study_v7.requests import model_configuration
        row={"source":"promptshield","candidate":"Synthetic ordinary request"}
        body=payload("sol_subscription",row,"external",configuration_revision="v7.0.2")
        configuration=model_configuration("sol_subscription","v7.0.2")
        self.assertNotIn("prompt_cache_options",body)
        parsed={"status":"ok","valid":True,"returned_model":"gpt-6.1-sol",
            "configuration_revision":"v7.0.2","usage":USAGE,
            "returned_settings":{"reasoning":{"effort":"low"},"service_tier":"default","store":False,
                                 "prompt_cache_options":{"mode":"implicit"}}}
        checked=op.settings_check("sol_subscription",body,parsed,True,
            configuration_revision="v7.0.2",model_configuration=configuration)
        self.assertEqual(checked["problems"],[])
        self.assertIn("uncontrolled",checked["requested"]["cache_control_status"])
        self.assertEqual(checked["requested"]["native_context_capacity_tokens"],500000)
        self.assertIsNone(checked["requested"]["max_output_tokens"])
        parsed["usage"]=dict(USAGE,input_tokens=500000)
        checked=op.settings_check("sol_subscription",body,parsed,True,
            configuration_revision="v7.0.2",model_configuration=configuration)
        self.assertIn("subscription_usage_or_capacity",checked["problems"])
        with self.assertRaisesRegex(ValueError,"explicitly frozen Sol"):
            op.settings_check("luna_responses",body,{},False,configuration_revision="v7.0.2",model_configuration=configuration)
        legacy=op.settings_check("sol_subscription",body,{},False)
        self.assertIn("requested_prompt_cache_options",legacy["problems"])

    def test_pure_replay_retains_archived_zero_cost_subscription_attempts(self):
        from scripts.study_v7 import budget,requests
        main=[dict(id=f"m-{label}",group_id="g",pair_id="pair",source="browsesafe",task="Synthetic task",
            candidate=f"Synthetic page {label}",upstream_label=label,partition="development") for label in (0,1)]
        external=[dict(id=f"e-{label}",group_id=f"eg-{label}",source="promptshield",candidate=f"Synthetic request {label}",
            upstream_label=label,partition="development") for label in (0,1)]
        old=requests.build_plan(main,external,sol_config="sol_subscription")
        new=requests.build_plan(main,external,sol_config="sol_subscription",sol_subscription_revision="v7.0.2")
        allocations=("development_sol_main","development_sol_external")
        def schedules(plan):
            return {a:[{"group":g["group"],"requests":[budget.reservation(plan["requests"][k]) for k in g["request_keys"]]}
                       for g in plan["schedules"][a]] for a in allocations}
        before,after=schedules(old),schedules(new)
        frozen=budget.policy({p:"0" for p in op.PROVIDERS},{p:"1" for p in op.PROVIDERS},
            {p:"1" for p in op.PROVIDERS},{a:{p:"0" for p in op.PROVIDERS} for a in allocations})
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);journal=root/"journal.jsonl";ledger=budget.BudgetLedger(journal,frozen)
            for a in allocations:ledger.register_schedule(a,before[a])
            admitted=ledger.reserve_next_group("development_sol_main")
            for key in admitted["request_keys"][:4]:
                ledger.mark_dispatched(key);ledger.settle(key,"0",evidence_sha256="f"*64)
            new_sha=digest(canonical(new))
            receipt={"version":"study-v7.0.2-sol-subscription-amendment","configuration_revision":"v7.0.2",
                "previous_plan_sha256":digest(canonical(old)),"new_plan_sha256":new_sha,
                "payload_revision_sha256":"c"*64,"failure_metadata_sha256":"d"*64,
                "previous_schedules_sha256":{a:digest(canonical(before[a])) for a in allocations},
                "new_schedules_sha256":{a:digest(canonical(after[a])) for a in allocations}}
            receipt_path=root/"amendment.json";receipt_path.write_bytes(canonical(receipt))
            ledger.supersede_subscription_development(receipt_path,after)
            original=journal.read_bytes()
            state,summary=op.read_journal(journal,new,plan_sha256=new_sha)
            self.assertTrue(summary["verified"])
            self.assertEqual(summary["superseded_zero_cost_subscription_entry_statuses"],{"settled":4,"cancelled_unsent":4})
            self.assertEqual(summary["incremental_accounted_usd"],{"openai":"0","typesafe":"0"})
            self.assertEqual(journal.read_bytes(),original)
            with self.assertRaisesRegex(ValueError,"exact new plan"):
                op.read_journal(journal,new,plan_sha256="e"*64)

    def test_scoped_development_reparse_preserves_originals_and_rejects_tampering(self):
        from scripts.study_v7 import routes
        plan,bodies=development_plan()
        request=next(r for r in plan['requests'].values() if r['config']=='luna_responses')
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);attempts=root/'attempts';body=bodies[request['key']]
            result=write_attempt(attempts,request,body)
            response=dict(model='gpt-6-luna',id='synthetic-response',status='completed',usage=USAGE,
                reasoning={'effort':'none'},max_output_tokens=256,service_tier='default',store=False,
                prompt_cache_options={'mode':'explicit','ttl':'30m'},
                output=[{'content':[{'type':'output_text','text':'{"injection":true}'}]}])
            raw='data: '+json.dumps({'type':'response.completed','response':response})+'\n\n'
            directory=attempts/request['key'];(directory/'response.raw').write_text(raw)
            derived=routes.parse_response('luna_responses',raw)
            self.assertEqual(derived['status'],'ok')
            original=dict(derived,status='settings_mismatch',valid=False,prediction=None,settings_mismatch_fields=['prompt_cache_options'])
            result.update(parsed=original,parser_version='study-v7-routes-1',observation={'http_status':200,'transport_exit_code':0})
            result['raw_hashes']['response.raw']=digest(raw.encode())
            (directory/'completed.json').write_bytes(canonical(result))
            journal=root/'journal.jsonl';write_journal(journal,plan,attempts)
            original_bytes=(directory/'completed.json').read_bytes()
            with patch.object(op,'RAW',root/'raw'):
                sidecar=root/'raw/development-reparse-v7.0.1.jsonl'
                records=op.create_development_reparses(plan,attempts,plan_sha256='a'*64,manifest_sha256='b'*64,output=sidecar,journal_path=journal)
                self.assertEqual(len(records),1)
                self.assertFalse(records[0]['retransmitted'])
                receipt=op.development_receipt(plan,attempts,plan_sha256='a'*64,journal_path=journal,reparses=sidecar,reparse_manifest_sha256='b'*64)
                part=next(p for p in receipt['source_config_coverage'] if p['config']=='luna_responses' and p['source']=='browsesafe')
                self.assertEqual(part['original_status_counts']['settings_mismatch'],1)
                self.assertEqual(part['status_counts']['ok'],1)
                self.assertEqual(part['derived_technical_resolutions'],1)
                self.assertEqual(part['settings_problems'],{})
                self.assertFalse(receipt['accuracy_calculated'])
                self.assertEqual((directory/'completed.json').read_bytes(),original_bytes)
                # A changed derived answer/status, manifest binding or scope cannot
                # bypass re-computation from exact retained source bytes.
                altered=json.loads(sidecar.read_text());altered['derived_parsed']['prediction']=0
                sidecar.write_bytes(canonical(altered)+b'\n')
                with self.assertRaisesRegex(ValueError,'exact original/parser/manifest'):
                    op.development_receipt(plan,attempts,plan_sha256='a'*64,journal_path=journal,reparses=sidecar,reparse_manifest_sha256='b'*64)
                with self.assertRaisesRegex(ValueError,'Luna Responses development'):
                    op._development_reparse_record(dict(request,split='confirmation'),{'parsed':original},attempts,plan_sha256='a'*64,manifest_sha256='b'*64)

    def test_audit_checks_literal_quotes_without_changing_labels(self):
        rows={};requests={};groups=[]
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);attempts=root/"attempts"
            for group in range(100):
                gid=f"g{group}";groups.append(gid)
                pair=[dict(id=f"{gid}:{label}",group_id=gid,source="browsesafe",partition="confirmation",
                    upstream_label=label,task=f"Find synthetic item {group}",candidate=f"Synthetic {'attack' if label else 'clean'} literal {group}") for label in (0,1)]
                rows.update({r["id"]:r for r in pair})
                body=audit_payload(pair,"sol_subscription");sha=digest(canonical(body));key=digest(str(group).encode())
                request=dict(key=key,config="sol_subscription",source="browsesafe",id=pair[0]["id"],group_id=gid,
                    condition="audit",split="confirmation",namespace="audit",payload_sha256=sha,allocation="audit",
                    audit_ids=[r["id"] for r in pair])
                requests[key]=request
                audit={"task_fidelity":True,"attack_visible":False,"ambiguous":True,"concerns":["Synthetic concern"],
                    "evidence_spans":[pair[0]["task"],pair[1]["candidate"] if group else "Fabricated quotation"]}
                write_attempt(attempts,request,body,audit=audit)
            plan={"requests":requests,"subsets":{"audit_groups":groups}}
            journal=root/"journal.jsonl";write_journal(journal,plan,attempts)
            with patch.object(op,"RAW",root/"raw"):
                result=op.audit_receipt(plan,attempts,rows,plan_sha256="c"*64,journal_path=journal,details_output=root/"raw/audit.jsonl")
                with self.assertRaisesRegex(ValueError,"must stay in ignored"):
                    op.audit_receipt(plan,attempts,rows,plan_sha256="c"*64,details_output=root/"tracked.jsonl")
            self.assertTrue(result["completed"])
            self.assertEqual(result["diagnostic_counts"]["literal_spans_verified"],199)
            self.assertEqual(result["diagnostic_counts"]["nonliteral_or_blank_spans"],1)
            self.assertTrue(result["source_labels_preserved"])
            self.assertFalse(result["inferred_ground_truth"])
            self.assertNotIn("Fabricated quotation",json.dumps(result))
            self.assertNotIn("Synthetic concern",json.dumps(result))


if __name__=="__main__":
    unittest.main()
