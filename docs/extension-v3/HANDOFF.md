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

At432721a, control tables and completion-status audit pushed; all8 CI checks passed.
New closure.py reconciles every frozen dev/confirmation job, raw record and ledger
entry under the budget lock. Live snapshot is ignored; --require-terminal correctly
rejects missing/in-flight cells and does not write a false completion receipt.
Current all-in conservative accounting is OpenAI0.2896254 /TypeSafe0.154397208,
including preserved prior spending. These are not refreshed balances/invoices.

Luna handle39721 terminated with444completed +3failed after another empty HTTP0/
curl28 failure `aa88b907dbf98f1972e2a798`. That failure is base-policy eligible.
The base continuation helper nevertheless stops on the prior resolved HTTP200
exception. Additive amendment-v3.0.3 and continue_reviewed.py fix receipt handling:
existing receipts are hash-verified unchanged; only unresolved base-eligible stops
receive new receipts. The one-failure HTTP200 exception is not generalized, and
all stops still count toward10. Four regression tests cover idempotence, existing
special-case receipt, semantic-error rejection and changed-failure rejection.
25 offline tests pass. New Luna handle31950 now continues only unattempted cells;
Astra58329 and Nimble54609 remain the other active handles. Confirm live state before
restarting anything. Prefer continue_reviewed.py for future base-eligible stops;
never bypass a new unsupported semantic/auth/billing/quota/HTTP200 failure.

Latest progress: live handles31950Luna,58329Astra,54609Nimble polled concurrently
for30seconds; observed loop positions513/512/976 respectively. No new failures in
that interval. Final accounting gate now has five operational regression fixtures:
reject missing cells, retain unknown-usage reserves plus prior spend, reject extra
raw records, reject settled-cost mismatches and enforce all-in caps.30 offline tests
pass. These fixtures are not generated benchmark examples/gold labels.

Source-artifact preparation reproduction now passed separately:494 pinned local
source files/replay copied into isolated export; prepare.py and independent
validate_collection.py reproduce five frozen outputs byte-for-byte (including full
prepared text, manifest, summary, exclusions and validation receipt). Original files
unchanged. No new model calls, upstream code/replay or downloads. New utility and
preparation-reproduction-v1.json record hashes and exact scope.
Latest polled loop positions:618Luna/591Astra/1065Nimble; same handles31950/58329/54609,
all live with no new failures in that observed interval.

Raw-record audit tightened without inference changes: detector windows must equal
1+ceil(max(0,input_tokens-window_tokens)/(window_tokens-overlap_tokens)); all761
scans/831windows pass. Nimble reported token usage must fit declared8194 bound,
without claiming per-call observed allocation. All four completed raw audits pass
with updated verifier hashes. Regenerate final isolated reproduction after these
verification/display-table changes before claiming current artifact identity.

Current isolated reproduction now PASSED19 commands /39 byte-identical artifacts,
including updated coverage audit and source/control display tables. Latest observed
loop positions859Luna/745Astra/1425Nimble, same three live handles. No new failures
in these checks. Complete-arm analyses remain four configurations, not final study.

## Five-arm checkpoint: Nimble completed

Nimble handle54609 exited0 after1771/1771. Do not restart it. All1771 parse
validly with no ties/failures; independent raw arithmetic, request/response audit
and18 reconstructed primary intervals passed. Total complete-arm cells7845.
Figures regenerated and actually inspected; native reliability grid includes
Nimble. Source/control interpretations saved without tuning any settings.
Isolated staged export passed23 commands/47 byte-identical artifacts.

Still-live handles: Luna31950 at loopposition1085/1771 (three preserved failures);
Astra58329 at884/1771 (one preserved failure). These are historical observations,
not terminal counts. Poll original handles; never restart a live process.
Latest accounting remains0.2896254 OpenAI and0.154397208 TypeSafe all-in.
Global moving ledger deliberately remains unstaged. No final closure receipt yet.

Continue through both remaining arms, final source-specific report/controls/error
review, all-cell closure, regenerated inspected figures, isolated reproduction and
private draft PR/green CI. Goal remains active; slow live inference is not a blocker.

## Independent control uncertainty verification

The second explicit-multiplicity bootstrap implementation now checks both primary
and preselected-control contrasts, taking control IDs from frozen confirmation
jobs. All72 primary and288 control cases pass for Jev/Luna Decisions/Laya/Nimble,
including insufficient-group omissions. No analysis estimates, prompts or settings
changed. This supersedes earlier statements that only primary intervals received
independent reconstruction. Numerical assertions remain full precision; displayed
receipt endpoints round12dp for cross-platform serialization.

## Second Astra transient stop

