"""Prepare source-faithful human-review material, never inference or semantic labels.

Public source bytes and review texts stay in Git-ignored data/raw/. The committed
summary contains counts, field availability, immutable revisions and byte hashes.
SPML is a policy-boundary setting: its submitted user prompt is not automatically
an untrusted tool message. AIB tool_result messages retain their original roles.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import subprocess
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/source-discovery"
SUMMARY = ROOT / "results/source-discovery/review-preparation.json"
SPML_REPO = "reshabhs/SPML_Chatbot_Prompt_Injection"
SPML_REVISION = "02ce8084e979bc7d4c24ee35d22ecb7f2db96ff5"
AIB_REPO = "ppradyoth/AgentInjectionBench"
AIB_REVISION = "540669a836e98063278fb0586e5e178818a20d88"
AIB_SHA256 = "606cb74f5ce874dba45d9cdf591af678d7c6bd8a92ff3189d0f522fb39fb941e"
MAX_SOURCE_BYTES = 40_000_000


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def require_ignored(path: Path, root: Path = ROOT) -> None:
    """Refuse to place source/review text outside this checkout's ignored paths."""
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError("Raw/review destination is outside the project") from exc
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", str(relative)],
        cwd=root, check=False,
    )
    if result.returncode != 0:
        raise ValueError(f"Raw/review destination is not Git-ignored: {relative}")


def preserve_write(path: Path, body: bytes, *, raw: bool = True) -> None:
    """Idempotent writes; refuse to silently replace changed historical material."""
    if raw:
        require_ignored(path)
    if path.exists():
        if path.read_bytes() != body:
            raise ValueError(f"Refusing to overwrite different existing bytes: {path.name}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(body)
    if raw:
        os.chmod(path, 0o600)


def fetch_source(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "DecisionContextBenchmark-review-preparation"})
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read(MAX_SOURCE_BYTES + 1)
    if len(body) > MAX_SOURCE_BYTES:
        raise ValueError("Source exceeds the preparation download limit")
    return body


def source_location(repo: str, revision: str, filename: str, row_number: int,
                    original: dict, source_id: str | None = None) -> dict:
    return {
        "repository": repo, "revision": revision, "file": filename,
        "row_number_1based": row_number,
        "row_id": source_id,
        "row_id_kind": "upstream_id" if source_id else "csv_data_row_1based",
        "parsed_row_sha256": sha256(canonical_bytes(original)),
        "parsed_row_hash_encoding": "UTF-8 canonical JSON; source bytes have a separate file hash",
    }


def review_base(source: dict, setting: str) -> dict:
    return {
        "schema_version": "source-review-v1",
        "source": source,
        "setting": setting,
        "semantic_gold": None,
        "review_status": "pending_human_review",
        "reviewers": [],
        "split": None,
        "inference_eligible": False,
        "flags": [],
    }


def adapt_spml(row: dict[str, str], row_number: int) -> dict:
    required = {"System Prompt", "User Prompt", "Prompt injection", "Degree", "Source"}
    if not required.issubset(row):
        raise ValueError("SPML schema does not contain the expected released fields")
    policy, submitted = row["System Prompt"], row["User Prompt"]
    if not isinstance(policy, str) or not isinstance(submitted, str):
        raise ValueError("SPML policy/user prompt is malformed")
    label = int(row["Prompt injection"])
    if label not in (0, 1):
        raise ValueError("Unexpected SPML label")
    record = review_base(source_location(SPML_REPO, SPML_REVISION,
                        "spml_prompt_injection.csv", row_number, row), "system_policy_boundary")
    record["upstream_annotation"] = {
        "label": label, "label_field": "Prompt injection",
        "label_meaning": "Intended violation of paired chatbot system definition, not universal maliciousness",
        "degree": int(row["Degree"]), "attack_source": row["Source"] or None,
    }
    record["detector_payload"] = {
        "setting": "system_policy_boundary", "trusted_policy": policy,
        "actual_user_task": None, "submitted_user_prompt": submitted,
    }
    record["field_provenance"] = {
        "trusted_policy": {"path": "System Prompt", "role": "system", "trust": "source_intended_system_policy"},
        "submitted_user_prompt": {"path": "User Prompt", "role": "user", "trust": "submitted_direct_user_instruction_not_lower_trust_tool_content"},
        "actual_user_task": {"status": "missing", "reason": "No independent legitimate user-task field is released; do not invent one"},
    }
    record["flags"] = ["synthetic_policy_relative_annotation", "requires_independent_semantic_review",
                       "missing_separate_legitimate_user_task", "not_indirect_tool_injection"]
    if not policy:
        record["flags"].append("empty_upstream_system_policy")
    if not submitted:
        record["flags"].append("empty_upstream_submitted_user_prompt")
    record["grouping_keys"] = {"system_policy_sha256": sha256(policy.encode())}
    return record


