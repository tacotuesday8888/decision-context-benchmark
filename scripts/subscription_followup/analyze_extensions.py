"""Closed-only extension analysis. No credentials, network, transport or models.

Pure pilot estimators accept synthetic fixtures. Production loading refuses to
open any extension completion before terminal STOP/journal/core-lineage checks.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import copy
import csv
import io
import json
from pathlib import Path

from scripts.study_v7.requests import canonical, digest
from scripts.subscription_followup import budget, extensions, pilot
from scripts.subscription_followup.analyze_core import (_json, _fingerprint, hash_file, require, signed_bounds)
from scripts.subscription_followup.prepare import write_once

ROOT=Path(__file__).resolve().parents[2]
VERSION="subscription-followup-extension-analysis-1"
SEED="subscription-followup-extension-analysis-v1-20261101"
DRAWS=20000
TERMINAL={"settled","unknown_usage","cancelled_unsent"}
ARMS=("no_gate","Jev_gate")
CONDITIONS=("clean","attack")


def closed_state(manifest_path, *, root=ROOT):
    """Read-only terminal barrier; no completion/accuracy reads in this step."""
    root=Path(root).resolve();manifest,msha=_json(manifest_path)
    execution=(root/manifest["execution_directory"]).resolve()
    require(execution.is_relative_to(root/"data/raw/subscription-followup"),"Execution escapes extension raw namespace")
    if not (execution/"STOP.json").is_file():
        raise RuntimeError("Extension collection is not closed; no current accuracy analysis permitted")
    stop,stop_sha=_json(execution/"STOP.json")
    require(stop.get("status")=="closed" and stop.get("manifest_sha256")==msha,"STOP does not bind exact extension manifest")
    journal=execution/"accounting.jsonl";before=_fingerprint(journal)
    body=journal.read_bytes();require(body.endswith(b"\n"),"Torn extension journal")
    require(digest(body)==stop.get("journal_sha256"),"STOP journal hash differs")
    state=None;previous="0"*64;events=0
    for i,line in enumerate(body.splitlines()):
        event=json.loads(line);sha=event.pop("sha256",None)
        require(event.get("index")==i and event.get("previous_sha256")==previous and digest(canonical(event))==sha,"Journal sequence/hash chain differs")
        state=extensions.ExtensionLedger._apply(state,event["kind"],event["data"])
        previous=sha;events=i+1
    require(before==_fingerprint(journal) and state is not None,"Journal changed/empty")
    require(all(e["status"] in TERMINAL for e in state["entries"].values()),"Extension has nonterminal intents; no accuracy analysis")
    require(state["policy"]["manifest_sha256"]==msha and state["policy"]["run_namespace"]==manifest["run_namespace"],"Policy manifest/namespace differs")
    snapshot,snapshot_sha=_json(execution/"final-ledger-snapshot.json")
    require(snapshot.get("terminal") is True and snapshot["entries"]==state["entries"] and snapshot["policy"]==state["policy"]
            and snapshot["head_sha256"]==previous and snapshot["window_started_at_utc"]==state["window_started_at_utc"]==extensions.GLOBAL_ANCHOR,
            "Final snapshot differs from terminal journal")
    for name,sha in manifest["frozen_files"].items():
        require(hash_file(root/name)==sha,"Frozen extension code/input changed")
    for value in manifest["closed_evidence"].values():
        require(hash_file(root/value["path"])==value["sha256"],"Inherited closed evidence changed")
    require(manifest["analysis"]["seed"]==SEED and manifest["analysis"]["bootstrap_draws"]==DRAWS,"Frozen analysis seed/draws differ")
    # freeze_policy hashes/replays both exact closed core ancestors and validates
    # their original clock, routes and monetary lineage before parses are opened.
    require(root==Path(extensions.ROOT).resolve(),"Use the runtime's exact checkout root")
    expected=extensions.freeze_policy(manifest_path)
    require(canonical(expected)==canonical(state["policy"]),"Frozen extension policy/finite roster differs")
    return manifest,state,execution,{"manifest_sha256":msha,"stop_sha256":stop_sha,
        "journal_sha256":digest(body),"journal_head_sha256":previous,"journal_events":events,"snapshot_sha256":snapshot_sha,
        "core_lineage_sha256":manifest["core_collection_lineage"]["sha256"]}


def spec_for(policy,group,cell):
    stage=cell.get("stage",group["stage"])
    batch=group["group_id"]+":"+stage if group["lane"]=="isolated_agent" else group["group_id"]
    return budget.request_spec(policy,lane=group["lane"],group_id=group["group_id"],batch_id=batch,
        stage=stage,cell_id=cell["cell_id"],config=cell["config"],payload=cell["payload"])


def choices(cell):
    result={cell["payload_sha256"]:copy.deepcopy(cell)}
    for variant in cell.get("payload_variants",{}).values():
        require(digest(canonical(variant["payload"]))==variant["payload_sha256"],"Frozen actor variant differs")
        result[variant["payload_sha256"]]=dict(copy.deepcopy(cell),payload=copy.deepcopy(variant["payload"]),payload_sha256=variant["payload_sha256"])
    return list(result.values())


def verify_attempt(cell,spec,entry,attempts,*,allow_simulated=False):
    """Reparse immutable raw bytes and verify exact once-only scientific identity."""
    directory=Path(attempts)/spec["key"]
    if entry is None or entry["status"]=="cancelled_unsent":
        require(not directory.exists(),"Unsent/unadmitted cell has attempt bytes")
        return {"status":"cancelled_unsent" if entry else "unattempted","valid":False,"prediction":None,"score":None},None
    require(entry["status"] in {"settled","unknown_usage"},"Nonterminal extension attempt")
    require(all(entry.get(k)==v for k,v in spec.items()),"Attempt specification differs from journal")
    result,csha=_json(directory/"completed.json",entry["evidence_sha256"])
    for key,value in {"key":spec["key"],"cell_id":cell["cell_id"],"config":cell["config"],"namespace":cell["namespace"],"request_sha256":cell["payload_sha256"]}.items():
        require(result.get(key)==value,"Completion scientific identity differs")
    require(result.get("route")==budget.ROUTES[cell["config"]]["route"] and result.get("paid_openai_api_request") is False,"Completion route/billing differs")
    hashes=result.get("raw_hashes",{})
    require(hashes.get("request.json")==spec["request_sha256"] and "started.json" in hashes,"Raw full request/start missing")
    for name,sha in hashes.items():
        require(isinstance(name,str) and Path(name).name==name and name not in {".","..","completed.json","simulated-execution.json"},"Unsafe/unbound raw filename")
        require(hash_file(directory/name)==sha,"Raw evidence hash differs")
    actual={p.name for p in directory.iterdir() if p.is_file()}
    permitted=set(hashes)|{"completed.json"}|({"simulated-execution.json"} if allow_simulated else set())
    require(actual<=permitted and set(hashes)|{"completed.json"}<=actual,"Unbound extra/missing raw file")
    payload,_=_json(directory/"request.json",spec["request_sha256"])
    require(canonical(payload)==canonical(cell["payload"]),"Complete materialized payload differs")
    started,_=_json(directory/"started.json",hashes["started.json"])
    for key,value in {"key":spec["key"],"cell_id":cell["cell_id"],"config":cell["config"],"namespace":cell["namespace"],"payload_sha256":spec["request_sha256"]}.items():
        require(started.get(key)==value,"Started identity differs")
    parsed=result.get("parsed");require(isinstance(parsed,dict) and isinstance(parsed.get("status"),str),"Missing terminal parsed disposition")
    if result.get("native_request_sent") is True:
        require("response.raw" in hashes,"Sent attempt lacks raw response")
        from scripts.subscription_followup.transport import parse_structured, parse_classification
        body=(directory/"response.raw").read_text()
        reparsed=parse_structured(body,payload,result["observation"]) if cell["config"]=="sol_subscription" else parse_classification(cell["config"],result["observation"],body)
        require(canonical(reparsed)==canonical(parsed),"Raw terminal parse differs from frozen retained parse")
    else:
        require(parsed.get("valid") is not True,"Never-sent attempt cannot have valid output")
    if entry["status"]=="settled":
        cost="0" if result.get("native_request_sent") is False else budget.usage_cost(cell["config"],parsed.get("usage"))
        require(cost is not None and budget.money(cost)==budget.money(entry["actual_usd"]),"Usage/settlement differs")
    return parsed,{"key":spec["key"],"completed_sha256":csha,"payload_sha256":spec["request_sha256"],
        "started_sha256":hashes["started.json"],"provider_request_id":parsed.get("provider_request_id"),"directory":str(directory)}


def recompute_actor(task,parsed):
    if parsed.get("status")!="ok" or parsed.get("valid") is not True:
        return None
    try:
        return pilot.evaluate(task,parsed.get("answer"))
    except ValueError:
        return {"status":"invalid_action_packet","legitimate_completion":None,"attacker_success":None}


def verify_gate_choice(original,gate,actual,*,admitted):
    disposition=pilot.gate_disposition(gate.get("score"),status=gate["status"])
    expected=pilot.select_actor_payload(original,disposition)
    if expected is None:
        require(not admitted,"Missing gate cannot admit any gated actor")
    elif admitted:
        require(digest(canonical(expected))==actual["payload_sha256"] and canonical(expected)==canonical(actual["payload"]),
                "Gate-selected variant differs from retained actor")
    return expected


def verify_simulated(cell,parsed,task,directory):
    derived=recompute_actor(task,parsed);path=Path(directory)/"simulated-execution.json"
    if derived is None:
        require(not path.exists(),"Missing provider result cannot create simulated protection")
        return None
    saved,sha=_json(path)
    require(canonical(saved)==canonical({"cell_id":cell["cell_id"],"result":derived,"no_external_actions":True}),
            "Simulated execution differs from raw packet/frozen interpreter")
    return sha


def analyze_pilot(plan,cells,observations):
    """Fixed12-case joint/transition tables and finite missingness bounds; no CI."""
    tasks={t["task_id"]:t for t in plan["tasks"]};require(len(tasks)==12,"Exactly12 frozen pilot tasks required")
    require(pilot.VERSION==plan["version"]=="subscription-followup-isolated-agent-4","Frozen pilot v4 required")
    indexed={c["cell_id"]:c for c in cells};require(len(indexed)==len(cells)==72,"Exact72 planned pilot cells required")
    require(set(observations)<=set(indexed),"Unplanned pilot outcome")
    actors={};gate_rows=[];details=[];gate_identities=set()
    for c in cells:
        require(c["task_id"] in tasks and c["condition"] in CONDITIONS,"Pilot task/condition differs")
        parsed=observations.get(c["cell_id"],{"status":"unattempted","valid":False})
        if c["kind"]=="gate":
            identity=(c["task_id"],c["condition"])
            require(identity not in gate_identities,"Duplicate pilot gate task/condition")
            gate_identities.add(identity)
            gate_rows.append({"task_id":c["task_id"],"condition":c["condition"],"status":parsed["status"],
                "disposition":pilot.gate_disposition(parsed.get("score"),status=parsed["status"])})
            continue
        require(c["kind"]=="actor" and c["arm"] in ARMS,"Unexpected pilot scientific cell")
        if c["arm"]=="Jev_gate" and parsed.get("valid") is True:
            gate=observations.get(c["gate_cell_id"],{"status":"unattempted"})
            require(pilot.gate_disposition(gate.get("score"),status=gate["status"])!="missing",
                    "A missing gate cannot produce a gated actor outcome")
        identity=(c["task_id"],c["condition"],c["arm"]);require(identity not in actors,"Duplicate actor cell")
        value=recompute_actor(tasks[c["task_id"]],parsed)
        complete=value is not None and type(value.get("legitimate_completion")) is bool and type(value.get("attacker_success")) is bool
        actors[identity]={"legitimate_completion":int(value["legitimate_completion"]) if complete else None,
                          "attacker_success":int(value["attacker_success"]) if complete else None,
                          "status":value.get("status",parsed["status"]) if value else parsed["status"]}
        details.append({"task_id":c["task_id"],"condition":c["condition"],"arm":c["arm"],**actors[identity]})
    require(set(actors)=={(t,c,a) for t in tasks for c in CONDITIONS for a in ARMS}
            and gate_identities=={(t,c) for t in tasks for c in CONDITIONS},"Pilot planned crossing differs")
    joint=[]
    for condition in CONDITIONS:
        for arm in ARMS:
            part=[actors[(t,condition,arm)] for t in sorted(tasks)]
            complete=[v for v in part if v["legitimate_completion"] is not None]
            table=Counter((v["attacker_success"],v["legitimate_completion"]) for v in complete);missing=12-len(complete)
            row={"condition":condition,"arm":arm,"planned_tasks":12,"valid_outcome_tasks":len(complete),"missing_tasks":missing,
                "joint_counts":{f"attacker_{a}_completion_{u}":table[(a,u)] for a in (0,1) for u in (0,1)},
                "status_counts":dict(Counter(v["status"] for v in part))}
            for outcome in ("attacker_success","legitimate_completion"):
                n=sum(v[outcome] for v in complete)
                row[outcome]={"known_true":n,"valid_denominator":len(complete),"planned_denominator":12,
                    "available_rate":n/len(complete) if complete else None,"all_planned_bounds":[n/12,(n+missing)/12]}
            joint.append(row)
    paired=[];transitions=[]
    for condition in CONDITIONS:
        for outcome in ("attacker_success","legitimate_completion"):
            pairs=[(actors[(t,condition,"no_gate")][outcome],actors[(t,condition,"Jev_gate")][outcome]) for t in sorted(tasks)]
            complete=[(a,b) for a,b in pairs if a is not None and b is not None]
            bounds=[signed_bounds([a,b],[1,-1]) for a,b in pairs]
            paired.append({"condition":condition,"outcome":outcome,"direction":"no_gate minus Jev_gate",
                "planned_tasks":12,"paired_tasks":len(complete),"paired_mean_difference":sum(a-b for a,b in complete)/len(complete) if complete else None,
                "all_planned_missing_bounds":[sum(v[i] for v in bounds)/12 for i in (0,1)],
                "transition_counts":{f"no_gate_{a}_Jev_gate_{b}":sum(aa==a and bb==b for aa,bb in complete) for a in (0,1) for b in (0,1)}})
        if condition=="attack":
            counts=Counter()
            for t in sorted(tasks):
                a,b=actors[(t,condition,"no_gate")],actors[(t,condition,"Jev_gate")]
                if all(v[k] is not None for v in (a,b) for k in ("attacker_success","legitimate_completion")):
                    counts[(a["attacker_success"],a["legitimate_completion"],b["attacker_success"],b["legitimate_completion"])]+=1
            transitions=[{"no_gate_attacker":a,"no_gate_completion":u,"Jev_gate_attacker":b,"Jev_gate_completion":v,"tasks":counts[(a,u,b,v)]}
                         for a in (0,1) for u in (0,1) for b in (0,1) for v in (0,1)]
    return {"planned_tasks":12,"task_ids":sorted(tasks),"task_ids_sha256":digest(canonical(sorted(tasks))),
        "joint_outcomes":joint,"paired_differences":paired,"attacked_joint_transitions":transitions,
        "gate_dispositions":[{"condition":c,"planned_tasks":12,"counts":dict(Counter(r["disposition"] for r in gate_rows if r["condition"]==c))} for c in CONDITIONS],
        "case_outcomes":details,"fixed_case_descriptive_only":True,"population_confidence_intervals":False,"pvalues":False}


def load_artifacts(manifest_path,*,root=ROOT):
    manifest,state,execution,proof=closed_state(manifest_path,root=root);root=Path(root).resolve()
    plan,plan_sha=_json(root/manifest["plan"]["path"],manifest["plan"]["sha256"])
    require(plan["run_namespace"]==manifest["run_namespace"] and plan["total_cells"]==1128 and len(plan["groups"])==78,"Exact frozen extension plan differs")
    require(plan["counts"]=={"sol_subscription":576,"jev_firstparty":552},"Frozen route counts differ")
    require(pilot.VERSION==plan["pilot"]["version"]=="subscription-followup-isolated-agent-4","Wrong frozen pilot scorer")
    records={};candidate_keys=set();selected={};groups_by_cell={}
    for group in plan["groups"]:
        for cell in group["cells"]:
            require(cell["cell_id"] not in records and cell["group_id"]==group["group_id"] and cell["namespace"]==manifest["run_namespace"],"Cell/group/namespace differs")
            require(cell.get("first_attempt_primary") is True and digest(canonical(cell["payload"]))==cell["payload_sha256"],"Frozen first-cell payload differs")
            records[cell["cell_id"]]=cell;groups_by_cell[cell["cell_id"]]=group
            available=[]
            for variant in choices(cell):
                spec=spec_for(state["policy"],group,variant);candidate_keys.add(spec["key"])
                if spec["key"] in state["entries"]:available.append((variant,spec,state["entries"][spec["key"]]))
            require(len(available)<=1,"Multiple variants/attempts for one scientific cell")
            selected[cell["cell_id"]]=available[0] if available else (cell,spec_for(state["policy"],group,cell),None)
    require(len(records)==1128 and set(state["entries"])<=candidate_keys,"Unplanned journal cell/key")
    require(set(state["policy"]["extension_roster"])==set(records),"Policy/plan roster differs")
    attempts=execution/"attempts"
    if attempts.exists():require({p.name for p in attempts.iterdir()}<={k for k,e in state["entries"].items() if e["status"] in {"settled","unknown_usage"}},"Unbound/unsent attempt directory")
    parsed={};metadata={};source_rows=[];pilot_cells=[];tasks={t["task_id"]:t for t in plan["pilot"]["tasks"]}
    # Verify gates first, regardless of their placement in the full saved plan.
    ordered=sorted(records.values(),key=lambda c:0 if c.get("kind")=="gate" else 1)
    for original in ordered:
        cell,spec,entry=selected[original["cell_id"]]
        if original.get("arm")=="Jev_gate":
            gate=parsed.get(original["gate_cell_id"]);require(gate is not None,"Gate must verify before actor variant")
            expected=verify_gate_choice(original,gate,cell,admitted=entry is not None)
            if expected is None:
                parsed[original["cell_id"]]={"status":"gate_missing_no_actor","valid":False,"prediction":None,"score":None};continue
        value,meta=verify_attempt(cell,spec,entry,attempts,allow_simulated=cell.get("kind")=="actor")
        parsed[cell["cell_id"]]=value
        if meta:metadata[cell["cell_id"]]=meta
        if cell.get("kind")=="actor" and meta:
            sha=verify_simulated(cell,value,tasks[cell["task_id"]],meta["directory"])
            if sha:meta["simulated_execution_sha256"]=sha
    for cell in records.values():
        value=parsed[cell["cell_id"]]
        group=groups_by_cell[cell["cell_id"]]
        if group["lane"]=="second_source":
            source_rows.append({"id":cell["id"],"group_id":cell["source_group_id"],"config":cell["config"],
                "condition":cell["condition"],"gold":cell["upstream_label"],"upstream_label":cell["upstream_label"],
                "namespace":cell["namespace"],"replicate":"first","stage":"secondary",
                **{k:value.get(k) for k in ("status","valid","prediction","score")}})
        else:pilot_cells.append(cell)
    require(len(source_rows)==1056 and len(pilot_cells)==72 and len({r["group_id"] for r in source_rows})==66,"Frozen scientific denominators differ")
    # Require exact evidence for every cancellation too, with positive unsent proof.
    for key,entry in state["entries"].items():
        if entry["status"]=="cancelled_unsent":
            cancellation,_=_json(execution/"unsent-closeout.json",entry["evidence_sha256"])
            require(key in cancellation["keys"],"Unsent closeout omits cancelled key")
    proof.update(plan_sha256=plan_sha,admitted_cells=len(state["entries"]),unattempted_cells=1128-len(state["entries"]),
        verified_completion_count=len(metadata),completed_evidence_sha256=digest(canonical(sorted((cid,m["completed_sha256"]) for cid,m in metadata.items()))))
    return {"source_rows":source_rows,"pilot_plan":plan["pilot"],"pilot_cells":pilot_cells,
            "observations":{c["cell_id"]:parsed[c["cell_id"]] for c in pilot_cells},"proof":proof}


def flatten(value,path=""):
    if isinstance(value,(dict,list)) and not value:
        yield {"path":path,"value_json":json.dumps(value)}
    elif isinstance(value,dict):
        for key,child in value.items():yield from flatten(child,(path+"/"+str(key)).lstrip("/"))
    elif isinstance(value,list):
        for i,child in enumerate(value):yield from flatten(child,path+"/"+str(i))
    else:yield {"path":path,"value_json":json.dumps(value,ensure_ascii=False,allow_nan=False)}


def csv_bytes(rows):
    rows=list(rows);fields=list(dict.fromkeys(k for row in rows for k in row)) or ["path","value_json"]
    stream=io.StringIO(newline="");writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    return stream.getvalue().encode()


def analyze_loaded(loaded,*,draws=DRAWS):
    from scripts.subscription_followup.extension_math import analyze_source
    return {"version":VERSION,"seed":SEED,"bootstrap_draws":draws,"proof":loaded["proof"],
            "source":analyze_source(loaded["source_rows"],draws=draws),
            "pilot":analyze_pilot(loaded["pilot_plan"],loaded["pilot_cells"],loaded["observations"]),
            "datasets_pooled":False,"new_pvalues":False}


def save_analysis(loaded,output_dir):
    result=analyze_loaded(loaded);out=Path(output_dir)
    files={"analysis.json":canonical(result)+b"\n","source.json":canonical(result["source"])+b"\n",
           "pilot.json":canonical(result["pilot"])+b"\n","provenance.json":canonical(result["proof"])+b"\n",
           "source-table.csv":csv_bytes(flatten(result["source"])),"pilot-table.csv":csv_bytes(flatten(result["pilot"]))}
    for name,body in files.items():
        path=out/name;require(not path.exists() or path.read_bytes()==body,"Refuse changed analysis overwrite")
    for name,body in files.items():write_once(out/name,body)
    return {"output_directory":str(out),"outputs":{name:digest(body) for name,body in files.items()}}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--root",type=Path,default=ROOT)
    parser.add_argument("--output-dir",type=Path,default=ROOT/"results/subscription-followup-extensions-execution")
    args=parser.parse_args()
    print(json.dumps(save_analysis(load_artifacts(args.manifest,root=args.root),args.output_dir),indent=2,sort_keys=True))
