# Subscription follow-up accounting

This is a new execution namespace. Closed v7 evidence is read-only. Importing
`scripts.subscription_followup.budget` neither loads credentials nor contacts a
provider. The owner executor must separately validate authorization, exact frozen
request-plan membership/order, route settings, raw evidence and stopping rules.
The ledger supplies bounded accounting and durable once-only dispatch intents;
it does not authorize inference.

## Inherited accounting and money limits

All money uses exact Decimal strings. The sole inherited closure is
`results/study-v7/execution-accounting-v7.0.8.json`, SHA256
`b5601c0cb6365f50ba40ad7ed48e35e16f6b13371c6a1b74b00cf20044655983`.
Its closed journal is `data/raw/study-v7/execution-v1/accounting.jsonl`, SHA256
`1f1df34267511c35addba2591c1def6f4aae1a4d07387f657283b7f75944f3e8`.
The follow-up verifies both byte hashes and the closure's terminal status before
freezing its policy. Old expanded/v3/v4/v6/v7 snapshots are not summed again.

| Provider | Prior conservative cumulative USD | Across-run cumulative cap USD | New authorization available USD |
|---|---:|---:|---:|
| TypeSafe | 7.77900912600000006 | 21.82758493400000006 | 14.048575808 |
| OpenAI | 38.71694205 | 38.71694205 | 0 |

The inherited OpenAI total includes the unchanged **v7** unknown-charge hold
`1.9952816`; new unknown TypeSafe holds in that v7 closure are zero. These are
v7-specific hold figures, not a release or recount of earlier historical unknown
charges: all earlier conservative amounts remain inside the inherited baselines.
The OpenAI total is
informational inherited accounting, not new API allowance. Project-OAuth Sol is
unmetered in this USD journal and consumes a bounded call allowance. Zero new
API dollars does not mean unlimited subscription use or verified quota.

