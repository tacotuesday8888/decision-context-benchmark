# Expanded v6 preparation handoff

Prepared 2026-10-30 in `/Users/langqi/Developer/Projects/Decision Context Benchmark`.
**Dataset acquisition and preparation are complete; independent label/group review
and the main experiment are not.** No v6 model forward passes or paid inference ran.

Start the separate reviewer with the complete copyable **REVIEW-GOAL.md** in a fresh
chat. After its label lock and grouping handoff, start the implementation/execution
chat with the complete **SOL-GOAL.md**. Both prompts are self-contained instructions
referencing saved artifacts; the user does not need to assemble snippets.
Sol High is a practical reviewer choice distinct from the evaluated Astra/Luna
routes; Ultra is optional rather than evidence of better annotation. Record the
actual model, not the intended selector. Sol may implement offline tooling while
review is pending but cannot manufacture its own independent review.

## Prepared data, not validated gold

| Source | Review rows | Proposed development / confirmation groups | Interpretation |
|---|---:|---:|---|
| BrowseSafe++ | 2,000 (1,000 pairs) | 191 / 808 | Main task-bearing paired page population; labeled training release, privacy rewritten. |
| NVIDIA agentic IPI | 400 (200 pairs) | 30 / 170 | Fully synthetic; locally constructed exact-deletion controls; field-level observations. |
| AIB | 158 | 29 / 128 | Existing source-derived task/policy replication. |
| SPML | 200 | 4 / 5 | Direct user/system-policy conflict; conservative domain/template closures retained. |
| INFUSE | 70 (35 pairs) | 1 / 9 | Static reconstruction, not executed agent trajectories. |
| Authored scope | 48 (24 pairs) | 1 / 7 | Explicit synthetic permission contracts. |
| **Total** | **2,876** | **1,383 total provisional components** | No semantic gold or inference admission assigned. |

BrowseSafe++ acquisition scanned metadata for all **59,000 train pages / 29,500
pairs**, yielding 18,726 exact task/injection pool components before selecting
1,000. Full-text lexical closure subsequently merged one selected pair family,
leaving 999 selected BrowseSafe++ components before review. All selected Markdown
pairs were nonempty and nonidentical; 88 pairs have no exact bound injection-reference
string in Markdown and need semantic assessment, not automatic relabeling.

NVIDIA audit adapted 1,253 of 1,272 raw records, quarantining four nonunique/missing
locations and 15 empty deletion controls. The pool has 205 provisional task/injection
components; 200 representatives were selected across nine domains. The actual
complete input and reference binding are verified, but no independent semantic
review has been completed. Original v5 files are unchanged.

## Exact artifacts and verification

Tracked:

- `scripts/study_v6/common.py`, `fetch_browse.py`, `prepare.py`: pinned train-only
  projection, exact field adapters, grouping, and bounded blinded chunks.
- `reviews.py`: complete independent label-lock validation without loading mappings.
- `exposure.py`: all four historical prepared collections, 1,776 rows including
  repeats; zero normalized exact task/candidate or candidate Jaccard >= .5 hits
  (near matching requires at least five distinct trigrams per candidate).
- `feasibility.py`, `precision.py`: reconciled accounting, conservative request
  envelopes and 60 seeded planning simulations. These are not experiment outcomes.
- `token_audit.py`: 18,468 exact Laya request assemblies, **zero forward passes**.
  3,344 assemblies across 559 BrowseSafe++ rows exceed its 8,192-token sequence
  budget. Largest untruncated state is 34,616 tokens; heads fit (maximum 76).
  These rows must be unsupported for Laya, not clipped into a purported full-input run.
- `verify.py`, `tests/study_v6/`, `.github/workflows/study-v6.yml`: source boundaries,
  pair/group preservation, reviewer completeness, leakage and budget checks.
- `results/study-v6/`: counts/hashes, acquisition, source implementation/object
  identities, exposure, cost and token receipts. See `verification.json` for delivery checks.

Ignored local data:

- `browse-metadata/`: 21 train metadata projections; `browse-selected/`: 21 selected
  Markdown projections. No screenshot columns or restricted test pages were read.
- `browse-train-selected.jsonl`: complete pinned source export for 2,000 pages.
- `browse-pool-groups.jsonl`, `browse-view-audit.jsonl`, `nvidia-pool-group-edges.jsonl`:
  grouping and exact reference diagnostics, never detector input.
