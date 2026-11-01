# Overnight experiment coordination

Updated 2026-11-01 06:10 UTC. This is an operational record, not a manuscript or a new frozen protocol.

## Current user instructions

- Work autonomously through 2026-11-01 16:06 UTC (11:06 AM America/New_York), with hourly supervision.
- Experiments are authorized now; the earlier pause is revoked. Finish readiness checks, then development, freeze, confirmation and verified analysis in order.
- The discussed incremental ceiling was $395: OpenAI experiments $350, optional coding help $25, TypeSafe $20. These are limits, not targets or confirmed available balances.
- Latest routing restriction supersedes permission to spend that full allocation: cheap models through API, Jev through its native API, expensive models/work through existing subscription. Do not schedule paid Sol Responses evaluation or paid coding assistance. If no supported reproducible subscription evaluation route exists, defer the expensive comparator and proceed with the other models.
- If credits run out, preserve progress and resume when legitimate allowances reset. This does not authorize purchases, recharge, bypassing limits, clearing evidence or duplicate paid requests. Record actual reset timing only when verified.
- Official Codex usage check at approximately 06:11 UTC: 8% used, 92% remains; ONE existing free full reset available. User explicitly authorized this reset if needed. Root alone coordinates redemption with `consume_usage_reset`; workers must not redeem independently. Tool eligibility requires <=10% remaining in the five-hour or weekly window. Use stable idempotency key `01a18da8-20261101-overnight-reset-1` for this one logical attempt and record outcome. No reset has been consumed by this coordinator. This does not refill API credit. Further resets require separate explicit confirmation per tool instructions.
- Do not draft the paper, LaTeX or final manuscript PDF. Analysis, methods notes, checked tables and figures are allowed. No publication/submission, purchases or billing changes.
- Additional broad literature research is optional; prioritize useful data and execution work.

## Single execution owner

Working chat: **Prepare the expanded experiment**, ID `01a195ae-3adc-7c80-beab-361bfab5e741`, host `local`, GPT-6.1 Sol Ultra.

Working checkout: `/Users/langqi/Developer/Projects/Decision Context Benchmark Plan`.

Root coordination checkout: `/Users/langqi/Developer/Projects/Decision Context Benchmark Research`, branch `codex/overnight-research`.

Canonical frozen older studies: `/Users/langqi/Developer/Projects/Decision Context Benchmark`. Do not restart old executor chats or run competing model calls. The user explicitly authorizes messages guiding the active working chat.

Last compact status cursor: `48e27ee0-0d56-4e05-98f1-457d179d0219:8`. Worker active; latest reported preparation/statistical checks underway and paid-run authorization received. Cheap-API/expensive-subscription update and credit-reset update were delivered afterward. No new experimental result or spend is yet independently verified by this coordinator.

## Plan and readiness

Saved plan package is `docs/next-study/{PLAN,PROTOCOL,REVIEW,HANDOFF}.md`; private draft PR 12: https://github.com/tacotuesday8888/decision-context-benchmark/pull/12 . Plan commit `7a35915e438e5f17f2262595bae59b0838c68e31`; 20 CI checks passed at initial delivery. Later user instructions above supersede the original offline-only handoff.

Planned main data: 3,000 fresh BrowseSafe++ groups, one benign/attack pair each (6,000 pages), plus separate development data. External PromptShield: 4,000 balanced test requests, nested 1,000-request general-model subset, 100 validation requests. These are targets until worker verifies final eligibility and manifests.

Cheap/native comparison: Jev, Luna Decisions, Luna Responses, local published ProtectAI detector. Sol subscription comparator only if a valid reproducible route exists. Native and Responses routes must stay separately identified. Do not present chat subscription and API results as equivalent configurations.

Four main conditions: actual task, format-only, generic warning and length control. Keep candidate fixed. Freeze before confirmation. Preserve source-label disagreements and technical failures. No outcome-dependent filtering. Save raw outputs and usage; one ledger/executor, safe restart IDs, complete-group comparisons, missing-result bounds.

