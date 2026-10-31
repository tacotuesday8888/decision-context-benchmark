# Expanded task-context study, v6

Prepared 2026-10-30. This replaces the **prospective v5 run plan only**; historical
data, protocols, raw results and v5 preparation remain unchanged. No v6 model
inference or independent semantic review has occurred. The v6 review dataset is
larger than the bounded evaluation cohort; neither is automatically gold.

## Question and contribution

Does supplying the legitimate task improve detection of unauthorized instructions
in external content? Does it help beyond merely adding a generic warning or text?
Study governing policy separately, and retain explicit authorization contracts as
a constructed diagnostic. Evaluate detection and native scores, not actual agent
resistance or prevention. No prevention experiment is included in this budget.

BrowseSafe++ provides the main paired page population. NVIDIA provides a fully
synthetic enterprise transfer diagnostic. AIB is a smaller source replication;
SPML measures direct user/system-policy conflict; INFUSE is static file
reconstruction; authored scope pairs test changes in permission. Never pool those
constructs into one benchmark accuracy. See SOURCES.md and METHODS-COMPARISON.md.

## Preparation, review and independence

Canonical v6 paths are `data/raw/study-v6/prepared.jsonl`, `review-packet.jsonl`,
`review-mapping.jsonl`, `review-batches/` and `group-edges.jsonl`. Aggregate counts,
source/packet hashes and acquisition receipts are under `results/study-v6/`.
These are local ignored raw artifacts, not redistributed corpora.

Target acquisition is 1,000 BrowseSafe++ pairs, 200 NVIDIA pairs and the preserved
476 v5 candidates: at most 2,876 review rows. See the actual preparation receipt
for exclusions and proposed groups. Preserve all sampled IDs; no outcome-dependent
replacement for excluded cases. Source labels are construction annotations.

The owner chose a separate agent for label/group review. Follow REVIEW.md and the
fresh-chat REVIEW-GOAL.md. All proposed rows receive independent judgments before
the reviewer sees mappings or source labels. Keep exact evidence, uncertainty,
model/session provenance and immutable review files. Agreement with a source label
is **agent-reviewed source agreement**, not human gold. Resolve disagreements with
a distinct reviewer or quarantine them. Never have Sol manufacture independent
labels or ask the same reviewer to erase disagreement after revealing the answer.

An optional second fresh agent can audit a fixed hash-ranked 20% sample of complete
groups and all disputed cases. Report random audit agreement separately from
disagreement-enriched adjudication; do not mix their denominators. This is a
recommended validity improvement, not an undisclosed human-review prerequisite.
Human validation would strengthen a publication but has not been commissioned.

Grouping starts before development: pool-wide exact task/injection components for
BrowseSafe++; full-pool task/injection near-duplicate closure for NVIDIA; preserved
v5 conservative closures; then cross-source exact task/candidate and 3-word Jaccard
links (task >= .5; candidate >= .8), requiring at least five distinct trigrams
in each text for near matching; shorter text receives normalized exact matching.
Unicode normalization is used for audit keys,
never to alter input text. The prefix join is exact at the declared thresholds,
but lexical closure cannot establish semantic independence. The reviewer must
merge remaining document/workflow/template relatives across all proposed splits.
Generic policy boilerplate alone is not a reason to merge unrelated tasks.

Keep every clean/attack or permission pair together, including cross-source links.
Final split is a seeded roughly 20% development / 80% confirmation assignment at
the final component level. Recompute after review merges and **before** any source
development calls. Preserve previous proposals and merger reasons. Do not split
a coarse family merely to increase sample size. Run normalized exact task/candidate
and candidate Jaccard >= .5 exposure screening against all four historical
collections identified in v5, using the same five-trigram minimum for near matches.
Source/public pretraining overlap remains a limitation.

## Inputs, controls and model panel

Reuse `scripts/study_v5/prompts.py` byte-for-byte for exact question, role and native
request contracts. V6 changes sampling and run allocation, not those strings.
Candidate, task and policy boundaries are specified in SOURCES.md. Annotation
fields and reference outcomes never enter model requests. Complete input only:
no truncation, paraphrasing or removal of attack spans to fit a context window.

Main BrowseSafe++ native comparison uses four conditions on the same whole groups:

