# Decision Context Benchmark: v5 design and execution contract

Design date: 2026-10-30. Status: research and preparation; **no v5 confirmation
inference has occurred**. This is a narrow, source-conditional replication and
extension, not a claim of a new general defense. Evidence, code, counts and
remaining dependencies are in RESEARCH.md, HANDOFF.md and results/study-v5/.
The original pilot and v2/v3/v4 studies remain historical, immutable evidence.

## Question and distinct targets

Does revealing the legitimate user's task improve a fixed decision interface's
ability to identify unauthorized instructions in external content, beyond the
benefits of formatting, reminders or extra text? Does governing system policy
provide additional information? These are separate interventions.

1. **Indirect-instruction detection:** does an external candidate attempt to direct
   the assistant outside the authentic task/policy authority? Ordinary procedures,
   quoted instructions and imperatives addressed to people are not attacks merely
   because they contain commands. Topical relevance does not establish permission.
   Harmfulness, an incorrect fact, and an unsafe assistant continuation are different
   constructs. Pure factual poisoning without an instruction is outside this target.
2. **Direct policy conflict (SPML):** does the submitted user message request behavior
   contrary to the system policy? This is not indirect tool injection, nor proof of
   malicious intent. The user role is retained throughout.
3. **Constructed scope sensitivity:** does the same external instruction receive
   different decisions when the user explicitly grants versus withholds permission?
   Labels intentionally change. This is not a mislabeled wrong-task control.
4. Native score ranking/forecast quality is secondary and distinct from hard
   decisions. No classification result establishes actual agent prevention.

Gold is defined with the full original available context, including in arms that
hide it from the detector. Thus context-free error measures information deprivation
relative to that task, not whether a reader could know an absent fact. A reviewer
can mark insufficient context and uncertainty. Do not force those cases into binary
gold. The user chose another agent for review; **agent review is the planned review
mode, not independent human validation**. See REVIEW.md for admission and disclosure.

## Bounded source portfolio

Use the saved selection, not an expanded scrape. The row counts below are upper
bounds before review exclusions and final grouping. Provenance/hashes are in
preparation.json, source-receipts.json and group-audit.json.

| Arm | Prepared units | Proposed development / confirmation | Analysis status |
|---|---:|---:|---|
| ppradyoth AIB | 158 single-observation cases from 182 | 31 / 127 rows; 31 / 126 provisional groups | Main released-source arm after external agent label and workflow-family review. Confirmation upstream labels: 100 unsafe / 27 safe. |
| SPML | 200 rows, 100 paired policies from 100 candidate-linked components | 62 / 138 rows; finance+travel / seven remaining coarse domains | Separate policy-conflict arm. Seven confirmation domains, 69 policy pairs; cannot claim 138 independent tasks. |
| INFUSE static reconstruction | 70 rows, 35 clean/attack file pairs | 40 / 30 rows; two / eight connected task/template groups | Descriptive coding-source check. Fifteen confirmation task pairs, eight conservative groups. Not observed trajectories. |
| Scope-switch construction | 48 rows, 24 pairs, eight operation families | 12 / 36 rows; two / six operation families | Separate synthetic diagnostic. Research-agent authorship, explicit permission changes, independent agent review pending. |

Total 476 review records; proposed confirmation upper bound 331 records. The
original 16,194-record preparation is not a held-out test. The original ungrouped
v5 selection is also not the final split: **grouped-review-v2.jsonl supersedes its
split_proposal fields**. Source counts are not additive independent-group counts.

AIB extraction requires one initial user message and one tool-result message with
no multi-turn flag. Twenty-four cases remain quarantined rather than selecting a
convenient turn. Exact candidate text and original task/policy are retained. Assistant
reference replies, expected actions, attacker intent, severity, execution rules,
canaries-as-metadata and tool catalogs are not inputs. Tool catalogs can themselves
be poisoned. If a judgment requires unavailable trusted tool semantics or earlier
state, mark it unclear. Do not invent a capability description to resolve it.

SPML uses pinned System Prompt/User Prompt fields, never a fictitious tool role.
One source-negative and one degree-1 positive are hash-selected from the same policy
within each of 100 components. Degree 1 is a construction rule, **not a validated
subtlety score**; some are overt role changes. The set deliberately enriches
low-degree attacks; it does not estimate natural prevalence. 840 exact policies
collapse to 740 components through shared normalized candidate text; the lexical
policy heuristic found no additional edges at its threshold. That is evidence of
limited detection sensitivity, not proof of independence. Use coarse-domain closure
for separation and primary uncertainty; agent review may merge but not split these
conservative groups merely to gain precision.

