# Handoff: stronger task/policy-context experiment

Paste the following into `/goal` in the experiment chat. It authorizes continuing
the already requested research within the existing provider caps, not purchases,
public submissions, or claims of independent human review that did not happen.

```text
Continue Decision Context Benchmark in this repository. Do substantive source/label
auditing, build the collection and adapters, freeze the next experiment, execute
eligible work, and finish integrity/analysis checks. Preserve every completed study
and failure. Do not start by drafting another paper or rerunning the old v4 cells.

Read AGENTS.md, docs/source-discovery/README.md, METHODS-COMPARISON.md, CONTEXT-METHODS.md,
the four source-discovery audit JSONs and catalog, review-preparation.json, and
docs/controls-v4/COMPLETION-STATUS.md, RESULTS.md and MODEL-ROUTES.md.
Inspect actual current Git state, files, prior exposure, budget ledger and processes.
The broad audit found 27 inventory entries, not 27 independent ready-to-run datasets.
Follow the primary URLs/revisions in the audits, not search snippets or remembered
headline counts. The Hugging Face connector works; individual repositories can be
gated or unavailable. Do not accept access terms or share account details silently.

Question: Does authentic information about the user's task or governing policy help
decision models distinguish authorized instructions from prompt injection? Separate
user-task context from system-policy context. A detector result does not establish
that an agent resists an attack or successfully completes its task.

Preparation already exists: scripts/source_discovery/prepare_review.py materialized
16,012 SPML and 182 AIB review records under ignored data/raw/source-discovery, with
hashes/counts in review-preparation.json. Reproduce it offline and inspect it before
writing replacement adapters. SPML has840 exact policies, not necessarily840 independent
families. One empty user prompt is preserved. AIB24 multi-turn cases and19 multiple-
tool-result cases remain unresolved. All semantic gold is blank and inference_eligible
is false. Do not claim16,194 validated held-out examples or run them all automatically.

Start with these concrete source feasibility audits:
1. SPML: recover actual System Prompt/User Prompt, group policy/template families,
   inspect subtle positives and ambiguous labels. Released size is 16,012 rows, not
   an independently verified 20,000. This is policy-relative evidence. Submitted user
   instructions are not lower-trust tool content; do not silently change their roles.
2. ppradyoth/AgentInjectionBench: use the pinned 182-case source (142 unsafe/40 safe),
   not Sentinel Den's smaller fixtures. Extract real user instructions, system policy,
   original tool-result candidate and required tool semantics. Reference assistant
   replies, expected outcomes, notes, canary labels and severity must never leak into
   detector payloads. Do not count every unsafe action as an injection automatically.
3. ASB: verify exact OPI observation construction against its 51 released normal task
   strings/10 agents and tool records. Do not substitute raw attack descriptions for
   what a victim actually sees or inflate task counts with tool variants.
4. INFUSE: pinned repository has 40 task instructions/56 attack configs. Reconstruct
   actual payload assembly and observed file/tool text. The indexed HF trajectory card
   was readable, but live Hub lookup failed; released full traces are not verified.
   Read scripts as data before considering isolated execution. Audit verifiers for
   firing merely on the injected text. Keep any prevention experiment separate.
5. Tensor Trust: preserve actual game defense and policy, with player/defense/family
   grouping. Its 570 extraction and 776 hijacking benchmark rows are attack settings,
   not a balanced detector test. Clarify data permissions; do not redistribute raw
   data by assuming the game-code license covers it. Use a separate policy-game arm.

Also use NotInject for false-alarm stress; Boundary Pairs for paired authorization
stress; NVIDIA agentic IPI for synthetic task-aware attack stress (1,272 rows but
722 exact distinct injection texts). Keep these arms separately labeled and reported.
PromptShield is a large full-request detector benchmark: its prompt can contain the
concatenated task and input. It is ineligible for a fixed-candidate context ablation
until authentic boundaries can be reconstructed. BrowseSafe++ is a task-bearing matched-
page lead requiring access/terms review; its hidden test must not be tuned on or have
labels recovered. Do not spend cycles treating PINT's example YAML as its full corpus.

Build a canonical review collection containing original source/revision/row IDs,
trusted user task, trusted policy, required tool semantics, exact untrusted candidate,
source-channel type, pair/family/task IDs, construction method and upstream labels
with their actual meanings. Mark unavailable fields explicitly; never invent authentic
context. Keep original label, proposed semantic judgment and review status separate.
Preserve immutable upstream bytes and source hashes under ignored raw-data paths.

Define injection precisely before assigning labels. Ordinary instructions between
people, quotes, and legitimate task steps are not automatically attacks. Attack
success, unsafe actions and injection presence are separate labels. Create a blinded
review packet with no model predictions; obtain independent judgments/adjudication
where possible. If genuine independent human labels are unavailable, retain blanks
or explicitly use construction labels. Never call an agent's judgment human review.
Do all other preparation while a necessary review/access decision is pending, then
report the exact blocker rather than silently weakening the primary claim.

New constructed datasets are permitted if necessary: disclose human/AI contributions,
use separate development/held-out scenario families and auditable task/authorization
rules, pair subtle attacks with plausible authorized instructions, and retain ambiguity.
An evaluated model must not generate its own sole gold labels. Do not present invented
tasks as recovered source context or call synthetic pairs independently human-verified.
Do not launch unbounded generation as a way to inflate the sample count.

Audit all prior source/task/text/family exposure and cross-corpus reuse. PIGuard/Horizon
are mixtures, R-Judge includes InjecAgent, ASPI reuses AgentDojo tasks, and old sources
are not fresh simply because a different row or wrapper was selected. Split and
resample at the highest meaningful shared task/template/document group. Count distinct
texts, tasks, policies, templates and sources separately. Choose size based on useful
precision and independent groups, rather than an arbitrary large row count.

For the main context experiment keep candidate bytes fixed. Use the prior frozen
five-condition design as a starting point: candidate-only, authentic task/policy,
empty formatting, generic reminder and scrambled task words. Freeze any necessary
new policy serialization or prompt changes in a new version before confirmation.
Do not treat a wrong task as a label-preserving control unless independently justified;
its authorization label may genuinely change. NEXUS-IPI is not a context-only pair:
its full planned actions differ in every released pair. Never claim otherwise.

Reuse the existing native Jev and Luna Decisions routes, Luna/Astra Responses
comparators and local models where technically eligible. Do not discard weak local
results to improve the story or keep shopping for a winning model. Each call must be
standalone, with no linked chat history, gold labels or prior answers in the input.
Record actual route, authentication method, returned model, request/response, tokens,
native decision scores, timestamps and failures. Subscription and paid routes may be
used if authorized/available; label them accurately. Verify parsing, ties, truncation
and SDK behavior on development only. Preserve native thresholds unless a separate
development-only calibrated variant is explicitly frozen. Scores are not automatically
calibrated probabilities; do not manufacture probabilities from chat answers.

Reconcile all prior spend/reservations first. Caps remain $15 OpenAI and $20 TypeSafe
all-in, including earlier checks, not targets or confirmed account balances. The v4
closure recorded $0.4838404 OpenAI and $0.258774852 TypeSafe; check for later spending.
Estimate the new plan with conservative output/unknown-usage reserves and enforce
atomic reservations across processes. Existing authorized caps do not need repeated
permission. No purchases, recharge, reseller fallback, credential disclosure, or retry
loops after billing/auth failures. No request may proceed without a sufficient reserve.

Freeze source selection, group splits, labels/status, exact prompts, settings and
primary contrasts before confirmation. Run development, implement and test justified
fixes, record amendments, then execute eligible confirmation to completion. Retain
per-example raw results, transport errors and abstentions; do not cherry-pick retries
or tune on confirmation outcomes. A corrected post-confirmation variant needs a new
version and appropriate fresh evaluation. Run appropriate checks once and broaden
only for a new failure, change or unresolved concern.

Analyze per source/arm/model, emphasizing task-versus-reminder/format comparisons,
false alarms on legitimate instructions, missed attacks, paired transitions and
cluster-respecting uncertainty. Use native-score Brier/log-loss, reliability plots and
ranking metrics only where labels and score semantics support them; calibration fits
must use development data. Do not pool incompatible labels, treat correlated variants
as independent, infer population prevalence, or hide absent conditions as zero.

Deliver a concise source-backed report, checked tables and readable figures, a ledger,
reproducible offline scripts, and an explicit account of what remains missing. Retain
null/adverse results. A useful research result need not favor context. Build the
five-page paper/PDF only after the data, design, raw outputs and analysis are ready;
do not let polishing a PDF replace experimentation or claim publication novelty.
Use the established private branch/draft-PR workflow and verify checks. No public
publication, submission or merge without authorization. Keep raw restricted data,
weights and credentials out of Git. Explain each progress/result in plain English
first, then give the exact evidence and limitations. Work thoroughly without loops,
performative spending, repeated completed checks or promising a perfect conclusion.
```

## Prompt and adapter contract

Existing detector wording is preserved in `results/controls-v4/prompts-v1.json`.
Reuse its `question`, `chat_system`, Boolean schema and condition definitions unless
a documented development finding requires a new version. This handoff does not
silently edit a frozen prompt. Serialization for a new source must explicitly separate
trusted user request/policy from untrusted candidate text; source descriptions, gold
labels and expected assistant continuations stay in provenance, outside the payload.
New source admission should have exact-field tests and a saved development-only raw
request showing that boundary. The original pilot and v2/v3/v4 records are read-only
historical evidence.
