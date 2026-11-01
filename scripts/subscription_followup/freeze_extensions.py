"""Offline immutable extension MF/owner-permit builder; never self-review/execute.

Only the root may invoke this with the final closed core lineage. The executor
still requires an independently supplied review bound to the produced manifest.
"""
from __future__ import annotations
import argparse
import copy
from datetime import datetime, timezone
import json
import math
from pathlib import Path

from scripts.study_v7.requests import canonical, digest
from scripts.subscription_followup import budget, extensions
from scripts.subscription_followup.analyze_core import hash_file, _json, require
from scripts.subscription_followup.prepare import write_once
from scripts.subscription_followup.prepare_extensions import NAMESPACE, SOURCE_ROWS_SHA, SOURCE_MANIFEST_SHA, SOURCE_SCHEDULE_SHA, PILOT_PLAN_SHA
from scripts.subscription_followup.continue_core import OVERLOAD_KEY

ROOT=Path(__file__).resolve().parents[2]
PLAN_SHA="65beeff34652de2eb488bad1713b04107074b9f12eaf5c45ee6632e306dec4ed"
SEED="subscription-followup-extension-analysis-v1-20261101"
OWNER_TURN="01a1977a-0e31-71b0-a539-d39cd1b0a8bf"
OWNER_CHAT="01a18da8-0f25-7372-830a-0907fc637c28"
OWNER_INSTRUCTION="Go ahead and finish those gaps. Use the subscription for OpenAI, keep everything on GitHub, and handle the other chats yourself. Don't write the paper yet, just get the experiments finished properly."
CORE_MANIFEST="results/subscription-followup/run-manifest-core-v2.json"
OWNER_FILE="results/subscription-followup/owner-authorization-core-v1.json"
INPUTS={
    "extension_preparation":"results/subscription-followup/extensions-preparation-v1.json",
    "preparation_review":"results/subscription-followup/extensions-preparation-review-v1.json",
    "source_selection":"results/subscription-followup/second-source-selection-v1.json",
    "source_capacity":"results/subscription-followup/second-source-capacity-v1.json",
    "source_audit":"results/subscription-followup/second-source-audit-v1.json",
    "source_precision":"results/subscription-followup/second-source-precision-v1.json",
    "source_rows":"data/raw/subscription-followup/second-source/selected-pairs-v1.jsonl",
    "source_schedule":"data/raw/subscription-followup/second-source/second-source-proposed-schedule-v1.json",
    "pilot_preparation":"results/subscription-followup/isolated-agent-preparation-v4.json",
    "pilot_plan":"data/raw/subscription-followup/isolated-agent-plan-v4.json",
}
STATIC_DOCS=("docs/subscription-followup/EXTENSIONS-PROTOCOL-v1.md",
             "docs/subscription-followup/SECOND-SOURCE.md","docs/subscription-followup/SOURCE-METHODS.md")
SOURCE_PROVENANCE=("dtap-code/LICENSE","dtap-code/README.md","dtap-code/tree.json","dtap-data/README.md",
                   "dtap-data/crm-benign-tree.json","dtap-data/crm-malicious-indirect-tree.json",
                   "dtap-data/legal-benign-tree.json","dtap-data/legal-malicious-indirect-tree.json")


def descriptor(path):
    path=Path(path).resolve()
    return {"path":str(path),"sha256":hash_file(path),"bytes":path.stat().st_size}


def prior_failure(core,*,root):
    """Preserve the exact one reviewed availability event, not a reset counter."""
    receipt,_=_json(core["closed_evidence"]["core_v1_receipt"]["path"],core["closed_evidence"]["core_v1_receipt"]["sha256"])
    require(receipt["failed_request_key"]==OVERLOAD_KEY and receipt["failure_code"]=="server_is_overloaded"
            and receipt["failure_http_status"]==200 and receipt["failure_type"]=="service_unavailable_error",
            "The reviewed original overload evidence differs")
    value=receipt["failed_first_outcome"]
    require(hash_file(value["path"])==value["sha256"],"Original failed first evidence changed")
    return [{"key":OVERLOAD_KEY,"http_status":200,"error_code":"server_is_overloaded","retry_after_seconds":120.}],copy.deepcopy(value)