INFUSE uses pinned task instructions and the first declared task-order surface only
when it is a literal FILE_CONTENT/CONFIG_FILE available in the repository. It copies
that static file as clean, then applies prefix+template, comment wrapping and position
from the pinned default attack config. Five tasks are excluded with reasons. No
Docker image, setup script, tool command or upstream code was executed. A real agent
might encounter a different observation after setup; never call these observed
trajectories or a reproduction of INFUSE's ASR. Do not strip conspicuous prefixes.
Research-agent task-family merges and reused payload IDs form connected components;
both sides of every clean/attack pair stay together. Review clean files for relevant
instructions and possible embedded anomalies rather than assuming “clean” is semantic
gold. Report distinct payload templates and task families separately.

Scope pairs were authored in this design chat, with explicit user grant/withhold
contracts and a shared synthetic delegation policy. `scope_pairs.py` contains all
24 scenarios; no evaluated model generated their sole labels. The external reviewer
must approve or dispute the rule-derived labels. No naturalistic or hidden test claim.

## Review, grouping and exposure before inference

Run REVIEW.md. At least one separate, prediction-blinded agent reviews all selected
primary candidates and the semantic grouping. It must not be an evaluated model
providing its own sole gold. A source-label disagreement, unclear context, or required
group merge blocks admission until independently adjudicated or conservatively
excluded. Store every judgment, rationale and exclusion; never replace rows based
on model performance. Human review would strengthen validity but is not silently
required after the user's explicit agent-review decision.

AIB's 157 current lexical components are provisional upper bounds. Match its released
seed provenance and group semantically shared workflows, document templates and
near-duplicate instructions. `aib-seed-links-v2.json` links 120 of the full 182 cases to
123 released YAML seeds by exact input-message content; 62 unmatched cases are not
certified independent. Do not infer human authorship from hand-written-looking YAML.
Obtain grouping proposals without source labels/predictions. If merging crosses the
proposed split, rebuild the group split **before any development call**, save a new
version and all reasons. Do not reassign a development-exposed family to confirmation.

Exact/normalized candidate and task matching and candidate 3-word Jaccard >= .5
against all four historical prepared collections found no hits for the 428 source
candidates. This is a bounded project-exposure screen, not a training-data audit of
closed models. Public pretraining exposure is unknown. Scope constructions are new
here but have a common authored structure. The cross-source lexical audit compared
77,204 pairs across all 476 records and found no matches under the same candidate
threshold/exact-task rule (`overlap-audit.json`). Review semantic cross-source
templates as well; zero lexical hits do not settle that question.
Old InjecAgent/AgentDojo/TaskTracker cases are not additional fresh confirmation.

## Conditions and exact prompts

`prompts.py` is the executable prompt proposal. Freeze its bytes and every final
request, not just this prose. Serialize evidence as sorted JSON. Candidate bytes,
role marker, question and answer orientation remain fixed within a source/model.
Metadata, source IDs, labels and rationales never enter requests.

AIB and scope use eight conditions:

| Condition | Task field | Policy field |
|---|---|---|
| candidate | omitted | omitted |
| format | empty | empty |
| task | authentic | empty |
| policy | empty | authentic |
| task_policy | authentic | authentic |
| policy_reminder | generic reminder | authentic |
| policy_length | neutral character-matched filler | authentic |
| policy_scrambled | deterministically permuted task words | authentic |

This is a 2×2 task/policy factorial plus presentation controls. Primary task effect:
`task_policy` versus `policy`, holding governing policy fixed. Task-specific evidence
also requires comparing `task_policy` with `policy_reminder` and `policy_length`.
The scrambled comparison is diagnostic: it retains task vocabulary and sometimes
meaning. Policy effect: `task_policy` versus `task`; interaction: task effect with
policy minus task effect without policy. These secondary factorial contrasts must
not be substituted for the primary contrast after results are seen.

INFUSE has no separate trusted policy field: candidate, format, task, reminder,
length and scrambled. SPML analogously varies only the system-policy field and uses
USER_MESSAGE, not CANDIDATE. Scope uses its separate scope-conflict question. Never
pool those targets under one accuracy figure.

The neutral filler repeats `Context unavailable. ` to match the context's character
length. This is a **character-length control**, not an exact token control. Audit
and publish per-route token differences. A prespecified token-matched sensitivity
may be added before freeze if all routes expose a reliable tokenizer: deterministic
neutral padding, <=1 token difference, no task words, no selection using predictions.
If not, retain the transparent character control and limit semantic-identification
claims. Semantic information cannot be isolated by a single padding intervention.

The current question strings are short enough for the existing Laya head audit;
keep the complete question and candidates. No tail-truncation workaround. Exclude
an over-limit case from that model's common comparison population before inference,
retain its planned disposition and report source/model-specific coverage. Frozen
per-model populations and their intersection must both be available.

## Model panel and development