- `prepared.jsonl`, `review-mapping.jsonl`, `group-edges.jsonl`: current coordinator
  material, hidden from the independent label pass.
- `review-packet.jsonl`, `review-batches/`: **383** nonoverlapping blinded chunks,
  at most 40 rows and 120 KB each here; accompanying blank CSVs. Reviewing this
  larger packet is sustained work, not a five-minute sample check.
- `reviews/`: destination for the external reviewer; no completed reviews exist yet.
- `historical-exposure-hits.jsonl`, `laya-token-audit.jsonl`, `budget-primary-proposal.jsonl`:
  ignored detail behind tracked summaries. The budget proposal is the up-front
  reservation prefix, not a final execution manifest or mandatory sample ceiling.
- `preparation-draft-1/`: preserved initial unreviewed grouping draft. The current
  preparation corrects inheritance of v5's conservative `split_group` closure;
  a regression test prevents inadvertently splitting those families again.

Reproduce from this shared workspace:

```sh
.venv/bin/python scripts/study_v6/fetch_browse.py
.venv/bin/python scripts/study_v6/prepare.py
.venv/bin/python scripts/study_v6/exposure.py
.venv/bin/python scripts/study_v6/feasibility.py
.venv/bin/python scripts/study_v6/precision.py
.venv-laya/bin/python scripts/study_v6/token_audit.py
python3 scripts/study_v6/verify.py --require-cache
python3 -m unittest discover -s tests/study_v6 -v
```

Fetch uses existing authenticated Hugging Face access and resumes completed shard
projections. Metadata/text projection libraries are recorded in browse-acquisition.json;
the existing `.venv` supplies them and NumPy/SciPy. `.venv-laya` and pinned weights
are required only for the local tokenizer/SDK audit. Other checks use stdlib.
Writers refuse changed historical bytes. A completely new checkout also needs
source-discovery/v5 preparation and all four historical exposure collections;
do not bypass missing caches with empty data. The source-implementation audit verifies
33 inert upstream files against Git blobs and SHA-256. Whole 39-GB Parquet objects
were not downloaded/rehashed; pinned object identities and exported-column hashes
are explicitly distinguished.

## Feasible execution and remaining gates

The full prepared pool is not a promise to run every model on every row. Complete
Markdown is much longer than v5: median 13,145 bytes, 95th percentile 44,707, maximum
90,747. The conservative native four-condition reservation envelope covers an
up-front prefix of **232 proposed main groups / 464 pages** for about **$8.9115 OpenAI
and $3.7408 TypeSafe**. These are planning reservations, not actual costs or balances.

DESIGN.md freezes a larger target and a cost-only whole-group stopping rule. Actual
usage may release enough reservation headroom to evaluate more of the 808 proposed
main confirmation groups under the same $9/provider main allocation. The rule must
be fixed and tested before inference; no accuracy/significance-based extension.
Report attained coverage and planned-denominator bounds if the full target does not
finish. Review, source overlap and hosted coverage can reduce the target further.

Proposed v6 total limits are $12/provider ($9 main, $2 supporting, $0.50 initial
development, $0.50 recovery), bounded by cumulative $15 OpenAI / $20 TypeSafe caps.
Historical conservative accounted totals remain $0.4838404 / $0.258774852 including
four retained unknown-usage reservations. No new inference spending was added.
Reconcile current activity and official pricing before dispatch. No purchases,
recharge or paid subscription fallback. The cost-stop rule does not increase caps.

Required next gates: independent review lock; explicit adjudication/quarantine;
semantic group closure and final split; source-conditional inclusion/exposure;
full-input native coverage and route access; tested runner, budgets and analysis;
then frozen exact requests and run plan. Independent review remains a real validity
limitation even if one agent agrees with source labels. Closed-model pretraining
exposure and original production-task provenance are not resolved by our audit.

The design is stronger in source breadth and paired benign coverage, but does not
guarantee a 5-point detectable effect or publication acceptance. Multiplicity and
final independent groups govern precision. See METHODS-COMPARISON.md for what
Jev, decision-model and injection papers actually did and what we borrow.

Delivery branch: `codex/study-v6-expansion`, based on `codex/study-v5-design`.
Open a private draft PR against that dependency; do not merge the historical stack.
Raw data/reviews/credentials stay ignored. Sol's main run and final empirical paper
are intentionally left to the separate execution chat after readiness gates.
