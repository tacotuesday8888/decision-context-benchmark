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

Completed-arm raw records, analysis, verifier, inspected figures and backend audit
are pushed at2114e80; all8 remote CI checks passed there. The later representative
error/fixture-keyword review is pending a follow-up commit. Read ERROR-REVIEW.md: the
frozen narrow credential-like regex does not remove prose/serialized details in
published fixtures. This is a documented limitation, not an outcome-based exclusion.


## Subsequent checkpoint

Astra original handle3156 terminated after261 completed plus one HTTP0/curl28
failure (edc449dacce83221b68d3adb, format control). Raw empty body and STOP preserved.
Existing amendment continuation receipt7375324915f5435f0edee0772ec87bdd0d1a5200367ae49e28749ef903f6e93f
was created; cooldown elapsed. New Astra handle58329 resumes only unattempted cells.
Do not poll/restart original3156 as live. Nimble54609 and Luna78558 remain live.

New research comparison explicitly maps prior ablations/calibration/interfaces.
Two System One protocol files fetched at pinned revision match upstream manifest.
Independent explicit-multiplicity bootstrap verification passed54 primary intervals
across Jev/Luna Decisions/Laya. Four fixed-bin reliability grids generated; figure
SVG hashes/timestamps made deterministic. Isolated staged-export reproduction is
being added; do not claim that check passed until its receipt exists and is verified.


Isolated staged-export reproduction PASSED:14 commands,31 byte-identical analysis,
CSV, verification and PNG/SVG/input artifacts. Receipt offline-reproduction-v1.json
binds the input index tree; existing installed Python/numpy/matplotlib used. No new
inference, credential/weight export, fresh install or raw-source rebuild claimed.
All54 primary intervals independently reconstructed; four reliability grids and
updated common-scale effect plot inspected (figure-visual-review-v1.json).
Remaining work includes a dedicated terminal raw-response/request/accounting audit,
with explicit per-route identity/usage checks, as well as remaining live arms and
final source-specific control interpretation. Do not infer full completion from
numerical reproduction alone.

At83011ff, six inherited CI jobs passed and both v3 jobs failed only at receipt
byte comparison: one independently recomputed bootstrap endpoint differed by
3e-17 on Linux. All numerical assertions passed. The follow-up keeps full-precision
comparison tolerance unchanged and rounds only independently computed receipt
endpoints to12 decimal places. Primary estimates/intervals and frozen experiment
remain unchanged. Regenerate verification receipts and isolated reproduction;
obtain green CI before calling this checkpoint verified.

A read-only Nimble runtime snapshot verified current loaded digest/Q4_K_M and8194
context. It is not per-request allocation evidence; v3 stores startup metadata per
record but lacks old study's per-call loaded-model snapshot. Final audit must say so.


Dedicated completed-arm raw-record audit now passes for Jev/Luna Decisions/Laya/
ProtectAI:6,074 terminal cells; exact frozen requests reconstructed from recorded
candidate/task strings checked against manifest hashes; raw responses reparsed;
model metadata, routes, usage, Laya preflight, ledger reserves/costs checked.
Jev1,759 decisions+12ties; Luna Decisions1,770+1tie; Laya1,771; ProtectAI761scans/
831forward windows. No false claim of per-call Nimble loaded context or Laya dtype.
Script audit_records.py is pure offline and uses no credential helpers/weights.
Include these audits in CI and the next isolated reproduction receipt.

Latest isolated reproduction PASSED18 commands /35 byte-identical artifacts,
including all four raw-record audits. The rounded verification receipts preserve
full-precision numerical assertions and leave primary estimates unchanged.

Luna handle78558 is now terminal:367completed +2failed. Second failure
`e883659b52b7095b4d2c917c` is empty-body HTTP200/curl28, missing terminal event,
not a semantic model answer. Original continuation helper correctly rejected it.
Additive amendment-v3.0.2 and continue_empty_timeout.py bind this one exact failure/
STOP, require subscription route/empty body/curl28/exact parser status, preserve
all old files/settings, and create a cooldown receipt for unattempted cells only.
Cooldown elapsed; a new Luna runner will be started after this checkpoint. Base
runner and v3.0.1 remain unchanged; new raw records still identify the base runtime
amendment, while the separate receipt identifies this additive resolution.

Latest pushed code/results commit:e7127a1. Luna continuation is confirmed live on
handle39721 (old78558 is terminal); Astra continuation58329 and Nimble54609 are
also confirmed live. Latest observed loop positions:374 Luna (two failed retained),
372 Astra (one failed retained),774 Nimble. Poll these same handles, not old ones.
Check current disk/process evidence rather than treating these counts as final.

All eight remote CI checks passed at e7127a1 after the receipt fix and raw audits.


New source/control summary tables and CONTROL-RESULTS.md distinguish useful task
information from format/reminder effects. Initial examples: Jev's selected InjecAgent
direct-harm task benefit disappears against empty-field/reminder; Luna Decisions'
selected stealing benefit remains with wide intervals; Laya can beat reminder but
still worsen versus candidate alone. These are same-subset predeclared contrasts,
not new labels or post-outcome prompt selection. All contrasts and denominators
are saved, with no pooled winner. Completion-status audit explicitly keeps remaining
three arms and final closure incomplete. tables.py now reproduces display CSVs;
full staged reproduction will include it at the next/final checkpoint.