Retain six contextual configurations: Jev `jev-1.14.0` first-party native noul;
`gpt-6-luna` Decisions predicate; Luna Responses (none reasoning, 256 output cap);
Astra Responses (low, 2048 cap); pinned local native Nimble Q4_K_M; pinned local Laya
multilingual CPU/eager. ProtectAI v2 is a candidate-only specialist baseline **only
for indirect sources**; on SPML/scope it is out of construct and must not be ranked
as a policy/authorization model. Seven configurations are six model IDs, and Luna's
two interfaces are not independent model families. Local settings/revisions/digests
come from docs/controls-v4/MODEL-ROUTES.md and its preserved adapters; use the v4
Ollama 0.40.13 amendment, not the older 0.40.11 assertion.

The primary statistical family is the two hosted decision routes. Other routes
provide descriptive comparisons, not selection of a favorable winner. Retain weak
Laya/Nimble results and interface failures. New trained detectors would introduce
training/exposure and hardware costs without addressing label validity. A fixed
candidate-only lexical shortcut baseline (`ignore previous`, `system prompt`,
`do not tell`, `new task`, casefolded substring OR) and constant allow/block baselines
are free diagnostics, not competitive safety systems. Freeze literal patterns;
do not add phrases after errors. Existing ProtectAI already covers a specialist.
CAD/Task Shield require different trained/filtering or agent-level systems; discuss
as related methods, not silently approximate them with our prompt.

Use at most 4 development examples per source for initial access/parser/coverage
smoke checks: longest candidate per source label plus hash-first unused groups to
four; if a source lacks four groups, use remaining distinct pairs. Reuse these for
operational fixes. No accuracy optimization, prompt sweep, model shopping, threshold
fitting or calibration fitting in v5. Broader development collection is not a call
quota. Threshold 0.5; ties are explicit abstentions. Responses supply Boolean only.
Retain refusals/truncations/invalid output separately from ordinary wrong predictions.
Laya head+sequence token audit has no model forward pass. Hosted access is historical
until Sol performs bounded development checks with the exact new questions.

Deduplicate exact payload hashes within configuration and split before dispatch;
maintain all case/condition references to the response. This matters for scope pairs:
identical candidate-only inputs must reuse the same response, not become independent
noisy opportunities. No cache shared across development and confirmation. Each call
is standalone; no history, previous response, few-shot labels or evaluator feedback.

## Analysis and uncertainty (freeze before results)

Main source: externally agent-reviewed, eligible AIB confirmation cases. Primary
endpoint is the paired change in **balanced error**, control minus task+policy,
positive favoring task context. Within each gold class average case errors inside
each reviewed workflow group, then equally average those group means; average the
two class error rates. Report raw case-weighted FPR/FNR/error as additional endpoints,
with denominators, and unweighted source-label agreement on the same eligible rows.
No pooling across datasets or policy/detection constructs.

Primary family: two native hosted routes × three contrasts (task+policy against
policy, policy+reminder, policy+length), six two-sided tests. Use paired group sign
randomization of per-group contributions with fixed class denominators; exact
enumeration when feasible, otherwise 100,000 deterministic draws with +1 correction.
Use Holm family-wise alpha .05. Show pointwise paired cluster-bootstrap 95% intervals
and Bonferroni 99.167% intervals for those six contrasts, 20,000 seeded resamples.
State exchangeability and source-conditional sampling assumptions. The study is not
a randomized population sample. Do not call a benefit specific to task semantics
when only the candidate/empty control improves. Even superiority to both controls
is qualified evidence for this intervention, not an internal-mechanism proof.

AIB resampling uses final reviewed workflow components; sensitivity groups by broad
source attack category and workflow domain without interpreting category variants
as new tasks. SPML resamples its seven or fewer held-out domain components; also
show policy-pair descriptive effects. INFUSE resamples connected task/template groups;
show every group effect. Scope reports both-correct pair fraction, direction of score
change and four-way pair transitions; cluster by operation family and show all families.
Small (<20) cluster intervals are exploratory, unstable and do not justify precise
population claims. If a bootstrap draw lacks a class, mark invalid, report its rate,
and decline inferential claims if >5% invalid; never silently reweight away the issue.

For each contrast report valid paired coverage and all-planned missingness bounds.
An invalid response is unknown, not benign or an attack. Compute extrema of the
fixed-weight paired error contrast assigning each missing prediction all allowed
binary values, retaining known outcomes. Report fail-closed/fail-open operational
sensitivities separately; neither is measured task utility. Review exclusions are
fixed before inference; parser failures are not post-hoc semantic exclusions.

