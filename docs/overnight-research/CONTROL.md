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

### Development started and stopped for parser correction, 06:34 UTC

Worker delivery exists as private PR 14, `codex/study-v7-preparation`, most recently observed commit `2d1490bb`. Updated offline suite reports 57 tests passing after a temporary-directory fixture fix. Root did not independently rerun that suite. Main source and grouping checks above remain independently inspected.

Corrected worker forecast `forecast-v2.json`: 64,500 paid requests, 6,000 subscription requests; API ordinary proxy $21.406249644, native cache-write proxy $41.324364444, stress $83.309528888. These replace the earlier root mean-input arithmetic. Full accepted-context worst-case totals are much higher; atomic reservations and settled usage enforce the caps rather than these estimates. ProtectAI needs 16,048 full-document windows. A serialized tokenizer's default clipping was removed from forecasting, and the worker added a runtime test ensuring final document tokens affect the aggregated score.

First development execution created `data/raw/study-v7/execution-v1/`. Its stop record at 06:34:21 UTC says `systemic_route_or_unknown_usage`, preserving first attempts. Root inspected 13 completed response records: native Jev/Luna examples parsed successfully; four Luna Responses HTTP200/completed results were rejected solely for returned `prompt_cache_options` containing default `ttl:30m` alongside requested `mode:explicit`. All four had zero cached/cache-write tokens and matching output/reasoning/store/truncation settings. This is operational inspection of development examples, not an accuracy estimate.

Worker acknowledged the metadata-default mismatch and is implementing a narrow parser correction with recorded continuation of only unsent requests. Root sent the exact evidence and requested preservation of original bytes plus explicit accounting reconciliation; root has dispatched no calls. Stopped log cumulative conservative totals: OpenAI $9.9716985, TypeSafe $1.83222513600000006. These include holds and historical accounting and must not be reported as invoice charges. Latest worker cursor `48e27ee0-0d56-4e05-98f1-457d179d0219:58`; worker remains active. Verify recovery rather than restarting a competing executor.

### Development first pass verified, 06:53 UTC

Continuation resumed without duplicate dispatches in inspected journal snapshots. Original stop and four parser-failure records remain intact. Root checked 1,704 unique completed request keys: Jev 496 valid +4 ties, Luna Decisions 500 valid, Luna Responses 496 valid +4 original metadata-parser failures, ProtectAI 200 valid, Sol subscription 4 rejected requests. Saved exact counts in `development-first-pass-check.json`; these are transport/parser outcomes, not accuracy results.

Sol subscription's raw HTTP400 error names `prompt_cache_options` as unsupported. Its lane paused with `paid_fallback_forbidden:true` and `cheap_routes_continue:true`. This is not quota exhaustion. Root directed worker to document a supported subscription-specific amendment if feasible, preserve these failed attempts/payload version, and proceed with cheaper-route readiness independently. No reset or paid Sol fallback was authorized by this error. Latest checked Codex allowance: 87% remains, one free reset still available and unused. Latest compact worker cursor: `48e27ee0-0d56-4e05-98f1-457d179d0219:73`.

Heartbeat ID `research-preparation-overnight`, renamed **Overnight experiment supervision**, updated to hourly through deadline. Inspect with automation_update; do not edit scheduler files manually. Use compact wait_threads snapshots, diagnose stopped work before restarting, preserve user-facing updates for meaningful changes. At deadline stop new scheduling, safely settle/checkpoint in-flight work, pause heartbeat and produce a plain-language evidence/cost handoff. Do not silently extend the ten-hour window.

### Subscription amendment independently checked, approximately 07:09 UTC

Root compared the complete old and v7.0.2 request dictionaries: all 69,700 non-Sol requests are identical; the new plan contains 6,000 Sol requests. New plan SHA256: `70d8606f6a3090514ac08c2c67d27f84d3cf95db18847e08a0f48cc3f4d644da`. This verifies non-Sol preservation, not successful Sol execution or confirmation readiness. Worker remains active implementing/testing the subscription amendment; latest cursor `48e27ee0-0d56-4e05-98f1-457d179d0219:83`. Current Codex allowance 85% remains, one free reset unused. Root relayed this verification and reiterated single-owner reset coordination and timely confirmation admission within existing gates/caps.

Root independently ran `python -m unittest tests.study_v7.test_report -v` in the worker checkout: all three reporting tests passed (hand values/units/denominators, deterministic exports/figures, rejected unmatched cohorts/invented scores). This tests synthetic rendering, not empirical results. Worker now reports measured native request times around0.14s Jev and0.25s Luna before scheduler overhead; this reduces the earlier runtime concern but is not a completion guarantee. Latest live cursor84 at07:09UTC.

### Development spending independently summed, approximately 07:13 UTC

