# V6 bounded execution

This execution is dependent on `codex/study-v6-review-resolution` at `45de24f2`.
The scientific question, source boundaries and literal prompt contracts remain
those of v6 DESIGN/SOURCES and `scripts/study_v5/prompts.py`. Historical collections,
failed attempts and the separate Laya reproduction are preserved. Nothing here
authorizes public publication, purchases, recharge or a paid Responses fallback.

## Admission and immutable evidence

The full 1,749-row distinct adjudication lock must pass before source development
or confirmation. Run final resolution/planning with `--with-adjudication`, verify
both with `--verify`, and run `verify_resolution.py --with-adjudication
--require-cache`. Only `review-resolution-v3/resolved.jsonl` supplies admission.
Original v1/v2 snapshots and every A/B judgment remain unchanged. Quarantine
unresolved judgments, pair partners and components touched by unresolved links.

`freeze.py prepare` saves exact requests and every row reference below ignored
`data/raw/study-v6/execution-v1/`. Every prepared flag remains false. Development
selects the longest complete candidate in UTF-8 bytes per source/label, ties by
`rank('development:' + id)`, then hash-first distinct groups to at most four rows
per source. Sources without development groups receive no calls. These choices
precede outputs and are for interface/access/coverage checks only.

Freeze code, tests, licensed source/review/adjudication receipts, grouping, splits,
exposure, exact requests, coverage, prices, inherited accounting and this analysis
plan. Commit each freeze before dispatch. Confirmation additionally pins retained
development evidence and the initial byte prefix of the append-only budget journal.
Any scientific change requires a new study version. Operational failures preserve
their first attempt; recovery, if justified, needs a separate linked manifest and
fresh recovery reservations, never editing the original evidence or repeating a
wrong answer. This runner performs no automatic retries.

## Coverage and deduplication

Laya uses its pinned exact assembly/tokenizer audit, including head and truncation
counts. ProtectAI uses its pinned tokenizer and complete candidate coverage with
510-token windows, 64-token overlap and two special tokens; it is candidate-only
on BrowseSafe++, AIB, NVIDIA and INFUSE. It is absent from policy/scope arms.

The hosted routes and native Nimble retain the prior full-input server-validation
approach, now explicitly identified as **server-gated coverage**. Public interfaces
do not expose an exact Jev preflight tokenizer. Complete unchanged requests are
sent without truncation controls or a long-context header; matching native model,
valid usage, accepted terminal status and absence of truncation are required.
Overflow is an unsupported first attempt, never a prediction. This is not a claim
that native token capacity was certified before dispatch. The byte reservation
proxy and another model's tokenizer cannot certify it. Report provisional admission,
actual full-input acceptance, route-specific support, intact sourcepairs and the
common intersection separately. A sourcepair with a known over-limit member is
excluded across all conditions for that route; main native preflight exclusions
apply to both providers and the whole group. Retain planned missingness denominators.

TypeSafe, Responses and the Nimble publisher explicitly document overflow rejection.
The inspected Decisions reference has no explicit overflow/truncation guarantee;
its accepted-input/usage behavior is an additional backend assumption, not proven
by the public documentation. Retain exact sent bytes and native returned usage and
flags, and disclose that limitation rather than infer it from other routes.

Payload hashes isolate configuration and development/confirmation. Identical
payloads within that scope share a first attempt and retain every row/condition
reference, including references excluded because a different pair partner is
unsupported. Only eligible references expand into predictions. A shared payload
is charged to its first actually reserved allocation once, separately recorded
from its original scheduled metadata. No development prediction can
serve confirmation. The literal lexical baseline is frozen to `ignore previous`,
`system prompt`, `do not tell`, `new task` (casefolded substring OR), alongside
constant allow/block. No phrases are added after errors.

## Cost-only execution

Global cumulative caps: OpenAI $15, TypeSafe $20. V6 limits per provider: main $9,
supporting $2, initial development $0.50, recovery $0.50, total $12. Earlier totals
are inherited exactly once from terminal v4 after validating preceding canonical
ledgers; raw export copies and derived analysis ledgers are never summed again.
Four historical unknown-usage reservations remain accounted. These are accounting
limits, not provider balances or permission to spend to the cap.

