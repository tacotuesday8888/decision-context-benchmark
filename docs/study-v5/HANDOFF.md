# V5 preparation handoff

Prepared 2026-10-30 in `/Users/langqi/Developer/Projects/Decision Context Benchmark`.
Research and feasible preparation are complete. **The reviewed confirmation dataset
is not ready, and no v5 inference has run.** The owner will use another agent for
label review. No human review is claimed or silently required instead.

## Read in this order

1. Project `AGENTS.md` and this file.
2. `DESIGN.md`: source-specific questions, exact interventions, routes, analysis,
   budgets, failures, freeze and paper gates.
3. `RESEARCH.md`: primary-paper methods and actual source-construction findings.
4. `REVIEW.md`: separate agent's blinded task, codebook, admission and grouping.
5. `SOL-GOAL.md`: the single complete continuation prompt.

Historical interpretation: v4 is complete with 13,547 terminal planned cells and
retained failures; it did not establish a general task-specific benefit. See
`results/controls-v4/execution-closure-v1.json`, `docs/controls-v4/` and the isolated
Laya reproduction. All earlier datasets, protocols, raw results and PRs are preserved.
The research and execution chats were read; their latest states agreed with files.

## What exists now

| Artifact | Purpose/status |
|---|---|
| `scripts/study_v5/fetch_evidence.py` | Bounded pinned acquisition; Git blob verification plus SHA-256 receipts; never executes upstream code. |
| `scripts/study_v5/source_audit.py` | Recomputes AIB seed lineage and INFUSE placement counts from inert YAML/TOML. |
| `scripts/study_v5/prepare.py` | Exact AIB/SPML field boundaries, bounded selection, static INFUSE pairs, historical-exposure checks, blinded packets. |
| `scripts/study_v5/group_audit.py` | Conservative connected task/template/domain closures and revised split proposals. |
| `scripts/study_v5/scope_pairs.py` | Disclosed authored permission pairs with fixed candidate/policy and changed task authority. |
| `scripts/study_v5/prompts.py` | Pure exact native payload proposals; no transport or inference. |
| `scripts/study_v5/reviews.py` | Provenance, verbatim evidence, ambiguity and agreement validation; no fabricated reviews. |
| `scripts/study_v5/feasibility.py` | Historical accounting reconciliation, request-cost envelope and precision scenarios. |
| `scripts/study_v5/token_audit.py` | Existing local Laya SDK/tokenizer audit, no forward pass. |
| `scripts/study_v5/verify.py`, `tests/study_v5/` | Source, intervention, grouping, review and cache integrity checks. |
| `results/study-v5/*.json` | Committable count/hash receipts and verification record; no raw corpora, review labels or credentials. |
| `.github/workflows/study-v5.yml` | Offline CI independent of private caches, network access and model weights. |

Raw paths below are local, Git-ignored, and intentionally not in the private PR:

- `data/raw/study-v5/grouped-review-v2.jsonl`: **current** proposed source collection,
  428 records (158 AIB, 200 SPML, 70 INFUSE). Its split proposals supersede
  `prepared-review.jsonl` and the old split fields in `review-mapping.jsonl`.
- `data/raw/study-v5/scope-pairs.jsonl`: 48 constructed records, 24 permission pairs.
- `data/raw/study-v5/review-packet.html` and `review-packet.jsonl`: 428 blinded cases.
- `data/raw/study-v5/reviewer-A.csv`, `reviewer-B.csv`: untouched blank templates.
- `data/raw/study-v5/scope-review-packet.jsonl`, `scope-reviewer.csv`: constructed arm.
- `data/raw/study-v5/review-mapping.jsonl`: coordinator-only labels/provenance;
  join to grouped-v2 by `id` after review. Scope's own JSONL is its mapping.
- `data/raw/study-v5/spml-all-policy-groups.json`, `group-edges-v2.jsonl` and
  `aib-seed-links-v2.json`: grouping/lineage evidence, never detector input.
- `data/raw/study-v5/token-audit.jsonl`: exact Laya request-hash/coverage evidence.
- Pinned source trees/files under `data/raw/study-v5/{aib,infuse,asb,authorization}`;
  earlier AIB/SPML full sources under `data/raw/source-discovery/`.

The older 16,194-record preparation remains unchanged. It is not the v5 held-out
evaluation. No row currently has semantic gold or inference admission. The local
review HTML escapes candidate markup and contains no active scripts.

## Verification and reproducibility

Python 3.11+ is required for TOML. The existing `.venv` supplies PyYAML for the
optional construction-code audit; `.venv-laya` supplies the pinned Laya SDK and
local artifacts for tokenizer checks. Ordinary verifier/tests need only stdlib.
From the repository root:

