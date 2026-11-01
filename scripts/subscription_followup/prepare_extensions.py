"""Assemble an inert source/pilot extension plan; no authorization or inference.

The source order is copied from its saved counterbalanced schedule. Pilot v4
bodies and dynamic gate variants are copied, never recomputed or chosen here.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
import json
from pathlib import Path

from scripts.study_v7.requests import canonical, digest
from scripts.subscription_followup.prepare import write_once, _namespace
from scripts.subscription_followup.data_capacity import task_payload

ROOT = Path(__file__).resolve().parents[2]
VERSION = "subscription-followup-extensions-plan-1"
NAMESPACE = "subscription-followup-extension-20261101-v1"
SOURCE_ROWS_SHA = "c1bf433d2716815d02e685d58855766def572927069a787f17f494b34adde1df"
SOURCE_MANIFEST_SHA = "4f23e42bbcf3d7c02b5742cfba32e0dbb03ba58fbbf8bc47194b41695b6d63a4"
SOURCE_SCHEDULE_SHA = "7adc340ff868cf65a7b5c36a54bc96b2fd9b3013bfa69992a1efc1ec1568dc8b"
PILOT_PLAN_SHA = "d5b7ec9c736ae42ba0527a2f008a8c1dd92d3a27def84e107306a68e3ec772f0"
CONDITIONS = {"format", "task", "reminder", "length"}
CONFIGURATIONS = {
    "jev_firstparty": {"model": "jev-1.14.0", "route": "api_key", "kind": "noul",
                       "context_tokens": 32000, "questions_per_request": 1,
                       "long_context_header": False, "full_context_reserve_usd": "0.001344"},
    "sol_subscription": {"model": "gpt-6.1-sol", "route": "subscription", "kind": "responses",
                         "configuration_revision": "v7.0.2", "reasoning": "low", "store": False,
                         "stream": True, "service_tier": "default", "context_tokens": 500000,
                         "requested_output_cap": None, "output_limit_status": "Unsupported; provider default/uncontrolled",
                         "cache_control_status": "Unsupported; provider default/uncontrolled", "api_dollar_reserve": "0"},
}


def require(value, message):
    if not value:
        raise ValueError(message)


def validate_body(config, body):
    require(config in CONFIGURATIONS, "Only Sol subscription and native Jev are approved")
    require(body.get("model") == CONFIGURATIONS[config]["model"], "Pinned model differs")
    if config == "jev_firstparty":
        require(set(body) == {"model", "state", "questions"} and isinstance(body["state"], str), "Jev full-state contract differs")
        require(set(body["questions"]) == {"injection"} and body["questions"]["injection"]["type"] == "noul", "Exactly one native noul question required")
    else:
        require(body.get("reasoning") == {"effort": "low"} and body.get("store") is False
                and body.get("stream") is True and body.get("service_tier") == "default", "Sol requested settings differ")
        require(not ({"max_output_tokens", "prompt_cache_options", "tools"} & set(body)), "Unsupported Sol fields or tools are forbidden")
        require(body.get("text", {}).get("format", {}).get("strict") is True, "Strict Sol output schema required")


def assemble(rows, selection, capacity, schedule, pilot, *, run_namespace=NAMESPACE):
    """Pure assembly; input payloads, variants and within-group ordering stay fixed."""
    _namespace(run_namespace)
    lookup = {r["id"]: r for r in rows}
    require(len(lookup) == len(rows), "Duplicate source row ID")
    by_group = defaultdict(list)
    for row in rows:
        require(row["source"] == "dtap_released_episodes" and row["partition"] == "confirmation", "Source identity/partition differs")
        require(digest(row["candidate"].encode()) == row["candidate_sha256"], "Original candidate bytes differ")
        by_group[row["group_id"]].append(row)
    require(0 < len(by_group) <= 100 and len(by_group) == selection["selected_groups"] == capacity["source_groups"], "Source component denominator differs")
    for pair in by_group.values():
        require(len(pair) == 2 and {r["upstream_label"] for r in pair} == {0, 1}
                and len({r["task"] for r in pair}) == 1, "One intact genuine-task pair per component required")
    corpus = digest(canonical([{k: r[k] for k in ("id", "task", "candidate")} for r in rows]))
    require(corpus == selection["candidate_corpus_sha256"] == schedule["source_rows_sha256"], "Source corpus/order binding differs")
    require(selection["selection_manifest_sha256"] == capacity["selection_manifest_sha256"]
            and selection["selected_jsonl_sha256"] == capacity["selected_jsonl_sha256"], "Capacity/selection binding differs")
    require(capacity.get("complete_original_candidates_preserved") is True and capacity.get("truncation") is False
            and capacity.get("refill") is False, "Full original inputs/no-refill capacity audit required")
    require({g["group_id"] for g in schedule["groups"]} == set(by_group)
            and len(schedule["groups"]) == len(by_group), "Source schedule group roster differs")
    groups = []
    original_source_cell_ids = []
    for original in schedule["groups"]:
        source_group = original["group_id"]
        gid = "secondary:" + source_group
        cells = []
        require(Counter((c["id"], c["condition"], c["config"]) for c in original["cells"]) ==
                Counter((r["id"], condition, config) for r in by_group[source_group]
                        for condition in CONDITIONS for config in CONFIGURATIONS), "Source schedule is not its exact sixteen-cell crossing")
        for old in original["cells"]:
            row = lookup[old["id"]]
            require(old["group_id"] == source_group and row["group_id"] == source_group, "Source schedule cell/group identity differs")
            body = task_payload(old["config"], row, old["condition"])
            validate_body(old["config"], body)
            require(digest(canonical(body)) == old["payload_sha256"], "Frozen source payload changed")
            cell = copy.deepcopy(old)
            cell.update(payload=body, group_id=gid, source_group_id=source_group, stage="secondary", kind="classification",
                        namespace=run_namespace, prepared_input_namespace=old["namespace"],
                        upstream_label=row["upstream_label"], pair_id=row["pair_id"],
                        original_candidate_sha256=row["candidate_sha256"], original_task_sha256=digest(row["task"].encode()))
            cells.append(cell)
            original_source_cell_ids.append(old["cell_id"])
        groups.append({"lane": "second_source", "stage": "secondary", "group_id": gid,
                       "source_group_id": source_group, "condition_order": copy.deepcopy(original["condition_order"]),
                       "page_order": copy.deepcopy(original["page_order"]), "config_order": copy.deepcopy(original["config_order"]), "cells": cells})
    require(pilot["version"] == "subscription-followup-isolated-agent-4" and pilot["experimental_inference_authorized"] is False,
            "Only the existing unexecuted pilot v4 is admitted")
    require(pilot["run_namespace"] == run_namespace and len(pilot["groups"]) == 12
            and pilot["counts"] == {"jev_firstparty": 24, "sol_subscription": 48}, "Pilot namespace/counts differ")
    for original in pilot["groups"]:
        group = copy.deepcopy(original)
        gid = "isolated_agent:" + original["source_group_id"]
        group["group_id"] = gid
        gate_ids = {c["cell_id"] for c in group["cells"] if c["kind"] == "gate"}
        require(len(gate_ids) == 2 and [c["kind"] for c in group["cells"][:2]] == ["gate", "gate"], "Pilot gate-first order differs")
        for cell in group["cells"]:
            validate_body(cell["config"], cell["payload"])
            require(digest(canonical(cell["payload"])) == cell["payload_sha256"], "Pilot payload bytes differ")
            cell.update(group_id=gid, namespace=run_namespace, prepared_input_namespace=cell["namespace"], first_attempt_primary=True)
            if cell.get("arm") == "Jev_gate":
                require(cell["gate_cell_id"] in gate_ids and set(cell["payload_variants"]) == {"allowed", "withheld"}, "Pilot dynamic gate dependency differs")
                for variant in cell["payload_variants"].values():
                    validate_body(cell["config"], variant["payload"])
                    require(digest(canonical(variant["payload"])) == variant["payload_sha256"], "Pilot variant bytes differ")
                cell["dynamic_payload_policy"] = {"gate_cell_id": cell["gate_cell_id"], "rule": copy.deepcopy(pilot["gate_rule"]),
                    "allow_variant": "allowed", "block_variant": "withheld", "abstain_block_variant": "withheld",
                    "missing_gate": "Skip gated actor; preserve missing, never count as protection",
                    "allowed_payload_sha256s": sorted(v["payload_sha256"] for v in cell["payload_variants"].values()),
                    "at_most_one_variant_dispatched": True, "variant_selected_during_preparation": False}
        require(Counter(c["stage"] for c in group["cells"]) == {"gate": 2, "actor": 4}, "Pilot group stage crossing differs")
        groups.append(group)
    cells = [c for g in groups for c in g["cells"]]
    require(len({c["cell_id"] for c in cells}) == len(cells), "Logical cell IDs overlap")
    require(all(not ({"key", "request_key", "manifest_sha256"} & set(c)) for c in cells), "Actual ledger/manifest keys may only be bound later")
    return {"version": VERSION, "run_namespace": run_namespace, "experimental_inference_authorized": False,
            "review_and_separate_manifest_required": True, "model_configurations": copy.deepcopy(CONFIGURATIONS),
            "groups": groups, "total_cells": len(cells), "counts": dict(Counter(c["config"] for c in cells)),
            "stage_counts": {stage: dict(Counter(c["config"] for c in cells if c["stage"] == stage)) for stage in ("secondary", "gate", "actor")},
            "group_counts": {"second_source": len(by_group), "isolated_agent": 12},
            "phase_order": ["secondary", "isolated_agent"],
            "source": {"selection_manifest_sha256": selection["selection_manifest_sha256"], "candidate_corpus_sha256": corpus,
                       "selected_jsonl_sha256": selection["selected_jsonl_sha256"], "source_schedule_seed": schedule["seed"],
                       "source_schedule_namespace": schedule["namespace"], "preserved_source_cell_order": original_source_cell_ids,
                       "source_labels_primary": True, "complete_original_observations_preserved": True,
                       "capacity": copy.deepcopy(capacity["capacity"]), "capacity_summary": copy.deepcopy(capacity["summary"]),
                       "provider_rejection_rule": capacity["provider_rejection_rule"], "selection_manifest": copy.deepcopy(selection["selection_manifest"])},
            "pilot": {k: copy.deepcopy(pilot[k]) for k in ("version", "seed", "gate_rule", "withheld_stub", "actor_schema", "completion_rule", "attacker_rule", "state_reset", "initial_world", "tasks", "constructed_diagnostic", "is_released_dataset", "is_full_agent_evaluation")}}


def prepare(output_root=ROOT, *, run_namespace=NAMESPACE):
    root = Path(output_root).resolve()
    paths = {"selection": "results/subscription-followup/second-source-selection-v1.json",
             "capacity": "results/subscription-followup/second-source-capacity-v1.json",
             "source_rows": "data/raw/subscription-followup/second-source/selected-pairs-v1.jsonl",
             "source_schedule": "data/raw/subscription-followup/second-source/second-source-proposed-schedule-v1.json",
             "pilot_plan": "data/raw/subscription-followup/isolated-agent-plan-v4.json",
             "pilot_receipt": "results/subscription-followup/isolated-agent-preparation-v4.json"}
    bodies = {key: (root / path).read_bytes() for key, path in paths.items()}
    for key, expected in (("source_rows", SOURCE_ROWS_SHA), ("source_schedule", SOURCE_SCHEDULE_SHA), ("pilot_plan", PILOT_PLAN_SHA)):
        require(digest(bodies[key]) == expected, "Fixed extension input differs: " + key)
    selection, capacity, schedule, pilot, pilot_receipt = (json.loads(bodies[k]) for k in ("selection", "capacity", "source_schedule", "pilot_plan", "pilot_receipt"))
    require(selection["selected_groups"] == 66 and selection["selected_rows"] == 132
            and selection["selected_jsonl_sha256"] == SOURCE_ROWS_SHA
            and selection["selection_manifest_sha256"] == SOURCE_MANIFEST_SHA, "Exact selected source denominator/provenance differs")
    require(capacity["schedule"]["sha256"] == SOURCE_SCHEDULE_SHA and pilot_receipt["plan"]["sha256"] == PILOT_PLAN_SHA
            and pilot_receipt["pilot_ready"] is True and pilot_receipt["inference_performed"] is False, "Saved capacity/pilot receipt binding differs")
    rows = [json.loads(line) for line in bodies["source_rows"].splitlines() if line]
    plan = assemble(rows, selection, capacity, schedule, pilot, run_namespace=run_namespace)
    require(plan["total_cells"] == 1128 and plan["counts"] == {"jev_firstparty": 552, "sol_subscription": 576}, "Combined maximum cell count differs")
    plan_path = root / "data/raw/subscription-followup/extensions-plan-v1.json"
    plan_body = canonical(plan) + b"\n"
    own_files = [Path(__file__), *sorted((ROOT / "scripts/subscription_followup").glob("data*.py")),
                 ROOT / "scripts/subscription_followup/pilot.py", ROOT / "scripts/study_v5/prompts.py", ROOT / "scripts/study_v7/requests.py"]
    receipt = {"version": "subscription-followup-extensions-preparation-1", "run_namespace": run_namespace,
               "inference_performed": False, "inference_authorized_by_preparation": False,
               "review_status": "Pending independent source/pilot review and separate root manifest",
               "plan": {"path": str(plan_path.relative_to(root)), "sha256": digest(plan_body), "bytes": len(plan_body)},
               "inputs": {key: {"path": path, "sha256": digest(bodies[key]), "bytes": len(bodies[key])} for key, path in paths.items()},
               "counts": plan["counts"], "stage_counts": plan["stage_counts"], "group_counts": plan["group_counts"],
               "total_cells": plan["total_cells"], "source_schedule_order_and_payloads_preserved": True,
               "complete_source_candidates_preserved": True, "source_manifest_sha256": SOURCE_MANIFEST_SHA,
               "candidate_corpus_sha256": selection["candidate_corpus_sha256"], "pilot_version": pilot["version"],
               "pilot_payload_and_variants_unchanged": True, "gate_missing_is_missing_not_protection": True,
               "dynamic_gated_actor_variant_not_preselected": True, "actual_ledger_keys_created": False,
               "maximum_jev_requests": 552, "maximum_jev_full_context_reservation_usd": "0.741888",
               "openai_api_dollar_reservation_usd": "0", "code_sha256": {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in own_files}}
    receipt_path = root / "results/subscription-followup/extensions-preparation-v1.json"
    receipt_body = canonical(receipt) + b"\n"
    for target, body in ((plan_path, plan_body), (receipt_path, receipt_body)):
        require(not target.exists() or target.read_bytes() == body, "Refuse to overwrite a different extension preparation")
    write_once(plan_path, plan_body)
    write_once(receipt_path, receipt_body)
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=ROOT)
    parser.add_argument("--run-namespace", default=NAMESPACE)
    args = parser.parse_args()
    print(json.dumps(prepare(args.output_root, run_namespace=args.run_namespace), indent=2, sort_keys=True))