The [official TypeSafe model table](https://docs.typesafe.ai/models), read on
November 1, 2026, lists `jev-1.14.0` at USD0.042 per million input tokens, free
output, default 32,000 tokens per question and 64,000 per request. This runner
admits exactly one question, preserves the default context configuration, and
reserves **USD0.001344 per Jev call** regardless of a tokenizer proxy or short
input. Multi-question and extra top-level context controls are rejected by
`request_spec`. Valid native usage can settle at the exact input price; absent,
invalid or excessive usage retains the entire reservation as unknown usage.
No new transport or pricing inference is used to release a hold.

## Frozen lanes and call limits

One manifest explicitly enables or disables each of these four lanes. Limits
are fixed in code and copied into the immutable policy. Disabled lanes cannot
reserve calls. An isolated-agent lane also needs `pilot_ready:true` and the SHA256
of its separately frozen pilot receipt.

| Lane | Stages and maximum calls | Group limit | Maximum new TypeSafe USD |
|---|---|---:|---:|
| `sol_general` | `preflight`:10 Sol; `main`:4,000 Sol; `repeat`:400 Sol | General batches at most10 Sol each | 0 |
| `blind_audit` | `audit`:100 Sol calls, each reviewing one frozen pair | 100, at most1 Sol each | 0 |
| `second_source` | `secondary`:800 Sol +800 Jev | 100, at most8 Sol +8 Jev each | 1.0752 |
| `isolated_agent` | `actor`:48 Sol; `gate`:24 Jev | 12, at most4 Sol +2 Jev each | 0.032256 |

All enabled maxima total **5,358 Sol and 824 Jev calls**, reserving at most
**USD1.107456 new TypeSafe**, below the available USD14.048575808. Unallocated
headroom does not authorize additional calls or another lane. A disabled lane's
monetary allocation is zero. There is no Jev general/preflight/audit lane, Luna
route, paid Sol route, purchase or billing fallback.

For Sol, only the public `https://api.openai.com/v1/responses` endpoint and the
`existing_project_oauth` credential source are allowed. For Jev, only
`https://api.typesafe.ai/v1/systemone` with `TYPESAFE_API_KEY` is allowed. The
executor must call `validate_route` before loading any credential or dispatching;
its route strings must equal the frozen `ROUTES` mapping. The ledger cannot
inspect a transport's bearer credential and does not itself implement transport.

## Small integration interface

The manifest needs `run_namespace` matching `subscription-followup-*`, a `routes`
object equal to `budget.ROUTES`, and a `lanes` object containing all four names.
Each lane declares an explicit Boolean `enabled`. Optional isolated-agent
activation also declares `pilot_ready` and `pilot_receipt_sha256`. Other manifest
fields can bind the request plan, source selections, authorization and runtime
code; the executor must verify them. The exact manifest bytes are hash-bound to
every group namespace and request key, so changing them cannot reopen this ledger
under another policy.

```python
policy = freeze_policy(
    manifest_path,
    prior_receipt_path=closed_v7_receipt_path,
    prior_journal_path=closed_v7_journal_path,
)
ledger = FollowupLedger(new_journal_path, policy)
spec = request_spec(
    policy, lane="second_source", group_id=group_id, batch_id=batch_id,
    stage="secondary", cell_id=planned_cell_id,
    config="jev_firstparty", payload=frozen_payload,
)
ledger.reserve_group("second_source", group_id, all_group_specs, batch_id=batch_id)
# After independent authorization/plan/stop/deadline checks, before transport:
ledger.mark_dispatched(spec["key"])
# Preserve raw evidence first; None retains the complete unknown-charge hold:
ledger.settle(spec["key"], actual_usd, evidence_sha256=completion_evidence_sha256)
```

`cell_id` is a stable bounded planned identity including source/page/condition.
It may contain identifiers but must never contain source text or credentials.
Distinct cells with identical payload bytes have distinct keys. A preserved cell
cannot be retried or replaced through a fresh batch. The stage distinguishes
primary and repeat cells; use stage-qualified general group IDs, such as
`main:<group>` and `repeat:<group>`, to preserve separate batch allowances.
All members of one source/model group must be supplied together; the runner
validates that complete membership against its frozen request plan before
calling `reserve_group`. The ledger atomically checks exact full-context costs,
provider/lane caps, group size, group count, stage count and identity, then fsyncs
one reservation event. A rejected admission appends no partial reservation.

Cancellation requires immutable unsent evidence and an entry still marked
`reserved`. It releases zero-cost/monetary holds only for positively never-sent
calls. It never releases a `dispatched`, `settled` or `unknown_usage` call, and it
never returns a consumed call/group/stage slot. Neither cancellation nor unknown
usage permits cohort replacement. Terminal settlement evidence is immutable.

## Durable clock, restart and integrity

The first durable dispatch intent starts one **18,000-second** clock. That start
is appended and fsynced before the dispatch intent, which itself is fsynced
before transport. All stages and lanes inherit the same start. Restart does not
reset it. At the deadline, new admission and dispatch stop; prior dispatched
calls may settle afterward, and never-sent reservations may close with evidence.
A backward wall clock cannot move a dispatch before the start or the latest
recorded dispatch. The outer runner owns its monotonic deadline as well.

Every process must use the same ledger path and a separate sole-executor lock.
The reviewed v7/v6 mechanics retain OS flock serialization, canonical hash-chained
append-only events, fsync, unchanged-prefix verification before each group and
full verification on snapshot/restart. Unchanged reads use the reviewed
inode/size/mtime/ctime cache; unexpected file changes fail closed. The prior
receipt/journal and current manifest are SHA-verified on first use or any stat
change. This assumes ordinary local filesystem metadata and cooperative writers,
not an attacker who controls process memory and privileged filesystem metadata.

An interrupted durable dispatch intent is never permission to resend. The runner
may settle it only from immutable evidence for that same key, payload, namespace,
model/revision and first attempt. Without completion evidence it remains held and
must stop dependent collection. A failed first attempt stays the first outcome.
Old initialization, schedule/clock reset, implicit supersession and old-study
continuation APIs are unavailable in this new ledger. Old-study paths cannot be
opened for new writes.

Focused verification uses synthetic temporary files only:
`python3 -m unittest discover -s tests/subscription_followup -p 'test_budget.py'`.
No authentication, catalogue, inference or provider balance check is part of
these tests.