def adapt_aib(row: dict, row_number: int) -> dict:
    conversation = row.get("conversation")
    if not isinstance(conversation, list) or not conversation:
        raise ValueError("AIB conversation is empty or malformed")
    if not isinstance(row.get("system_prompt"), str):
        raise ValueError("AIB system policy is not text")
    user_messages, source_messages, inputs, omitted = [], [], [], []
    unexpected_roles = []
    for index, message in enumerate(conversation):
        role = message.get("role")
        if not isinstance(message.get("content"), str):
            raise ValueError("AIB message content is not text")
        # Reference assistant responses/tool calls are held only in the ignored
        # original source, never shown to a detector as context or as an answer.
        if role in {"assistant", "tool_call"}:
            omitted.append({"original_index": index, "role": role})
            continue
        if role not in {"user", "tool_result"}:
            unexpected_roles.append(role)
            continue
        item = {"original_index": index, **message}
        inputs.append(item)
        if role == "user":
            user_messages.append(item)
        else:
            source_messages.append(item)
    initial_user = conversation[0] if conversation[0].get("role") == "user" else None
    actual_task = initial_user["content"] if initial_user else None
    record = review_base(source_location(AIB_REPO, AIB_REVISION,
                        "data/agent_injection_bench.jsonl", row_number, row, row["id"]), "indirect_tool_content")
    record["upstream_annotation"] = {
        "label": row.get("ground_truth"), "label_field": "ground_truth",
        "label_meaning": "Upstream safe/unsafe case label; not yet independently adjudicated semantic gold",
        "attack_category": row.get("attack_category"),
        "injection_surface": row.get("injection_surface"),
        "declared_complexity": row.get("complexity"),
    }
    record["detector_payload"] = {
        "setting": "indirect_tool_content", "trusted_policy": row["system_prompt"],
        "actual_user_task": actual_task,
        "source_conversation_inputs": inputs,
        "candidate_message_indexes": [m["original_index"] for m in source_messages],
    }
    record["field_provenance"] = {
        "trusted_policy": {"path": "system_prompt", "role": "system", "trust": "source_intended_system_policy"},
        "actual_user_task": {"path": "conversation[0].content" if initial_user else None,
                             "role": "user" if initial_user else None,
                             "status": "explicit_initial_user_request" if initial_user else "missing"},
        "candidate_messages": [{"path": f"conversation[{m['original_index']}]", "role": "tool_result",
                                "trust": "external_tool_result", "tool": m.get("tool")}
                               for m in source_messages],
        "additional_user_turns": [{"path": f"conversation[{m['original_index']}]", "role": "user",
                                   "trust": "not_automatically_promoted_to_trusted_task"}
                                  for m in user_messages if m["original_index"] != 0],
        "omitted_reference_messages": omitted,
    }
    # Tool catalogs can themselves be an attack surface. Keep the original
    # metadata for review without automatically assigning it a trusted role.
    record["review_only_tool_catalog"] = row.get("tools_available")
    flags = ["synthetic_upstream_fixture", "requires_independent_semantic_review",
             "assistant_reference_outputs_excluded", "tool_catalog_trust_unadjudicated"]
    if not initial_user:
        flags.append("missing_explicit_initial_user_task")
    if len(source_messages) != 1:
        flags.append("multiple_or_missing_tool_results_candidate_unit_unresolved")
    if len(user_messages) != 1 or row.get("complexity") == "multi_turn":
        flags.append("multi_turn_requires_turn_level_review")
    if [m.get("role") for m in conversation] not in (["user", "tool_result", "assistant"], ["user", "tool_result"]):
        flags.append("noncanonical_conversation_order")
    if any(m["role"] == "tool_call" for m in omitted):
        flags.append("reference_tool_call_excluded")
    if unexpected_roles:
        flags.append("unexpected_source_role_requires_manual_review")
    record["flags"] = flags
    record["candidate_unit"] = "all_original_tool_result_messages_pending_review"
    record["grouping_keys"] = {"system_policy_sha256": sha256(row["system_prompt"].encode())}
    return record


def load_spml(download: bool) -> tuple[bytes, list[dict]]:
    prefix = f"spml-{SPML_REVISION}"
    receipt_path = RAW / f"{prefix}-receipt.json"
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if receipt["revision"] != SPML_REVISION:
            raise ValueError("SPML source revision mismatch")
        for entry in receipt["files"]:
            body = (ROOT / entry["local_cache"]).read_bytes()
            if sha256(body) != entry["sha256"]:
                raise ValueError("SPML cached bytes failed source hash verification")
        return (RAW / f"{prefix}-data.csv").read_bytes(), receipt["files"]
    if not download:
        raise ValueError("Pinned SPML cache is absent; use --download-spml to download public inert bytes")
    receipts = []
    for filename, local_suffix in [("README.md", "README.md"), ("spml_prompt_injection.csv", "data.csv")]:
        url = f"https://huggingface.co/datasets/{SPML_REPO}/resolve/{SPML_REVISION}/{filename}"
        body = fetch_source(url)
        path = RAW / f"{prefix}-{local_suffix}"
        preserve_write(path, body)
        receipts.append({"url": url, "local_cache": str(path.relative_to(ROOT)),
                         "bytes": len(body), "sha256": sha256(body)})
    receipt = {"repository": SPML_REPO, "revision": SPML_REVISION, "files": receipts}
    preserve_write(receipt_path, canonical_bytes(receipt) + b"\n")
    return (RAW / f"{prefix}-data.csv").read_bytes(), receipts


