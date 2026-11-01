"""Offline BrowseSafe++ repeat stability; first attempts are never replaced.

Descriptive only. Whole-group bootstrap draws preserve clean/attack members and
recompute paired-page denominators. Score changes are native probabilities only.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np
from scripts.study_v7 import analysis
from scripts.study_v7.operational import retained_attempt
from scripts.study_v7.requests import PANEL, canonical, digest

DEFAULT_OUTPUT=Path(__file__).resolve().parents[2]/"results/study-v7-execution"
NATIVE={"jev_firstparty","luna_decisions"}
BOOLEAN={"luna_responses","sol_responses","sol_subscription"}
TIES={"tie","tied"}


def group_ratio_interval(numerators, denominators, *, draws=analysis.BOOTSTRAP_DRAWS, seed=analysis.SEED):
    """Resample planned whole groups; ratio of totals, not unweighted group rates."""
    values=np.column_stack((numerators,denominators)).astype(float)
    if (np.any(~np.isfinite(values)) or np.any(values<0) or np.any(values[:,0]>values[:,1]) or
            type(draws) is not int or draws<1):
        raise ValueError("Invalid bounded group numerator/denominator")
    n=len(values);total=float(values[:,1].sum())
    result={"mean":float(values[:,0].sum()/total) if total else None,"interval_95":None,
        "draws":draws,"seed":str(seed),"omitted_zero_denominator_draws":draws,
        "method":"whole planned-group percentile bootstrap; paired-page denominator recomputed in each draw"}
    if not n or not total:return result
    support,counts=np.unique(values,axis=0,return_counts=True)
    rng=np.random.default_rng(analysis._seed(seed,"repeat-group-ratio"));rates=[]
    for start in range(0,draws,2048):
        weights=rng.multinomial(n,counts/n,size=min(2048,draws-start))
        totals=weights@support;valid=totals[:,1]>0
        rates.extend((totals[valid,0]/totals[valid,1]).tolist())
    result["omitted_zero_denominator_draws"]=draws-len(rates)
    if rates:result["interval_95"]=np.quantile(rates,[.025,.975],method="linear").tolist()
    return result


def read_attempt(request, directory):
    """Validate separate first/repeat raw/started/terminal identities and scores."""
    root=Path(directory)/request["key"];started={};completed={};started_sha=None
    if (root/"started.json").exists():
        started=json.loads((root/"started.json").read_text())
        started_sha=digest((root/"started.json").read_bytes())
        if any(started.get(k)!=v for k,v in {"key":request["key"],"config":request["config"],
                "namespace":request["namespace"],"payload_sha256":request["payload_sha256"],"route":PANEL[request["config"]]["route"]}.items()):
            raise ValueError("Repeat/first started identity changed")
        if not (root/"request.json").exists() or digest((root/"request.json").read_bytes())!=request["payload_sha256"]:
            raise ValueError("Repeat/first raw request payload changed")
    if (root/"completed.json").exists():
        completed=json.loads((root/"completed.json").read_text())
        if not (root/"started.json").is_file() or completed.get("raw_hashes",{}).get("started.json")!=digest((root/"started.json").read_bytes()):
            raise ValueError("Repeat/first completed evidence lacks its exact started hash")
    if (root/"interrupted.json").exists():
        interrupted=json.loads((root/"interrupted.json").read_text())
        if interrupted.get("key")!=request["key"] or interrupted.get("first_attempt_primary") is not (request["namespace"]=="first"):
            raise ValueError("Interrupted repeat/first identity changed")
    retained=retained_attempt(request,directory)
    parsed=retained["parsed"];valid=retained["valid"];status=retained["status"]
    prediction=parsed.get("prediction") if valid else None;score=parsed.get("score")
    if valid and (status!="ok" or not analysis._binary(prediction) or parsed.get("returned_model")!=PANEL[request["config"]]["model"]):
        raise ValueError("Valid repeat/first decision has inconsistent model/Boolean identity")
    if valid and request.get("configuration_revision") is not None and parsed.get("configuration_revision")!=request["configuration_revision"]:
        raise ValueError("Repeat/first parsed configuration revision changed")
    if request["config"] in BOOLEAN:
        if score is not None:raise ValueError("Boolean repeats cannot invent confidence scores")
    else:
        if score is not None and not analysis._probability(score):raise ValueError("Invalid native repeat probability")
        if valid and (score is None or score==.5 or int(prediction)!=int(score>.5)):
            raise ValueError("Native repeats require threshold0.5 with exact ties abstaining")
        if status in TIES and (valid or score!=.5):raise ValueError("Native repeat ties must abstain")
    headers=(completed.get("observation") or {}).get("response_headers") or {}
    def recorded(value):return value if isinstance(value,str) and value else None
    return {"status":status,"valid":valid,"prediction":prediction,"score":score,
        "evidence_sha256":retained["evidence_sha256"],"fresh_evidence":{
            "attempt_key":request["key"],"namespace":request["namespace"],"started_record_sha256":started_sha,
            "provider_response_id":recorded(parsed.get("provider_request_id")),
            "provider_transport_request_id":recorded(headers.get("x-request-id") or headers.get("request-id")),
            "started_at":recorded(started.get("started_at")),"finished_at":recorded(completed.get("finished_at"))}}


def analyze_repeats(plan, attempts_directory, *, draws=analysis.BOOTSTRAP_DRAWS, synthetic_fixture=False):
    if type(draws) is not int or draws<1 or draws!=analysis.BOOTSTRAP_DRAWS and not synthetic_fixture:
        raise ValueError("Reduced draws require explicitly synthetic fixtures")
    cells={}
    for cell in plan["cells"]:
        if cell["request_key"] in cells:raise ValueError("Duplicate planned cell reference")
        cells[cell["request_key"]]=cell
    first={};parts=defaultdict(list)
    for request in plan["requests"].values():
        if request["namespace"]=="first" and request["source"]=="browsesafe" and request["split"]=="confirmation":
            key=(request["config"],request["id"],request["condition"])
            if key in first:raise ValueError("Duplicate first request identity")
            first[key]=request
        elif request["namespace"].startswith("repeat"):
            if (request["namespace"]!="repeat-1" or request["source"]!="browsesafe" or request["split"]!="confirmation" or
                    request["config"] not in NATIVE|BOOLEAN or request["condition"] not in analysis.CONDITIONS):
                raise ValueError("Only frozen BrowseSafe++ contextual repeat-1 requests are admitted")
            parts[(request["config"],request["condition"])].append(request)
    expected_parts={(c,condition) for c in plan["active_configurations"] if c in NATIVE|BOOLEAN for condition in analysis.CONDITIONS}
    if set(parts)!=expected_parts:raise ValueError("Every active contextual configuration requires all four frozen repeat conditions")
    summaries=[];evidence=[];fresh_evidence=[]
    for (config,condition),repeats in sorted(parts.items()):
        expected=set(plan["subsets"]["native_repeat_groups" if config in NATIVE else "general_repeat_groups"])
        if not synthetic_fixture and len(expected)!=(100 if config in NATIVE else 50):
            raise ValueError("Frozen native100/general50 repeat group count changed")
        groups=defaultdict(dict);first_status=Counter();repeat_status=Counter();joint=Counter()
        paired_classes=Counter({"0":0,"1":0});planned_classes=Counter({"0":0,"1":0})
        first_valid_classes=Counter({"0":0,"1":0});repeat_valid_classes=Counter({"0":0,"1":0})
        first_tie_classes=Counter({"0":0,"1":0});repeat_tie_classes=Counter({"0":0,"1":0})
        valid_first=valid_repeat=paired=flips=up=down=score_pairs=0
        fresh_counts=Counter()
        for repeat in repeats:
            original=first.get((config,repeat["id"],condition))
            if original is None or original["key"]==repeat["key"] or any(original.get(k)!=repeat.get(k) for k in
                    ("source","group_id","payload_sha256","configuration_revision")):
                raise ValueError("Repeat must match the exact first payload/configuration in a distinct namespace")
            for request in (original,repeat):
                cell=cells.get(request["key"])
                if cell is None or any(cell.get(k)!=request.get(k) for k in ("id","config","condition","source","group_id","split","namespace")):
                    raise ValueError("Repeat/first planned cell differs from its frozen request")
            gold=cells[repeat["key"]]["upstream_label"]
            if not analysis._binary(gold) or gold!=cells[original["key"]]["upstream_label"]:
                raise ValueError("Original clean/attack source class changed across repeats")
            if gold in groups[repeat["group_id"]]:raise ValueError("Repeat group has duplicate source arm")
            a,b=read_attempt(original,attempts_directory),read_attempt(repeat,attempts_directory)
            fa,fb=a["fresh_evidence"],b["fresh_evidence"]
            fresh_counts["both_started_records_verified"]+=bool(fa["started_record_sha256"] and fb["started_record_sha256"])
            for field in ("provider_response_id","provider_transport_request_id"):
                available=bool(fa[field] and fb[field]);fresh_counts[field+"_pairs_available"]+=available
                fresh_counts["duplicate_"+field+"_pairs"]+=bool(available and fa[field]==fb[field])
            fresh_counts["both_start_timestamps_recorded"]+=bool(fa["started_at"] and fb["started_at"])
            fresh_counts["both_finish_timestamps_recorded"]+=bool(fa["finished_at"] and fb["finished_at"])
            fresh_evidence.append({"config":config,"condition":condition,"group_id":repeat["group_id"],"source_id":repeat["id"],
                "first":fa,"repeat":fb,"distinct_attempt_keys":original["key"]!=repeat["key"]})
            first_status[a["status"]]+=1;repeat_status[b["status"]]+=1;joint[a["status"]+"|"+b["status"]]+=1
            valid_first+=a["valid"];valid_repeat+=b["valid"];planned_classes[str(gold)]+=1
            first_valid_classes[str(gold)]+=a["valid"];repeat_valid_classes[str(gold)]+=b["valid"]
            first_tie_classes[str(gold)]+=int(a["status"] in TIES);repeat_tie_classes[str(gold)]+=int(b["status"] in TIES)
            both=a["valid"] and b["valid"];changed=bool(both and a["prediction"]!=b["prediction"])
            if both:
                paired+=1;flips+=changed;paired_classes[str(gold)]+=1
                up+=int(not a["prediction"] and b["prediction"]);down+=int(a["prediction"] and not b["prediction"])
            scored=config in NATIVE and all(r["status"] in {"ok",*TIES} and analysis._probability(r["score"]) for r in (a,b))
            change=abs(a["score"]-b["score"]) if scored else 0.
            score_pairs+=int(scored)
            groups[repeat["group_id"]][gold]={"paired":int(both),"flip":int(changed),"scored":int(scored),"score_change":change}
            evidence.extend([original["key"],a["evidence_sha256"],repeat["key"],b["evidence_sha256"]])
        if set(groups)!=expected or any(set(members)!={0,1} for members in groups.values()):
            raise ValueError("Repeat subset must preserve both pages of every locked whole group")
        vectors=[[sum(v[k] for v in groups[g].values()) for k in ("flip","paired","score_change","scored")] for g in sorted(groups)]
        complete_values=[sum(v["flip"] for v in members.values())/2 for members in groups.values() if all(v["paired"] for v in members.values())]
        interval=analysis.bootstrap_mean(complete_values,draws=draws,seed=f"{analysis.SEED}/repeat/{config}/{condition}/complete-groups")
        paired_rate=group_ratio_interval([v[0] for v in vectors],[v[1] for v in vectors],draws=draws,seed=f"{analysis.SEED}/repeat/{config}/{condition}/paired-pages")
        score_change=group_ratio_interval([v[2] for v in vectors],[v[3] for v in vectors],draws=draws,seed=f"{analysis.SEED}/repeat/{config}/{condition}/native-score") if config in NATIVE else None
        summaries.append({"source":"browsesafe","config":config,"condition":condition,"first_namespace":"first","repeat_namespace":"repeat-1",
            "planned_groups":len(groups),"planned_page_pairs":len(repeats),"planned_class_rows":dict(planned_classes),
            "valid_first_pages":valid_first,"valid_repeat_pages":valid_repeat,"both_valid_page_pairs":paired,"both_valid_class_rows":dict(paired_classes),
            "first_valid_class_rows":dict(first_valid_classes),"repeat_valid_class_rows":dict(repeat_valid_classes),
            "first_status_counts":dict(first_status),"repeat_status_counts":dict(repeat_status),"joint_status_counts":dict(joint),
            "first_tie_class_rows":dict(first_tie_classes),"repeat_tie_class_rows":dict(repeat_tie_classes),
            "first_missing_or_invalid_non_tie":sum(n for status,n in first_status.items() if status!="ok" and status not in TIES),
            "repeat_missing_or_invalid_non_tie":sum(n for status,n in repeat_status.items() if status!="ok" and status not in TIES),
            "disagreements":flips,"unchanged":paired-flips,"first_false_repeat_true":up,"first_true_repeat_false":down,
            "paired_page_disagreement":paired_rate,"complete_two_page_groups":len(complete_values),
            "complete_group_mean_disagreement":sum(complete_values)/len(complete_values) if complete_values else None,
            "complete_group_interval_95":interval["pointwise_95"],"complete_group_omitted_draws":interval["omitted_draws"],
            "native_scored_page_pairs_including_ties":score_pairs,"native_absolute_score_change":score_change,
            "fresh_evidence_diagnostics":dict(fresh_counts),
            "payload_identity_preserved":True,"repeat_replaced_first":False,"scope":"descriptive stability conditional on observed paired outputs; missing cases remain explicit"})
    return {"version":"study-v7-repeat-stability-1","source":"browsesafe","bootstrap_draws":draws,"seed":analysis.SEED,
        "synthetic_fixture":synthetic_fixture,"network_or_model_calls":0,"p_values_calculated":False,
        "first_attempts_replaced":False,"evidence_references_sha256":digest(canonical(evidence)),
        "recorded_fresh_evidence":fresh_evidence,"provider_ids_or_timestamps_invented":False,"summaries":summaries}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan",type=Path,required=True);parser.add_argument("--attempts",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument("--draws",type=int,default=analysis.BOOTSTRAP_DRAWS);parser.add_argument("--synthetic-fixture",action="store_true")
    args=parser.parse_args();body=args.plan.read_bytes()
    result=analyze_repeats(json.loads(body),args.attempts,draws=args.draws,synthetic_fixture=args.synthetic_fixture)
    result["plan_sha256"]=digest(body);result["module_sha256"]=digest(Path(__file__).read_bytes())
    args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir/"repeat-stability.json").write_bytes(canonical(result)+b"\n")
    with (args.output_dir/"repeat-stability.csv").open("w",newline="") as handle:
        if result["summaries"]:
            writer=csv.DictWriter(handle,fieldnames=list(result["summaries"][0]));writer.writeheader()
            writer.writerows({k:json.dumps(v,sort_keys=True,separators=(",",":")) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in result["summaries"])


if __name__=="__main__":main()
