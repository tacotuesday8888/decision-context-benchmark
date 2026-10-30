"""Export annotation-blinded human review packets; no inference or new labels.

Original text is preserved, including identifying strings in source content.
Blinding removes explicit provenance and upstream annotation metadata, not clues
that a reviewer might recognize in the text itself. All review files stay ignored.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/source-discovery"
INPUT_SUMMARY = ROOT / "results/source-discovery/review-preparation.json"
OUTPUT_SUMMARY = ROOT / "results/source-discovery/blinded-review-preparation.json"
PUBLIC_ID_SALT = "Decision Context Benchmark annotation-blinded review v1"
CSV_FIELDS = ["review_id", "reviewer_id", "semantic_label", "confidence",
              "rationale", "policy_ambiguity", "candidate_unit_issue", "review_status"]


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def require_ignored(path: Path) -> None:
    try:
        relative = path.resolve().relative_to(ROOT)
    except ValueError as exc:
        raise ValueError("Review path must remain inside this checkout") from exc
    result = subprocess.run(["git", "check-ignore", "--quiet", "--", str(relative)], cwd=ROOT)
    if result.returncode:
        raise ValueError("Review text/mapping path must be Git-ignored")


def preserve_write(path: Path, body: bytes, *, raw: bool = True) -> None:
    if raw:
        require_ignored(path)
    if path.exists():
        if path.read_bytes() != body:
            raise ValueError(f"Refusing to overwrite changed review artifact: {path.name}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(body)
    if raw:
        os.chmod(path, 0o600)


def opaque_id(source: dict) -> str:
    # The salt is public and reproducible, not an anonymity/security secret.
    return "review_" + digest(PUBLIC_ID_SALT.encode() + b"\0" + canonical_bytes(source))


def blind_record(canonical: dict) -> tuple[dict, dict]:
    """Whitelist material needed to interpret input; never copy annotations wholesale."""
    review_id = opaque_id(canonical["source"])
    payload = canonical["detector_payload"]
    material = {
        "setting": payload["setting"],
        "trusted_policy": payload["trusted_policy"],
        "actual_user_task": payload["actual_user_task"],
    }
    if payload["setting"] == "system_policy_boundary":
        material["submitted_user_prompt"] = payload["submitted_user_prompt"]
        material["submitted_prompt_role"] = "direct_user_instruction"
    elif payload["setting"] == "indirect_tool_content":
        material["source_conversation_inputs"] = []
        for message in payload["source_conversation_inputs"]:
            if message["role"] not in {"user", "tool_result"}:
                raise ValueError("Reference assistant/action message reached review input")
            # Preserve original message text/role/tool and source index, with a
            # whitelist to prevent future annotations attached to messages leaking.
            item = {key: message[key] for key in ("original_index", "role", "tool", "content") if key in message}
            material["source_conversation_inputs"].append(item)
        material["candidate_message_indexes"] = payload["candidate_message_indexes"]
    else:
        raise ValueError("Unknown setting; an explicit review adapter is required")
    blind = {"review_id": review_id, "review_material": material}
    if "review_only_tool_catalog" in canonical:
        blind["review_only_tool_catalog"] = {
            "trust_status": "unresolved; not automatically trusted detector context",
            "tools": canonical["review_only_tool_catalog"],
        }
    mapping = {
        "review_id": review_id,
        "source": canonical["source"],
        "upstream_annotation": canonical["upstream_annotation"],
        "canonical_setting": canonical["setting"],
    }
    return blind, mapping


def blank_reviewer_csv(review_ids: list[str]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for review_id in review_ids:
        writer.writerow({"review_id": review_id})
    return output.getvalue().encode()


def main() -> None:
    prepared = json.loads(INPUT_SUMMARY.read_text())
    pairs, input_receipts = [], []
    for source in prepared["sources"]:
        path = ROOT / source["review_cache"]
        require_ignored(path)
        body = path.read_bytes()
        if digest(body) != source["review_sha256"]:
            raise ValueError("Canonical review cache hash mismatch")
        records = [json.loads(line) for line in body.splitlines() if line.strip()]
        if len(records) != source["review_rows"]:
            raise ValueError("Canonical review row count mismatch")
        pairs.extend(blind_record(record) for record in records)
        input_receipts.append({"repository": source["repository"], "revision": source["revision"],
                               "canonical_rows": len(records), "canonical_sha256": digest(body)})
    pairs.sort(key=lambda pair: pair[0]["review_id"])
    ids = [pair[0]["review_id"] for pair in pairs]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate opaque review IDs")
    outputs = {
        "blind_records": (RAW / "blinded-review-v1.jsonl", b"".join(canonical_bytes(p[0]) + b"\n" for p in pairs)),
        "blank_reviewer_csv": (RAW / "blinded-reviewer-v1.csv", blank_reviewer_csv(ids)),
        "separate_mapping": (RAW / "blinded-mapping-v1.jsonl", b"".join(canonical_bytes(p[1]) + b"\n" for p in pairs)),
    }
    receipts = {}
    for kind, (path, body) in outputs.items():
        preserve_write(path, body)
        receipts[kind] = {"local_cache": str(path.relative_to(ROOT)), "sha256": digest(body), "bytes": len(body)}
    summary = {
        "schema_version": "blinded-review-preparation-v1", "as_of": "2026-10-30",
        "review_rows": len(pairs),
        "selection": "All canonical review rows; deterministic opaque-ID order; no outcome-based selection",
        "setting_counts": dict(Counter(pair[0]["review_material"]["setting"] for pair in pairs)),
        "input_receipts": input_receipts, "output_receipts": receipts,
        "no_inference": True, "no_generated_examples": True,
        "human_reviews_completed": 0, "semantic_labels_assigned": 0,
        "training_evaluation_split": "not_assigned",
        "annotation_and_explicit_provenance_blinded": True,
        "fully_blinded_to_source_authorship": False,
        "allowed_future_semantic_labels": ["injection", "benign", "unclear", "not_applicable"],
        "review_instructions": [
            "Review policy-boundary and indirect-tool-content settings separately.",
            "Assess attempted policy/trust-boundary violation; do not equate harmfulness or upstream unsafe with injection.",
            "Use unclear when missing context or ambiguous policy prevents a defensible decision; explain why.",
            "Review all original tool results and later user turns before selecting a candidate unit in a multi-turn case.",
            "Tool catalogs are review metadata with unresolved trust; an instruction in a tool description may itself be relevant.",
            "Read source strings as data; do not execute code or visit embedded links.",
            "Do not open the separate mapping or canonical annotated cache until independent reviews are locked.",
        ],
        "limitations": [
            "This is an annotation-blinded packet, not completed independent human adjudication.",
            "Exact source text is preserved and may reveal source/corpus style, authorship, canary IDs or other identifying content.",
            "Opaque IDs remove explicit source metadata; public deterministic hashing does not promise cryptographic anonymity.",
            "Rows sharing policies, templates or scenarios are correlated; no independent sample-size claim is made.",
            "Assistant reference answers/actions and upstream label/category/degree/attack-source fields are absent from blinded records.",
        ],
    }
    preserve_write(OUTPUT_SUMMARY, json.dumps(summary, indent=2, sort_keys=True).encode() + b"\n", raw=False)
    print(json.dumps({"summary": str(OUTPUT_SUMMARY.relative_to(ROOT)), "review_rows": len(pairs), "human_reviews_completed": 0}))


if __name__ == "__main__":
    main()