def summarize(records: list[dict], path: Path, body: bytes, source_receipts: list[dict]) -> dict:
    flag_counts = Counter(flag for row in records for flag in row["flags"])
    labels = Counter(str(row["upstream_annotation"]["label"]) for row in records)
    return {
        "repository": records[0]["source"]["repository"],
        "revision": records[0]["source"]["revision"],
        "review_rows": len(records),
        "review_cache": str(path.relative_to(ROOT)), "review_sha256": sha256(body),
        "review_bytes": len(body), "source_receipts": source_receipts,
        "upstream_label_counts": dict(sorted(labels.items())),
        "semantic_gold_populated": sum(r["semantic_gold"] is not None for r in records),
        "independently_reviewed": 0,
        "flag_counts": dict(sorted(flag_counts.items())),
        "distinct_exact_system_policies": len({r["grouping_keys"]["system_policy_sha256"] for r in records}),
        "actual_user_task_available": sum(r["detector_payload"]["actual_user_task"] is not None for r in records),
        "trusted_policy_available": sum(bool(r["detector_payload"]["trusted_policy"]) for r in records),
        "submitted_user_prompt_nonempty": sum(bool(r["detector_payload"].get("submitted_user_prompt")) for r in records),
        "inference_eligible": sum(r["inference_eligible"] for r in records),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-spml", action="store_true", help="Download two pinned public files; no model requests")
    args = parser.parse_args()
    require_ignored(RAW / "review-placeholder.jsonl")
    spml_bytes, spml_receipts = load_spml(args.download_spml)
    spml_original = list(csv.DictReader(io.StringIO(spml_bytes.decode("utf-8-sig"), newline="")))
    spml = [adapt_spml(row, index) for index, row in enumerate(spml_original, 1)]
    aib_path = RAW / "aib-cases.jsonl"
    aib_bytes = aib_path.read_bytes()
    if sha256(aib_bytes) != AIB_SHA256:
        raise ValueError("AIB cache does not match the pinned inspected source")
    aib_original = [json.loads(line) for line in aib_bytes.decode().splitlines() if line.strip()]
    aib = [adapt_aib(row, index) for index, row in enumerate(aib_original, 1)]
    summaries = []
    for name, records, receipts in [
        ("spml", spml, spml_receipts),
        ("aib", aib, [{"url": f"https://raw.githubusercontent.com/{AIB_REPO}/{AIB_REVISION}/data/agent_injection_bench.jsonl",
                       "local_cache": str(aib_path.relative_to(ROOT)), "bytes": len(aib_bytes), "sha256": AIB_SHA256}]),
    ]:
        path = RAW / f"{name}-review-v1.jsonl"
        body = b"".join(canonical_bytes(record) + b"\n" for record in records)
        preserve_write(path, body)
        summaries.append(summarize(records, path, body, receipts))
    summary = {
        "schema_version": "review-preparation-v1", "as_of": "2026-10-30",
        "no_inference": True, "no_generated_examples": True, "no_new_semantic_labels": True,
        "training_evaluation_split": "not_assigned",
        "all_review_texts_git_ignored": True,
        "sources": summaries,
        "available_fields": {
            "spml": {"trusted_policy": True, "separate_legitimate_user_task": False,
                     "submitted_user_instruction": True, "indirect_untrusted_tool_candidate": False},
            "aib": {"trusted_policy": True, "initial_user_task": True,
                    "tool_result_messages_with_original_roles": True,
                    "assistant_reference_outputs_in_detector_payload": False,
                    "unique_attack_span_or_target_turn": "not_assumed"},
        },
        "limitations": [
            "Review preparation is not verified semantic gold and does not freeze an experiment.",
            "SPML submitted user instructions remain a separate policy-boundary arm, not lower-trust tool content.",
            "AIB multi-turn or multiple-tool-result cases need turn-level review before selecting a candidate.",
            "AIB later user turns and tool catalogs have not been automatically assigned trusted status.",
            "Original reference assistant messages and execution/gold metadata remain only in the ignored source; they are excluded from detector payloads.",
            "No development/evaluation split or source independence claim is made; group policies, templates and related cases before splitting.",
        ],
    }
    preserve_write(SUMMARY, json.dumps(summary, indent=2, sort_keys=True).encode() + b"\n", raw=False)
    print(json.dumps({"summary": str(SUMMARY.relative_to(ROOT)),
                      "review_rows": {s["repository"]: s["review_rows"] for s in summaries},
                      "inference_eligible": 0}))


if __name__ == "__main__":
    main()
