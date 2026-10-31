# V6 review coordination and experiment handoff

October 31, 2026. The owner explicitly authorized creating Sol Ultra chats and
continuing autonomously through preparation, bounded execution and private delivery.
Existing cumulative caps ($15 OpenAI / $20 TypeSafe) and smaller v6 operational caps
remain unchanged. No inference or new spending occurred during this cleanup.

## Current state: grouping resolved; caveat adjudication running

The first full review is complete. Its 54 source disagreements, 296 unclear cases
and one not-applicable case remain quarantined. Original reviewer judgments and
preparation files are unchanged. All 48 stale review IDs are corrected only in the
derived corpus. All 43 grouping proposals and 1,008 blinded link records have explicit
dispositions, including one harmless self-reference. Forty proposals were accepted
as conservative merges, two held components quarantined, and seven weak cross-source
links rejected after task/evidence inspection. One unrelated cross-source link also
remains rejected. Two overlooked persona/jailbreak links were explicitly quarantined.
Original pairs and groups remain intact; final groups close transitively before
label attrition and use the original seeded split rule.

A final admission check found that reviewer A used `ambiguity` both for uncertain
labels and incidental factual limitations. A binary verdict alone does not resolve
that field. The original candidate resolution (v1) therefore **is not final label
admission**, despite its earlier draft completion flag. It is preserved locally as
an audit record, with draft receipts under review-resolution-v1/draft-receipts/.

A fresh independent agent is adjudicating all **1,749 otherwise candidate-eligible
rows with ambiguity != none**. Its chat is **Adjudicate v6 reviewer caveats**,
`01a19420-9345-76a1-ae83-3c166cd97813`, host `local`, requested model `gpt-6.1-sol`,
reasoning `ultra`. Actual runtime identity must come from its session record rather
than being inferred from the requested selector. This is distinct adjudication,
not a blinded first-pass repeat: B sees A's judgment and complete original evidence,
but no upstream labels. It must put incidental caveats in `limitations`, preserve
label-relevant uncertainty, and never blanket-clear cases.

The immutable packet has 1,749 rows in 282 bounded batches under
`data/raw/study-v6/adjudication-v1/`. Packet SHA-256:
`e6444b607356e6ede6c03a30c2e03b5835f2ad3558f3691ee943081e51196f57`.
Outputs are reviewer-B.csv, reviewer-B-session.json, reviewer-B-lock.json and
ADJUDICATION-HANDOFF.md in that directory. The reviewer owns only those raw artifacts.
Do not duplicate its review, edit its active files, or ask the absent owner to do it.
Sol can implement offline tools while B works and use wait_threads/artifact checks
for completion. No experimental inference may start while this gate is pending.

## Coordinator artifacts and admission

- POLICY.json records every group decision and the caveat gate.
- scripts/study_v6/resolve_review.py verifies A's lock, original fields, discrepancy
  identities, all grouping links and transitive pair/group closure. Its default
  output is **pending v2** under data/raw/study-v6/review-resolution-v2/ and
  results/study-v6-review-resolution/resolution.json. Caveated rows and affected pairs
  are ineligible. `review_resolution_complete=false` prevents premature admission.
- When B's full lock exists, run `resolve_review.py --with-adjudication`. It requires
  exact full packet coverage, evidence, distinct session identity and lock hashes.
  It writes separate final v3 outputs under review-resolution-v3/ and
  resolution-final.json. It only admits B judgments agreeing with A/source, with
  ambiguity=none and no unresolved grouping flags. Other B cases and affected pairs
  are quarantined. New B grouping flags quarantine all touched final components.
- No labels are silently changed. The numeric semantic_gold field is a compatibility
  field, with explicit agent/source-agreement provenance; it is not human gold.
- Run `resolved_plan.py --with-adjudication` only after final resolution. It refuses
  a pending gate and writes planning-final.json plus final target/coverage manifests.
- Verify with `resolve_review.py --with-adjudication --verify`,
  `resolved_plan.py --with-adjudication --verify` and
  `verify_resolution.py --with-adjudication --require-cache`.
- CI verifies tracked receipts and synthetic fixtures. Raw verification requires the
  local ignored corpora/reviews. Neither validation nor hashes prove comprehension.

## Candidate pool before the caveat gate — not final counts

| Source | Prepared | Candidate rows after original dispute/group exclusions | Candidate development groups | Candidate confirmation groups |
|---|---:|---:|---:|---:|
| BrowseSafe++ | 2,000 | 1,338 | 127 | 535 |
| NVIDIA | 400 | 368 | 0 | 6 |
| AIB | 158 | 139 | 22 | 110 |
| SPML | 200 | 171 | 4 | 5 |
| INFUSE | 70 | 64 | 0 | 3 |
| Authored scope | 48 | 48 | 0 | 1 |
| Total | 2,876 | 2,128 | 153 | 660 |

The first pass excludes 748 rows, including pair partners and unresolved grouping
components. The 2,128 are an upper bound until B's gate finishes. Candidate BrowseSafe
confirmation has 535 groups / 1,084 pages, and its old planning prefix was 202 groups /
404 pages (~$8.9821 OpenAI / $3.7707 TypeSafe). **Recompute these after B.** Never run
from the v1 candidate files or treat the old prefix as a fixed execution ceiling.

The full original pool closes from 1,383 to 1,141 components before attrition. All
1,259 explicit pairs are preserved. NVIDIA/INFUSE/scope have no development groups:
make no source development calls, use deterministic fixtures and available reviewed
development sources for interface checks, and never move confirmation cases into
 development. Secondary sources with fewer than 20 groups must be descriptive; scope
is one constructed contract family. Do not split templates to restore sample size.

The candidate-only Laya audit checked 13,878 exact payload hashes without forward
passes; 395 candidate-eligible BrowseSafe rows exceeded a limit in some condition.
Among the first 100 candidate main groups (200 pages), 143 pages fit all six conditions.
Those are not 143 complete pairs. Recompute retained coverage after B. Other routes
need exact full-input checks; no clipping or different convenient subsets per route.

Excluding ambiguous/disputed cases changes the estimand and may make this benchmark
easier. Report full attrition and source denominators, not general deployment FPR or
real agent resistance. Reviewer A's model remains unknown. Its blinding is declared,
not independently proven; synthetic/rewritten source provenance, hidden genealogy and
closed-model training exposure remain limitations. B adjudication is not human gold.

## Delivery and execution

Review coordination is on codex/study-v6-review-resolution, dependent on
codex/study-v6-expansion. Sol owns the future execution branch and sole inference
run. Read the complete SOL-GOAL.md here. Finish runner, accounting, full-input native
coverage, current price checks, exact requests and a committed experiment freeze
before dispatch. Preserve original files and all failed/draft records. Raw corpora,
labels, review outputs and credentials remain local and ignored. Do not merge the
historical PR stack, publish publicly, buy subscriptions or enable recharge.
