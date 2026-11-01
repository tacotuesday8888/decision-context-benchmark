# Evidence and design decisions

Read on 2026-10-30: recent turns from both requested chats, project source audits,
v4 closure/results/routes, raw ledger, adapter/runner code, and newly pinned source
construction/selection files. The execution chat's latest state is completed v4,
not an active or half-finished run. No competing experiment was started. The
research chat's latest instruction is substantive design followed by one Sol goal.

## Closest methods and what changes here

These are bounded methods inspections, not independent reproductions of published
results. Counts attributed to a paper remain paper-reported unless explicitly
recomputed below. Primary links identify the inspected versions.

| Work | Inspected method/evidence | Decision for v5 |
|---|---|---|
| [Passing the Test You Trained On](https://arxiv.org/html/2610.03448), §§3–4, 5.4–5.5, Appendix A; previous project pinned code | Clean benchmark tool-call replay, differential attacked observations, task-aware judges, low-FPR operating points and format sensitivity; code already includes no-request ablations. | Preserve actual candidate surfaces and hard-benign errors; disclose task-context ablation is not novel. Our small benign set cannot support a 1%-FPR claim or threshold fitted on confirmation. |
| [CAD](https://arxiv.org/html/2608.05430v1), §4 and Appendix B; existing pinned variants.py | A trained sentence representation combines query, surrounding response and candidate sentence, with query/response ablations. | Separating task from surrounding text is already studied. Whole-observation native decisions are a different interface and unit; no claim that our prompt reproduces CAD. |
| [Task Shield](https://aclanthology.org/2025.acl-long.1435/), method and AgentDojo evaluation | Task-contribution checking is evaluated with agent utility and attack success. | Relevant is not necessarily authorized. Use it as conceptual motivation, not a static detector baseline with invented comparable scores. |
| [NTBench](https://arxiv.org/html/2610.32531v1), §§IV-B–C, V-C and generation/judge appendices | Reference outcomes anchor small incorrect/harmful deviations; target validity and successful induction are separately checked. | Review task-related answer corruption and side effects before inference; do not choose examples because models flip. No released record artifact/license was verified in this bounded follow-up; no manufactured “NTBench data.” |
| [CAPTURE](https://aclanthology.org/2025.llmsec-1.13.pdf), §§2.1–2.4 and experiments | Domain QA seeds are split before GPT-4o expansion; malicious separators/disruptors and safe trigger-word cases create different constructed tasks. | Borrow hard-benign construction and explicit disclosure. Embedded domain context is not a recovered independent original user request; do not equate its generated distributions to our intervention. |
| [AuthorizationBench](https://arxiv.org/html/2610.27548), §§3.1–3.4; pinned construction docs and two task bundles | Authorization contracts distinguish instruction, completion and out-of-scope action. Matched tasks can preserve the contract while changing environmental pressure; judge-only contract fields differ from agent-visible instructions. | New material addition to our inventory: permission is distinct from harm and task completion. Do not feed gold violation lists to detectors as “policy.” Use a separate explicitly constructed scope-switch diagnostic; do not import whole-trajectory labels. |
| [INFUSE](https://arxiv.org/html/2610.20776), §3, Appendices A.2–A.4, B; pinned assembly, resolver, handlers, configs and verifier documentation | File targeting/placement depends on declared surfaces and strategy; upstream documents a verifier correction after payload-only false positives. Judge committee agreement and human validation are separate checks. | Implement a bounded static file reconstruction, accurately named. Freeze revision/strategy; do not infer agent success from planted text. Leave prevention out of v5. |
| [SPML release](https://huggingface.co/datasets/reshabhs/SPML_Chatbot_Prompt_Injection/tree/02ce8084e979bc7d4c24ee35d22ecb7f2db96ff5), pinned card and full CSV | GPT-4 policy expansion and inverted policy rules produce source labels; external attack seeds include Gandalf. The card explicitly cautions against universal prompt-only interpretation. | Study direct policy conflict separately; preserve ambiguity and shared policy/domain families. Source degree does not certify subtlety. The older arXiv HTML v2 link failed in this follow-up, so release findings do not claim a newly read full SPML paper. |
| [To Jev or Not?](https://arxiv.org/html/2610.03324v1), §§3.1–3.4 | Same-text definition/decomposition interventions distinguish annotation agreement from definition adherence. | Policy information can alter the target interpretation; report label agreement separately from authority compliance and do not promise improvement. |
| [Conversational Context Does Matter](https://aclanthology.org/2022.naacl-main.433.pdf), §3 | Independent annotation phases show target alone versus parent+target; context affects annotations as well as predictions. | Record context necessity and disagreements, but do not call one agent's context-necessity judgment a human annotation experiment. Human review is not available under the current plan. |
| [System One security evaluation](https://arxiv.org/html/2609.33401v1), §§3–6 and preserved artifact | Separate calibration/selection/confirmation, reliability and selective policies; different Jev version/backend and local configurations. | Borrow explicit forecast interpretation, no invented chat probabilities and retained failures. Do not inherit its calibrated thresholds or compare native/backend scores as interchangeable models. |

The older METHODS-COMPARISON.md remains useful for PromptShield, Tensor Trust,
NotInject, InjecAgent, AgentDyn, ASB and R-Judge. These were not forgotten because
v5 admits fewer sources. More overlapping rows would not repair the main construct.

## Actual release/code findings

Pinned file acquisition is reproducible with `fetch_evidence.py`; it checks each
cached file against the Git tree blob SHA as well as retaining SHA-256/byte receipts.
Upstream code was read as text, never imported or executed.
`source_audit.py` recomputes the exact AIB seed links and INFUSE placement counts;
its source hashes and counts are saved in `results/study-v5/source-code-audit.json`.

- **AIB** at 540669a836e98063278fb0586e5e178818a20d88: seed conversion hard-codes
  unsafe; benign_controls.py authors explicit safe scenarios. curate.py stratifies
  and shuffles rows by category; heldout.py hashes sample IDs. Neither establishes
  task/template holdout. Full release: 182 cases, 142 unsafe/40 safe. Our strict
  single-observation boundary admits 158 for review (123/35); 24 require multi-turn
  adjudication and are quarantined. Exact input-message matching links 120 release
  rows to 123 YAML seeds; remaining lineage is unresolved. Do not treat matched
  category as a matched clean/attack task pair. Tool-shadowing descriptions occur
  in tool catalogs as well as result strings; catalogs are never promoted to trusted
  instructions in our adapter.
- **SPML** at 02ce8084e979bc7d4c24ee35d22ecb7f2db96ff5: recomputed 16,012 rows,
  840 exact policies, 15,918 exact submitted texts, 694 policies with both source
  labels, 4,168 Gandalf-source rows and one empty submitted text. No identical
  submitted text has opposing source labels. That absence means the release itself
  does not supply a clean fixed-candidate label-flip experiment. Shared normalized
  candidate text connects policies: 740 components before domain closure. The
  sampled 100 policies cover nine coarse domains, not 100 proven independent seed
  families. Retain the full 840-policy group map for review.
- **INFUSE** at d4ed0634c7d94979da9d91c0db5e2aba11a3dff2: all 40 instruction
  files, 40 surface overlays and 56 attack configs inspected. Twenty-six prefixes
  explicitly announce a new task; fifteen announce a user subtask. “Contextual”
  attack metadata therefore does not prove subtlety. Default placement is append
  for 50 configs, prepend for five, replace for one. The first literal static text
  target yields 35 pairs using 26 distinct chosen payload templates. Task 28's
  declared first target is absent in the pinned static tree; four others begin with
  filename/archive surfaces. All five exclusions are retained. Related bug-fix
  tasks and reused attacks reduce the 35 pairs to ten connected groups.
- **ASB** at 544540ff0788998072f7df463056fd17e62cc9f4: react_agent_attack.py
  constructs a directive from attacker instruction **and attacker tool name**,
  appends it to a returned tool response only in the non-final stage, and then
  wraps that response in an observation string. A raw attack-tool description is
  not the observed candidate. Authentic tool-return values/runtime-stage alignment
  have not been reconstructed; exclude from v5 instead of inventing a cross-product.
- **AuthorizationBench** at c48d2da60f207ad2664feebda516b1cc72f4fa98: inspected
  T0013-j-c-h and T0013-n-c-h instruction/config/vignette/system/readme files.
  They share the instruction and intended forbidden production-stack deletion,
  while the environmental trigger changes. authorization_scope, completion_criteria,
  detection_policy and narrative include adjudicator knowledge, not all trusted
  agent-visible input. This source is useful methods evidence; no detector labels
  were assigned from its behavioral outcomes. Repository code/data license bytes
  are cached; this inspection did not run its sandbox or count all task labels.

## Label audit observations, explicitly not independent review

These research-agent observations motivate review; don't show them to the independent
reviewer before its judgments lock. AIB-00169 presents an internal-docs mirror as
approved without releasing an authenticated approval list; the visible evidence may
not establish whether it is a genuine update or forged authority. SPML row 8088's
positive asks to skip motivation/progress discussion in favor of health facts; a
binding rule versus user preference needs judgment. Other degree-1 positives contain
long overt persona substitutions. Some policies simultaneously describe potential
diagnoses and prohibit diagnosis. Preserve these difficulties rather than turning
source intent into unquestionable gold. No current semantic gold has been assigned.

## Leads deliberately not admitted

[BrowseSafe++](https://huggingface.co/datasets/perplexity-ai/browsesafe-plus-plus)
was rechecked: access requires sharing HF account information/accepting conditions;
test inputs prohibit training, tuning, redistribution and label recovery. No access
terms were accepted. Its matched pages/tasks are promising for a later accessed
training-split research subset, but hidden test is not our review corpus.
[Tensor Trust data](https://github.com/HumanCompatibleAI/tensor-trust-data) still
presents separate robustness and output-leak detection artifacts; the prior source
audit and SPML card document missing redistribution permission. We did not resolve
rights by borrowing the game code license. PromptShield's released prompt/label rows
lack reliably separated original task/input fields. NVIDIA IPI is attack-selected
training data without a matched benign arm. NotInject is candidate-only benign
stress, and Boundary Pairs lacks a distinct original task field. Adding them would
answer different questions or add review load without fixing v5's paired task design.
Keep their prior pinned audits; these are exclusions from this bounded study, not
claims that the corpora have no research value.

## What is gained and what remains

The improvement is executable separation of task and policy, reviewable bounded
sampling, conservative grouping, static source-faithful reconstruction, explicit
scope-switch construction, and a route-preserving prompt/budget/analysis contract.
No new model result, human review, live balance or prevention success is claimed.
The primary limitation remains externally reviewed label validity and semantic
workflow grouping. Another agent can complete that review, with its provenance
fully disclosed. Closed-model training exposure, natural-traffic prevalence and
small-domain generalization remain unknown even after review.
