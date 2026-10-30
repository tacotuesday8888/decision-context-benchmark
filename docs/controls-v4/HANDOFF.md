# Controls v4 progress

Active objective: attachment d06ed192-6f72-4221-8caa-7d589d046b11/goal-objective.md.
Previous goal turn completed v3 and is classified as progress. This turn starts the
separate stronger-control experiment on `codex/context-controls-v4`.

Read SOURCE-AUDIT.md and results/controls-v4 receipts. Baseline PR4 is private/draft,
eight checks successful at d929836; no need to repeat old numerical reproduction.
The new source audit reads pinned tau-bench historical JSON, not private simulator
instructions. Inventory is unapproved and semantic labels remain null. Existing
InjecAgent task/family coverage is exhausted for freshness. BIPIA/AgentDyn and other
published sources need deeper remaining-group and label audits, not arbitrary reuse.

No model requests or new spending; no background inference. Do not run old freeze
or model commands. Keep old records immutable. New adapter currently audits only;
unit tests, independent record inspection, richer exposure grouping, review packet,
eligibility/splits, protocol and experiment implementation remain. The whole goal
remains active, not blocked merely because review may become necessary.

## Further source progress

TaskTracker clone is pinned b4fabe25504dc1d3f7c6fdf5e50d4bb209a152b0. Audited
notebook cells as text (temporary /tmp/dcb-tasktracker-*.py, never executed).
SQuAD dev and CodeAlpaca downloaded; all 6,000 published QA/code attack normalized
hashes match, but NC CodeAlpaca text remains ignored/not selected. Better path:
3,120 published QA/AdvBench constructions verify (2,387 questions, 1,100 paragraphs,
35 articles, 520 attack prompts). AdvBench MIT/SQuAD CC-BY-SA4/TaskTracker MIT.
1,204 published clean QA records verify cumulative raw prompt-prefix hashes (different
hash semantics from per-prompt whitespace-normalized attacks). Scripts preserve both.

Owner answered: proceed with defensible published labels; quarantine ambiguity.
No human labels may be invented. Review packet has 24 existing records and blank
reviewer fields; full text stays ignored. It is a policy-audit aid, not a completed
annotation or selected evaluation set.

Next substantive actions: pin new download URLs/revisions/licenses; compare original
paragraph/question/attack hashes and lexical templates with prior exposed material;
choose article/document/attack grouping before splits; inspect ambiguous candidates
against explicit source-construction policy; evaluate actual coverage and precision.
Tau alone has large shared-document components even after removing generic tools.
Retain full control experiment objective, both error directions and no new labels.
No confirmation/protocol freeze or model use yet. Two grouping regression tests pass.
Source reconstruction audits passed; no live process remains from those audits.

## Current draft scope and leak correction

Private draft PR5 is open, base codex/context-extension-v3. Initial checkpoint
`e69364c` passed all ten push/PR checks including the new controls workflow. Current
uncommitted work adds overlap/selection/AIB adapters and updated source fields.
TaskTracker trusted_task now preserves original sep_prompt + question (not just
question); all reconstructions regenerated before inference. No freeze exists.

Draft v1 is automatically rejected: 11 wrappers crossed splits. draft_selection_v2
keeps all TaskTracker override wrappers in confirmation: 48 new clean dev examples
from 8 articles plus 60 reused prior dev rows; 408 confirmation examples (204 matched
QA questions/paragraphs) in 27 other articles. No exact/near prior document overlap;
no full normalized selected-wrapper substring in prior candidate texts. The latter
was manually inspected, still needs durable validator output. Independent split
validation and clustering remain required; do not mistake draft counts for approval.

New bounded alternative search: NetInjectBench has no released artifacts in its
paper (after acceptance promised); NTBench no usable release found, important
near-target limitation. Community agent-injection-bench d75c8ad8d255d018b75258d22ea1c78a8c37428b
has 24 fixtures, 17 potentially eligible static document/page/tool cases:14 intended
attacks,3 controls incl legitimate runbook instructions. Seven rejected for extra
trusted context or unsupported surfaces. MIT; source is authored synthetic fixtures,
not historical production traces. All metadata/labels stay out of future requests.
Potential supplementary source only; source-specific results and very wide FPR limits.
Read ELIGIBILITY-DRAFT.md. No new inference, spending or live background processes.

## Development started (v4.0 + documented v4.0.1 correction)

533 prepared rows validated; confirmation425 (408QA/17AIB), development108.
Source/exposure validators pass, all8 initial tests plus2 cap-ledger tests pass.
Laya2665payloadtokenchecks zero truncations, max3671tokens. Protocol/prompts and
372development jobs frozen. No confirmation yet. Original changed runtime files
are archived and byte-verified against original development freeze.

Development live handles: Luna chat98450, Astra97819, Nimble54027; Luna Decisions
62998 restarted untouched jobs after reviewed503. Laya49812 and ProtectAI57922
likely finished; poll exact handles or inspect records, never restart blindly.
Jev50134finished60. Nimble initially made zero calls: external Ollama updated to
0.40.13. Separate nimble_runtime.py pins actual version, unchanged model digest.
Official release checked. Development amendment v4.0.1 binds five changed files,
original source archive and one Decisions503 (no usage; full reservation retained).
That one failed dev cell may remain missing; other cells must pass. Never overwrite
failed record. Existing running processes retain original loaded code and freeze.

Current run.py requires original+amended development hashes, fresh confirmation
freeze binds amendment. All-in budgets use v3 closure, never legacy expanded-only
spending. New analysis/statistics draft source-specific estimators, not run yet.
Need finish development report and gate, confirmationfreeze, full execution,
continuation policy tool/tests, analysis/independentverifiers/figures/repro/commitCI.
Current changes mostly uncommitted. Do not stop after development.

## Confirmation live

Development ended372attempts:371valid,onepreservedDecisions503. No chat truncation;
Laya weak positive bias and Nimble all-negative outputs retained, no prompt/threshold
change. development-report-v1.json verifies all request hashes and ledger records.
Confirmationfreeze-v1.json created and all7routes started. Exact live handles:
Jev10591, Decisions42194, Luna85775, Astra28541, Laya9426, Nimble65326, ProtectAI15441.
Poll those handles; never restart a live process. No confirm failures observed yet.
Continue_transient.py supports bounded reviewed HTTP transients only, preserving all
failed cells and unknown-cost reservations; unsupported failures require inspection.
Analysis/audit draft copied and adapted;14tests pass with numpy. Analysis not run.
Full confirmation is13,175calls (2125/contextualroute,425specialist).