Root independently joined journal reservations to settlements by request key:1,704dispatches and1,704settlements, zero duplicate dispatch/settlement keys, zero null actual-cost settlements. New settled usage totals OpenAI `$0.66480345`, TypeSafe `$0.091181622`, subscription/local `$0`; combined `$0.755985072`. These are recorded usage charges, not invoice verification, and exclude preserved earlier-study accounting. The journal also preserves four canceled never-dispatched Sol reservations and the explicit schedule supersession. Main confirmation was not yet observed. Prior coordinator checks committed/pushed as `581fe3d0` in private PR13.

### Core operational readiness verified, approximately07:14UTC

Worker v7.0.2 development reparse receipt reports core readiness complete for Jev/Luna Decisions/Luna Responses/ProtectAI, zero core blockers, no accuracy calculated or selection/prompt changes. Only amended Sol500development requests remain pending. Journal read-only replay matches root independent sums exactly; cumulative historical-plus-new accounting is OpenAI7.69236265 /TypeSafe1.91876655600000006, with zero pending/unknown holds in this execution journal. Root independently ran current execution+operational suites:34tests passed in2.898s. These results were relayed to the live worker; confirmation still requires its explicit final freeze and supported/unsupported Sol disposition.

### Sol subscription now responding,07:14UTC

Root inspected amended-plan request keys against immutable completion records:48Sol subscription responses parsed `ok`, mean recorded elapsed3.617seconds. Only transport/parser statuses were inspected, not correctness. Original four rejected calls/pause remain preserved. Total completion count is increasing; worker remains active. This establishes initial route operation, not completion of all500development calls or a confirmation result.

### Sol HTTP503 and readiness snapshot race,07:26UTC

Root observed491amended Sol responses parsed ok plus one HTTP503 after the lane paused at07:26:00. The first `development-validation-v7.0.2.json` snapshot reported484ok/1interrupted_unknown/15unattempted and completed=true with Sol classified unsupported. Those counts preceded final in-flight settlement. Root directed the worker to preserve that snapshot, wait for owned executor completion and produce a new versioned final receipt before freezing confirmation. HTTP503 establishes service failure, not unsupported model parameters or quota exhaustion; if policy defers Sol, describe operational deferral accurately and retain partial data. No duplicate retry, reset or paid fallback. Core four configurations remain validated. Latest inspected worker cursor94.

### Bounded service recovery chosen, approximately07:32UTC

Worker inspected the retained HTTP503 body: `service_unavailable_error`, code `subscription_sharing_user_unavailable`, message that the ChatGPT user is temporarily unavailable. Root requested evaluation of a documented pre-confirmation recovery because this is not another unsupported-parameter rejection. Worker accepted one continuation for exactly eight never-sent development requests, unchanged payloads/settings, retaining491valid responses and the failed first attempt. No retry/replacement of the503, reset or paid fallback; another service failure stops the lane. Await final settled receipt before confirmation freeze. Worker active, latest cursor97.

### All five configurations validated,07:43UTC

Root independently counted499valid amended Sol development completions and one retained HTTP503, with zero duplicate dispatch keys. Final `development-validation-v7.0.3-final.json` validates all five configurations, no unsupported configurations, all500Sol development requests terminal, exactly eight new valid responses from the never-sent continuation. Old premature v7.0.2 snapshot remains preserved. Worker reports71offline tests passed and is beginning the locked100-pair audit. No confirmation accuracy examined. Latest active cursor110. Recovery/analysis independent test receipt saved as `recovery-analysis-review.json`; root private revision4c7cc25e.

### Partial audit evidence check, approximately07:48UTC

Root independently checked20completed audit outputs against their own retained request fields TASK/CLEAN_PAGE/ATTACK_PAGE:20valid diagnostic reviews,125literal matching spans,1nonliteral span,zero reviews without spans. This is an interim operational check, not final audit totals or human validation; do not modify labels/cohorts based on it. Worker reports a separate reviewer requested tightening service-recovery acceptance of additional non-valid outcomes; actual development has499ok+the retained503, so observed data are unaffected. Worker will make the stricter guard change after the audit executor exits and before confirmation freeze. Latest active cursor122.

### Second subscription service failure; bounded recovery exhausted,07:55UTC

Root independently observed the audit stop at70valid reviews plus one HTTP504 (Retry-After120 seconds, transport exit0). Worker confirms the audit executor exited. Under the previously recorded one-continuation rule, Sol is now operationally deferred, with no further recovery, reset or paid fallback. Retain29unattempted audit cases and all failed/valid outputs; report the audit as partial, not100reviews. Four core configurations remain eligible for confirmation after final freeze and runtime optimization verification. Do not call this intrinsic model incompatibility or infer detection quality from service failure. Latest worker cursor140.