```sh
python3 scripts/source_discovery/verify.py --require-cache
python3 -m unittest discover -s tests/source_discovery -v
python3 scripts/study_v5/verify.py --require-cache
python3 -m unittest discover -s tests/study_v5 -v
```

Recompute preparation against the existing exact caches:

```sh
python3 scripts/study_v5/fetch_evidence.py
.venv/bin/python scripts/study_v5/source_audit.py
python3 scripts/study_v5/prepare.py
python3 scripts/study_v5/group_audit.py
python3 scripts/study_v5/scope_pairs.py
python3 scripts/study_v5/feasibility.py
.venv-laya/bin/python scripts/study_v5/token_audit.py
```

`fetch_evidence.py` may download missing pinned public files; use
`prepare.py --download-static` only to recover missing pinned INFUSE static targets.
All other preparation commands above use local inputs. Reconstructing a completely
new checkout also needs the earlier source-discovery preparation and four historical
prepared collections named in `results/study-v5/preparation.json`. They are present
in this shared folder. Do not bypass missing exposure evidence with empty inputs.
Changed artifact bytes are refused by preparation writers; create a new version.

Local checks cover 269 source/static-file receipt entries, 476 prepared records,
unaltered candidates across conditions, exact source-field/static reconstruction,
proposed group/pair separation, packet blinding and hashes. The tokenizer audit
covers 3,268 payloads: max input 1,343 tokens, max head 76, zero truncation/dropped
state tokens, zero model forward passes. It verifies Laya only. Hosted access and
coverage for the exact new requests still need Sol's bounded development checks.
See `results/study-v5/verification.json` for commands and evidence; CI checks tracked
artifacts only. All 21 v5 tests and eight existing source-discovery tests passed.
The cross-source lexical audit checked 77,204 pairs with no hits; semantic overlap
and closed-model pretraining exposure remain unresolved.

## Remaining gates and what Sol can do

**Separate agent review:** review all selected packets without mapping/source labels,
lock output hashes, then perform workflow/template grouping. Preserve model/session
provenance. One agent's agreement with construction labels is explicitly weaker than
human validation; disagreements/ambiguity remain excluded or separately adjudicated.
The review reducer is a label gate, not an execution-ready manifest. It deliberately
blocks unresolved ambiguity/group flags; original reviews must never be edited to
erase them. Sol must add a tested explicit resolution manifest and, if needed, a
distinct adjudicator import. Do not convert missing review into an automatic pass.

**Before confirmation:** final group/split closure and overlap audit; review-based
inclusion/exclusion counts; exact route settings/coverage; bounded development access
and parser checks; current accounting/prices; tests of spending locks, timeout
reservations, raw retention, deterministic resumption and analysis; frozen hashes
for code/data/reviews/groups/prompts/settings/plan. AIB's 126 proposed confirmation
groups may shrink. No source requires expansion merely to replace exclusions.

Sol can implement the runner, import/validation, budget controls, analysis, synthetic
regression fixtures and report/figure pipeline while review is pending. It may run
offline fixtures without review. Development model calls on selected source rows
wait until review/grouping is settled; confirmation waits for the complete freeze.
If reviews never arrive, deliver a verified implementation and methods/limitations
handoff, not a falsely reviewed experiment or final empirical paper. No fresh human
recruitment, inaccessible source or prevention sandbox is a current run dependency.

## Spending and delivery

No inference spending was added in this phase. Reconciled conservative cumulative
accounting: **OpenAI $0.4838404; TypeSafe $0.258774852**, including four retained
unknown-usage reservations. These are not provider balances. Global caps remain
$15/$20 respectively; check all subsequent activity before dispatch. Proposed v5
limits are **$5 per provider total**, with **$0.50 per provider for initial development**.
The full 476-row, all-development upper envelope is approximately $3.52/$1.48;
actual bounded development and deduplication should reduce it. The historical
`six_contextual_plus_specialist_cells` field is a conservative planning overcount:
ProtectAI is eligible only for AIB/INFUSE, not SPML/scope. It is not an execution plan.
See DESIGN.md for atomic reservations and no-automatic-retry rules. Stop on changed
prices, authorization or route. No purchases, recharge or paid Responses fallback.

Work is on `codex/study-v5-design`, based on `codex/dataset-source-expansion` (PR #7).
The remote is private. Deliver a draft PR against that branch; do not merge or rebase
the unrelated historical PR stack. Commit code/docs/count receipts only; never force
add ignored raw data, mappings, review outputs, weights, credentials or local config.
Sol should start its own dependent feature branch and deliver a private PR with green
checks. A final approximately five-page paper/PDF follows evidence and verification,
not a promised positive result. No public publication or submission is authorized.
