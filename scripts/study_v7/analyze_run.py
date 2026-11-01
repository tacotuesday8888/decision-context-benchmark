"""Offline v7 first-attempt analysis and artifact driver; no inference or paper.

The native primary procedure is imported unchanged. Other model comparisons are
descriptive on predeclared source subsets, with pair-specific complete cohorts.
Every planned confirmation first cell remains in coverage/missingness reporting.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from itertools import combinations
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.study_v7 import analysis, report
from scripts.study_v7.operational import retained_attempt
from scripts.study_v7.requests import PANEL, canonical, digest

ROOT=Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT=ROOT/"results/study-v7-execution"
CONTEXTUAL=("jev_firstparty","luna_decisions","luna_responses","sol_responses","sol_subscription")
BOOLEAN={"luna_responses","sol_responses","sol_subscription"}


def reconstruct_confirmation(plan, attempts_directory):
    """Normalize all current-plan confirmation first cells; never use repeats."""
    attempts=Path(attempts_directory);rows=[];seen=set();invariants={}
    active=set(plan["active_configurations"])
    for cell in plan["cells"]:
        if cell["split"]!="confirmation" or cell["namespace"]!="first":
            continue
        key=cell["request_key"];request=plan["requests"].get(key)
        if request is None or request.get("key")!=key or any(request.get(k)!=cell.get(k) for k in
                ("id","config","source","group_id","condition","split","namespace")):
            raise ValueError("Confirmation cell differs from its frozen request identity")
        if cell["config"] not in active or cell["source"] not in {"browsesafe","promptshield"}:
            raise ValueError("Inactive or unknown confirmation configuration/source")
        identity=(cell["id"],cell["config"],cell["condition"])
        if identity in seen:
            raise ValueError("Duplicate planned confirmation cell")
        seen.add(identity)
        gold=cell["upstream_label"]
        if not analysis._binary(gold):
            raise ValueError("Original binary source label required")
        invariant=(cell["source"],cell["group_id"],cell.get("pair_id"),int(gold))
        if cell["id"] in invariants and invariants[cell["id"]]!=invariant:
            raise ValueError("Original source/group/pair/label changed across model conditions")
        invariants[cell["id"]]=invariant
        directory=attempts/key
        if (directory/"started.json").exists():
            started=json.loads((directory/"started.json").read_text())
            if (started.get("key")!=key or started.get("config")!=request["config"] or
                    started.get("namespace")!="first" or started.get("payload_sha256")!=request["payload_sha256"] or
                    started.get("route")!=PANEL[request["config"]]["route"]):
                raise ValueError("Started first-attempt identity changed")
            if not (directory/"request.json").exists() or digest((directory/"request.json").read_bytes())!=request["payload_sha256"]:
                raise ValueError("Started raw request differs from its frozen payload")
        if (directory/"completed.json").exists():
            completed=json.loads((directory/"completed.json").read_text())
            if not (directory/"started.json").is_file() or completed.get("raw_hashes",{}).get("started.json")!=digest((directory/"started.json").read_bytes()):
                raise ValueError("Completed evidence lacks its exact started record")
            for field in ("id","config"):
                if field in completed and completed[field]!=request[field]:
                    raise ValueError("Completed optional cell identity changed")
        if (directory/"interrupted.json").exists():
            interrupted=json.loads((directory/"interrupted.json").read_text())
            if interrupted.get("key")!=key or interrupted.get("first_attempt_primary") is not True:
                raise ValueError("Interrupted first-attempt identity changed")
        retained=retained_attempt(request,attempts)
        parsed=retained["parsed"];status=retained["status"];valid=retained["valid"]
        prediction=parsed.get("prediction") if valid else None
        score=parsed.get("score")
        if status in {"pending","reserved","running","in_flight","started"}:
            raise ValueError("Nonterminal output cannot enter analysis")
        if valid and (status!="ok" or not analysis._binary(prediction)):
            raise ValueError("Valid retained classification requires a binary prediction")
        if valid and parsed.get("returned_model")!=PANEL[cell["config"]]["model"]:
            raise ValueError("Valid retained response has a different model identity")
        if valid and cell["config"]=="protectai_local" and parsed.get("revision")!=PANEL["protectai_local"]["revision"]:
            raise ValueError("Valid local response has a different pinned revision")
        if valid and request.get("configuration_revision") is not None and parsed.get("configuration_revision")!=request["configuration_revision"]:
            raise ValueError("Parsed response has a different explicit configuration revision")
        if cell["config"] in BOOLEAN:
            if score is not None:
                raise ValueError("Boolean outputs cannot invent confidence scores")
        elif score is not None and not analysis._probability(score):
            raise ValueError("Native probability is invalid")
        if valid and cell["config"] not in BOOLEAN:
            if score is None or score==.5 or int(prediction)!=int(score>.5):
                raise ValueError("Native classification must use frozen threshold0.5 with ties abstaining")
        if status in {"tie","tied"} and (valid or score!=.5):
            raise ValueError("Native ties must abstain and retain probability0.5")
        rows.append(dict(cell,gold=int(gold),status=status,valid=valid,prediction=prediction,score=score,
                         configuration_revision=request.get("configuration_revision")))
    unknown=[];ignored=Counter()
    if attempts.exists():
        for directory in attempts.iterdir():
            if not directory.is_dir() or len(directory.name)!=64 or any(c not in "0123456789abcdef" for c in directory.name):
                continue
            request=plan["requests"].get(directory.name)
            if request is None:
                unknown.append(directory.name)
                ignored["legacy_completed_directories"]+=int((directory/"completed.json").is_file())
                ignored["legacy_interrupted_directories"]+=int((directory/"interrupted.json").is_file())
            elif request["split"]!="confirmation" or request["namespace"]!="first":
                ignored["current_plan_nonconfirmation_or_repeat_directories"]+=1
    return rows,{"planned_confirmation_first_cells":len(rows),"ignored_legacy_directories":len(unknown),
                 "ignored_legacy_keys_sha256":digest(canonical(sorted(unknown))),**dict(ignored),
                 "repeat_or_development_outputs_substituted":False}


def matched_comparisons(plan, rows, *, draws=analysis.BOOTSTRAP_DRAWS, seed=analysis.SEED):
    """Predeclared pair-specific descriptive comparisons; no additional p values."""
    active=set(plan["active_configurations"])
    contextual=[c for c in CONTEXTUAL if c in active]
    all_configs=[c for c in PANEL if c in active]
    main_groups=list(plan["subsets"]["general_groups"])
    external_ids=list(plan["subsets"]["external_general_ids"])
    if len(set(main_groups))!=len(main_groups) or len(set(external_ids))!=len(external_ids):
        raise ValueError("Fixed general subsets contain duplicate identifiers")
    main={};external={}
    for row in rows:
        if row["source"]=="browsesafe":
            key=(row["group_id"],row["config"],row["condition"],row["gold"])
            if key in main:raise ValueError("Main comparison has duplicate group/model/condition/arm")
            main[key]=row
        else:
            key=(row["id"],row["config"])
            if key in external:raise ValueError("External comparison must have one original request per model")
            external[key]=row
    result=[]
    def finish(source,condition,left,right,planned,complete,values,planned_classes,complete_classes,cohort_members,estimand,left_condition,right_condition):
        intervals=analysis.bootstrap_mean(values,draws=draws,seed=f"{seed}/descriptive/{source}/{condition}/{left}/{right}")
        result.append({"source":source,"condition":condition,"left_config":left,"right_config":right,
            "left_condition":left_condition,"right_condition":right_condition,"matched_cohort":True,
            "cohort_id":digest(canonical(sorted(cohort_members))),"planned_groups":planned,"complete_groups":complete,
            "planned_rows":sum(planned_classes.values()),"complete_rows":sum(complete_classes.values()),
            "planned_class_rows":dict(planned_classes),"complete_class_rows":dict(complete_classes),
            "mean_error_difference":sum(values)/len(values) if values else None,"interval_95":intervals["pointwise_95"],
            "bootstrap_draws":draws,"bootstrap_omitted_draws":intervals["omitted_draws"],
            "estimand":estimand,"direction":"positive favors right configuration","inferential_scope":"descriptive; outside primary Holm6 family"})
    for condition in analysis.CONDITIONS:
        for left,right in combinations(contextual,2):
            values=[];members=[]
            for group in main_groups:
                cells=[main.get((group,config,condition,gold)) for config in (left,right) for gold in (0,1)]
                if any(row is None for row in cells):
                    raise ValueError("Locked main comparison group is absent from the planned panel")
                if any(cells[i]["id"]!=cells[i+2]["id"] for i in (0,1)):
                    raise ValueError("Compared main models must see identical source pages")
                if all(row["valid"] for row in cells):
                    values.append(analysis.group_difference([int(row["prediction"]!=row["gold"]) for row in cells]))
                    members.append([group,cells[0]["id"],cells[1]["id"]])
            finish("browsesafe",condition,left,right,len(main_groups),len(values),values,
                {"0":len(main_groups),"1":len(main_groups)},{"0":len(values),"1":len(values)},members,
                "equal-group mean balanced-pair error difference",condition,condition)
    for left,right in combinations(all_configs,2):
        values=[];members=[];planned_classes=Counter({"0":0,"1":0});complete_classes=Counter({"0":0,"1":0})
        used_groups=set()
        for identity in external_ids:
            a,b=external.get((identity,left)),external.get((identity,right))
            if a is None or b is None or any(a[k]!=b[k] for k in ("group_id","gold","source")):
                raise ValueError("Locked external comparison must retain identical original requests/labels/groups")
            if a["group_id"] in used_groups:
                raise ValueError("External matched requests must represent distinct source components")
            used_groups.add(a["group_id"]);planned_classes[str(a["gold"])]+=1
            if a["valid"] and b["valid"]:
                values.append(int(a["prediction"]!=a["gold"])-int(b["prediction"]!=b["gold"]))
                members.append([a["group_id"],identity]);complete_classes[str(a["gold"])]+=1
        finish("promptshield","external",left,right,len(external_ids),len(values),values,planned_classes,complete_classes,members,
            "matched-request mean error difference; not balanced error under missing class imbalance",
            "candidate" if left=="protectai_local" else "external","candidate" if right=="protectai_local" else "external")
    return result


def analyze_run(plan, attempts_directory, *, plan_sha256, output_dir=DEFAULT_OUTPUT,
                draws=analysis.BOOTSTRAP_DRAWS, synthetic_fixture=False):
    if type(draws) is not int or draws<1 or (draws!=analysis.BOOTSTRAP_DRAWS and not synthetic_fixture):
        raise ValueError("Reduced bootstrap draws are allowed only for explicitly synthetic fixtures")
    rows,reconstruction=reconstruct_confirmation(plan,attempts_directory)
    planned,observed=analysis.reconstruct_main_observations(plan,attempts_directory)
    primary=analysis.analyze_main(analysis.collect_main(planned,observed),draws=draws)
    selected=[r for r in rows if r["source"]=="promptshield" or r["config"] not in analysis.NATIVE_CONFIGS]
    descriptive=analysis.classification_summary(selected,draws=draws)
    matched=matched_comparisons(plan,rows,draws=draws)
    output=Path(output_dir);output.mkdir(parents=True,exist_ok=True)
    payloads={"primary-analysis.json":primary,"descriptive-analysis.json":descriptive,"matched-comparisons.json":matched}
    for name,value in payloads.items():(output/name).write_bytes(canonical(value)+b"\n")
    with (output/"matched-comparisons.csv").open("w",newline="") as handle:
        if matched:
            writer=csv.DictWriter(handle,fieldnames=list(matched[0]));writer.writeheader()
            writer.writerows({k:json.dumps(v,sort_keys=True,separators=(",",":")) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in matched)
    hashes={name:digest((output/name).read_bytes()) for name in payloads}
    hashes["matched-comparisons.csv"]=digest((output/"matched-comparisons.csv").read_bytes())
    artifacts=report.write_report(primary,descriptive_summaries=descriptive,general_comparisons=matched,output_dir=output,input_hashes=hashes)
    metadata={"version":"study-v7-offline-analysis-driver-1","plan_sha256":plan_sha256,"bootstrap_draws":draws,
        "synthetic_fixture":synthetic_fixture,"network_or_model_calls":0,"sources_pooled":False,
        "reconstruction":reconstruction,"analysis_sha256":digest(Path(analysis.__file__).read_bytes()),
        "report_sha256":digest(Path(report.__file__).read_bytes()),"driver_sha256":digest(Path(__file__).read_bytes()),
        "analysis_artifact_sha256":hashes,"rendered_artifact_manifest_sha256":digest(canonical(artifacts)+b"\n")}
    (output/"analysis-driver.json").write_bytes(canonical(metadata)+b"\n")
    return metadata


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan",type=Path,required=True);parser.add_argument("--attempts",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument("--draws",type=int,default=analysis.BOOTSTRAP_DRAWS)
    parser.add_argument("--synthetic-fixture",action="store_true")
    args=parser.parse_args();body=args.plan.read_bytes()
    analyze_run(json.loads(body),args.attempts,plan_sha256=digest(body),output_dir=args.output_dir,
                draws=args.draws,synthetic_fixture=args.synthetic_fixture)


if __name__=="__main__":
    main()
