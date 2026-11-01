"""Prepare released DTap matched episodes without executing benchmark code.

Public acquisition is opt-in. Preparation is offline, outcome blind, preserves
the full published observation strings, and emits source text only under RAW.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re

import yaml

from .data_sources import RAW, ROOT, fetch, sha
from .data_exposure import build_history, norm, screen, grams

REPOSITORY = "AI-secure/DecodingTrust-Agent"
REVISION = "1702810c7fd3496dedd83ecf1e7d455525a334a3"
HF_REPOSITORY = "AI-Secure/DTap-Bench-Agent-Trajectories"
HF_REVISION = "836caf2fdd78b888ddd14fb62dc038e932e17898"
CODE = RAW / "dtap-code"
TRACES = RAW / "dtap-data"
DOMAIN_CHOICES = ("crm", "finance", "legal", "travel", "telecom", "customer-service", "research", "workflow")
SEED = "subscription-followup-dtap-crm-released-v1"
READ_TOOLS = {"channels_history", "conversations_history", "inbox", "dm_feed",
              "get_gmail_content", "list_messages", "get_message", "find_message",
              "search_messages", "get_message_body", "get_record", "get_entry",
              "get_entry_list", "list_records", "search_cases", "search_leads",
              "search_accounts", "search_contacts", "search_opportunities",
              "get_case_by_id", "get_account_by_id", "get_contact_by_id"}


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def pinned_fetch(repository, revision, relative, destination):
    if not destination.exists():
        fetch(f"https://raw.githubusercontent.com/{repository}/{revision}/{relative}", destination)


def configs(domain="crm"):
    prefix = f"benchmark/dtap-bench/{domain}/"
    tree = json.loads((CODE / "tree.json").read_text())
    if tree.get("truncated") or tree["sha"] != REVISION:
        raise ValueError("Need exact complete pinned code inventory")
    return sorted(x["path"] for x in tree["tree"] if x["type"] == "blob"
                  and x["path"].startswith(prefix + "malicious/indirect/")
                  and x["path"].endswith("/config.yaml"))


def environment_steps(config):
    steps = [step for turn in config.get("Attack", {}).get("attack_turns", [])
             for step in turn.get("attack_steps", [])]
    return steps if steps and all(s.get("type") == "environment" for s in steps) else []


def trace_paths(domain="crm"):
    result = []
    for part in ("benign", "malicious/indirect"):
        path = TRACES / (domain + "-" + part.replace("/", "-") + "-tree.json")
        rows = json.loads(path.read_text())
        # Endpoint limit is 1000. These scoped inventories are strictly smaller;
        # the top-level metadata's capped sibling list is never completeness proof.
        if len(rows) >= 1000:
            raise ValueError("Scoped public trajectory inventory may be truncated")
        result.extend(r["path"] for r in rows if r["type"] == "file"
                      and r["path"].endswith(".json")
                      and not r["path"].endswith("/judge_result.json"))
    return sorted(result)


def acquire(domain="crm"):
    """Download only pinned source files; never invoke third-party code."""
    if not (CODE / "tree.json").exists():
        fetch(f"https://api.github.com/repos/{REPOSITORY}/git/trees/{REVISION}?recursive=1", CODE / "tree.json")
    for relative in ("README.md", "LICENSE"):
        pinned_fetch(REPOSITORY, REVISION, relative, CODE / relative)
    if not (TRACES / "README.md").exists():
        fetch(f"https://huggingface.co/datasets/{HF_REPOSITORY}/resolve/{HF_REVISION}/README.md", TRACES / "README.md")
    prefix = f"benchmark/dtap-bench/{domain}/"
    trace_prefix = f"openaisdk/gpt-5.2/{domain}/"
    for part in ("benign", "malicious/indirect"):
        filename = domain + "-" + part.replace("/", "-") + "-tree.json"
        if not (TRACES / filename).exists():
            fetch(f"https://huggingface.co/api/datasets/{HF_REPOSITORY}/tree/{HF_REVISION}/"
                  f"{trace_prefix}{part}?recursive=true&limit=1000", TRACES / filename)
    def get_config(path):
        pinned_fetch(REPOSITORY, REVISION, path, CODE / path)
        return yaml.safe_load((CODE / path).read_text())
    with ThreadPoolExecutor(max_workers=8) as executor:
        parsed = list(executor.map(get_config, configs(domain)))
    paths = trace_paths(domain)
    wanted = set()
    for path, config in zip(configs(domain), parsed):
        if not environment_steps(config):
            continue
        base = config["Task"].get("base_task", "")
        if not re.fullmatch(r"benign/(?:[a-z][a-z0-9_-]*/)?\d+", base):
            continue
        get_config(prefix + base + "/config.yaml")
        attack = path[len(prefix):].removesuffix("/config.yaml")
        for suffix in (base, attack):
            candidates = [x for x in paths if x.startswith(trace_prefix + suffix + "/")]
            # Fixed lexicographic source run; never choose by judge or agent outcome.
            if candidates:
                wanted.add(candidates[0])
    def get_trace(path):
        if not (TRACES / path).exists():
            fetch(f"https://huggingface.co/datasets/{HF_REPOSITORY}/resolve/{HF_REVISION}/{path}", TRACES / path)
    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(get_trace, sorted(wanted)))
    return {"configs": len(parsed), "downloaded_run_paths": len(wanted)}


def text_values(value):
    """Inspect source literals safely for provenance; do not alter candidates."""
    result = []
    def walk(item, depth=0):
        if depth > 8:
            return
        if isinstance(item, str):
            result.append(item)
            if len(item) < 2_000_000 and item.lstrip().startswith(("{", "[")):
                try:
                    child = json.loads(item)
                except (ValueError, TypeError):
                    try:
                        child = ast.literal_eval(item)
                    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                        return
                walk(child, depth + 1)
        elif isinstance(item, dict):
            for child in item.values():
                walk(child, depth + 1)
        elif isinstance(item, list):
            for child in item:
                walk(child, depth + 1)
    walk(value)
    return result


def is_read_tool(name):
    lowered = name.lower()
    if any(term in lowered for term in ("login", "token", "password", "credential", "secret")):
        return False
    return name in READ_TOOLS or bool(re.match(r"(?:get|list|search|read|query|fetch|inspect|view|find)_", lowered))


def calls(episode):
    trace = episode["trajectory"]
    for i, row in enumerate(trace):
        metadata = row.get("metadata", {})
        if row.get("role") != "tool" or not is_read_tool(metadata.get("tool_name", "")):
            continue
        if not isinstance(row.get("state"), str) or i == 0:
            continue
        previous = trace[i - 1]
        call = previous.get("metadata", {})
        if (previous.get("role") != "agent" or call.get("server") != metadata.get("server")
                or call.get("tool_name") != metadata.get("tool_name") or "tool_params" not in call):
            continue
        identity = {k: call[k] for k in ("server", "tool_name", "tool_params")}
        yield i, identity, row["state"]


def align(clean, attack, clean_config, attack_config):
    """One earliest witnessed injection, exact released base link/call/settings."""
    steps = environment_steps(attack_config)
    if not steps:
        return None, "not_environment_only"
    task = attack["task_info"]["original_instruction"]
    if task != clean["task_info"]["original_instruction"]:
        return None, "released_user_instruction_bytes_mismatch"
    if clean_config.get("Attack"):
        return None, "benign_source_configuration_has_attack"
    if not (task.strip() == clean["task_info"]["original_instruction"].strip()
            == attack_config["Task"]["task_instruction"].strip()
            == clean_config["Task"]["task_instruction"].strip()):
        return None, "task_instruction_mismatch"
    if clean_config.get("Agent") != attack_config.get("Agent"):
        return None, "non_environment_agent_configuration_difference"
    if clean["task_info"]["task_id"] != clean_config["Task"]["task_id"] or attack["task_info"]["task_id"] != attack_config["Task"]["task_id"]:
        return None, "released_run_config_identity_mismatch"
    # Exact substantive source attack text must be witnessed in the selected
    # published observation. Source-defined attack condition is the label;
    # utility/security/agent output/judge results are never consulted.
    payloads = [s["kwargs"][k] for s in steps for k in ("message", "body", "text", "content", "prompt", "summary",
                       "summary_inject", "notes_inject", "strategy_prefix", "strategy_inject",
                       "notes_prefix", "notes_replace", "strategy_replace", "settlement_inject",
                       "notes_suffix", "strategy_suffix")
                if isinstance(s.get("kwargs", {}).get(k), str) and len(s["kwargs"][k]) >= 40]
    if not payloads:
        return None, "no_substantive_source_environment_payload"
    clean_calls = list(calls(clean))
    for attack_index, identity, attacked in calls(attack):
        witnessed = [p for p in payloads if any(p in text for text in text_values(attacked))]
        if not witnessed:
            continue
        for clean_index, clean_identity, benign in clean_calls:
            if clean_identity != identity:
                continue
            if any(p in text for p in witnessed for text in text_values(benign)):
                continue
            return {"task": task, "clean": benign, "attack": attacked, "call": identity,
                    "clean_index": clean_index, "attack_index": attack_index,
                    "witnessed_payload_sha256": sorted(sha(p.encode()) for p in witnessed),
                    "incidental_runtime_differences_possible": True}, None
    return None, "no_exact_call_with_witnessed_source_attack"


def prepare(domain="crm"):
    prefix = f"benchmark/dtap-bench/{domain}/"
    trace_prefix = f"openaisdk/gpt-5.2/{domain}/"
    paths = trace_paths(domain)
    candidates = []
    exclusions = Counter()
    for config_path in configs(domain):
        config = yaml.safe_load((CODE / config_path).read_text())
        if not environment_steps(config):
            exclusions["not_environment_only"] += 1
            continue
        base = config["Task"].get("base_task", "")
        if not re.fullmatch(r"benign/(?:[a-z][a-z0-9_-]*/)?\d+", base):
            exclusions["missing_explicit_benign_base_link"] += 1
            continue
        relative = config_path[len(prefix):].removesuffix("/config.yaml")
        selected = []
        for suffix in (base, relative):
            matches = [p for p in paths if p.startswith(trace_prefix + suffix + "/")]
            selected.append(matches[0] if matches else None)
        if None in selected or not all((TRACES / p).is_file() for p in selected):
            exclusions["missing_released_episode"] += 1
            continue
        clean_config_path = prefix + base + "/config.yaml"
        clean_config = yaml.safe_load((CODE / clean_config_path).read_text())
        episodes = [json.loads((TRACES / p).read_text()) for p in selected]
        pair, reason = align(*episodes, clean_config, config)
        if pair is None:
            exclusions[reason] += 1
            continue
        pair.update({"domain": domain, "source_id": relative, "base_task": base,
                     "clean_trace": selected[0], "attack_trace": selected[1],
                     "clean_config": clean_config_path, "attack_config": config_path})
        candidates.append(pair)
    raw_path = RAW / f"dtap-{domain}-matched-candidates-v1.json"
    write_json(raw_path, candidates)
    summary = {"status": "CANDIDATE_PAIRING_ONLY_PENDING_EXPOSURE_COMPONENT_REVIEW",
               "code_revision": REVISION, "trajectory_revision": HF_REVISION,
               "domain": domain, "source_indirect_configs": len(configs(domain)), "faithful_episode_pairs": len(candidates),
               "exclusions": dict(sorted(exclusions.items())),
               "candidate_raw_path": str(raw_path.relative_to(ROOT)),
               "candidate_raw_sha256": sha(raw_path.read_bytes()),
               "no_inference": True, "no_benchmark_code_executed": True}
    write_json(ROOT / f"results/subscription-followup/second-source-dtap-{domain}-pairing.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("acquire", "prepare"))
    parser.add_argument("--domain", choices=DOMAIN_CHOICES, default="crm")
    args = parser.parse_args()
    print(json.dumps(acquire(args.domain) if args.action == "acquire" else prepare(args.domain), sort_keys=True))
