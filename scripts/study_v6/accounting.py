"""Crash-safe v6 reservations, with one cost-only schedule shared by both providers.

The journal is authoritative and append-only. A durable dispatch intent is written
*before* an external call; an interrupted intent is never permission to resend.
Money is serialized as decimal strings. No credential or model response belongs in
this ledger. Raw request/response evidence is owned by the runner.
"""
from __future__ import annotations

from contextlib import contextmanager
import copy
from decimal import Decimal, InvalidOperation
import fcntl
import hashlib
import json
import os
from pathlib import Path
from typing import Callable


PROVIDERS = ("openai", "typesafe")
DEFAULT_CAPS = {"openai": "15", "typesafe": "20"}
DEFAULT_V6_CAPS = {p: "12" for p in PROVIDERS}
DEFAULT_ALLOCATIONS = {name: {p: value for p in PROVIDERS} for name, value in
                       (("main", "9"), ("supporting", "2"),
                        ("development", "0.50"), ("recovery", "0.50"))}
ZERO_HASH = "0" * 64


class AccountingError(ValueError):
    """Evidence is corrupt or an operation conflicts with preserved history."""


class BudgetExceeded(PermissionError):
    """The next complete batch cannot fit its frozen provider allocations."""


class AlreadyDispatched(PermissionError):
    """A previous process might have sent this attempt. Never resend it."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def money(value):
    if isinstance(value, bool):
        raise AccountingError("Boolean is not a monetary amount")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise AccountingError("Invalid monetary amount") from None
    if not result.is_finite() or result < 0:
        raise AccountingError("Money must be finite and nonnegative")
    if result.as_tuple().exponent < -24:
        raise AccountingError("Money exceeds the exact 24-decimal accounting precision")
    return result


def amount(value):
    result = money(value)
    if result == 0:
        return "0"
    literal = format(result, "f")
    return literal.rstrip("0").rstrip(".") if "." in literal else literal


def _read_json(path):
    return json.loads(Path(path).read_text(), parse_float=Decimal)


def _sum(entries, provider):
    return sum((money(e["accounted_usd"]) for e in entries if e["provider"] == provider), Decimal(0))


def reconcile_history(root):
    """Validate inherited totals once, without summing inherited snapshots twice.

    Canonical expanded ledgers feed v3's prior total; v3's closure feeds v4's
    prior total; only the final v4 all-in total is inherited by v6. Analysis
    ledgers are derived tables, and ignored offline exports are historical copies.
    """
    root = Path(root)
    files = {}
    prior = None
    expanded = root / "results/expanded-execution"
    expanded_names = ("check-ledger.json", "execution-ledger-luna_decisions.json",
                      "execution-ledger.json", "local-ledger.json", "openai-ledger-v2.3.json")
    base = {p: Decimal(0) for p in PROVIDERS}
    for name in expanded_names:
        path = expanded / name
        files[str(path.relative_to(root))] = digest(path.read_bytes())
        entries = _read_json(path).get("entries", [])
        if len({e["key"] for e in entries}) != len(entries):
            raise AccountingError("Duplicate canonical expanded ledger key")
        for entry in entries:
            parts = entry["key"].split(":")
            config = parts[1] if len(parts) > 1 else ""
            provider = "typesafe" if config == "jev_firstparty" else "openai" if config in (
                "luna_decisions", "luna_chat", "astra_chat") else None
            value = money(entry["accounted_usd"])
            if provider:
                base[provider] += value
    for stage in ("extension-v3", "controls-v4"):
        folder = root / "results" / stage
        closure_path, ledger_path, plan_path = (folder / name for name in
            ("execution-closure-v1.json", "inference-ledger-v1.json", "request-plan-v1.json"))
        closure, ledger, plan = map(_read_json, (closure_path, ledger_path, plan_path))
        for path in (closure_path, ledger_path, plan_path):
            files[str(path.relative_to(root))] = digest(path.read_bytes())
        if digest(ledger_path.read_bytes()) != closure["ledger_sha256"]:
            raise AccountingError("Historical ledger no longer matches terminal closure")
        if (closure["status"] != "terminal" or closure["pending_reservations"] or
                closure["in_flight_records"] or closure["unattempted_or_missing"]):
            raise AccountingError("Historical experiment is not terminal")
        entries = ledger["entries"]
        if len({e["key"] for e in entries}) != len(entries):
            raise AccountingError("Duplicate historical ledger key")
        for entry in entries:
            if entry["status"] not in ("settled", "unknown_usage"):
                raise AccountingError("Historical reservation remains pending")
            if money(entry["accounted_usd"]) > money(entry["reserved_usd"]):
                raise AccountingError("Historical settlement exceeds reservation")
            if entry["status"] == "unknown_usage" and money(entry["accounted_usd"]) != money(entry["reserved_usd"]):
                raise AccountingError("Historical unknown usage lost its reservation")
        for provider in PROVIDERS:
            # Historical receipts contain binary-float artifacts. Validate at their
            # established tolerance, then inherit the conservative closure literal.
            expected_prior = base[provider] if prior is None else money(prior[provider])
            values = (closure["prior_accounted_usd"][provider], plan["prior_accounted_usd"][provider])
            if any(abs(money(v) - expected_prior) > Decimal("1e-12") for v in values):
                raise AccountingError("Historical inherited totals do not join")
            total = expected_prior + _sum(entries, provider)
            if abs(total - money(closure["all_in_conservative_accounted_usd"][provider])) > Decimal("1e-12"):
                raise AccountingError("Historical all-in accounting mismatch")
        prior = {p: amount(closure["all_in_conservative_accounted_usd"][p]) for p in PROVIDERS}
    latest = _read_json(root / "results/controls-v4/execution-closure-v1.json")
    return {"version": "v6-inherited-accounting-1", "prior_accounted_usd": prior,
            "provider_caps_usd": {p: amount(latest["provider_caps_usd"][p]) for p in PROVIDERS},
            "evidence_sha256": files,
            "retained_unknown_usage_reservations": latest["unknown_usage_reservations_retained"],
            "is_provider_balance": False,
            "scope": "Final v4 all-in total inherited exactly once; expanded and v3 checked as dependencies."}


def verify_history(receipt, root):
    """Reject changed inherited evidence or unexpected new canonical spend ledgers."""
    root = Path(root)
    expected = receipt["evidence_sha256"]
    for name, sha in expected.items():
        if digest((root / name).read_bytes()) != sha:
            raise AccountingError("Historical accounting evidence changed: " + name)
    known_ledgers = {name for name in expected if "ledger" in Path(name).name}
    for path in (root / "results").glob("*/*ledger*.json"):
        if str(path.relative_to(root)) not in known_ledgers:
            raise AccountingError("Unreconciled canonical ledger: " + str(path.relative_to(root)))


def _request(spec):
    allowed = {"key", "provider", "reserved_usd", "request_sha256", "config", "split"}
    if set(spec) - allowed or not {"key", "provider", "reserved_usd", "request_sha256"} <= set(spec):
        raise AccountingError("Reservation requires key/provider/amount/payload hash only")
    result = dict(spec, reserved_usd=amount(spec["reserved_usd"]))
    if not isinstance(result["key"], str) or not result["key"]:
        raise AccountingError("Missing attempt key")
    if result["provider"] not in (*PROVIDERS, None):
        raise AccountingError("Unknown provider")
    if result["provider"] is None and money(result["reserved_usd"]) != 0:
        raise AccountingError("Unmetered route has a monetary reservation")
    sha = result["request_sha256"]
    if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
        raise AccountingError("Missing exact request SHA-256")
    return result


def _requests(specs):
    rows = [_request(s) for s in specs]
    if not rows or len({r["key"] for r in rows}) != len(rows):
        raise AccountingError("Empty batch or duplicate request key")
    return rows


def _policy(prior_receipt, caps, v6_caps, allocations):
    prior = {p: amount(prior_receipt["prior_accounted_usd"][p]) for p in PROVIDERS}
    caps = {p: amount((caps or DEFAULT_CAPS)[p]) for p in PROVIDERS}
    v6_caps = {p: amount((v6_caps or DEFAULT_V6_CAPS)[p]) for p in PROVIDERS}
    allocations = {a: {p: amount(v[p]) for p in PROVIDERS}
                   for a, v in (allocations or DEFAULT_ALLOCATIONS).items()}
    if set(allocations) != set(DEFAULT_ALLOCATIONS):
        raise AccountingError("All four frozen allocations are required")
    for p in PROVIDERS:
        if money(caps[p]) > money(DEFAULT_CAPS[p]) or money(caps[p]) > money(prior_receipt.get("provider_caps_usd", DEFAULT_CAPS)[p]):
            raise AccountingError("Global cap cannot increase")
        if money(v6_caps[p]) > money(DEFAULT_V6_CAPS[p]):
            raise AccountingError("V6 cap cannot increase")
        if money(prior[p]) > money(caps[p]):
            raise AccountingError("Inherited accounting already exceeds global cap")
        for a in allocations:
            if money(allocations[a][p]) > money(DEFAULT_ALLOCATIONS[a][p]):
                raise AccountingError("Allocation cannot increase")
        if sum((money(allocations[a][p]) for a in allocations), Decimal(0)) > money(v6_caps[p]):
            raise AccountingError("Allocations exceed v6 operational cap")
    return {"prior_accounted_usd": prior, "provider_caps_usd": caps,
            "v6_caps_usd": v6_caps, "allocations_usd": allocations,
            "prior_receipt": prior_receipt}


class BudgetLedger:
    """One journal, one OS lock, no implicit retries or prediction-aware decisions.

    Reopen with just a path after initialization. Pass history_root to verify all
    inherited evidence before reservations and dispatch; production execution must
    do so. The optional guard provides an additional external-state gate and must
    be read-only. All caller-supplied keys must identify an exact attempt, never a
    row whose payload can later change.
    """
    def __init__(self, path, prior_receipt=None, *, caps=None, v6_caps=None,
                 allocations=None, history_root=None, guard: Callable | None = None):
        self.path = Path(path)
        self.lock_path = self.path.with_name(self.path.name + ".lock")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.history_root, self.guard = history_root, guard
        self._cache = None
        with self._locked() as state:
            if state is None:
                if prior_receipt is None:
                    raise AccountingError("Missing initialized journal or inherited receipt")
                policy = _policy(prior_receipt, caps, v6_caps, allocations)
                self._append(None, "initialize", {"policy": policy})
            elif prior_receipt is not None:
                policy = _policy(prior_receipt, caps, v6_caps, allocations)
                if state["policy"] != policy:
                    raise AccountingError("Initialized accounting policy is immutable")

    @contextmanager
    def _locked(self):
        with self.lock_path.open("a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield self._read()
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def _read(self):
        if not self.path.exists():
            self._cache = None
            return None
        body = self.path.read_bytes()
        if not body or not body.endswith(b"\n"):
            raise AccountingError("Empty or torn journal; preserve evidence, do not repair silently")
        # Rehash the complete retained prefix, but replay only new events. This
        # preserves corruption detection without reparsing a large frozen request
        # schedule before every dispatch. Multiple processes still serialize on
        # the OS lock and validate every appended event.
        state, start, index = None, 0, 0
        if self._cache is not None:
            size, old_hash, cached_state = self._cache
            if len(body) < size:
                raise AccountingError("Journal shrank; preserved accounting was removed")
            if digest(body[:size]) != old_hash:
                raise AccountingError("Retained journal prefix changed")
            state, start, index = cached_state, size, cached_state["events"]
        self._cache = None
        for i, line in enumerate(body[start:].splitlines(), index):
            try:
                event = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                raise AccountingError("Unreadable journal event") from None
            sha = event.pop("sha256", None)
            if sha != digest(canonical(event)) or event["index"] != i:
                raise AccountingError("Journal hash or sequence changed")
            if event["previous_sha256"] != (ZERO_HASH if state is None else state["head_sha256"]):
                raise AccountingError("Journal chain broken")
            state = self._apply(state, event["kind"], event["data"])
            state["head_sha256"], state["events"] = sha, i + 1
        self._cache = (len(body), digest(body), state)
        return state

    @staticmethod
    def _apply(state, kind, data):
        if state is None:
            if kind != "initialize":
                raise AccountingError("Journal has no initialization")
            policy = data["policy"]
            checked = _policy(policy["prior_receipt"], policy["provider_caps_usd"],
                              policy["v6_caps_usd"], policy["allocations_usd"])
            if policy != checked:
                raise AccountingError("Invalid immutable policy")
            return {"policy": policy, "entries": {}, "batches": {}, "schedules": {}, "continuations": {}}
        if kind == "register_schedule":
            allocation = data["allocation"]
            if allocation in state["schedules"]:
                raise AccountingError("Schedule registered twice")
            state["schedules"][allocation] = {"groups": data["groups"], "admitted": 0, "stopped": None}
        elif kind == "reserve":
            batch_id = data["batch_id"]
            if batch_id in state["batches"]:
                raise AccountingError("Duplicate batch event")
            for row in data["new_requests"]:
                if row["key"] in state["entries"]:
                    raise AccountingError("Duplicate reservation event")
                state["entries"][row["key"]] = dict(row, allocation=data["allocation"],
                    status="reserved", accounted_usd=row["reserved_usd"], actual_usd=None,
                    evidence_sha256=None)
            state["batches"][batch_id] = {k: v for k, v in data.items() if k != "new_requests"}
            if data.get("group") is not None:
                schedule = state["schedules"][data["allocation"]]
                if schedule["groups"][schedule["admitted"]]["group"] != data["group"]:
                    raise AccountingError("Reservation skipped the frozen order")
                schedule["admitted"] += 1
        elif kind == "dispatch":
            entry = state["entries"][data["key"]]
            if entry["status"] != "reserved":
                raise AccountingError("Duplicate durable dispatch intent")
            entry["status"] = "dispatched"
        elif kind == "settle":
            entry = state["entries"][data["key"]]
            if entry["status"] != "dispatched":
                raise AccountingError("Settlement is not linked to a dispatch")
            entry.update(status="unknown_usage" if data["actual_usd"] is None else "settled",
                         accounted_usd=entry["reserved_usd"] if data["actual_usd"] is None else data["actual_usd"],
                         actual_usd=data["actual_usd"], evidence_sha256=data["evidence_sha256"])
        elif kind == "cancel_reserved":
            entry = state["entries"][data["key"]]
            if entry["status"] != "reserved":
                raise AccountingError("Only an undispatched reservation can be cancelled")
            entry.update(status="cancelled_unsent", actual_usd="0", accounted_usd="0",
                         evidence_sha256=data["evidence_sha256"], cancellation_reason=data["reason"])
        elif kind == "cost_stop":
            schedule = state["schedules"][data["allocation"]]
            if schedule["stopped"] is not None:
                raise AccountingError("Duplicate schedule stop")
            schedule["stopped"] = data
        elif kind == "continuation":
            key = data["failed_key"]
            entry = state["entries"][key]
            if key in state["continuations"] or entry["status"] not in ("settled", "unknown_usage"):
                raise AccountingError("Continuation requires a unique terminal first-attempt failure")
            if entry["evidence_sha256"] != data["failure_evidence_sha256"]:
                raise AccountingError("Continuation failure evidence differs from terminal accounting")
            state["continuations"][key] = data
        else:
            raise AccountingError("Unknown journal event")
        return state

    def _append(self, state, kind, data):
        event = {"index": 0 if state is None else state["events"],
                 "previous_sha256": ZERO_HASH if state is None else state["head_sha256"],
                 "kind": kind, "data": data}
        event["sha256"] = digest(canonical(event))
        line = canonical(event) + b"\n"
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            written = os.write(fd, line)
            if written != len(line):
                raise AccountingError("Partial journal write; preserve torn evidence")
            os.fsync(fd)
        finally:
            os.close(fd)
        # Persist creation of the directory entry as well as the journal bytes.
        directory = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        # _read validates the newly appended tail and updates the local cache.
        return self._read()

    def _check_guard(self, state):
        if self.history_root is not None:
            verify_history(state["policy"]["prior_receipt"], self.history_root)
        if self.guard is not None:
            self.guard()

    @staticmethod
    def _totals(state):
        policy = state["policy"]
        entries = list(state["entries"].values())
        incremental = {p: _sum(entries, p) for p in PROVIDERS}
        by_allocation = {a: {p: _sum([e for e in entries if e["allocation"] == a], p)
                            for p in PROVIDERS} for a in policy["allocations_usd"]}
        return incremental, by_allocation

    def snapshot(self):
        with self._locked() as state:
            incremental, by_allocation = self._totals(state)
            return dict(copy.deepcopy(state), incremental_accounted_usd={p: amount(v) for p, v in incremental.items()},
                allocation_accounted_usd={a: {p: amount(v) for p, v in values.items()} for a, values in by_allocation.items()},
                all_in_accounted_usd={p: amount(money(state["policy"]["prior_accounted_usd"][p]) + incremental[p]) for p in PROVIDERS},
                terminal=not any(e["status"] in ("reserved", "dispatched") for e in state["entries"].values()))

    def register_schedule(self, allocation, groups):
        if allocation not in ("main", "supporting"):
            raise AccountingError("Only main/supporting use ordered group schedules")
        groups = [{"group": g["group"], "requests": _requests(g["requests"])} for g in groups]
        if len({g["group"] for g in groups}) != len(groups) or any(not isinstance(g["group"], str) or not g["group"] for g in groups):
            raise AccountingError("Schedule groups must be unique nonempty identities")
        for group in groups:
            if {r["provider"] for r in group["requests"] if r["provider"] is not None} != set(PROVIDERS):
                raise AccountingError("Each paid group must cover both native providers")
        with self._locked() as state:
            self._check_guard(state)
            if allocation in state["schedules"]:
                if state["schedules"][allocation]["groups"] != groups:
                    raise AccountingError("Frozen schedule changed")
                return copy.deepcopy(state["schedules"][allocation])
            state = self._append(state, "register_schedule", {"allocation": allocation, "groups": groups})
            return copy.deepcopy(state["schedules"][allocation])

    def _reserve(self, state, batch_id, allocation, requests, group=None):
        references = [r["key"] for r in requests]
        proposed = {"batch_id": batch_id, "allocation": allocation, "group": group,
                    "request_keys": references, "requests_sha256": digest(canonical(requests))}
        if batch_id in state["batches"]:
            if state["batches"][batch_id] != proposed:
                raise AccountingError("Existing batch identity changed")
            return copy.deepcopy(state["batches"][batch_id])
        new = []
        for request in requests:
            previous = state["entries"].get(request["key"])
            if previous is not None:
                if any(previous.get(k) != v for k, v in request.items()):
                    raise AccountingError("Attempt key reused across payload/provider/configuration/split")
                if previous["allocation"] != allocation:
                    if {previous["allocation"], allocation} != {"main", "supporting"}:
                        raise AccountingError("Development/recovery attempts cannot share confirmation reservations")
                    if (request.get("split") != "confirmation" or
                            previous.get("split") != "confirmation" or
                            not request.get("config") or previous.get("config") != request["config"]):
                        raise AccountingError("Cross-allocation sharing requires an exact confirmation configuration/split")
                # Shared exact payloads may be referenced by multiple whole groups;
                # the first allocation owns the charge. Development never feeds
                # confirmation, and recovery never reuses a first-attempt key.
            else:
                new.append(request)
        increment, by_allocation = self._totals(state)
        policy = state["policy"]
        reasons = []
        for p in PROVIDERS:
            addition = sum((money(r["reserved_usd"]) for r in new if r["provider"] == p), Decimal(0))
            if money(policy["prior_accounted_usd"][p]) + increment[p] + addition > money(policy["provider_caps_usd"][p]):
                reasons.append(p + ":global_cap")
            if increment[p] + addition > money(policy["v6_caps_usd"][p]):
                reasons.append(p + ":v6_cap")
            if by_allocation[allocation][p] + addition > money(policy["allocations_usd"][allocation][p]):
                reasons.append(p + ":" + allocation + "_allocation")
        if reasons:
            raise BudgetExceeded(", ".join(reasons))
        return copy.deepcopy(self._append(state, "reserve", dict(proposed, new_requests=new))["batches"][batch_id])

    def reserve_batch(self, batch_id, allocation, requests):
        if allocation not in ("development", "recovery"):
            raise AccountingError("Main/supporting reservations must follow their whole-group schedule")
        requests = _requests(requests)
        with self._locked() as state:
            self._check_guard(state)
            return self._reserve(state, batch_id, allocation, requests)

    def reserve_unmetered_batch(self, batch_id, requests):
        """Journal local/subscription attempts without changing paid group order.

        These records use the supporting accounting bucket with exactly zero
        money; the runner retains their scientific comparator allocation. No
        request on a paid route may enter through this path.
        """
        requests = _requests(requests)
        if any(r["provider"] is not None or money(r["reserved_usd"]) != 0 for r in requests):
            raise AccountingError("Unmetered dispatch journal only accepts zero-cost non-provider attempts")
        with self._locked() as state:
            self._check_guard(state)
            return self._reserve(state, batch_id, "supporting", requests)

    def reserve_next_group(self, allocation):
        """Reserve the next whole group, or permanently record a cost-only stop.

        Previous-group attempts must be terminal, so a denied next group cannot
        later become affordable through a delayed release. The returned status is
        admitted/stopped/complete. Predictions and labels are never inputs.
        """
        if allocation not in ("main", "supporting"):
            raise AccountingError("Unknown ordered allocation")
        with self._locked() as state:
            self._check_guard(state)
            schedule = state["schedules"][allocation]
            if schedule["stopped"] is not None:
                return {"status": "stopped", **copy.deepcopy(schedule["stopped"])}
            index = schedule["admitted"]
            if index:
                previous_group = schedule["groups"][index - 1]
                if any(state["entries"][r["key"]]["status"] == "cancelled_unsent" for r in previous_group["requests"]):
                    raise AccountingError("Cancelled unsent attempts close a stopped batch; do not advance the cohort")
                unsettled = [r["key"] for r in previous_group["requests"] if state["entries"][r["key"]]["status"] in ("reserved", "dispatched")]
                if unsettled:
                    raise AccountingError("Previous whole group is not terminal; resume its preserved attempts")
            if index == len(schedule["groups"]):
                return {"status": "complete", "admitted_groups": index}
            group = schedule["groups"][index]
            try:
                batch = self._reserve(state, allocation + ":group:" + group["group"], allocation,
                                      group["requests"], group["group"])
            except BudgetExceeded as error:
                stop = {"allocation": allocation, "group": group["group"], "index": index,
                        "reason": str(error), "unrun_groups": len(schedule["groups"]) - index}
                self._append(state, "cost_stop", stop)
                return {"status": "stopped", **stop}
            return {"status": "admitted", "index": index, **batch}

    def mark_dispatched(self, key):
        with self._locked() as state:
            self._check_guard(state)
            if state["entries"][key]["status"] != "reserved":
                raise AlreadyDispatched("Attempt is no longer an undispatched reservation: " + key)
            return dict(self._append(state, "dispatch", {"key": key})["entries"][key])

    def cancel_reserved(self, key, evidence_sha256):
        """Close a positively never-dispatched attempt after execution has stopped.

        The caller must retain immutable evidence proving no dispatch occurred and
        its global stop. A durable dispatch intent forbids cancellation even when
        the caller suspects that the network call never started. Released holds
        must never be used to choose a different cohort after a systemic failure.
        """
        if (not isinstance(evidence_sha256, str) or len(evidence_sha256) != 64 or
                any(c not in "0123456789abcdef" for c in evidence_sha256)):
            raise AccountingError("Cancellation requires an exact immutable unsent-evidence hash")
        with self._locked() as state:
            entry = state["entries"][key]
            if entry["status"] == "cancelled_unsent":
                if entry["evidence_sha256"] != evidence_sha256:
                    raise AccountingError("Unsent cancellation evidence is immutable")
                return dict(entry)
            if entry["status"] != "reserved":
                raise AccountingError("Cannot cancel an attempt with a preserved dispatch intent")
            return dict(self._append(state, "cancel_reserved", {
                "key": key, "evidence_sha256": evidence_sha256,
                "reason": "positively_not_dispatched_after_execution_stop"})["entries"][key])

    def settle(self, key, actual_usd=None, *, evidence_sha256=None):
        actual = None if actual_usd is None else amount(actual_usd)
        if evidence_sha256 is not None and (not isinstance(evidence_sha256, str) or len(evidence_sha256) != 64 or
                any(c not in "0123456789abcdef" for c in evidence_sha256)):
            raise AccountingError("Invalid raw evidence hash")
        with self._locked() as state:
            entry = state["entries"][key]
            if actual is not None and money(actual) > money(entry["reserved_usd"]):
                raise AccountingError("Usage exceeds reservation; stop and retain the full hold")
            if entry["status"] in ("settled", "unknown_usage"):
                if entry["actual_usd"] != actual or entry["evidence_sha256"] != evidence_sha256:
                    raise AccountingError("Terminal accounting evidence is immutable")
                return dict(entry)
            if entry["status"] != "dispatched":
                raise AccountingError("No durable dispatch intent for settlement")
            return dict(self._append(state, "settle", {"key": key, "actual_usd": actual,
                                "evidence_sha256": evidence_sha256})["entries"][key])

    def record_continuation(self, failed_key, *, failure_record, failure_evidence_sha256,
                            stop_sha256, manifest_sha256, manifest_path,
                            receipt_path, receipt_sha256, activated_at_epoch):
        """Journal reviewed continuation of remaining first attempts, never a retry.

        The activation module independently validates retained native bytes,
        committed receipt, frozen scope, cooldown and archived stop. This final
        ledger gate additionally rejects any valid prediction and binds the exact
        terminal raw first attempt. No reservation or settlement is changed.
        """
        hashes = (failure_evidence_sha256, stop_sha256, manifest_sha256, receipt_sha256)
        if any(not isinstance(v, str) or len(v) != 64 or any(c not in "0123456789abcdef" for c in v) for v in hashes):
            raise AccountingError("Continuation evidence requires exact SHA-256 values")
        for value in (manifest_path, receipt_path):
            if not isinstance(value, str) or Path(value).is_absolute() or ".." in Path(value).parts:
                raise AccountingError("Continuation evidence paths must stay inside the project")
        if isinstance(activated_at_epoch, bool) or not isinstance(activated_at_epoch, (int, float)) or not money(activated_at_epoch) > 0:
            raise AccountingError("Continuation requires an explicit activation time")
        if digest(canonical(failure_record) + b"\n") != failure_evidence_sha256:
            raise AccountingError("Continuation does not bind the exact retained failure record")
        parsed = failure_record.get("result", {}).get("parsed", {})
        observation = failure_record.get("result", {}).get("observation", {})
        http = observation.get("http_status")
        interrupted = (parsed.get('status') == 'interrupted_unknown' and
            failure_record.get('result', {}).get('interrupted_dispatch_intent_preserved') is True and
            not failure_record.get('result', {}).get('reserved_raw_conflict_retained') and
            {'request.json', 'started.json'} <= set(failure_record.get('result', {}).get('raw_hashes', {})))
        transport = (parsed.get('status') in ('transport_error', 'http_error') and
            type(http) is int and http in (0, 200, 500, 502, 503, 504) and
            (http not in (0, 200) or bool(observation.get('transport_exit_code'))) and
            (http != 200 or parsed.get('status') == 'transport_error'))
        if (failure_record.get("key") != failed_key or failure_record.get("attempt") != 0 or
                failure_record.get("first_attempt_primary") is not True or
                failure_record.get("result", {}).get("stop_required") is not True or
                parsed.get("valid") is not False or parsed.get("prediction") is not None or
                parsed.get("score") is not None or not (transport or interrupted)):
            raise AccountingError("Only an invalid transient transport first attempt can permit continuation")
        data = dict(failed_key=failed_key, failure_evidence_sha256=failure_evidence_sha256,
                    stop_sha256=stop_sha256, manifest_sha256=manifest_sha256,
                    manifest_path=manifest_path, receipt_path=receipt_path, receipt_sha256=receipt_sha256,
                    activated_at_epoch=activated_at_epoch)
        with self._locked() as state:
            self._check_guard(state)
            entry = state["entries"][failed_key]
            if entry["status"] not in ("settled", "unknown_usage") or entry["evidence_sha256"] != failure_evidence_sha256:
                raise AccountingError("Continuation requires the unchanged terminal failure and retained hold")
            if failed_key in state["continuations"]:
                old = state["continuations"][failed_key]
                if any(old[k] != data[k] for k in data if k != 'activated_at_epoch'):
                    raise AccountingError("A failed first attempt already has a different immutable continuation")
                return dict(old)
            return dict(self._append(state, "continuation", data)["continuations"][failed_key])