Current official snapshots are in `price-verification-v1.json`. OpenAI Decisions
base input is $0.10/M, cache read $0.01/M, 30m write $0.125/M and 12h write $0.25/M;
output is free. TypeSafe input is $0.042/M; output is free. Requests retain global
native endpoints/default processing and activate no premium/long-context tier.
The reservation proxy preserves serialized UTF-8 bytes + 4096, with $0.25/M for
OpenAI and $0.084/M for TypeSafe. This revises the older OpenAI 2x proxy to cover
the documented 2.5x cache-write rate. It does not tighten the tokenizer assumption.
Settle TypeSafe from measured input; OpenAI cache details yield a conservative
usage-priced upper/range. Without invoice evidence, never call those exact billed
charges. Unknown usage retains the full original reservation. Input/cache counts
are inclusive, not added twice. A usage/rate/auth/model mismatch stops dispatch.

Freeze all review-cleared main confirmation groups in
`rank('budget-order:' + group)` order. The allocator atomically reserves the next
whole group's four-condition requests for **both** providers under one file lock.
Settle all previous-group attempts before admitting another. Released holds can
extend the cohort beyond the saved up-front reservation prefix. Stop permanently
at the first group that cannot fit either provider; never skip a costly group or
consult predictions/correctness/significance. Report target, attained common
prefix, excluded coverage, unrun groups and planned-denominator bounds.

Supporting groups follow the fixed round-robin AIB/SPML/INFUSE/NVIDIA/scope order,
at most 12 groups per source, then native candidate/scrambled extras on the first
100 main groups. Local/subscription comparators use the first 100 main groups and
the same bounded secondary candidates. Their limits are operationally finite;
no replacement route follows quota failure. One executor lock prevents competing
processes. Every attempt has a durable dispatch intent before any external call.
First streams/partial responses remain raw evidence. A saved systemic STOP blocks
new reservations. Accounting-only closure can preserve interrupted intents as
unknown and cancel positively unsent reservations at zero. Neither permits resend
or silently advancing a failed cohort.

## Local commands after final admission

Use existing `.venv` for ordinary analysis, `.venv-laya` for local model execution
when its pinned dependencies are needed. No new model downloads or upgrades.

```sh
python3 scripts/study_v6/resolve_review.py --with-adjudication
python3 scripts/study_v6/resolved_plan.py --with-adjudication
python3 scripts/study_v6/resolve_review.py --with-adjudication --verify
python3 scripts/study_v6/resolved_plan.py --with-adjudication --verify
python3 scripts/study_v6/verify_resolution.py --with-adjudication --require-cache
.venv/bin/python scripts/study_v6/freeze.py prepare
# Run/review offline verification, then commit code and aggregate receipts.
.venv/bin/python scripts/study_v6/freeze.py freeze-development
# Commit the development freeze before this command.
.venv-laya/bin/python scripts/study_v6/run.py development
# Verify access/parsing/coverage/accounting, then create and commit confirmation freeze.
.venv/bin/python scripts/study_v6/freeze.py freeze-confirmation
.venv/bin/python scripts/study_v6/run.py main
.venv/bin/python scripts/study_v6/run.py supporting
.venv/bin/python scripts/study_v6/run.py comparator --config luna_chat
.venv/bin/python scripts/study_v6/run.py comparator --config astra_chat
.venv-laya/bin/python scripts/study_v6/run.py comparator --config laya_local
.venv-laya/bin/python scripts/study_v6/run.py comparator --config nimble_local
.venv/bin/python scripts/study_v6/run.py comparator --config protectai_local
```

After terminal evidence, independently reparse retained raw responses, verify
journal/terminal dispositions and spending, reproduce analysis/tables/figures and
inspect rendered denominators/intervals. The approximately five-page paper/PDF
requires those gates. Push only intended code/docs/aggregate receipts to a private
dependent draft PR against review resolution and obtain green CI. No stack merges.