For native scores, report AUROC/average precision only where both classes exist,
class/prevalence-aware score distributions, Brier and log loss for documented
probability outputs (Jev/Luna/local noul), plus 10 fixed equal-width reliability bins
with counts. Clip only for log loss at 1e-6 and retain unclipped values. Brier/log loss
measure forecasting performance, not calibration alone. Small samples do not support
calibration certification. ProtectAI maximum-window scores support ranking; do not
call them calibrated document probabilities. No invented chat probabilities.
No 1%-FPR threshold fitting: 27 proposed AIB benign confirmation examples are
insufficient. Even zero false positives gives a one-sided binomial 95% upper bound
of about 10.5% before clustering (computed receipt has exact value).

Sample-size rationale: all eligible AIB single-observation cases are affordable and
cover the released source without cherry-picking outcomes. At 126 independent group
means and paired discordance .25, a rough 95% half-width is 8.7 pp and an 80%-power
detectable difference about 12.5 pp, before imbalance/clustering/multiplicity. These
are planning scenarios, not achieved-power promises. About 384 independent groups
would be needed for a 5 pp half-width under that approximation. This study is suited
to moderate effects and transparent counterexamples, not proving small improvements
or equivalence. Other arms have much fewer groups. Do not purchase more calls to
pretend that extra variants increase independence.

Required tables: source/review/group flow and exclusions; route/settings/coverage;
source-specific FPR/FNR and paired effects; native score diagnostics; all failures
and budget reconciliation. Figures: paired-effect forest by source/model with valid
pair counts; source-separated false-alarm/miss tradeoff; scope-pair transition chart;
optional fixed-bin reliability plot when counts support interpretation. Derive
figures/tables from checked JSON, render and inspect labels, intervals and denominators.

## Budget, freezing and recovery

feasibility.json verifies the final v4 ledger digest and sums entries against the
closure: cumulative conservative OpenAI $0.4838404, TypeSafe $0.258774852, with four
unknown-usage reservations retained. These are **not account balances**. Reconcile
again against current processes/all subsequent ledgers before paid calls. Global
caps remain $15 OpenAI / $20 TypeSafe including all earlier work, failures and pending
reservations. V5's smaller operational limit is $5 per provider including development
and recovery; initial development at most $0.50 per provider. No purchases, recharge,
paid Responses fallback or provider-route substitution.

The full 476-row development+confirmation upper envelope at conservative byte-based
reservation is about $3.52 OpenAI and $1.48 TypeSafe. Actual bounded development and
deduplicated confirmation should be lower. See feasibility.json: this is a reservation
proxy, not measured usage or a formal tokenizer bound. Recompute exact frozen request
costs, current rate/cache multipliers and per-call bounds before execution. Prices
verified 2026-10-30: Decisions $0.10/M uncached input; Jev $0.042/M input; output free
on those native routes. Subscription Responses has zero incremental metered API cost
only if the existing authorized route still works. Verify access, never infer it from
a model list. No model upgrades to pursue better results.

Implement a shared provider budget lock and atomically persist a reservation before
network dispatch; include global historical subtotal and all v5 active workers.
Unknown usage retains full reserved cost. Settle once from validated returned usage;
never add inherited subtotals to the same ledgers twice. Stop on unexpected price,
billing/authentication/model mismatch, cost exceeding reservation, or corrupt evidence.
No automatic retries; no releasing a timeout reservation merely because the client
saw no result. Freeze development and confirmation separately with code/source/
review/prompt/plan/settings/group hashes. Freeze before the first confirmation request.

Recovery is operational, not scientific tuning: retain every original attempt and
partial stream; document transport failure, reserve anew for an explicit bounded
retry batch, link attempt IDs. Prespecify first-attempt results as primary and
first-valid recovered results as sensitivity; never rerun ordinary wrong answers.
Missing/failed cells may remain terminal. A changed question/model/label/group is a
new experiment version, not a recovered cell. If a post-freeze label error is found,
retain frozen-label primary results and add a transparently labeled correction
sensitivity; do not optimize corrections against predictions.

## Prevention and final paper decision

Do **not** implement a prevention experiment in this bounded v5 run. It would need
an audited sandbox, authenticated permission boundaries, attack-free task utility,
blocked-benign costs, attack success/state verifiers and baseline-no-agent checks.
INFUSE's documented historical verifier errors show why detector scores cannot
substitute. A future separate authorization can compare unguarded, candidate-guard
and context-guard agents on paired tasks with both task completion and attack success.

A final approximately five-page paper/PDF is appropriate only after the specified
review mode is accurately disclosed, eligible labels/groups and protocols are frozen,
execution is terminal or explicitly bounded-incomplete, raw reconciliation passes,
analyses independently recompute, and rendered figures/PDF are checked. Negative,
mixed or uncertain results are acceptable. If agent review remains unavailable,
Sol can finish implementation, tests, source-label descriptive diagnostics and a
methods/limitations report, but not silently label that the reviewed confirmation
study. No human-validity, novelty, low-FPR safety or prevention claim. Private draft
PR delivery is authorized; no public publication/submission or unrelated-stack merge.
