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
    if request["config"] == "protectai_local":
        parsed["revision"]=PANEL["protectai_local"]["revision"]
    if PANEL[request["config"]]["kind"] == "responses":
        parsed["returned_settings"]={k:body.get(k) for k in ("reasoning","max_output_tokens","service_tier","prompt_cache_options","store")}
    if audit is not None:
        parsed["audit"]=audit
    result={"parsed":parsed,"request_sha256":digest(request_bytes),"namespace":request["namespace"],
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


def development_plan():
    plan={"requests":{},"active_configurations":list(CONFIGS),"model_configurations":{c:PANEL[c] for c in CONFIGS}}
    bodies={}
    for config in CONFIGS:
        for source,n in (("browsesafe",100),("promptshield",100)):
            for i in range(n):
                row={"source":source,"candidate":f"Synthetic page {source} {i}","task":f"Synthetic task {i//2}"}
                for condition in (("candidate",) if config=="protectai_local" else CONDITIONS) if source=="browsesafe" else ("external",):
                    body=payload(config,row,condition); sha=digest(canonical(body))
                    key=digest(f"{config}/{source}/{i}/{condition}".encode())
                    request={"key":key,"source":source,"config":config,"split":"development","namespace":"first",
                        "id":f"{source}:{i}","group_id":f"{source}:{i//2 if source=='browsesafe' else i}",
                        "condition":condition,"payload_sha256":sha,"allocation":"development_"+source}
                    plan["requests"][key]=request;bodies[key]=body
    return plan,bodies


class OperationalTests(unittest.TestCase):
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
