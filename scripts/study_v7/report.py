"""Deterministic tables and charts from saved v7 analysis; no new statistics.

No raw source snippets, model calls, credentials, manuscript or PDF. The caller
supplies separately calculated source summaries and explicitly matched general
cohorts; this renderer never pools sources or invents scores/cohort membership.
"""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import re

SOURCES={"browsesafe":"BrowseSafe++", "promptshield":"PromptShield"}
CONFIGS={"jev_firstparty":"Jev", "luna_decisions":"Luna Decisions", "luna_responses":"Luna Responses",
         "sol_responses":"Sol Responses", "sol_subscription":"Sol subscription", "protectai_local":"ProtectAI"}
CONDITIONS={"format":"empty task", "task":"authentic task", "reminder":"reminder", "length":"length filler",
            "candidate":"candidate only", "external":"full request"}
BOOLEAN_CONFIGS={"luna_responses","sol_responses","sol_subscription"}
DEFAULT_OUTPUT=Path(__file__).resolve().parents[2]/"results/study-v7-execution"


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def number(value):
    if value is None:
        return None
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError("Table values must be finite numbers or explicit missing values")
    return value


def count(value):
    if type(value) is not int or value < 0:
        raise ValueError("Explicit nonnegative integer denominator required")
    return value


def pp(value):
    value=number(value)
    return None if value is None else float(Decimal(str(value))*100)


def interval(value):
    if value is None:
        return (None,None)
    if not isinstance(value,(list,tuple)) or len(value)!=2:
        raise ValueError("Explicit two-endpoint interval required")
    lower,upper=map(number,value)
    if lower is None or upper is None or lower>upper:
        raise ValueError("Invalid interval endpoints")
    return lower,upper


def identity(row):
    source,config,condition=(row[k] for k in ("source","config","condition"))
    if source not in SOURCES or config not in CONFIGS or condition not in CONDITIONS:
        raise ValueError("Unknown source/configuration/condition; do not embed raw source text in tables")
    return {"source":source,"config":config,"condition":condition}


