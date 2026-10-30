# Controls v4 handoff

Status: execution in progress. The active goal is attachment
`d06ed192-6f72-4221-8caa-7d589d046b11/goal-objective.md`.
The preceding goal turn made substantive progress: preparation, development, full
confirmation launch, four completed configurations and independent verification.
The latest continuation re-polled all three remaining handles and confirmed them live.
Do not mark the goal complete or blocked while these authorized runs are progressing.

## Branch and preservation

Current branch: `codex/context-controls-v4`. Pushed checkpoint:
`4937d5891102b1e5e9087598622abb5b6aade4c1`; private draft PR5 targets
`codex/context-extension-v3`. All ten CI checks passed at this checkpoint.
The completed v3 baseline is `d929836982347374695a0d38797623f8276a1cd5` / draft PR4.
The 5,793 protected earlier files and v3 evidence remain unchanged. No merge, public
publication, new PDF, purchases, new subscriptions or rented compute are authorized.

## Live execution: re-poll these exact handles

| Configuration | exec session | Last observed completed index (moving) |
|---|---|---|
| Luna chat | 85775 | 742 / 2,125 |
| Astra chat | 28541 | 452 / 2,125 |
| Nimble local | 65326 | 893 / 2,125 |

All three returned fresh progress on the current continuation. Do not launch duplicate
processes, change frozen order/settings, or infer termination from an observation timeout.
No failures have been observed on these routes yet. Their sequential runs can take
hours. Inspect new STOP records if present. `continue_transient.py` permits at most ten
HTTP-transient continuations per route, after cooldown, preserving every failed cell.
It never resends a failed confirmation cell. Other error classes require inspection.

## Completed work and evidence

- Sources: actual tau-bench/BIB code audited; private simulator goals rejected as
  assistant-visible requests. TaskTracker published reconstructions verified; AIB
  synthetic fixtures disclosed. Related-work and provenance are in SOURCE-AUDIT.md.
- Owner decision: use defensible published labels and quarantine ambiguity. No human
  review was simulated. The 24-case review packet has blank judgments. Semantic labels
  remain null; evaluation labels are published construction/control status.
- Collection: 108 development rows; 425 confirmation rows (408 matched QA examples,
  204 questions, 27 articles; 17 supplemental AIB fixtures with three benign controls).
  Split/exposure validation passed. Generic attack tactics are not claimed novel.
- Source preparation reproduced in isolation: six commands, 13 byte-identical outputs,
  including the full ignored prepared collection. Receipt: preparation-reproduction-v1.json.
- Exact protocol, prompts and jobs frozen. Every confirmation example gets all five
  conditions for six contextual configurations; ProtectAI is candidate-only.
- Development: 372 attempts, 371 valid responses and one preserved Decisions 503 with
  full reservation. No chat truncation or prompt/threshold tuning. The development
  amendment pins external Ollama update 0.40.13 with unchanged Nimble weights.
- Laya token preflight: all 2,665 prepared payloads fit; maximum 3,671 tokens. Its initial
  confirmation constructor failed before any reservation because analysis statistics.py
  shadowed the standard library. Renamed to metrics.py, with receipt and regression test;
  no frozen inference code/settings changed.
- Jev, Laya, Luna Decisions and ProtectAI confirmation are complete and committed.
  Raw request/parser/accounting audits, independent arithmetic/CSV checks and bootstrap
  verification passed. Decisions retained three HTTP failures and four ties.
- Tables and figures currently cover those four completed configurations. Earlier
  control-error and absolute-error figures were visually inspected; final all-route
  figures still need inspection. ERROR-REVIEW.md contains exploratory fixed-ID source
  inspections and counterexamples, without relabeling or post-outcome exclusions.
- Seventeen offline tests pass. Analysis helpers use metrics.py to avoid import shadowing.

## Accounting and files still moving

All paid routes are finished. Cumulative conservative project totals:
OpenAI **$0.4838404**, TypeSafe **$0.25877485200000006**, under $15 / $20 caps.
These include prior studies and four unknown-usage reservations (one development,
three confirmation); they are not provider balances or invoices. No further paid
requests are planned. Remaining subscription/local routes have zero incremental API
accounting, but calls/tokens are still reported.

The live inference ledger and three unfinished route directories remain untracked to
avoid committing inconsistent snapshots. MODEL-ROUTES.md and recent eligibility/handoff
clarifications are uncommitted. Do not overwrite historical or frozen inputs.

## Finish the actual objective

1. Monitor the three live handles; retain failures and resolve only eligible continuations.
2. For each finished route run analyze.py, verify_analysis.py, verify_bootstrap.py and
   audit_records.py under scripts/controls_v4. Use .venv for numpy; no new inference.
3. Rebuild tables and figures for all seven configurations. Inspect final images and
   extend the exploratory error review with both beneficial and adverse transitions.
4. Run closure.py --require-terminal, then report.py. The report refuses incomplete
   closure or missing per-route checks. Do not claim success from a live snapshot.
5. Inspect/scan intended changes, stage final evidence, then run reproduce_offline.py.
   It exports the Git index and runs 32 offline commands, requiring byte-identical
   analyses, checks, tables, figures, closure and report. It has not run yet.
6. Resolve genuine issues, run relevant checks, inspect final diffs/secrets, commit/push,
   update private draft PR5, and obtain green CI. Verify preservation and remote state.
7. Audit every requirement in the goal against actual evidence before marking complete.

Read REPRODUCE.md for exact offline commands. Do not rerun successful inference or
old frozen commands as a reproduction step. Source-specific conclusions and the limits
of construction labels, tiny benign supplement, lexical controls and fixed attack
family must remain explicit in the final answer.