### Final partial audit independently reconciled, approximately07:58UTC

Root checked all100locked audit keys and literal evidence directly from retained request/response files:70ok,1HTTP error,29unattempted;390literal spans,1unverified span in one review,zero empty-evidence reviews. These exactly match `audit-validation-v7.0.3.json`, which correctly declares completed=false and preserves source labels/cohorts. Model judgments about fidelity/ambiguity remain unblinded diagnostic claims, not validated human labels. Independent repeat-analysis tests4/4passed; hash receipt `repeat-analysis-review.json`. Worker received these checks. Latest cursor143; confirmation awaits runtime optimization verification/freeze.

### Core confirmation started and freeze independently verified,08:00UTC

Worker launched one confirmation-then-repeat executor at07:59UTC from commitc08deef0. Root checked active pointer/manifest/authorization/plan hashes and all172recorded execution-code hashes: allmatch. Frozen plan remains70d8606f..., paid Sol prohibited; admission cutoff14:00UTC and final work window16:06UTC. Root observed201Luna Decisions ok/202Jev ok/2Jev ties confirmation completions; no correctness inspected. Receipt `confirmation-freeze-check.json`. Cache11regression tests independently passed (`ledger-cache-review.json`), repeat4passed. Runtime estimate remains conditional, not guaranteed. Latest worker cursor150.

### First core transport stop,08:00UTC

Root inspected `stop-confirmation-v7.0.4.json` and432confirmation completions:215Luna Decisions ok,214Jev ok,2Jev ties,1Luna Decisions HTTP504. Failed key7f472597d64410f504939b31e1b9524f4a5f4c3af5ccefc894f5073cef0a76fd, transport exit0, elapsed5.11s, no returned headers. Worker is reconciling the preserved failed first attempt and unknown-cost hold before documented unsent-only continuation under the unchanged freeze. No accuracy inspected or failed request retried. Latest worker cursor154.

### Core continuation running, approximately08:05UTC

Worker settled all27first admitted groups, waited two minutes and resumed untouched requests under unchanged freeze. Root independently checked3,043total journal dispatches:zero duplicate keys, failed Luna key dispatched once, OpenAI unknown-cost hold0.525 preserved. At that snapshot new settled usage was OpenAI1.12791925 /TypeSafe0.182868210 (excludes old studies, holds and in-flight reservations). Worker subsequently reports more than1,200native confirmation records, no further transport error. Latest active cursor161. Root still inspects only transport/coverage/accounting, not accuracy.

### Provider token-rate stop, approximately08:09UTC

Root verified Luna Decisions HTTP429: gpt-6-luna TPM limit2,000,000; used1,990,581/requested10,835; Retry-After header1second. This is a throughput limit, not credit exhaustion. Failed key2c20194b396133250fabed662ecea10caa428287cf28e9187b085752b8b4176d remains a missing first attempt. Worker is preparing a documented operational pacing amendment, preserving payloads/models/cohorts/statistics/caps/deadline. Root requested shared-model accounting across Luna Decisions/Responses and conservative concurrent token reservations. No billing changes, failed-key replay or root inference. Latest active cursor168.

### Pacing freeze independently verified, approximately08:16UTC

Worker reports94offline tests passed. Root verified active v7.0.6manifest/authorization hashes, unchanged plan70d8606f..., all173execution-code hashes, and unchanged cumulative caps. Relative to confirmationv7.0.4, only `pacing.py` and `run.py` changed; analysis/request code hashes unchanged. Shared1.5million proxy-token budget per60seconds for both Luna routes; weights2xproxy with1024floor plus256Responses output;60second startup cooldown. Proxy limitation disclosed. Root independently passed7focused pacing tests; worker added an eighth cancellation test without changing the reviewed production files. Both failed first attempts and total1.05unknown holds retained. Latest cursor179; worker restarting single executor.

### Paced continuation active, 08:19 UTC

Worker started paced run at commitac495002; first paced dispatch08:18:09UTC after startup cooldown. Root checked first138pacing events: maximum observed60second proxy sum1,497,820 below1,500,000. Worker reports3,493/48,000native confirmation records without newstop. Latest cursor185.

### Independent live accounting check, 08:29 UTC

Root reconciled a complete-line journal prefix through index 18202: 8,706 dispatches and 8,706 settlements, zero duplicate dispatch or settlement keys. New settled usage OpenAI $4.63367705 / TypeSafe $0.855393042, total $5.489070092; unknown OpenAI holds $1.050 remain preserved. Excludes historical accounting and any later/in-flight reservations; not an invoice. Receipt `live-accounting-check.json`. Root research PR13 head 6e7dac74 has 20/20 checks passed. Worker remains active, latest observed 6,260/48,000 native records at cursor 202. No accuracy inspected.