Historical conservative accounting before new work: OpenAI $7.02755920 and TypeSafe $1.827584934, including unresolved holds. Reconcile actual ledger rather than treating these as invoices or remaining credit. Prior $343.48 stress scenario included paid Sol and is obsolete for the newly restricted panel; worker must recompute cost. No promise that all work will consume the cap.

## Literature helpers

Two existing helpers are finishing focused notes only:
- `overnight_decision_papers` owns `decision-model-papers.md`.
- `overnight_detector_papers` owns `detector-papers.md`.

Both were told the latest routing/reset instructions and to avoid expanding the reading list. Read final files before relying on detailed findings. Preliminary material corrections: newer JevOut includes blinded human review; prior work already studies task-aware detection; Nudge's released flips-first subset cannot estimate natural attack prevalence. These narrow novelty claims without invalidating this controlled experiment.

## Supervision

### Verified checkpoint, approximately 06:16 UTC

Research notes committed as `5a3c74ef` and pushed in private draft PR 13 (base `codex/research-plan-update`); all 20 CI jobs passed. Both literature helpers completed their assigned notes. No experimental result is claimed by their reviews.

Worker acknowledged cheap-API/expensive-subscription routing and confirmed no paid Sol calls had run. Its subscription configuration cannot preserve the original API output-token cap, so any such comparison requires explicit route documentation. Worker remains live; latest observed cursor `48e27ee0-0d56-4e05-98f1-457d179d0219:16`.

External selection v3 now includes every individual historical AIB message in its exposure screen (20,167 historical unique inputs versus 20,117 previously). Compared v2/v3 selected IDs: zero additions/removals, still 4,100 unique groups and the planned balanced counts. The saved v2 inspection remains a historical check, not a checksum attestation for v3. At this check the execution authorization JSON was still unpopulated pending readiness; this is not a user pause or missing permission.

### Main sample and request plan ready, approximately 06:23 UTC

The long-running main preparation process ended successfully and produced `results/study-v7/main-selection.json` in the worker checkout. Root independently checked 3,200 unique groups and 6,400 unique page IDs, one benign/attack pair per group, 200 development versus 3,000 confirmation groups, no group crossing partitions, and all seven output file sizes/SHA256s. Receipt: `main-selection-check.json`. The worker reports 47 passing offline tests. Root's separate synthetic prefix-join oracle check passed in all four configurations (`grouping-oracle-check.json`). These checks do not establish semantic label correctness or lack of model-training overlap.

Saved request summary: Jev 29,300; Luna Decisions 29,300; Luna Responses 5,900; Sol subscription 6,000 including 100 audit calls; ProtectAI local 5,200 records. Total paid API calls 64,500. `allow_paid_sol_api:false` verified in worker run manifest. Actual model inference still not independently verified at this checkpoint. Final request token/cost check and independent readiness review precede development calls.

Worker's written route amendment and authorization are now in `docs/study-v7/ROUTE-AMENDMENT.md` and `RUN-AUTHORIZATION.md`. Sol uses supported public Responses OAuth with no claimed API output cap. Authoring allocation zero; operational cumulative ceilings OpenAI $357.0275592 and TypeSafe $21.82758493400000006 (preserved historical accounting artifact). New confirmation admissions stop at 14:00 UTC, leaving verification/settlement time until 16:06 UTC. Template authorization remains false by design; separate bound receipts authorize execution. Last inspected worker cursor: `48e27ee0-0d56-4e05-98f1-457d179d0219:32`.

Heartbeat ID `research-preparation-overnight`, renamed **Overnight experiment supervision**, updated to hourly through deadline. Inspect with automation_update; do not edit scheduler files manually. Use compact wait_threads snapshots, diagnose stopped work before restarting, preserve user-facing updates for meaningful changes. At deadline stop new scheduling, safely settle/checkpoint in-flight work, pause heartbeat and produce a plain-language evidence/cost handoff. Do not silently extend the ten-hour window.