def build_tables(primary, descriptive_summaries=None, general_comparisons=None):
    """Flatten the frozen analysis schema, retaining units and exact denominators.

    General rows require matched_cohort=True, source/condition, left_config and
    right_config, cohort_id, planned_groups/complete_groups, planned_rows/
    complete_rows. Optional mean_error_difference/interval_95 are precomputed.
    """
    planned=count(primary["planned_groups"]);complete=count(primary["primary_complete_groups"])
    if complete>planned or len(primary["contrasts"])!=6:
        raise ValueError("Primary display requires the planned six-test family and valid group denominators")
    cohort=primary["primary_complete_group_ids"]
    if len(cohort)!=complete or len(set(cohort))!=complete or any(not isinstance(g,str) for g in cohort):
        raise ValueError("Primary cohort identifiers must match the shared group denominator")
    tables={"primary_contrasts":[],"planned_bounds":[],"descriptive":[],"coverage_status":[],"reliability":[],"general_comparisons":[]}
    seen=set()
    for original in primary["contrasts"]:
        config,control=original["config"],original["control"]
        if config not in {"jev_firstparty","luna_decisions"} or control not in {"format","reminder","length"} or (config,control) in seen:
            raise ValueError("Primary family identity changed")
        seen.add((config,control))
        test=original["primary"]["test"];cis=original["primary"]["intervals"]
        if count(test["n"])!=complete:
            raise ValueError("All primary contrasts must use the same complete-group cohort")
        lower95,upper95=interval(cis["pointwise_95"])
        lower99,upper99=interval(cis["conservative_six_99_166667"])
        sensitivity=original["contrast_complete_sensitivity"]
        sensitivity_n=count(sensitivity["test"]["n"])
        if not complete<=sensitivity_n<=planned:
            raise ValueError("Contrast-specific cohort denominator conflicts with primary/planned groups")
        adjusted=original["primary"]["holm6"]
        row={"source":"browsesafe","config":config,"control":control,"task":"task",
             "planned_groups":planned,"primary_complete_groups":complete,"contrast_complete_groups":sensitivity_n,
             "estimate_fraction":number(test["mean"]),"estimate_pp":pp(test["mean"]),
             "pointwise_95_lower_fraction":lower95,"pointwise_95_upper_fraction":upper95,
             "pointwise_95_lower_pp":pp(lower95),"pointwise_95_upper_pp":pp(upper95),
             "conservative_99_166667_lower_fraction":lower99,"conservative_99_166667_upper_fraction":upper99,
             "conservative_99_166667_lower_pp":pp(lower99),"conservative_99_166667_upper_pp":pp(upper99),
             "t":number(test["t"]),"df":test["df"],"unadjusted_p":number(test["p"]),
             "holm6_adjusted_p":number(adjusted["adjusted_p"]),"holm6_reject":bool(adjusted["reject"]),
             "contrast_complete_estimate_fraction":number(sensitivity["test"]["mean"]),
             "contrast_complete_estimate_pp":pp(sensitivity["test"]["mean"]),
             "bootstrap_draws":count(cis["draws"]),"bootstrap_omitted_draws":count(cis["omitted_draws"])}
        tables["primary_contrasts"].append(row)
        low,high=interval(original["all_planned_error_difference_bounds"])
        tables["planned_bounds"].append({"source":"browsesafe","config":config,"control":control,
            "planned_groups":planned,"lower_fraction":low,"upper_fraction":high,"lower_pp":pp(low),"upper_pp":pp(high),
            "is_confidence_interval":False,"known_individual_errors_retained":True})
    parts=list(primary.get("coverage",[]))+list(descriptive_summaries or [])
    seen=set()
    for original in parts:
        ids=identity(original);key=tuple(ids.values())
        if key in seen:
            raise ValueError("Duplicate descriptive source/config/condition; choose one explicit cohort")
        seen.add(key)
        total=count(original["planned_rows"]);valid=count(original["valid_rows"])
        if valid>total:
            raise ValueError("Valid rows exceed their planned denominator")
        scored=original.get("score_diagnostics") or {}
        score_n=count(scored.get("n",0))
        if score_n>total:
            raise ValueError("Scored rows exceed their planned denominator")
        if ids["config"] in BOOLEAN_CONFIGS and (score_n or scored.get("auroc") is not None or scored.get("brier") is not None):
            raise ValueError("Boolean outputs cannot acquire invented confidence/score metrics")
        confusion={k:count(original["confusion"][k]) for k in ("tn","fp","fn","tp")}
        if sum(confusion.values())!=valid:
            raise ValueError("Confusion counts do not match the explicit valid denominator")
        row=dict(ids,planned_rows=total,valid_rows=valid,coverage=number(original.get("coverage")),
            valid_benign_rows=confusion["tn"]+confusion["fp"],valid_attack_rows=confusion["fn"]+confusion["tp"],
            **confusion,fpr=number(original.get("fpr")),fnr=number(original.get("fnr")),
            balanced_error=number(original.get("balanced_error")),scored_rows=score_n,
            auroc=number(scored.get("auroc")),brier=number(scored.get("brier")))
        cis=original.get("intervals") or {}
        for metric in ("fpr","fnr","balanced_error","brier"):
            lower,upper=interval(cis.get(metric))
            row[metric+"_95_lower"],row[metric+"_95_upper"]=lower,upper
        tables["descriptive"].append(row)
        for status,n in sorted(original.get("status_counts",{}).items()):
            if not re.fullmatch(r"[a-z0-9_]{1,80}",status):
                raise ValueError("Only parser disposition names may enter tracked status tables")
            tables["coverage_status"].append(dict(ids,status=status,rows=count(n),planned_rows=total))
        for bin_row in scored.get("reliability_10_fixed_bins",[]):
            tables["reliability"].append(dict(ids,lower=number(bin_row["lower"]),upper=number(bin_row["upper"]),
                rows=count(bin_row["n"]),mean_score=number(bin_row["mean_score"]),attack_frequency=number(bin_row["attack_frequency"])))
    for original in general_comparisons or []:
        source=original["source"];condition=original["condition"]
        left,right=original["left_config"],original["right_config"]
        if source not in SOURCES or condition not in CONDITIONS or left not in CONFIGS or right not in CONFIGS or left==right or original.get("matched_cohort") is not True:
            raise ValueError("General comparisons require an explicit same-source matched cohort")
        cohort=original["cohort_id"]
        if not isinstance(cohort,str) or not re.fullmatch(r"[A-Za-z0-9:._/-]{1,128}",cohort):
            raise ValueError("Explicit text-free matched cohort identifier required")
        pg,cg,pr,cr=(count(original[k]) for k in ("planned_groups","complete_groups","planned_rows","complete_rows"))
        if cg>pg or cr>pr:
            raise ValueError("Matched comparison counts exceed their planned denominators")
        lower,upper=interval(original.get("interval_95"))
        tables["general_comparisons"].append({"source":source,"condition":condition,"left_config":left,"right_config":right,
            "matched_cohort":True,"cohort_id":cohort,"planned_groups":pg,"complete_groups":cg,"planned_rows":pr,"complete_rows":cr,
            "mean_error_difference":number(original.get("mean_error_difference")),"lower_95":lower,"upper_95":upper})
    return {"version":"study-v7-analysis-tables-1","tables":tables,
        "metadata":{"primary_family_size":6,"primary_source":"browsesafe","planned_groups":planned,
            "primary_complete_groups":complete,"primary_cohort_sha256":sha(canonical(sorted(primary.get("primary_complete_group_ids",[])))),
            "primary_direction":"positive favors task information","primary_units":"error fractions and percentage points",
            "sources_pooled":False,"planned_bounds_are_confidence_intervals":False,"new_statistics_calculated":False,
            "auroc_reliability_intervals_supplied":False,"raw_source_text_included":False,
            "general_comparisons_supplied":bool(tables["general_comparisons"])}}