Astra handle58329 exited0 at loopposition1079 with a preserved failure:
`6d3310f4ceaec83cf6d0090d`, HTTP0/curl28,60.0184s, empty body, no accounting
error. The v3.0.3 reviewed-continuation helper verified prior receipts and added
a hash-bound receipt under unchanged transient eligibility. Cooldown was already
zero. Continued only unattempted jobs with handle78481. Do not reuse58329 as live.
Total preserved transport failures now five (Luna3/Astra2). Luna31950 remains
live, latest observed1427/1771. No request was retried or replaced.

## Two additional transport stops; v3.0.4

Luna31950 exited0 at1445 with failed `282dac5e77ed9db98cef36de`: HTTP0/curl28,
empty body,60.0149s. Its base-policy receipt preserves the failure; after cooldown
continued with handle99369 (observed1466/1771). Astra78481 exited0 at1090 with
failed `21d74dd5ed29cfa05988e36c`: HTTP200/curl28,60.0313s, only SSE created and
in_progress events, empty output, no usage/provider error/terminal event.

Committed v3.0.4 before further Astra evaluation: one exact hash-bound exception
plus unchanged base transient eligibility and prior receipt validation. New helper
`continue_reviewed_v4.py` supports future eligible stops without replacing prior
receipts. The exception checks structured errors; the echoed prompt's word
unauthorized must not be mistaken for an authentication error. The conservative
keyword guard remains for base HTTP failures. Four transport-only regression tests
passed (34 total); helper rerun was idempotent. No model/prompt/output setting or
failure changed. Astra continuation handle36506 is now live; poll it directly.

Total preserved failures: Luna4, Astra3. Ten-stop-per-route limit remains. No
failed cell has been retried. Handles31950/78481 are terminal; do not poll as live.

## Luna Responses complete

Handle99369 exited0 after1771 planned attempts:1767 valid,3 http_error,
1 interrupted_stream. No retry. Analysis/raw-request/accounting checks and
independent9 primary+36 control uncertainty checks passed. Six complete arms
now9616 cells. Astra36506 is the sole live handle (last seen1267/1771).
Updated effect plot inspected; Boolean probability panel hidden rather than
invented values or irrelevant axes. Numeric/control interpretation saved,
including high absolute direct-harm misses despite improvement.

Six-arm isolated reproduction passed27 commands/53 byte-identical artifacts,
including all independent control checks. Preserve completed raw Luna records.
Remaining live Astra36506 was observed1299/1771; final closure/report/CI remain.

## Final report preparation while Astra runs

Added `report.py`: final markdown tables require terminal closure, matching ledger,
all seven analyses/audit receipts, and unchanged raw record hashes. Missing closure
correctly refuses output. Evidence-binding assumptions checked against all six
complete arms; no final report yet. `reproduce_offline.py` conditionally reruns
closure/report and compares their artifacts when report.md is present. Full final
branch remains to be exercised after Astra completes. No claim of final validation.
Astra36506 remains live; latest observed1421/1771, still three failures preserved.
The six-arm CI checkpoint0644d48 passed all eight checks.

## Terminal extension and final reproduction

All seven configurations are complete: 11,387 confirmation attempts, 11,367 valid
answers, 13 exact-threshold abstentions and seven preserved transport failures.
Closure reconciles all 11,495 development/confirmation records and settled or
unknown-usage reservations, with no missing/pending/in-flight cells. No failed
request was replaced. All earlier live-status entries above are historical.

Final isolated export passed 33 commands and reproduced 62 artifacts byte-for-byte,
including all analyses, independent raw/arithmetic/bootstrap checks, figures, closure
and report. The first export found an absent ignored lock directory; closure now
creates it and a regression test covers clean exports. All 35 tests pass. All
5,793 protected historical files remain unchanged. Configured-secret scan passed.

Read ABSTRACT.md for the plain-English finding, ASTRA-ACCESS.md for standalone
subscription-request traceability, and NEXT-RUN.md for the separately proposed
broader study. Subscription access remains authorized; an API-only migration was
explicitly withdrawn, so no route change or unnecessary paid check was performed.
Astra processed 1,771 confirmation requests (1,768 valid), reporting 786,259 input
and 40,965 output tokens on valid responses. All-in metered accounting is
$0.2896254 OpenAI / $0.154397208 TypeSafe, not provider invoices or fresh balances.

The controls limit the claim: task-versus-candidate improvements alone do not prove
meaningful task information helps; Astra's eight-pair direct-harm subset shows no
advantage over reminders or scrambled tasks. No universal winner, calibrated-safety
or prevention claim. No new PDF, public publication or merge. Final private PR/CI
status is checked after pushing the reviewed commit.

Artifact commit `7141b44` passed all eight remote checks. Private PR4 remains open
and draft; canonical checkout/remote matched and working tree was clean. This
closing documentation commit records that verified delivery. The bounded experiment
is complete; NEXT-RUN.md remains proposed work, not an active inference run.
