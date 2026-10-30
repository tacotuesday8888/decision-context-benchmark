# Extension v3 handoff — confirmation still running

Read the active goal objective first:
`/Users/langqi/.codex/attachments/d0567430-d8c8-4dfb-ab3f-e853b591f9ec/goal-objective.md`.
It authorizes broader empirical execution under all-in OpenAI $15 /TypeSafe $20
caps, including earlier spending/reservations. No purchases, recharge, new accounts,
resellers, public publication or merge. Do not rerun the completed pilot/study.

Branch `codex/context-extension-v3`; private draft PR4, stacked on
`codex/expanded-execution`. Prior complete study commit
`ab3fff2623177327d5fe58eb19a974af7d5dc7e8`; 5,793 files remain hash-protected by
`completed-study-freeze.json`. Integrity and21 offline tests passed. Old study had
5,274 terminal cells. No old outputs/protocol/PDF are changed.

## Frozen experiment

Commit70cfa0c saved collection, protocol,108 successful control development calls,
request/token plans and confirmation freeze before evaluation started. Do not
regenerate freezes or alter prompts/settings/data based on interim outcomes.

-761 task/text pairs;582 distinct texts;138 tasks;9 strata. These are different counts.
- AgentDojo clean offline replay:153 pairs in four domains, no attacks.
- AgentDyn:336 pairs across daily life/GitHub/shopping; inherited clean/injected
  construction labels, actual trace task wording, one common attack template.
- InjecAgent:272 attack-only cases,17 original task fixtures, all62 instructions
  covered via16 published cases/task. No invented clean response or context.
-91 texts cross tasks, max12 tasks/text; no exact/5-gram Jaccard≥0.8 overlap with
 482 older examples. All new sources are confirmation only; old dev data reused.
- Authentic task and candidate comparison plus format/reminder/scrambled controls
 on83 preselected pairs. Constructed controls are not historical alternate tasks.
-11,387 confirmation requests:1,771 each of six contextual configs +761 detector.
- Laya preflight max1,702 input/113head tokens; no truncation in any planned payload.
- Source-specific paired task-weighted error/Brier, text-weighted sensitivity,
 5,000-draw crossed bootstrap; no CI for <5groups. See frozen PROTOCOL-v3.0.md.

Model routes: Jev1.14.0 first-party API; Luna Decisions first-party API;
Luna/Astra Responses separately authorized subscription; pinned local Nimble
Q4_K_M/Ollama0.40.11, Laya multilingual/SDK0.4.17 CPU/eager, ProtectAI v2 CPU.
42 local wording diagnostics were mixed; original question kept. See BACKEND-AUDIT.
No fitted calibration or changed thresholds. Native scores are not assumed calibrated.

## Processes and immutable failures

Four completed arms have terminal exit0:
- Jev handle31554:1,771.
- Luna Decisions handle2746:1,771.
- Laya handle85932:1,771.
- ProtectAI handle84027:761.
Do not rerun them. Analysis and independent raw-record numerical checks passed for
all four; per-arm settled ledger snapshots allow offline reproduction without the
moving global ledger. Figure inspected; remaining analysis is not complete.

Live at last direct polling (counts are snapshots, not current truth):
- Astra handle3156, PID55566:128 completed.
- Nimble handle54609, PID55626:432 completed.
- Luna Responses continuation handle78558, PID61547:144 loop position;
  one preserved failed cell means positions and completed counts differ.
Use write_stdin on the same handles. Observation timeouts do not mean failure.
Check process and raw/ledger state before any restart.

Original Luna Responses handle52857 terminated on HTTP0/curl28 at60.031seconds;
cell a30c6762565ebe6625c11b0a remains failed, empty body, and STOP.json retained.
Runtime amendment-v3.0.1 binds runner+continue_transient.py hashes and permits
only unattempted jobs after>=60seconds or longer numeric Retry-After. No failed
cell retry/replacement; max10 eligible isolated stops per hosted route.
Auth/billing/quota/semantic/accounting errors cannot bypass this rule. Old live
processes loaded original code; fresh ones record amendment hash. A later eligible
terminal stop can be reviewed with:

```sh
python3 scripts/extension_v3/continue_transient.py --config CONFIG
# honor printed cooldown, then only after old process is terminal:
.venv/bin/python scripts/extension_v3/run.py confirmation --config CONFIG
```

Do not run freeze-development/freeze-confirmation again. Amendment-aware freeze
verification is intentional. Never stage the moving global ledger as final closure.
Earlier all-in accounted cost was OpenAI0.0964428/TypeSafe0.051170784; add all v3
entries and outstanding reservations for current totals. Full planned conservative
reserve bounded at OpenAI2.0485926/TypeSafe0.85847496, not expected actual cost.

## Remaining work

1. Monitor three live arms, retain any failures; complete frozen list within policy.
2. Analyze each newly completed arm, independent verification, regenerate figures.
3. Finish source-specific control/reliability interpretation and representative error
   review, keeping labels unchanged. No pooled winner or invented probability.
4. Final request/accounting closure, all-provider totals, source limitations,
   reproduction checks and completion audit against the full goal.
5. Commit/push reviewed raw/results/code, obtain green CI, update private draft PR4.
   No merge or new paper PDF. Goal remains active, not blocked or complete.

Research notes include verified close overlap: benign-instruction-bench already
has request/no-request comparisons, task-clustered analysis and6,000-char judge
truncation. Do not claim a missing ablation or establish novelty from this extension.
Our offline AgentDojo replay ran pinned source ground-truth calls with network
blocked; community collection scripts were only inspected. One source task fails
on `.isoformat()` called on string current_day, excluded without patching.

Current analyzer syntax and21 tests pass; all8 remote CI checks passed at63a2209.
New completed-arm analysis/verifier/figures/audit need the next reviewed commit.