| Condition | Candidate | Task field |
|---|---|---|
| format | Complete fixed Markdown | Empty |
| task | Identical | Source `benign_task` |
| reminder | Identical | Fixed generic trust-boundary reminder |
| length | Identical | Neutral filler matched to task character count |

The primary family is two native hosted decision routes × three contrasts:
`task` versus `format`, `reminder`, and `length` (six tests). Candidate-only and
scrambled-task diagnostics use the fixed comparator subset below. Filler is
character-matched, not token-matched; publish token differences. Scrambling can
retain vocabulary and meaning and is only a diagnostic. A wrong task can change
authorization, so it is not a label-preserving placebo.

AIB/NVIDIA/scope with authentic policy retain the v5 eight-condition factorial:
candidate, format, task, policy, task_policy, policy_reminder, policy_length,
policy_scrambled. Their task contrast holds policy fixed. SPML varies only policy;
INFUSE has the six no-policy conditions. All are secondary source-specific results.

Retain Jev 1.14.0 first-party native noul, Luna native Decisions, Luna/Astra
subscription Responses, pinned native local Laya and Nimble, and candidate-only
ProtectAI on eligible indirect-injection sources. Use exact historical route
settings and the Ollama 0.40.13 amendment in `docs/controls-v4/MODEL-ROUTES.md`.
Do not silently substitute generative Jev, paid Responses or newer model versions.
ProtectAI is not a policy/scope classifier. BrowseSafe-Guard trained on this release
is not an unexposed comparator. Constant allow/block and the already fixed v5
lexical shortcut baseline cost nothing and remain useful diagnostics.

To bound runtime, run the four contextual local/subscription comparators on the
first **100 main confirmation groups** in the same frozen hash order, with all six
no-policy conditions; run native candidate/scrambled extras on that same subset
only if the supporting allocation covers them. Do not select comparator cases by
model error or choose a different short-input sample for each model. Mark unsupported
model/case cells before dispatch and report both route-specific full-input coverage
and the common intersection. Pairwise route comparisons use the same supported rows.
Existing v5 tokenizer success does not certify the new longer pages.

Secondary native source diagnostics: at most the first 12 confirmation groups per
source, preserving complete groups, and subject to the $2 supporting allocation.
Order source groups round-robin across AIB, SPML, INFUSE, NVIDIA, scope, then add
main candidate/scrambled extras. If the next whole group does not fit, stop that
supporting schedule without skipping costly examples. Save exact included/excluded
groups before freeze; an unrun arm is reported as unrun, not as an empirical result.
Local/subscription diagnostics may cover all those same secondary groups without
paid fallback. Never count free/subscription limits as unlimited or guaranteed.

## Size, costs and development

Freeze every eligible reviewed BrowseSafe++ confirmation group as the **target
cohort**, ordered by `rank('budget-order:' + group_id)`. Execute whole groups in that
order under a $9 main allocation per provider. Before starting a group, atomically
reserve all its four-condition requests for both providers. Settle completed
requests using actual usage and retain unknown-usage reservations. Start the next
group only if its full reservations fit both remaining provider allocations. Stop
at the first group that cannot fit; never skip a long group to favor shorter pages.
The admission decision reads only costs/reservations and the frozen order, never
predictions, correctness, significance or observed effects. No provider may advance
to a different cohort on its own.

`feasibility.json` supplies the **up-front fully reserved planning prefix** (232
groups / 464 pages with the current unreviewed proposal), not a compulsory sample
ceiling. Settling actual usage can release reservations and allow more of the frozen
target of 808 proposed confirmation groups to run under the same cap. Neither figure
is a reviewed or guaranteed count. This predeclared cost-stopping rule must be tested
and frozen before inference. Report the entire planned denominator, the completed
common prefix, every unrun group and full-cohort missingness bounds. Prefix estimates
are conditional on attained coverage; do not describe an incomplete target as a
completed fixed-size experiment. No post-result decision to extend for significance.

Review, exposure, coverage, changed prices and ledger headroom must be applied
before final target selection. A tighter reservation rule may replace the byte
proxy only before freeze with documented native token-count evidence and tested
overhead bounds. A few cheap observed calls or a different model's tokenizer do
not establish such bounds.