def render_figures(package, directory):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"svg.hashsalt":"Decision-Context-Benchmark-v7", "font.size":9})
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    outputs=[]
    def save(fig,name):
        fig.tight_layout()
        for suffix in ("png","svg"):
            path=directory/(name+"."+suffix)
            metadata={"Software":"Decision Context Benchmark"} if suffix=="png" else {"Date":None,"Creator":"Decision Context Benchmark"}
            fig.savefig(path,dpi=160,metadata=metadata);outputs.append(path)
        plt.close(fig)
    rows=package["tables"]["primary_contrasts"]
    fig,ax=plt.subplots(figsize=(9,5))
    labels=[]
    for i,row in enumerate(rows):
        labels.append(f"{CONFIGS[row['config']]} / {CONDITIONS[row['control']]}  N={row['primary_complete_groups']}")
        for prefix,color,width,offset in (("conservative_99_166667","#90a9bf",5,-.07),("pointwise_95","#173a55",2,.07)):
            low,high=row[prefix+"_lower_pp"],row[prefix+"_upper_pp"]
            if low is not None:
                ax.hlines(i+offset,low,high,color=color,linewidth=width,
                    label="99.1667% per comparison" if i==0 and offset<0 else "95% pointwise" if i==0 else None)
        if row["estimate_pp"] is not None:
            ax.plot(row["estimate_pp"],i,"o",color="#173a55",markersize=4)
    ax.axvline(0,color="#777777",linewidth=.8);ax.set_yticks(range(len(rows)),labels);ax.invert_yaxis()
    ax.set_xlabel("Control − task balanced error (percentage points)")
    ax.set_title("BrowseSafe++: shared complete-group native contrasts")
    handles,_=ax.get_legend_handles_labels()
    if handles:ax.legend(loc="best")
    save(fig,"primary-contrasts")
    fig,ax=plt.subplots(figsize=(9,5))
    bounds=package["tables"]["planned_bounds"]
    for i,row in enumerate(bounds):
        if row["lower_pp"] is not None:
            ax.hlines(i,row["lower_pp"],row["upper_pp"],color="#925b19",linewidth=3)
    ax.axvline(0,color="#777777",linewidth=.8)
    ax.set_yticks(range(len(bounds)),[f"{CONFIGS[r['config']]} / {CONDITIONS[r['control']]}  planned N={r['planned_groups']}" for r in bounds]);ax.invert_yaxis()
    ax.set_xlabel("Control − task error bounds (percentage points)")
    ax.set_title("BrowseSafe++: all planned groups; missing-error bounds (not confidence intervals)")
    save(fig,"planned-missingness-bounds")
    for source in SOURCES:
        part=[r for r in package["tables"]["descriptive"] if r["source"]==source]
        if not part:continue
        fig,(ax,cov)=plt.subplots(1,2,figsize=(11,max(4,len(part)*.48+1.6)),sharey=True,gridspec_kw={"width_ratios":[2,1]})
        for i,row in enumerate(part):
            for metric,offset,color in (("fpr",-.17,"#1e668c"),("fnr",0,"#b05a32"),("balanced_error",.17,"#4b6e36")):
                if row[metric] is None:continue
                low,high=row[metric+"_95_lower"],row[metric+"_95_upper"]
                if low is not None:ax.hlines(i+offset,pp(low),pp(high),color=color,linewidth=1.2)
                ax.plot(pp(row[metric]),i+offset,"o",color=color,markersize=4,label=metric.upper() if i==0 else None)
            if row["coverage"] is not None:cov.barh(i,pp(row["coverage"]),color="#8fa5b2",height=.45)
        ax.set_yticks(range(len(part)),[f"{CONFIGS[r['config']]} / {CONDITIONS[r['condition']]}  rows {r['valid_rows']}/{r['planned_rows']}" for r in part]);ax.invert_yaxis()
        ax.set_xlim(0,100);cov.set_xlim(0,100);ax.set_xlabel("Observed-cohort error (%) with 95% group intervals");cov.set_xlabel("Valid classification coverage (%)")
        handles,_=ax.get_legend_handles_labels()
        if handles:ax.legend(loc="best")
        fig.suptitle(SOURCES[source]+": source-specific error and coverage")
        save(fig,source+"-error-coverage")
    return outputs


