"""Offline source-family closure, historical screen and prospective precision.

Outputs contain source text only in the ignored new source directory. A saved
selection never authorizes inference; root must bind a later run manifest.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import yaml

from .data_dtap import CODE, TRACES, REVISION, HF_REVISION, SEED, text_values, write_json, align
from .data_exposure import build_history, screen, norm, grams
from .data_sources import ROOT, RAW, sha


def substantial_texts(candidate):
    return sorted({norm(s) for s in text_values(candidate)
                   if len(s.strip()) >= 80 and not s.lstrip().startswith(("{", "["))})


def component_closure(pairs):
    parent = list(range(len(pairs)))
    edges = []
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    def union(a, b, reason):
        aa, bb = find(a), find(b)
        if aa != bb:
            parent[max(aa, bb)] = min(aa, bb)
        edges.append({"left": a, "right": b, "reason": reason})
    tasks = [norm(p["task"]) for p in pairs]
    tg = [grams(p["task"]) for p in pairs]
    cg = [[grams(p[arm]) for arm in ("clean", "attack")] for p in pairs]
    docs = [set(substantial_texts(p["clean"]) + substantial_texts(p["attack"])) for p in pairs]
    for i, left in enumerate(pairs):
        for j in range(i):
            right = pairs[j]
            reason = None
            if (left["domain"], left["base_task"]) == (right["domain"], right["base_task"]):
                reason = "explicit_same_benign_base_task"
            elif tasks[i] == tasks[j]:
                reason = "normalized_task_exact"
            elif min(len(tg[i]), len(tg[j])) >= 5 and len(tg[i] & tg[j]) / len(tg[i] | tg[j]) >= .5:
                reason = "task_three_word_jaccard_at_least_0.5"
            elif docs[i] & docs[j]:
                reason = "substantive_original_document_text_exact"
            elif any(min(len(a), len(b)) >= 5 and len(a & b) / len(a | b) >= .8
                     for a in cg[i] for b in cg[j]):
                reason = "candidate_three_word_jaccard_at_least_0.8"
            if reason:
                union(i, j, reason)
    groups = defaultdict(list)
    for i in range(len(pairs)):
        groups[find(i)].append(i)
    return list(groups.values()), edges


def file_proof(path, tree_rows=None, trace_rows=None):
    body = path.read_bytes()
    receipt_path = path.with_suffix(path.suffix + ".receipt.json")
    receipt = json.loads(receipt_path.read_text())
    if sha(body) != receipt["sha256"] or len(body) != receipt["bytes"]:
        raise ValueError("Source bytes differ from acquisition receipt")
    if receipt.get("authenticated") is not False or receipt.get("repository_code_executed") is not False:
        raise ValueError("Source acquisition boundary not established")
    proof = {"path": str(path.relative_to(ROOT)), "sha256": sha(body), "bytes": len(body),
             "url": receipt["url"], "receipt_sha256": sha(receipt_path.read_bytes())}
    if tree_rows is not None:
        rel = str(path.relative_to(CODE))
        expected = tree_rows[rel]["sha"]
        blob = hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
        if blob != expected:
            raise ValueError("Pinned Git source blob differs from tree")
        proof["pinned_git_blob_sha1"] = expected
    if trace_rows is not None:
        rel = str(path.relative_to(TRACES))
        metadata = trace_rows[rel]
        if len(body) != metadata["size"]:
            raise ValueError("Released trajectory byte length differs from pinned tree")
        if metadata.get("lfs"):
            expected = metadata["lfs"]["oid"]
            if sha(body) != expected:
                raise ValueError("Released LFS trajectory differs from pinned SHA256")
            proof["pinned_lfs_sha256"] = expected
        else:
            expected = metadata["oid"]
            blob = hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
            if blob != expected:
                raise ValueError("Released trajectory differs from pinned Git blob")
            proof["pinned_git_blob_sha1"] = expected
    return proof


def precision_scenarios(actual_groups):
    from scipy.stats import t
    rows = []
    for n in sorted({25, 50, 100, 500, actual_groups} - {0, 1}):
        for sd in (.25, .5, .75, 1.0):
            rows.append({"independent_groups": n, "assumed_group_difference_sd": sd,
                         "approximate_95_halfwidth_pp": float(100 * t.ppf(.975, n - 1) * sd / n ** .5)})
    return {"method": "Prospective t halfwidth = 100*t_(G-1,0.975)*assumed_SD/sqrt(G)",
            "effect_range": [-1, 1], "no_observed_effect_or_variance_used": True,
            "planning_approximation_not_achieved_bootstrap_interval": True,
            "not_powered_for_one_percentage_point": True,
            "actual_selected_groups": actual_groups, "scenarios": rows}


def select(domains, maximum=100):
    if not 1 <= maximum <= 100:
        raise ValueError("Second-source maximum is 100 components")
    pairs = []
    pairing_receipts = []
    for domain in sorted(set(domains)):
        path = RAW / f"dtap-{domain}-matched-candidates-v1.json"
        values = json.loads(path.read_text())
        pairs.extend(values)
        summary_path = ROOT / f"results/subscription-followup/second-source-dtap-{domain}-pairing.json"
        pairing_receipts.append({"path": str(summary_path.relative_to(ROOT)), "sha256": sha(summary_path.read_bytes())})
    pairs.sort(key=lambda p: (p["domain"], p["source_id"]))
    history = build_history()
    hits = []
    for p in pairs:
        # Also inspect unmodified source leaf strings for cross-format exposure;
        # full observed candidate bytes are still the eventual model input.
        leafs = substantial_texts(p["clean"]) + substantial_texts(p["attack"])
        hits.append(screen(p["task"], [p["clean"], p["attack"], *leafs], history))
    components, edges = component_closure(pairs)
    records = []
    for members in components:
        identities = sorted(pairs[i]["domain"] + "/" + pairs[i]["source_id"] for i in members)
        component_id = "dtap:" + sha(json.dumps(identities, separators=(",", ":")).encode())[:24]
        exposed = any(hits[i] for i in members)
        chosen = min(members, key=lambda i: sha((SEED + ":" + pairs[i]["domain"] + "/" + pairs[i]["source_id"]).encode()))
        records.append({"group_id": component_id, "members": members, "source_ids": identities,
                        "historically_exposed": exposed, "chosen_index": chosen,
                        "selection_rank": sha((SEED + ":" + component_id).encode())})
    eligible = sorted((r for r in records if not r["historically_exposed"]), key=lambda r: r["selection_rank"])
    selected = eligible[:maximum]
    code_tree = {x["path"]: x for x in json.loads((CODE / "tree.json").read_text())["tree"] if x["type"] == "blob"}
    trace_tree = {}
    for domain in domains:
        for part in ("benign", "malicious-indirect"):
            trace_tree.update({x["path"]: x for x in json.loads((TRACES / f"{domain}-{part}-tree.json").read_text()) if x["type"] == "file"})
    rows, manifest, proofs = [], [], {}
    for record in selected:
        pair = pairs[record["chosen_index"]]
        rebuilt, reason = align(json.loads((TRACES / pair["clean_trace"]).read_text()),
                                json.loads((TRACES / pair["attack_trace"]).read_text()),
                                yaml.safe_load((CODE / pair["clean_config"]).read_text()),
                                yaml.safe_load((CODE / pair["attack_config"]).read_text()))
        if reason or any(rebuilt[key] != pair[key] for key in rebuilt):
            raise ValueError("Selected pair cannot be reconstructed exactly from retained source")
        pair_id = "dtap:" + pair["domain"] + ":" + pair["source_id"].replace("/", ":")
        entry = {"group_id": record["group_id"], "pair_id": pair_id, "domain": pair["domain"],
                 "base_task": pair["base_task"], "source_id": pair["source_id"],
                 "component_source_ids": record["source_ids"], "task_sha256": sha(pair["task"].encode()),
                 "clean_candidate_sha256": sha(pair["clean"].encode()),
                 "attack_candidate_sha256": sha(pair["attack"].encode()),
                 "clean_pointer": f"/trajectory/{pair['clean_index']}/state",
                 "attack_pointer": f"/trajectory/{pair['attack_index']}/state",
                 "exact_call_sha256": sha(json.dumps(pair["call"], sort_keys=True, separators=(",", ":")).encode()),
                 "witnessed_payload_sha256": pair["witnessed_payload_sha256"],
                 "upstream_condition_labels": [0, 1],
                 "upstream_source_conditions": ["benign", "malicious/indirect"],
                 "incidental_runtime_differences_possible": True}
        for field, folder in (("clean_trace", TRACES), ("attack_trace", TRACES), ("clean_config", CODE), ("attack_config", CODE)):
            proof = file_proof(folder / pair[field], code_tree if folder == CODE else None,
                               trace_tree if folder == TRACES else None)
            proofs[proof["path"]] = proof
            entry[field] = proof["path"]
            entry[field + "_sha256"] = proof["sha256"]
        for arm, label in (("clean", 0), ("attack", 1)):
            rows.append({"id": pair_id + ":" + arm, "group_id": record["group_id"], "pair_id": pair_id,
                         "source": "dtap_released_episodes", "task": pair["task"], "candidate": pair[arm],
                         "upstream_label": label, "arm": arm, "domain": pair["domain"],
                         "upstream_source_condition": "benign" if label == 0 else "malicious/indirect",
                         "partition": "confirmation", "source_code_revision": REVISION,
                         "source_trajectory_revision": HF_REVISION,
                         "candidate_sha256": sha(pair[arm].encode()), "provenance": entry})
        manifest.append(entry)
    raw_selection = RAW / "selected-pairs-v1.jsonl"
    raw_selection.write_text("".join(json.dumps(r, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n" for r in rows))
    raw_edges = RAW / "component-and-history-edges-v1.json"
    write_json(raw_edges, {"pairs": [{"domain": p["domain"], "source_id": p["source_id"]} for p in pairs],
                           "history_hits": hits, "components": records, "edges": edges})
    manifest_bytes = json.dumps(manifest, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    corpus_bytes = json.dumps([{k: r[k] for k in ("id", "task", "candidate")} for r in rows],
                             sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    summary = {"status": "PREPARED_REQUIRES_INDEPENDENT_REVIEW_AND_SEPARATE_RUN_FREEZE",
               "repository_url": "https://github.com/" + "AI-secure/DecodingTrust-Agent",
               "code_revision": REVISION, "trajectory_repository_url": "https://huggingface.co/datasets/AI-Secure/DTap-Bench-Agent-Trajectories",
               "trajectory_revision": HF_REVISION, "domains_screened": sorted(set(domains)),
               "released_eligible_episode_pairs": len(pairs), "components": len(components),
               "historically_exposed_components": sum(r["historically_exposed"] for r in records),
               "fresh_components": len(eligible), "selected_groups": len(selected), "selected_rows": len(rows),
               "source_label_counts": dict(Counter(r["upstream_label"] for r in rows)),
               "per_domain_selected_groups": dict(Counter(pairs[r["chosen_index"]]["domain"] for r in selected)),
               "selected_jsonl": str(raw_selection.relative_to(ROOT)), "selected_jsonl_sha256": sha(raw_selection.read_bytes()),
               "selection_manifest_sha256": sha(manifest_bytes), "selection_seed": SEED,
               "candidate_corpus_sha256": sha(corpus_bytes),
               "selection_manifest": manifest, "source_file_proofs": list(proofs.values()),
               "pairing_receipts": pairing_receipts, "historical_files": history["receipts"],
               "historical_task_source_ids": sorted(history["task_ids"]), "historical_source_text_rows": len(history["rows"]),
               "raw_closure_receipt": str(raw_edges.relative_to(ROOT)), "raw_closure_receipt_sha256": sha(raw_edges.read_bytes()),
               "planned_calls_per_model": 8 * len(selected), "two_model_max_calls": 16 * len(selected),
               "no_inference": True, "no_source_code_executed": True,
               "preparation_code_sha256": {str(p.relative_to(ROOT)): sha(p.read_bytes())
                                           for p in sorted((ROOT / "scripts/subscription_followup").glob("data*.py"))},
               "labels_are_source_conditions_not_independently_adjudicated_truth": True,
               "source_condition_numeric_encoding": {"benign": 0, "malicious/indirect": 1},
               "source_supplied_numeric_binary_labels": False,
               "observation_projection": "Exact published trajectory[index].state string; no trimming or reserialization",
               "selection_does_not_use_agent_outcomes_or_judge_results": True,
               "precision": precision_scenarios(len(selected))}
    write_json(ROOT / "results/subscription-followup/second-source-selection-v1.json", summary)
    return {k: summary[k] for k in ("status", "released_eligible_episode_pairs", "components", "historically_exposed_components", "selected_groups", "selected_rows", "selection_manifest_sha256", "selected_jsonl_sha256", "planned_calls_per_model")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domains", nargs="+", required=True)
    parser.add_argument("--maximum", type=int, default=100)
    args = parser.parse_args()
    print(json.dumps(select(args.domains, args.maximum), sort_keys=True))
