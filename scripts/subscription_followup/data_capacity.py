"""Full-input, tokenization-only audit and inert second-source cell ordering.

No credential, transport, model weights, live result or accounting access. The
native tokenizers are not certified; the full original inputs are never clipped.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import importlib.metadata
import json
from pathlib import Path

from scripts.study_v5 import prompts
from scripts.study_v7 import requests
from .data_sources import RAW, ROOT, sha
from .data_dtap import write_json

CONDITIONS = ("format", "task", "reminder", "length")
CONFIGS = ("jev_firstparty", "sol_subscription")
ORDER_SEED = "subscription-followup-second-source-order-v1-20261101"


def task_payload(config, row, condition):
    """New task-source adapter with the unchanged frozen condition formulas."""
    if config not in CONFIGS or condition not in CONDITIONS:
        raise ValueError("Only the predefined second-source routes and conditions")
    if row.get("source") != "dtap_released_episodes" or not row.get("task") or not row.get("candidate"):
        raise ValueError("Complete authentic selected second-source row required")
    safe = {"source": row["source"], "setting": "indirect_tool_content",
            "task": row["task"], "candidate": row["candidate"], "policy": None}
    state, question = prompts.serialize(safe, condition), prompts.question(safe)
    # Verify source bytes survive serialization; source labels never enter input.
    if json.loads(state)["CANDIDATE"] != row["candidate"]:
        raise ValueError("Candidate changed during input serialization")
    if config == "jev_firstparty":
        return {"model": "jev-1.14.0", "state": state,
                "questions": {"injection": {"type": "noul", "instructions": question}}}
    return requests._responses("sol_subscription", state, question, configuration_revision="v7.0.2")


def counterbalanced_schedule(rows, namespace):
    if not namespace.startswith("subscription-followup-"):
        raise ValueError("Separate follow-up namespace required")
    groups = defaultdict(list)
    for row in rows:
        groups[row["group_id"]].append(row)
    ordered = sorted(groups, key=lambda g: sha((ORDER_SEED + ":groups:" + g).encode()))
    result = []
    for i, group in enumerate(ordered):
        pair = sorted(groups[group], key=lambda r: r["id"])
        if len(pair) != 2 or {r["upstream_label"] for r in pair} != {0, 1}:
            raise ValueError("Exactly one complete source pair per component")
        # Cyclic Latin rotation balances every condition's position within one
        # group; parity counterbalances page order and model order before outcomes.
        rotation = i % len(CONDITIONS)
        conditions = CONDITIONS[rotation:] + CONDITIONS[:rotation]
        if i % 2:
            pair.reverse()
        configs = CONFIGS if i % 2 == 0 else CONFIGS[::-1]
        cells = []
        for config in configs:
            for condition in conditions:
                for row in pair:
                    body = task_payload(config, row, condition)
                    payload_sha = sha(requests.canonical(body))
                    identity = ["second-source-v1", namespace, group, row["id"], config, condition, payload_sha]
                    cells.append({"cell_id": "second-source:" + sha(requests.canonical(identity)),
                                  "config": config, "configuration_revision": "v7.0.2" if config == "sol_subscription" else None,
                                  "id": row["id"], "source": row["source"], "group_id": group,
                                  "condition": condition, "namespace": namespace, "replicate": "first",
                                  "first_attempt_primary": True, "payload_sha256": payload_sha})
        result.append({"group_id": group, "condition_order": list(conditions),
                       "page_order": [r["id"] for r in pair], "config_order": list(configs), "cells": cells})
    return {"version": "second-source-proposed-schedule-1", "namespace": namespace,
            "seed": ORDER_SEED, "experimental_inference_authorized": False,
            "groups": result, "counts": dict(Counter(c["config"] for g in result for c in g["cells"])),
            "condition_position_counts": {str(pos): dict(Counter(g["condition_order"][pos] for g in result)) for pos in range(4)},
            "source_rows_sha256": sha(requests.canonical([{k: r[k] for k in ("id", "task", "candidate")} for r in rows]))}


def audit(namespace="subscription-followup-second-source-v1"):
    # Neither route has a certified native tokenizer in this preparation.
    # Do not let a tokenization audit implicitly download packages or cache data.
    encoding = None
    try:
        proxy_package_version = importlib.metadata.version("tiktoken")
    except importlib.metadata.PackageNotFoundError:
        proxy_package_version = None
    def count(text):
        return len(encoding.encode(text, disallowed_special=())) if encoding else None
    path = RAW / "selected-pairs-v1.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    selection = json.loads((ROOT / "results/subscription-followup/second-source-selection-v1.json").read_text())
    if sha(path.read_bytes()) != selection["selected_jsonl_sha256"]:
        raise ValueError("Selected source rows differ from fixed selection receipt")
    measurements = []
    for row in rows:
        for config in CONFIGS:
            for condition in CONDITIONS:
                body = task_payload(config, row, condition)
                serialized = requests.canonical(body)
                state = body["state"] if config == "jev_firstparty" else body["input"][0]["content"]
                question = body["questions"]["injection"]["instructions"] if config == "jev_firstparty" else body["instructions"]
                measurements.append({"id": row["id"], "group_id": row["group_id"], "config": config,
                                     "condition": condition, "payload_sha256": sha(serialized),
                                     "serialized_payload_chars": len(serialized.decode()),
                                     "serialized_payload_utf8_bytes": len(serialized),
                                     "state_chars": len(state), "state_utf8_bytes": len(state.encode()),
                                     "question_or_instructions_chars": len(question),
                                     "question_or_instructions_utf8_bytes": len(question.encode()),
                                     "o200k_serialization_proxy_tokens": count(serialized.decode()),
                                     "o200k_state_proxy_tokens": count(state),
                                     "o200k_question_or_instructions_proxy_tokens": count(question),
                                     "candidate_chars": len(row["candidate"]), "candidate_utf8_bytes": len(row["candidate"].encode())})
    measurement_path = RAW / "full-input-capacity-measurements-v1.jsonl"
    measurement_path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in measurements))
    schedule = counterbalanced_schedule(rows, namespace)
    schedule_path = RAW / "second-source-proposed-schedule-v1.json"
    write_json(schedule_path, schedule)
    numeric = [k for k in measurements[0] if k.endswith(("chars", "bytes", "tokens")) and isinstance(measurements[0][k], int)]
    summary = {config: {"requests": len(part), **{k: {"min": min(r[k] for r in part), "max": max(r[k] for r in part),
                                                      "sum": sum(r[k] for r in part)} for k in numeric}}
               for config in CONFIGS for part in [[r for r in measurements if r["config"] == config]]}
    record = {"status": "FULL_INPUT_MEASURED_NATIVE_CAPACITY_UNCERTIFIED", "no_inference": True,
              "selection_manifest_sha256": selection["selection_manifest_sha256"], "selected_jsonl_sha256": sha(path.read_bytes()),
              "complete_original_candidates_preserved": True, "truncation": False, "refill": False,
              "source_groups": len(schedule["groups"]), "measurements": len(measurements), "summary": summary,
              "native_tokenizer_verified": {config: False for config in CONFIGS},
              "tokenizer_proxy": {"encoding": "o200k_base" if encoding else None,
                                  "package_version": proxy_package_version,
                                  "availability": "No certified native encoding; no tokenizer/package/cache download or proxy substitution performed",
                                  "not_native": "Exact local encoding counts of full canonical JSON, not certified Jev/Sol tokens or hidden provider framing."},
              "capacity": {"jev_firstparty": {"default_context_tokens": 32000, "long_context_header": False,
                            "question_plus_state_framing_eligibility": "Native tokenizer and combined-state/question acceptance not certified; full-input server gate only after separate authorization.",
                            "proxy_requests_above_32000": sum(r["o200k_serialization_proxy_tokens"] > 32000 for r in measurements if r["config"] == "jev_firstparty") if encoding else None,
                            "reserved_usd_per_request": "0.001344", "requests": schedule["counts"]["jev_firstparty"],
                            "full_32000_token_reserved_usd": str(Decimal("0.001344") * schedule["counts"]["jev_firstparty"])},
                           "sol_subscription": {"conservative_catalog_context_tokens": 500000, "requested_output_cap": None,
                            "output_cap_status": "Unsupported; provider default/uncontrolled", "reasoning": "low",
                            "api_dollar_reserve": "0", "quota_and_service_availability": "Unverified for later separate source run"}},
              "provider_rejection_rule": f"Retain unsupported/unattempted as missing in the predeclared {len(schedule['groups'])} groups; never trim, replace, retry failed first attempts, or refill.",
              "schedule": {"path": str(schedule_path.relative_to(ROOT)), "sha256": sha(schedule_path.read_bytes()),
                           "seed": ORDER_SEED, "namespace": namespace, "counts": schedule["counts"],
                           "condition_position_counts": schedule["condition_position_counts"]},
              "measurement_path": str(measurement_path.relative_to(ROOT)), "measurement_sha256": sha(measurement_path.read_bytes()),
              "renderer_code_sha256": {str(Path(module.__file__).relative_to(ROOT)): sha(Path(module.__file__).read_bytes()) for module in (prompts, requests)},
              "audit_code_sha256": sha(Path(__file__).read_bytes())}
    write_json(ROOT / "results/subscription-followup/second-source-capacity-v1.json", record)
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--namespace", default="subscription-followup-second-source-v1")
    args = parser.parse_args()
    result = audit(args.namespace)
    print(json.dumps({k: result[k] for k in ("status", "source_groups", "measurements", "summary", "capacity", "schedule")}, sort_keys=True))