def write_report(primary, *, descriptive_summaries=None, general_comparisons=None,
                 output_dir=DEFAULT_OUTPUT, input_hashes=None):
    package=build_tables(primary,descriptive_summaries,general_comparisons)
    output=Path(output_dir);tables_dir=output/"tables";tables_dir.mkdir(parents=True,exist_ok=True)
    package["metadata"]["input_sha256"]=dict(sorted((input_hashes or {}).items()))
    artifacts=[]
    path=tables_dir/"analysis-tables.json";path.write_bytes(canonical(package)+b"\n");artifacts.append(path)
    for name,rows in package["tables"].items():
        path=tables_dir/(name.replace("_","-")+".csv")
        with path.open("w",newline="") as handle:
            if rows:
                writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        artifacts.append(path)
    artifacts.extend(render_figures(package,output/"figures"))
    manifest={"version":"study-v7-result-artifacts-1","metadata":package["metadata"],
              "artifacts":{str(p.relative_to(output)):sha(p.read_bytes()) for p in artifacts}}
    (output/"artifact-manifest.json").write_bytes(canonical(manifest)+b"\n")
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis",type=Path,required=True)
    parser.add_argument("--descriptive",type=Path,action="append",default=[])
    parser.add_argument("--general-comparisons",type=Path)
    parser.add_argument("--output-dir",type=Path,default=DEFAULT_OUTPUT)
    args=parser.parse_args()
    body=args.analysis.read_bytes();primary=json.loads(body);hashes={"primary_analysis":sha(body)}
    summaries=[]
    for i,path in enumerate(args.descriptive):
        raw=path.read_bytes();value=json.loads(raw);hashes[f"descriptive_{i}"]=sha(raw)
        summaries.extend(value if isinstance(value,list) else value["coverage"])
    general=[]
    if args.general_comparisons:
        raw=args.general_comparisons.read_bytes();value=json.loads(raw);hashes["general_comparisons"]=sha(raw)
        general=value if isinstance(value,list) else value["general_comparisons"]
    write_report(primary,descriptive_summaries=summaries,general_comparisons=general,output_dir=args.output_dir,input_hashes=hashes)


if __name__=="__main__":
    main()