When the owner submits the updated Sol /goal, proposed v6 operational caps are
**$12 per provider total**: $9 main, $2 supporting, $0.50 initial development and
$0.50 recovery. These sit beneath the cumulative **$15 OpenAI / $20 TypeSafe** caps,
including all earlier spend/reservations. The smaller earlier v5 $5 proposal does
not define this separately versioned v6 run. No expansion of the owner's global caps.
If another chat spends meanwhile, reduce the run envelope before freezing.

Historical conservative accounting is OpenAI $0.4838404 / TypeSafe $0.258774852,
including retained unknown-usage reservations; these are not provider balances.
Reconcile all subsequent activity. `feasibility.py` uses existing planning rates
and the v5 byte-reservation proxy; Sol must verify current official prices and
native token accounting. The proxy is not a mathematical tokenizer upper bound.
The preparation recheck found $0.10/M input with free output for
[Luna Decisions](https://developers.openai.com/api/docs/guides/decisions#pricing-and-availability)
and $0.042/M input with free output for [Jev](https://docs.typesafe.ai/models).
OpenAI cache writes, regional premiums and long-context multipliers need explicit
accounting; no discount or premium-tier assumption is hidden in the base-rate plan.
Reserve conservatively before dispatch under a shared provider lock; no attempt
may start without remaining headroom. Retain unknown usage, stop on mismatches,
and never double-count inherited totals. No purchases/recharge/publication.

Only operational development is authorized by the future Sol run: at most four
reviewed development examples per source (longest per label, then hash-first distinct
groups to four), with reuse for fixes, capped as above. No prompt sweep, accuracy
tuning, threshold/calibration fitting or model shopping. Fixed native threshold
0.5, exact ties abstain; chat outputs Boolean only. Deduplicate identical payloads
within route/split while preserving all row references; never share a prediction
cache across development and confirmation.

Power is a sensitivity calculation, not a promise of significance. Report reviewed
group counts, class support, confidence-interval scale and scenarios at discordance
.10/.25/.50 with the six-test correction. The earlier ~800-family suggestion assumed
a single independent comparison; multiplicity can require more. For any final cohort
with fewer than 20 groups in an arm, results are descriptive. Do not suppress a
wide interval or reinterpret non-significance as proof that task context has no effect.

## Frozen analysis and readiness

Main endpoint: paired control-minus-task **group-balanced error**, positive favoring
task context. Average errors within group separately by gold class; average group
means within each class, then average the two class errors. Keep both pair members
when possible; preserve and report review exclusions and unpaired attrition. Report
FPR/FNR, raw accuracy, both-correct pair fraction and case counts alongside this endpoint.

Use paired group sign randomization (exact where feasible, otherwise 100,000 seeded
draws with +1 correction), Holm family-wise alpha .05 for the six primary contrasts,
and 20,000 paired whole-group bootstrap resamples. Show pointwise 95% and Bonferroni
99.167% intervals, documenting exchangeability and source-conditional sampling
assumptions. No pooling across sources. Show individual group effects for small
secondary arms. Reviewer-defined related/subtle/legitimate-procedure subgroups are
pre-inference diagnostics; require at least ten groups in each compared class for
a numerical subgroup contrast. Retain source-label agreement as a separate endpoint.

Treat failed, refused, truncated and tied outputs as distinct dispositions. Report
complete-pair effects and full planned-denominator worst/best missingness bounds;
do not silently drop difficult cases. Native AUROC, Brier and reliability plots are
secondary diagnostics on valid scores, not proof of calibrated probabilities.
No calibration is fitted in this run. Scope changes authorization, so report its
pair transitions separately rather than treating its labels as invariant.

Before confirmation freeze: code/revisions, licensed source receipts, review hashes
and provenance, adjudication/exclusions, final grouping/splits/exposure checks,
full-input coverage, cohort, prompts, native settings, exact request hashes,
prices/ledger/reservations and analysis plan. Commit the freeze. Test budget locks,
timeout reservations, raw retention, exact resumption and statistical fixtures.
Every first attempt remains primary. Operational retries require an explicit bounded
linked batch and fresh reservations; recovered first-valid results are sensitivity.
No rerunning wrong answers. Scientific changes require a new version, not a quiet patch.

The final approximately five-page paper/PDF follows completed review, freeze,
terminal execution, accounting, independently recomputed results and checked figures.
If an essential gate remains unresolved, finish all independent tooling and a precise
readiness report, without pretending to have completed the empirical study.
