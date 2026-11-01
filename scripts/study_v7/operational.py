"""Read-only, outcome-blind v7 development and source-audit evidence receipts.

No credentials, model clients, forward passes, journal locks or accounting writes.
Classifier correctness is deliberately never calculated. Audit flags are unblinded
model concerns, not established truths or a source-label/selection gate.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import json
import math
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v7.budget import BudgetLedger, PROVIDERS, amount, money, usage_cost
from scripts.study_v7.requests import PANEL, AUDIT_SCHEMA, canonical, digest, materialize

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw/study-v7"
SYSTEMIC = {"model_mismatch", "settings_mismatch", "context_limit_mismatch", "unexpected_cache_usage"}
SOL_UNSUPPORTED = {"subscription_exhausted", "subscription_access_denied", "subscription_unavailable",
    "subscription_quota_exceeded", "subscription_route_unsupported",
    "subscription_model_unavailable", "authentication_error", "http_error", "runtime_error",
    "model_mismatch", "settings_mismatch", "missing_usage", "provider_failed", "invalid_format",
    "interrupted_stream", "interrupted_unknown", "transport_error", "parse_error"}


def _development_reparse_record(request, retained, attempts_directory, *, plan_sha256, manifest_sha256):
    """Narrow v7.0.1 technical resolution, never a new request or relabeling."""
    from scripts.study_v7 import routes
    if (request["config"] != "luna_responses" or request["split"] != "development" or
            request["namespace"] != "first" or request["source"] not in {"browsesafe","promptshield"}):
        raise ValueError("Technical reparse is limited to original Luna Responses development first attempts")
    original=retained["parsed"]
    if (retained["status"] != "settings_mismatch" or original.get("settings_mismatch_fields") != ["prompt_cache_options"] or
            original.get("valid") is not False or
            (original.get("returned_settings") or {}).get("prompt_cache_options") != {"mode":"explicit","ttl":"30m"}):
        raise ValueError("Original failure is outside the fixed default-TTL parser amendment")
    directory=Path(attempts_directory)/request["key"]
    completed=json.loads((directory/"completed.json").read_text())
    if completed.get("parser_version") != "study-v7-routes-1" or routes.PARSER_VERSION != "study-v7-routes-2":
        raise ValueError("Development technical resolution requires the exact v7.0.1 parser versions")
    observation=completed.get("observation")
    if not isinstance(observation,dict):
        raise ValueError("Original technical transport observation is missing")
    response=(directory/"response.raw").read_bytes()
    derived=routes.parse_transport(request["config"],observation,response.decode())
    if derived.get("status") != "ok" or derived.get("valid") is not True:
        raise ValueError("Amended parser did not resolve the retained technical failure")
    if derived.get("usage") != original.get("usage") or derived.get("returned_model") != original.get("returned_model"):
        raise ValueError("Technical reparse changed retained usage/model evidence")
    return {"version":"study-v7-development-reparse-v7.0.1","request_key":request["key"],
        "config":request["config"],"source":request["source"],"split":"development","namespace":"first",
        "plan_sha256":plan_sha256,"amendment_manifest_sha256":manifest_sha256,
        "original_completed_sha256":retained["evidence_sha256"],"original_status":retained["status"],
        "original_parsed_sha256":digest(canonical(original)),"response_raw_sha256":digest(response),
        "request_payload_sha256":request["payload_sha256"],"observation_sha256":digest(canonical(observation)),
        "parser_version":routes.PARSER_VERSION,"parser_code_sha256":digest(Path(routes.__file__).read_bytes()),
        "derived_parsed":derived,"technical_resolution":"unchanged explicit mode; additive provider-default30mTTL",
        "retransmitted":False,"original_records_unchanged":True,"accuracy_calculated":False}


def create_development_reparses(plan, attempts_directory, *, plan_sha256, manifest_sha256, output, journal_path=None):
    """Exclusively create an ignored sidecar from retained raw development bytes."""
    path=Path(output).resolve()
    if RAW.resolve() not in path.parents:
        raise ValueError("Development reparse sidecar must stay in ignored data/raw/study-v7")
    state,_=read_journal(journal_path,plan)
    records=[]
    for request in plan["requests"].values():
        if request["config"] != "luna_responses" or request["split"] != "development" or request["namespace"] != "first":
            continue
        retained=retained_attempt(request,attempts_directory,state)
        if retained["status"] == "settings_mismatch" and retained["parsed"].get("settings_mismatch_fields") == ["prompt_cache_options"]:
            records.append(_development_reparse_record(request,retained,attempts_directory,
                plan_sha256=plan_sha256,manifest_sha256=manifest_sha256))
    if not records:
        raise ValueError("No eligible original development failures to reparse")
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("xb") as handle:
        handle.write(b"".join(canonical(r)+b"\n" for r in sorted(records,key=lambda r:r["request_key"])))
    return records


def load_development_reparses(path, plan, attempts_directory, state, *, plan_sha256, manifest_sha256):
    """Recompute every derived parse and verify all original/hash/scope bindings."""
    if path is None:
        return {},None
    if not manifest_sha256:
        raise ValueError("An explicit preserved amendment-manifest hash is required for reparses")
    path=Path(path).resolve()
    if RAW.resolve() not in path.parents:
        raise ValueError("Development reparse sidecar must remain in ignored data/raw/study-v7")
    body=path.read_bytes();result={}
    for line in body.splitlines():
        record=json.loads(line);key=record["request_key"]
        if key in result or key not in plan["requests"]:
            raise ValueError("Duplicate or unplanned technical reparse")
        request=plan["requests"][key]
        retained=retained_attempt(request,attempts_directory,state)
        expected=_development_reparse_record(request,retained,attempts_directory,
            plan_sha256=plan_sha256,manifest_sha256=manifest_sha256)
        if canonical(record) != canonical(expected):
            raise ValueError("Development reparse differs from exact original/parser/manifest evidence")
        result[key]=record
    return result,{"sidecar_sha256":digest(body),"amendment_manifest_sha256":manifest_sha256,
        "resolved_original_first_attempts":len(result),"original_status_counts":dict(Counter(r["original_status"] for r in result.values())),
        "parser_versions":sorted({r["parser_version"] for r in result.values()}),
        "parser_code_sha256":sorted({r["parser_code_sha256"] for r in result.values()}),"retransmissions":0}


def read_journal(path, plan):
    """Replay a stable byte snapshot through the pure state machine; never lock."""
    if path is None or not Path(path).exists():
        return None, {"verified": False, "reason": "No retained accounting journal supplied"}
    body = Path(path).read_bytes()
    if not body or not body.endswith(b"\n"):
        raise ValueError("Empty or torn accounting journal")
    state, previous = None, "0"*64
    for index, line in enumerate(body.splitlines()):
        event = json.loads(line)
        sha = event.pop("sha256", None)
        if event.get("index") != index or event.get("previous_sha256") != previous or sha != digest(canonical(event)):
            raise ValueError("Accounting hash chain or sequence changed")
        state = BudgetLedger._apply(state, event["kind"], event["data"])
        previous = sha
    totals = {p: Decimal(0) for p in PROVIDERS}
    holds = {p: Decimal(0) for p in PROVIDERS}
    allocations = {a:{p:Decimal(0) for p in PROVIDERS} for a in state["policy"]["allocations_usd"]}
    statuses = Counter()
    for key, entry in state["entries"].items():
        request = plan["requests"].get(key)
        if request is None or entry.get("request_sha256") != request["payload_sha256"] or entry.get("config") != request["config"]:
            raise ValueError("Accounting entry differs from frozen request")
        if entry["provider"] != PANEL[request["config"]]["provider"] or entry["allocation"] != request["allocation"]:
            raise ValueError("Accounting provider/allocation differs from frozen request")
        reserved, accounted = money(entry["reserved_usd"]), money(entry["accounted_usd"])
        if accounted > reserved:
            raise ValueError("Accounted cost exceeds its reservation")
        status = entry["status"]
        if status == "settled" and (entry["actual_usd"] is None or money(entry["actual_usd"]) != accounted):
            raise ValueError("Known settlement has inconsistent exact cost")
        if status in {"unknown_usage", "reserved", "dispatched"} and accounted != reserved:
            raise ValueError("Unknown or pending charge lost its full reservation")
        if status == "unknown_usage" and entry["actual_usd"] is not None:
            raise ValueError("Unknown usage cannot invent an actual cost")
        if entry["provider"] is None and (reserved or accounted):
            raise ValueError("Unmetered route has a monetary charge")
        statuses[status] += 1
        if entry["provider"] is not None:
            totals[entry["provider"]] += accounted
            if entry["allocation"] not in allocations:
                raise ValueError("Unbudgeted accounting allocation")
            allocations[entry["allocation"]][entry["provider"]] += accounted
            if status in {"unknown_usage", "reserved", "dispatched"}:
                holds[entry["provider"]] += accounted
    all_in = {}
    for provider in PROVIDERS:
        all_in[provider] = money(state["policy"]["prior_accounted_usd"][provider])+totals[provider]
        if totals[provider] > money(state["policy"]["incremental_caps_usd"][provider]) or all_in[provider] > money(state["policy"]["provider_caps_usd"][provider]):
            raise ValueError("Conservative accounting exceeds a frozen provider cap")
        if any(values[provider] > money(state["policy"]["allocations_usd"][name][provider]) for name,values in allocations.items()):
            raise ValueError("Conservative accounting exceeds a frozen allocation cap")
    return state, {"verified": True, "journal_sha256": digest(body), "events": len(body.splitlines()),
        "status_counts": dict(statuses), "incremental_accounted_usd": {p: amount(v) for p,v in totals.items()},
        "all_in_accounted_usd": {p: amount(v) for p,v in all_in.items()},
        "unknown_and_pending_holds_usd": {p: amount(v) for p,v in holds.items()},
        "is_invoice_or_balance": False, "read_only_replay": True}


def retained_attempt(request, attempts_directory, state=None):
    """Verify exact retained first/audit evidence without reading its prediction."""
    key = request["key"]
    if len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
        raise ValueError("Invalid request key")
    directory = Path(attempts_directory)/key
    completed, interrupted = directory/"completed.json", directory/"interrupted.json"
    if completed.exists() and interrupted.exists():
        raise ValueError("Conflicting terminal evidence")
    entry = state["entries"].get(key) if state is not None else None
    if completed.exists():
        body = completed.read_bytes()
        result = json.loads(body)
        if result.get("request_sha256") != request["payload_sha256"] or result.get("namespace") != request["namespace"]:
            raise ValueError("Completed payload/namespace changed")
        if result.get("first_attempt_primary") is not (request["namespace"] == "first"):
            raise ValueError("Incorrect first-attempt disposition")
        hashes = result.get("raw_hashes", {})
        if hashes.get("request.json") != request["payload_sha256"]:
            raise ValueError("Missing matching raw request hash")
        for name, sha in hashes.items():
            if Path(name).name != name or not (directory/name).is_file() or digest((directory/name).read_bytes()) != sha:
                raise ValueError("Retained raw evidence hash changed")
        parsed = result.get("parsed")
        if not isinstance(parsed, dict) or not isinstance(parsed.get("status"), str):
            raise ValueError("Missing terminal parser disposition")
        if parsed.get("valid") is True and "response.raw" not in hashes:
            raise ValueError("Valid response lacks retained raw response")
        elapsed = result.get("elapsed_seconds")
        if not isinstance(elapsed, (int,float)) or isinstance(elapsed,bool) or not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError("Invalid retained elapsed time")
        if entry is not None:
            if entry["status"] not in {"settled", "unknown_usage"} or entry["evidence_sha256"] != digest(body):
                raise ValueError("Completed evidence differs from terminal accounting")
            cost = usage_cost(request["config"], parsed.get("usage") or {})
            if entry["status"] == "settled" and (cost is None or money(cost) != money(entry["actual_usd"])):
                raise ValueError("Retained usage cost differs from exact settlement")
        elif state is not None:
            raise ValueError("Completed attempt has no accounting entry")
        payload = json.loads((directory/"request.json").read_text())
        return {"status": parsed["status"], "valid": parsed.get("valid") is True,
                "parsed": parsed, "payload": payload, "elapsed_seconds": elapsed,
                "evidence_sha256": digest(body), "accounting_status": entry["status"] if entry else None}
    if interrupted.exists():
        body = interrupted.read_bytes(); result = json.loads(body)
        if result.get("payload_sha256") != request["payload_sha256"] or result.get("namespace") != request["namespace"]:
            raise ValueError("Interrupted request identity changed")
        if state is not None and (entry is None or entry["status"] != "unknown_usage" or entry["evidence_sha256"] != digest(body)):
            raise ValueError("Interrupted attempt lacks its held unknown charge")
        return {"status": "interrupted_unknown", "valid": False, "parsed": {}, "payload": None,
                "elapsed_seconds": None, "evidence_sha256": digest(body), "accounting_status": "unknown_usage"}
    return {"status": "interrupted_unknown" if (directory/"started.json").exists() else "unattempted",
            "valid": False, "parsed": {}, "payload": None, "elapsed_seconds": None, "evidence_sha256": None,
            "accounting_status": entry["status"] if entry else None}


def settings_check(config, payload, parsed, valid):
    """Inspect requested/returned technical settings only; no labels or answers."""
    p = PANEL[config]
    requested = {"model": p["model"], "route": p["route"]}
    problems, not_echoed = [], []
    if payload is not None:
        if payload.get("model") != p["model"]:
            problems.append("requested_model")
        if p["kind"] == "responses":
            expected = {"reasoning": {"effort":p["reasoning"]}, "store":False,
                "service_tier":"default", "prompt_cache_options":{"mode":"explicit"}, "stream":True}
            if p.get("output_cap") is not None:
                expected["max_output_tokens"] = p["output_cap"]
            elif "max_output_tokens" in payload:
                problems.append("subscription_unsupported_output_cap_requested")
            for field, value in expected.items():
                if payload.get(field) != value:
                    problems.append("requested_"+field)
            schema = (payload.get("text",{}).get("format") or {})
            if schema.get("type") != "json_schema" or schema.get("strict") is not True:
                problems.append("requested_strict_schema")
            requested.update({k:payload.get(k) for k in expected})
            requested["max_output_tokens"] = p.get("output_cap")
            requested["fixed_max_output_supported"] = p.get("output_cap") is not None
            if p.get("output_cap") is None:
                requested["output_limit_status"] = p["output_limit_status"]
            returned = parsed.get("returned_settings") or {}
            for field, expected_value in expected.items():
                if field == "stream":
                    continue
                if returned.get(field) is None:
                    not_echoed.append(field)
                elif field == "prompt_cache_options":
                    cache=returned[field]
                    if (not isinstance(cache,dict) or set(cache)-{"mode","ttl"} or cache.get("mode") != "explicit" or
                            ("ttl" in cache and cache["ttl"] != "30m")):
                        problems.append("returned_"+field)
                elif (returned[field].get("effort") != expected_value["effort"] if field == "reasoning" and isinstance(returned[field],dict) else returned[field] != expected_value):
                    problems.append("returned_"+field)
        elif p["kind"] in {"noul","predicate"}:
            expected_keys = {"model","state","questions"} if p["kind"] == "noul" else {"model","input","questions"}
            if set(payload) != expected_keys:
                problems.append("native_contract_or_unverified_responses_options")
        else:
            for field in ("revision","window_tokens","overlap_tokens","aggregation"):
                requested[field] = p[field]
                if payload.get(field) != p[field]:
                    problems.append("requested_"+field)
    returned_model = parsed.get("returned_model")
    if (valid and returned_model != p["model"]) or (returned_model is not None and returned_model != p["model"]):
        problems.append("returned_model")
    if valid and p["kind"] == "local_detector" and parsed.get("revision") != p["revision"]:
        problems.append("returned_revision")
    usage = parsed.get("usage") or {}
    if valid and p["provider"] is not None:
        n = usage.get("input_tokens")
        if type(n) is not int or not 0 < n <= p["context_tokens"]:
            problems.append("input_usage_or_capacity")
        if p["kind"] == "responses":
            out = usage.get("output_tokens")
            if type(out) is not int or not 0 <= out <= p["output_cap"] or (type(n) is int and n+out > p["context_tokens"]):
                problems.append("output_usage_or_capacity")
        if usage_cost(config, usage) is None:
            problems.append("unpriceable_valid_usage")
    if valid and config == "sol_subscription":
        n, out = usage.get("input_tokens"), usage.get("output_tokens")
        if type(n) is not int or type(out) is not int or n < 1 or out < 0 or n+out > p["context_tokens"]:
            problems.append("subscription_usage_or_capacity")
    return {"requested": requested, "returned_model":returned_model,
            "returned_settings":parsed.get("returned_settings"), "accepted_not_echoed_fields":not_echoed,
            "problems":sorted(set(problems))}


def development_receipt(plan, attempts_directory, *, plan_sha256, journal_path=None, reparses=None, reparse_manifest_sha256=None):
    state, accounting = read_journal(journal_path, plan)
    reparsed,reparse_receipt=load_development_reparses(reparses,plan,attempts_directory,state,
        plan_sha256=plan_sha256,manifest_sha256=reparse_manifest_sha256)
    active = plan.get("active_configurations") or list(plan["model_configurations"])
    requests = [r for r in plan["requests"].values() if r["split"] == "development" and r["namespace"] == "first"]
    by_part = defaultdict(list)
    for request in requests:
        by_part[(request["source"],request["config"])].append(request)
    summaries, validated, unsupported, blockers = [], [], {}, []
    config_rows = defaultdict(list)
    for (source,config), part in sorted(by_part.items()):
        expected = (100 if config == "protectai_local" else 400) if source == "browsesafe" else 100
        if len(part) != expected or len({r["key"] for r in part}) != expected:
            raise ValueError("Development schedule does not preserve exact frozen counts")
        if source == "browsesafe" and len({r["group_id"] for r in part}) != 50:
            raise ValueError("Development main schedule must contain exactly50intact groups")
        if source == "browsesafe":
            groups=defaultdict(set)
            for r in part:
                groups[r["group_id"]].add((r["id"],r["condition"]))
            conditions={"candidate"} if config == "protectai_local" else set(("format","task","reminder","length"))
            if any(len({identity for identity,_ in members}) != 2 or
                   members != {(identity,c) for identity,_ in members for c in conditions} for members in groups.values()):
                raise ValueError("Development main groups must preserve both complete pages and every frozen condition")
        elif source != "promptshield" or len({r["id"] for r in part}) != 100 or len({r["group_id"] for r in part}) != 100:
            raise ValueError("External development requires100unique original requests/components")
        statuses, models, problems, echoes, settings = Counter(), Counter(), Counter(), Counter(), {}
        original_statuses=Counter();resolved=0
        elapsed, input_tokens, output_tokens = [], [], []
        valid = terminal = 0
        evidence_hashes = []
        for request in part:
            retained = retained_attempt(request, attempts_directory, state)
            original_statuses[retained["status"]] += 1
            if request["key"] in reparsed:
                derived=reparsed[request["key"]]["derived_parsed"]
                retained=dict(retained,parsed=derived,status=derived["status"],valid=derived.get("valid") is True)
                resolved += 1
            statuses[retained["status"]] += 1
            valid += retained["valid"]
            terminal += retained["evidence_sha256"] is not None
            checked = settings_check(config,retained["payload"],retained["parsed"],retained["valid"])
            problems.update(checked["problems"])
            echoes.update(checked["accepted_not_echoed_fields"])
            if checked["returned_model"] is not None:
                models[checked["returned_model"]] += 1
            settings[digest(canonical(checked["requested"]))] = checked["requested"]
            if retained["elapsed_seconds"] is not None:
                elapsed.append(retained["elapsed_seconds"])
            usage = retained["parsed"].get("usage") or {}
            for field,destination in (("input_tokens",input_tokens),("output_tokens",output_tokens)):
                if type(usage.get(field)) is int and usage[field] >= 0:
                    destination.append(usage[field])
            if retained["evidence_sha256"]:
                evidence_hashes.append([request["key"],retained["evidence_sha256"]])
        confirmation_count = sum(r["config"] == config and r["source"] == source and r["split"] == "confirmation" and r["namespace"] == "first" for r in plan["requests"].values())
        summary = {"source":source,"config":config,"planned_requests":expected,"terminal_attempts":terminal,
            "valid_responses":valid,"status_counts":dict(statuses),"returned_models":dict(models),
            "original_status_counts":dict(original_statuses),"derived_technical_resolutions":resolved,
            "settings_problems":dict(problems),"accepted_not_echoed_field_counts":dict(echoes),
            "requested_configurations":list(settings.values()),"observed_input_tokens_total":sum(input_tokens),
            "observed_input_tokens_max":max(input_tokens) if input_tokens else None,
            "native_context_capacity_tokens":PANEL[config]["context_tokens"],
            "unsupported_capacity_attempts":statuses["unsupported_over_limit"],
            "local_window_tokens":PANEL[config].get("window_tokens"),
            "unattempted_inputs_trimmed_or_refilled":False,
            "observed_output_tokens_total":sum(output_tokens),"completed_elapsed_seconds_sum":sum(elapsed),
            "completed_elapsed_seconds_mean":statistics.mean(elapsed) if elapsed else None,
            "confirmation_planned_requests":confirmation_count,
            "serial_request_seconds_extrapolation":statistics.mean(elapsed)*confirmation_count if elapsed else None,
            "runtime_limitation":"Sum of request durations, not wall clock; concurrent throughput/rate limits and long-input mix need separate checks.",
            "evidence_set_sha256":digest(canonical(sorted(evidence_hashes)))}
        summaries.append(summary); config_rows[config].append(summary)
    for config in active:
        parts = config_rows[config]
        if {p["source"] for p in parts} != {"browsesafe","promptshield"}:
            raise ValueError("Every active configuration requires both development sources")
        valid_count = sum(p["valid_responses"] for p in parts)
        statuses = Counter()
        for part in parts:
            statuses.update(part["status_counts"])
        problems = any(p["settings_problems"] for p in parts) or any(statuses[s] for s in SYSTEMIC)
        finished = all(p["terminal_attempts"] == p["planned_requests"] for p in parts)
        if config == "sol_subscription" and any(statuses[s] for s in SOL_UNSUPPORTED):
            unsupported[config] = {"reason":"retained_subscription_route_failure_before_complete_development",
                "status_counts":dict(statuses),"remaining_requests_preserved_unattempted":statuses["unattempted"],
                "valid_responses_before_route_failure":valid_count,
                "paid_fallback_used":False,"fixed_max_output_supported":False,"requested_output_cap":None}
        elif valid_count and not problems and finished:
            validated.append(config)
        else:
            blockers.append({"config":config,"valid_responses":valid_count,"all_planned_development_terminal":finished,
                "systemic_settings_or_model_problem":bool(problems),"status_counts":dict(statuses)})
    return {"version":"study-v7-development-validation-1","completed":not blockers and accounting["verified"],
        "plan_sha256":plan_sha256,"validated_configurations":sorted(validated),
        "unsupported_configurations":unsupported,"blockers":blockers,"source_config_coverage":summaries,
        "accounting":accounting,"accuracy_calculated":False,"selection_or_prompts_changed":False,
        "development_technical_reparse":reparse_receipt,
        "recorded_at_utc":datetime.now(timezone.utc).isoformat(),"network_or_model_calls":0}


def audit_receipt(plan, attempts_directory, rows_by_id, *, plan_sha256, journal_path=None, details_output=None):
    state, accounting = read_journal(journal_path, plan)
    requests = [r for r in plan["requests"].values() if r["condition"] == "audit"]
    locked = plan["subsets"]["audit_groups"]
    if len(locked) != 100 or len(set(locked)) != 100 or len(requests) != 100 or {r["group_id"] for r in requests} != set(locked):
        raise ValueError("Audit must preserve exactly100locked confirmation groups")
    counts, statuses, details = Counter(), Counter(), []
    evidence = []
    for request in requests:
        if request["namespace"] != "audit" or request["split"] != "confirmation":
            raise ValueError("Audit is a separate locked namespace")
        body = materialize(request,rows_by_id)
        source = json.loads(body["input"][0]["content"])
        fields = {name:source[name] for name in ("TASK","CLEAN_PAGE","ATTACK_PAGE")}
        retained = retained_attempt(request,attempts_directory,state)
        statuses[retained["status"]] += 1
        checked = settings_check(request["config"],retained["payload"],retained["parsed"],retained["valid"])
        if checked["problems"]:
            counts["technical_settings_problem"] += 1
        case = {"group_id":request["group_id"],"request_key":request["key"],"status":retained["status"]}
        if retained["evidence_sha256"]:
            evidence.append([request["key"],retained["evidence_sha256"]])
        audit = retained["parsed"].get("audit")
        if retained["valid"] and isinstance(audit,dict) and set(audit) == set(AUDIT_SCHEMA["required"]):
            if not all(type(audit[k]) is bool for k in ("task_fidelity","attack_visible","ambiguous")) or not all(isinstance(audit[k],list) and all(isinstance(v,str) for v in audit[k]) for k in ("concerns","evidence_spans")):
                raise ValueError("Retained audit schema changed")
            counts["valid_diagnostic_reviews"] += 1
            for name in ("task_fidelity","attack_visible","ambiguous"):
                counts[name+"_"+str(audit[name]).lower()] += 1
            counts["reported_concern_strings"] += len(audit["concerns"])
            matches = []
            for span in audit["evidence_spans"]:
                locations = [name for name,text in fields.items() if span and span.strip() and span in text]
                counts["literal_spans_verified" if locations else "nonliteral_or_blank_spans"] += 1
                matches.append({"span":span,"matched_source_fields":locations,"literal_quote_verified":bool(locations)})
            if not audit["evidence_spans"]:
                counts["reviews_without_evidence_spans"] += 1
            if any(not m["literal_quote_verified"] for m in matches):
                counts["reviews_with_unverified_spans"] += 1
            case.update(diagnostic=audit,span_validation=matches)
        details.append(case)
    if details_output is not None:
        path = Path(details_output).resolve()
        if RAW.resolve() not in path.parents:
            raise ValueError("Per-case source/audit text must stay in ignored data/raw/study-v7")
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text("".join(json.dumps(c,sort_keys=True,ensure_ascii=False,allow_nan=False)+"\n" for c in details))
    return {"version":"study-v7-audit-diagnostic-1","completed":len(evidence)==100 and accounting["verified"] and not counts["technical_settings_problem"],"plan_sha256":plan_sha256,
        "locked_groups":100,"terminal_attempts":len(evidence),"status_counts":dict(statuses),
        "diagnostic_counts":dict(counts),"evidence_set_sha256":digest(canonical(sorted(evidence))),
        "accounting":accounting,"diagnostic_only":True,"unblinded_ai_reviewer":True,
        "source_labels_preserved":True,"selection_or_prompts_changed":False,"inferred_ground_truth":False,
        "raw_spans_in_aggregate":False,"network_or_model_calls":0}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase",choices=("development","audit"),default="development")
    parser.add_argument("--plan",type=Path,required=True)
    parser.add_argument("--attempts",type=Path,required=True)
    parser.add_argument("--journal",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--source-rows",type=Path,action="append",default=[])
    parser.add_argument("--audit-details",type=Path)
    parser.add_argument("--create-development-reparse",type=Path)
    parser.add_argument("--manifest",type=Path,help="Preserved amended development manifest when creating a sidecar")
    parser.add_argument("--reparses",type=Path)
    parser.add_argument("--reparse-manifest",type=Path,help="Same preserved amended development manifest bound by the sidecar")
    args=parser.parse_args()
    body=args.plan.read_bytes(); plan=json.loads(body)
    def manifest_hash(path):
        if path is None:
            return None
        from scripts.study_v7 import routes
        retained=path.read_bytes();manifest=json.loads(retained)
        if manifest.get("plan_sha256") != digest(body) or manifest.get("execution_code_sha256",{}).get("scripts/study_v7/routes.py") != digest(Path(routes.__file__).read_bytes()):
            raise ValueError("Preserved amendment manifest does not bind this plan and parser code")
        return digest(retained)
    if args.phase == "development":
        if args.create_development_reparse:
            if args.manifest is None or args.reparses is not None:
                raise ValueError("Sidecar creation requires its preserved amendment manifest and no existing --reparses")
            create_development_reparses(plan,args.attempts,plan_sha256=digest(body),
                manifest_sha256=manifest_hash(args.manifest),output=args.create_development_reparse,journal_path=args.journal)
            args.reparses=args.create_development_reparse
            args.reparse_manifest=args.manifest
        result=development_receipt(plan,args.attempts,plan_sha256=digest(body),journal_path=args.journal,
            reparses=args.reparses,reparse_manifest_sha256=manifest_hash(args.reparse_manifest))
    else:
        rows={}
        for path in args.source_rows:
            for line in path.open():
                row=json.loads(line)
                if row["id"] in rows:
                    raise ValueError("Duplicate locked source row")
                rows[row["id"]]=row
        result=audit_receipt(plan,args.attempts,rows,plan_sha256=digest(body),journal_path=args.journal,details_output=args.audit_details)
    output=args.output.resolve()
    if ROOT not in output.parents:
        raise ValueError("Receipt output must remain in the prepared checkout")
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+"\n")


if __name__ == "__main__":
    main()
