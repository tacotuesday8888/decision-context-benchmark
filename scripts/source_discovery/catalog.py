"""Combine source audits without treating duplicate collections as new evidence."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results/source-discovery"
AUDITS = {
    "human-datasets.json": "datasets",
    "benign-training.json": "datasets",
    "agent-datasets.json": "rows",
    "priority-source-inspection.json": "records",
}
NAMES = {
    "nvidia/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1": "NVIDIA agentic indirect prompt injection",
    "ScaleAI/aspi": "ASPI",
    "ppradyoth/AgentInjectionBench": "AgentInjectionBench (ppradyoth)",
    "EliasHossain/nexus-ipi": "NEXUS-IPI",
    "judydnguyen/infuse": "INFUSE",
}


def build():
    sources = {}
    receipts = []
    search_slots = 50  # Root Exa queries: 10 + 10 + 6 + 8 + 8 + 8; not a reviewed-paper count.
    for filename, field in AUDITS.items():
        path = OUT / filename
        doc = json.loads(path.read_text())
        search_slots += doc.get("sources_reviewed", 0)
        receipts.append({"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        for record in doc[field]:
            key = record["id"]
            entry = sources.setdefault(key, {"id": key, "name": record.get("name", NAMES.get(key, key)), "audits": []})
            entry["audits"].append({"path": str(path.relative_to(ROOT)), "record_id": key})
            urls = record.get("inspected_urls", []) + record.get("primary_urls", [])
            urls += [u for u in record.get("urls", {}).values() if isinstance(u, str)]
            if record.get("source_url"):
                urls.append(record["source_url"])
            entry["urls"] = sorted(set(entry.get("urls", []) + urls))
    for repo, name, status, role in [
        ("perplexity-ai/browsesafe-plus-plus", "BrowseSafe++", "Gated files; public card read; actual rows not accessed", "Conditional task-bearing matched-page candidate; train CC BY 4.0, test evaluation-only and hidden labels"),
        ("perplexity-ai/browsesafe-bench", "BrowseSafe original", "Live HF structure/card inspected; original user task not separately exposed", "Candidate-only detector replication/stress; not a task-context confirmation source without additional provenance"),
    ]:
        sources[repo] = {"id": repo, "name": name, "audits": [{"path": "docs/source-discovery/README.md", "record_id": repo}], "urls": ["https://huggingface.co/datasets/" + repo], "availability": status, "intended_role": role}
    result = {
        "audit_date": "2026-10-30",
        "inference_requests": 0,
        "generated_examples": 0,
        "search": {"provider": "Exa", "queries": 15, "requested_result_slots": search_slots, "definition": "Requested search-result slots, including duplicates; not papers fully read or sources independently validated."},
        "unique_inventory_entries": len(sources),
        "workstream_entry_count_before_alias_deduplication": sum(len(json.loads((OUT / f).read_text())[k]) for f, k in AUDITS.items()) + 2,
        "counting_warning": "Inventory entries have unequal evidence and overlap in data. Do not sum their rows, scenarios or variants into an experimental sample size.",
        "audit_file_receipts": receipts,
        "sources": sorted(sources.values(), key=lambda r: r["name"].lower()),
    }
    return result


def main():
    result = build()
    (OUT / "catalog.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    with (OUT / "catalog.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["id", "name", "audit_paths", "primary_urls"], lineterminator="\n")
        writer.writeheader()
        for row in result["sources"]:
            writer.writerow({"id": row["id"], "name": row["name"], "audit_paths": " | ".join(x["path"] for x in row["audits"]), "primary_urls": " | ".join(row["urls"])})
    print(json.dumps({"unique_inventory_entries": result["unique_inventory_entries"], "requested_result_slots": result["search"]["requested_result_slots"]}))


if __name__ == "__main__":
    main()
