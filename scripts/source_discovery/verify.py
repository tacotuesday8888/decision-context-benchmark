"""Offline inventory checks; optionally reparse the pinned source downloads."""
import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from catalog import AUDITS, OUT, ROOT, build


def require(condition, message):
    if not condition:
        raise ValueError(message)


def expected_receipts(records):
    """Require the artifacts used by this audit, with data URLs pinned to revisions."""
    expected = {}

    def add(filename, url):
        expected["data/raw/source-discovery/" + filename] = url

    for repo, slug, paths in [
        ("nvidia/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1",
         "Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1", ["train.jsonl"]),
        ("ScaleAI/aspi", "aspi", ["data/" + s + ".jsonl" for s in ("banking", "slack", "travel", "workspace")]),
        ("EliasHossain/nexus-ipi", "nexus", ["ipi_v1.jsonl", "ipi_v2.jsonl"]),
    ]:
        revision = records[repo]["revision"]
        base = "https://huggingface.co/datasets/" + repo + "/resolve/" + revision + "/"
        add(slug + "-metadata.json", "https://huggingface.co/api/datasets/" + repo)
        add(slug + "-README.md", base + "README.md")
        for path in paths:
            filename = path.replace("/", "-")
            if slug == "nexus":
                filename = path.replace("ipi_", "")
            add(slug + "-" + filename, base + path)

    for repo, slug, paths in [
        ("ppradyoth/AgentInjectionBench", "aib", ["data/agent_injection_bench.jsonl", "LICENSE"]),
        ("judydnguyen/infuse", "infuse", [
            "README.md", "LICENSE", "benchmark/tasks/task_1/instruction.md",
            "benchmark/tasks/task_1/environment/overlays/benign.toml",
            "benchmark/tasks/task_1/tests/test.sh", "benchmark/attacks/attack_1/config.toml",
        ]),
    ]:
        revision = records[repo]["revision"]
        add(slug + "-commit.json", "https://api.github.com/repos/" + repo + "/commits/HEAD")
        if slug == "infuse":
            add("infuse-tree.json", "https://api.github.com/repos/" + repo + "/git/trees/" + revision + "?recursive=1")
        for path in paths:
            filename = "cases.jsonl" if slug == "aib" and path.endswith(".jsonl") else path.replace("/", "-")
            add(slug + "-" + filename, "https://raw.githubusercontent.com/" + repo + "/" + revision + "/" + path)
    return expected