def freeze(lineage_path,*,root=ROOT,now=None):
    root=Path(root).resolve();require(root==Path(extensions.ROOT).resolve(),"Exact execution checkout required")
    lineage,lineage_sha=_json(lineage_path)
    # This is deliberately before output creation and any derived permit.
    closure=extensions.verify_closed_core(lineage)
    require(closure=={"actual_cells":4510,"anchor":extensions.GLOBAL_ANCHOR,"deadline":extensions.GLOBAL_DEADLINE},"Original closed core scope/clock differs")
    core,core_sha=_json(root/CORE_MANIFEST,extensions.CORE_MANIFESTS[1])
    owner,owner_sha=_json(root/OWNER_FILE)
    require(owner.get("experimental_inference_authorized") is True and owner.get("authorization_source")=="explicit_owner_instruction"
            and owner.get("manifest_sha256")==extensions.CORE_MANIFESTS[0] and owner.get("human_turn")==OWNER_TURN
            and owner.get("trusted_source_chat")==OWNER_CHAT and owner.get("openai_subscription_only") is True
            and owner.get("allow_paid_openai_api") is False and owner.get("allow_purchases_or_recharge") is False
            and owner.get("owner_instruction")==OWNER_INSTRUCTION
            and owner.get("prior_typesafe_conservative_accounted_usd")==budget.PRIOR["typesafe"]
            and owner.get("typesafe_cumulative_cap_usd")==budget.CAPS["typesafe"],"Exact existing owner instruction/route authority required")
    bound={key:descriptor(root/path) for key,path in INPUTS.items()}
    values={key:_json(root/path)[0] for key,path in INPUTS.items() if key not in {"source_rows"}}
    require(bound["source_rows"]["sha256"]==SOURCE_ROWS_SHA and bound["source_schedule"]["sha256"]==SOURCE_SCHEDULE_SHA
            and bound["pilot_plan"]["sha256"]==PILOT_PLAN_SHA,"Original source/pilot input bytes changed")
    selection=values["source_selection"];prep=values["extension_preparation"];review=values["preparation_review"]
    require(selection["selection_manifest_sha256"]==SOURCE_MANIFEST_SHA and selection["selected_groups"]==66
            and selection["selected_rows"]==132 and selection["historically_exposed_components"]==0,"Source selection/freshness denominator differs")
    require(review.get("status")=="pass" and not review.get("remaining_preparation_findings")
            and review.get("execution_not_authorized_by_this_review") is True,"Independent preparation review required")
    for name,sha in review["inputs"].items():
        require(hash_file(root/"results/subscription-followup"/name)==sha,"Preparation review input changed")
    for name,sha in selection["preparation_code_sha256"].items():require(hash_file(root/name)==sha,"Source preparation code binding differs")
    for name,sha in prep["code_sha256"].items():require(hash_file(root/name)==sha,"Combined preparation code changed")
    for name,value in prep["inputs"].items():require(hash_file(root/value["path"])==value["sha256"],"Combined preparation original input changed")
    plan_path=root/prep["plan"]["path"];plan,plan_sha=_json(plan_path,PLAN_SHA)
    require(plan_sha==prep["plan"]["sha256"] and plan["run_namespace"]==NAMESPACE and plan["total_cells"]==1128
            and plan["counts"]=={"sol_subscription":576,"jev_firstparty":552}
            and plan["group_counts"]=={"second_source":66,"isolated_agent":12},"Exact reviewed extension scope differs")
    require(plan["pilot"]["version"]=="subscription-followup-isolated-agent-4" and values["pilot_preparation"]["plan"]["sha256"]==PILOT_PLAN_SHA,
            "Only the reviewed pilot v4 is admitted")
    frozen={}
    for name,sha in core["frozen_files"].items():
        require(hash_file(root/name)==sha,"Inherited frozen dependency changed")
        frozen[name]=sha
    explicit={root/path for path in STATIC_DOCS}|set((root/"scripts/subscription_followup").glob("*.py"))|set((root/"tests/subscription_followup").glob("test_*.py"))
    explicit.update(root/path for path in INPUTS.values())
    explicit.update({root/CORE_MANIFEST,root/OWNER_FILE,plan_path})
    for name in SOURCE_PROVENANCE:
        path=root/"data/raw/subscription-followup/second-source"/name
        receipt=path.with_suffix(path.suffix+".receipt.json")
        acquisition,_=_json(receipt)
        require(hash_file(path)==acquisition["sha256"] and acquisition.get("authenticated") is False
                and acquisition.get("repository_code_executed") is False,"Pinned source licence/inventory acquisition differs")
        explicit.update((path,receipt))
    for proof in selection["source_file_proofs"]:
        path=root/proof["path"];require(hash_file(path)==proof["sha256"],"Pinned original source bytes changed")
        explicit.add(path)
        receipt=path.with_suffix(path.suffix+".receipt.json")
        require(hash_file(receipt)==proof["receipt_sha256"],"Original public acquisition receipt changed")
        explicit.add(receipt)
    for path in sorted(explicit):
        require(path.resolve().is_relative_to(root),"Frozen extension file escapes checkout")
        frozen[str(path.relative_to(root))]=hash_file(path)
    failures,failure_evidence=prior_failure(core,root=root)
    event_proofs=[];seen_failures={OVERLOAD_KEY};consecutive=0;old_overload_events=0
    for index,run in enumerate(lineage["runs"]):
        mf,_=_json(run["manifest_path"],run["manifest_sha256"])
        path=root/mf["execution_directory"]/"runtime-events.jsonl"
        events=[json.loads(line) for line in path.read_text().splitlines()]
        for event in events:
            if event.get("kind")=="valid_response":
                consecutive=0
            elif (index==0 and event.get("kind")=="fatal_failure" and event.get("key")==OVERLOAD_KEY
                  and event.get("http_status")==200 and event.get("error_code")=="server_is_overloaded"):
                old_overload_events+=1;consecutive+=1
            elif event.get("kind")=="service_failure":
                key=event.get("key");http=event.get("http_status");retry=event.get("retry_after_seconds")
                require(isinstance(key,str) and key not in seen_failures,"Duplicate availability event/attempt key")
                require((type(http) is int and 500<=http<=599) or
                        (http==200 and event.get("error_code")=="server_is_overloaded"),"Unapproved prior availability event")
                require(type(retry) in (int,float) and math.isfinite(retry) and 120<=retry<=600,"Prior cooldown exhausted/outside frozen bound")
                row={k:event[k] for k in ("key","http_status","retry_after_seconds","error_code") if k in event}
                failures.append(row);seen_failures.add(key);consecutive+=1
        event_proofs.append(descriptor(path))
    require(old_overload_events==1,"Original overload must appear once in the original closed runtime metadata")
    require(len(failures)<=5 and consecutive<3,"Global technical recovery bound is already exhausted")
    manifest_path=root/"results/subscription-followup/run-manifest-extensions-v1.json"
    auth_path=root/"results/subscription-followup/owner-authorization-extensions-v1.json"
    current=now or datetime.now(timezone.utc)
    require(current.tzinfo is not None,"UTC-aware freeze time required")
    require(current<budget._utc(extensions.GLOBAL_DEADLINE),"Original global admission window has ended")
    recorded=_json(manifest_path)[0]["frozen_at_utc"] if manifest_path.exists() else current.astimezone(timezone.utc).isoformat()
    lanes={name:{"enabled":name in {"second_source","isolated_agent"}} for name in budget.LANES}
    lanes["isolated_agent"].update(pilot_ready=True,pilot_receipt_sha256=bound["pilot_preparation"]["sha256"])
    closed=copy.deepcopy(core["closed_evidence"])
    closed.update({"extension_"+key:value for key,value in bound.items()})
    closed["explicit_owner_instruction"]={"path":str((root/OWNER_FILE).resolve()),"sha256":owner_sha}
    closed["prior_failed_first_evidence"]=failure_evidence
    for i,value in enumerate(event_proofs):closed[f"core_runtime_events_{i}"]=value
    manifest={"version":"subscription-followup-extensions-manifest-1","run_namespace":NAMESPACE,"frozen_at_utc":recorded,
        "execution_directory":"data/raw/subscription-followup/execution-extensions-v1","workers":4,"window_seconds":18000,
        "plan":{"path":str(plan_path.relative_to(root)),"sha256":plan_sha,"bytes":plan_path.stat().st_size},
        "plan_cells":1128,"plan_counts":plan["counts"],"group_counts":plan["group_counts"],"lanes":lanes,
        "routes":copy.deepcopy(budget.ROUTES),"frozen_files":dict(sorted(frozen.items())),"closed_evidence":closed,
        "core_collection_lineage":{"path":str(Path(lineage_path).resolve()),"sha256":lineage_sha},
        "global_clock_anchor_utc":extensions.GLOBAL_ANCHOR,"global_deadline_utc":extensions.GLOBAL_DEADLINE,
        "prior_transient_failure_events":failures,"global_availability_policy":{"maximum_total_events":5,
            "maximum_consecutive_events":3,"prior_events_counted":True,"minimum_cooldown_seconds":120,"maximum_retry_after_seconds":600},
        "prior_consecutive_service_failures":consecutive,
        "maximum_jev_calls":552,"maximum_jev_full_context_reservation_usd":"0.741888","paid_openai_api_allowed":False,
        "no_route_model_substitution":True,"independent_execution_review_required":True,
        "analysis":{"protocol":"docs/subscription-followup/EXTENSIONS-PROTOCOL-v1.md","seed":SEED,"bootstrap_draws":20000,
            "descriptive_only":True,"source_planned_groups":66,"source_common_required_cells":16,"pilot_planned_tasks":12,
            "pointwise_alpha":.05,"all_planned_missing_bounds":True,"pilot_population_intervals":False,"new_pvalues":False}}
    mbody=canonical(manifest)+b"\n";msha=digest(mbody)
    authorization={key:copy.deepcopy(owner[key]) for key in ("authorization_source","owner_instruction","human_turn","trusted_source_chat",
        "openai_subscription_only","allow_paid_openai_api","allow_purchases_or_recharge")}
    authorization.update(version="subscription-followup-extension-owner-authorization-1",experimental_inference_authorized=True,
        manifest_sha256=msha,recorded_at_utc=recorded,max_sol_calls=576,max_jev_calls=552,max_extension_calls=1128,
        global_clock_anchor_utc=extensions.GLOBAL_ANCHOR,original_deadline_utc=extensions.GLOBAL_DEADLINE,
        prior_typesafe_conservative_accounted_usd=budget.PRIOR["typesafe"],typesafe_cumulative_cap_usd=budget.CAPS["typesafe"],
        maximum_extension_jev_usd="0.741888",no_route_model_substitution=True,
        source_owner_authorization={"path":str((root/OWNER_FILE).resolve()),"sha256":owner_sha},
        independent_review_still_required=True,no_review_authorization_created=True)
    abody=canonical(authorization)+b"\n"
    for path,body in ((manifest_path,mbody),(auth_path,abody)):
        require(not path.exists() or path.read_bytes()==body,"Refuse to replace different immutable extension freeze output")
    write_once(manifest_path,mbody);write_once(auth_path,abody)
    return {"manifest":{"path":str(manifest_path),"sha256":msha},"owner_authorization":{"path":str(auth_path),"sha256":digest(abody)},
            "frozen_files":len(frozen),"planned_cells":1128,"review_created":False,"inference_performed":False}


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lineage",type=Path,required=True)
    parser.add_argument("--root",type=Path,default=ROOT)
    args=parser.parse_args()
    print(json.dumps(freeze(args.lineage,root=args.root),indent=2,sort_keys=True))