def verify_cached_records(records, cached):
    """Recompute findings from bytes already authenticated against source receipts."""
    def raw(filename):
        return cached["data/raw/source-discovery/" + filename]

    def document(filename):
        try:
            return json.loads(raw(filename))
        except (ValueError, UnicodeError) as exc:
            raise ValueError("Cannot parse cached JSON " + filename) from exc

    def jsonl(filename):
        rows = []
        for number, line in enumerate(raw(filename).splitlines(), 1):
            if line.strip():
                try:
                    record = json.loads(line)
                except (ValueError, UnicodeError) as exc:
                    raise ValueError(f"Cannot parse {filename} line {number}") from exc
                require(isinstance(record, dict), f"Expected an object in {filename} line {number}")
                rows.append(record)
        require(bool(rows), "Empty source data: " + filename)
        return rows

    def compare(source, reported, observed):
        for field, value in observed.items():
            require(reported.get(field) == value, f"Cached {source} does not match reported {field}")

    for repo, filename in [
        ("nvidia/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1", "Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1-metadata.json"),
        ("ScaleAI/aspi", "aspi-metadata.json"),
        ("EliasHossain/nexus-ipi", "nexus-metadata.json"),
        ("ppradyoth/AgentInjectionBench", "aib-commit.json"),
        ("judydnguyen/infuse", "infuse-commit.json"),
    ]:
        metadata = document(filename)
        require(metadata.get("sha") == records[repo]["revision"], "Cached revision mismatch: " + repo)
        if "cardData" in metadata:
            require(metadata["cardData"].get("license") == records[repo]["license_declared"], "Cached license mismatch: " + repo)

    rows = jsonl("Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1-train.jsonl")
    compare("NVIDIA", records["nvidia/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1"], {
        "rows_counted": len(rows), "schema_keys": sorted(rows[0]),
        "domains": dict(Counter(r["domain"] for r in rows)),
        "attack_categories": dict(Counter(r["attack_category"] for r in rows)),
        "distinct_injection_texts": len({r["injection"]["injection_text"] for r in rows}),
        "has_explicit_task_and_attack": all(r["responses_create_params"]["input"] and r["injection"]["injection_text"] for r in rows),
    })

    rows = []
    for suite in ("banking", "slack", "travel", "workspace"):
        part = jsonl("aspi-data-" + suite + ".jsonl")
        require(all(r["suite"] == suite for r in part), "ASPI suite/file mismatch: " + suite)
        rows.extend(part)
    compare("ASPI", records["ScaleAI/aspi"], {
        "rows_counted": len(rows), "schema_keys": sorted(rows[0]),
        "suites": dict(Counter(r["suite"] for r in rows)),
        "distinct_agentdojo_tasks": len({(r["suite"], r["user_task_id"]) for r in rows}),
        "injection_variants": sum(len(r["injections"]) for r in rows),
    })

    rows = jsonl("aib-cases.jsonl")
    compare("AgentInjectionBench", records["ppradyoth/AgentInjectionBench"], {
        "rows_counted": len(rows), "schema_keys": sorted(rows[0]),
        "category_counts": dict(Counter(r["attack_category"] for r in rows)),
        "label_counts": dict(Counter(r["ground_truth"] for r in rows)),
        "license_file_sha256": hashlib.sha256(raw("aib-LICENSE")).hexdigest(),
    })

    nexus = records["EliasHossain/nexus-ipi"]
    require(set(nexus["versions"]) == {"v1", "v2"}, "Unexpected NEXUS version coverage")
    for version, reported in nexus["versions"].items():
        rows = jsonl("nexus-" + version + ".jsonl")
        pairs = defaultdict(list)
        for record in rows:
            pairs[record["control_pair_id"]].append(record)
        require(all(len(pair) == 2 for pair in pairs.values()), "NEXUS " + version + " has an incomplete or oversized pair")
        for pair_id, pair in pairs.items():
            require({r["safety_label"] for r in pair} == {0, 1}, "NEXUS pair lacks opposite safety labels: " + pair_id)
            require({r["intervention_label"] for r in pair} == {"allow", "block"}, "NEXUS pair lacks allow/block interventions: " + pair_id)
        compare("NEXUS " + version, reported, {
            "rows_counted": len(rows), "schema_keys": sorted(rows[0]),
            "pairs_counted": len(pairs), "two_record_pairs": len(pairs),
            "label_counts": dict(Counter(str(r["safety_label"]) for r in rows)),
            "distinct_requests": len({r["request"] for r in rows}),
            "identical_request_pairs": sum(p[0]["request"] == p[1]["request"] for p in pairs.values()),
            "identical_full_plan_steps_pairs": sum(p[0]["structured_plan"]["steps"] == p[1]["structured_plan"]["steps"] for p in pairs.values()),
            "identical_first_plan_step_pairs": sum(p[0]["structured_plan"]["steps"][:1] == p[1]["structured_plan"]["steps"][:1] for p in pairs.values()),
        })

    tree = document("infuse-tree.json")
    require(tree.get("truncated") is False, "Cached INFUSE repository tree is incomplete")
    paths = [item["path"] for item in tree["tree"] if item["type"] == "blob"]
    require(len(paths) == len(set(paths)), "Duplicate paths in INFUSE repository tree")
    compare("INFUSE", records["judydnguyen/infuse"], {
        "task_instruction_files_counted": sum(p.startswith("benchmark/tasks/task_") and p.endswith("/instruction.md") for p in paths),
        "attack_config_files_counted": sum(p.startswith("benchmark/attacks/attack_") and p.endswith("/config.toml") for p in paths),
    })


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-cache", action="store_true")
    args = parser.parse_args()
    saved = json.loads((OUT / "catalog.json").read_text())
    require(saved == build(), "Catalog does not match its source audits")
    require(len({r["id"] for r in saved["sources"]}) == saved["unique_inventory_entries"], "Duplicate source IDs")
    for entry in saved["sources"]:
        require(bool(entry["urls"]), "Missing evidence URLs: " + entry["id"])
        require(all(u.startswith("https://") for u in entry["urls"]), "Non-HTTPS source URL")
        for audit in entry["audits"]:
            require((ROOT / audit["path"]).is_file(), "Missing source audit file")
    docs = {name: json.loads((OUT / name).read_text()) for name in AUDITS}
    priority = docs["priority-source-inspection.json"]
    require(priority["no_model_requests"] and priority["no_generated_examples"], "Discovery scope changed")
    keyed = {r["id"]: r for r in priority["records"]}
    require(len(keyed) == len(priority["records"]), "Duplicate priority source IDs")
    for record in keyed.values():
        require(bool(re.fullmatch("[a-f0-9]{40}", record["revision"])), "Invalid pinned revision: " + record["id"])
    nvidia = keyed["nvidia/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1"]
    require(sum(nvidia["domains"].values()) == nvidia["rows_counted"] == sum(nvidia["attack_categories"].values()), "NVIDIA count mismatch")
    aib = keyed["ppradyoth/AgentInjectionBench"]
    require(sum(aib["label_counts"].values()) == aib["rows_counted"] == sum(aib["category_counts"].values()), "AIB label/category mismatch")
    aspi = keyed["ScaleAI/aspi"]
    require(sum(aspi["suites"].values()) == aspi["rows_counted"], "ASPI count mismatch")
    for version in keyed["EliasHossain/nexus-ipi"]["versions"].values():
        require(version["rows_counted"] == version["two_record_pairs"] * 2, "Broken NEXUS pairs")
        require(version["identical_request_pairs"] == version["pairs_counted"], "NEXUS request pairing changed")
        require(version["identical_full_plan_steps_pairs"] == 0, "Re-audit NEXUS full-plan difference finding")
    checked = 0
    expected = expected_receipts(keyed)
    seen_paths, seen_urls, cached = set(), set(), {}
    for receipt in priority["receipts"]:
        require(bool(re.fullmatch("[a-f0-9]{64}", receipt["sha256"])), "Invalid digest")
        require(receipt["url"].startswith("https://"), "Invalid receipt URL")
        require(type(receipt["bytes"]) is int and receipt["bytes"] > 0, "Invalid receipt byte count")
        require(receipt["local_cache"] not in seen_paths, "Duplicate receipt cache path: " + receipt["local_cache"])
        require(receipt["url"] not in seen_urls, "Duplicate receipt URL: " + receipt["url"])
        seen_paths.add(receipt["local_cache"])
        seen_urls.add(receipt["url"])
        require(expected.get(receipt["local_cache"]) == receipt["url"], "Unexpected or unpinned source receipt: " + receipt["local_cache"])
        cache = (ROOT / receipt["local_cache"]).resolve()
        require(cache.is_relative_to((ROOT / "data/raw/source-discovery").resolve()), "Unsafe cache path")
        if args.require_cache:
            raw = cache.read_bytes()
            require(len(raw) == receipt["bytes"] and hashlib.sha256(raw).hexdigest() == receipt["sha256"], "Source bytes changed: " + receipt["local_cache"])
            cached[receipt["local_cache"]] = raw
            checked += 1
    require(seen_paths == set(expected), "Missing required source receipts: " + ", ".join(sorted(set(expected) - seen_paths)))
    if args.require_cache:
        verify_cached_records(keyed, cached)
    print(json.dumps({"inventory_entries": saved["unique_inventory_entries"], "audit_files": len(AUDITS), "priority_byte_receipts_verified": checked, "cached_source_findings_recomputed": 5 if args.require_cache else 0, "cache_required": args.require_cache, "network_requests": 0, "inference_requests": 0}))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError) as exc:
        raise SystemExit("Verification failed: " + str(exc)) from None
