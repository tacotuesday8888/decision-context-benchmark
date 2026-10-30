# What comparable papers teach us

Audit date: October 30, 2026. This is a focused comparison of eight relevant works,
not an exhaustive literature review or a claim that their results reproduce here.
Primary links below support the paper descriptions; the source-discovery audit JSONs
record the inspected releases, revisions, access limitations and count receipts.

Our strongest next step is to test **whether knowing the real task or policy helps a
detector tell a useful instruction from an attack**. That needs both kinds of text,
the actual task or policy, trustworthy labels and genuinely separate task families.
Thousands of variations of the same task cannot replace that combination.

## How large were these studies, really?

“Counted” below means this source audit parsed the indicated release. “Reported”
means the paper, card or repository states the number; it was not independently
recomputed. Task fixtures, attack attempts, model runs and labeled rows are different
units and should not be added together.

| Work and publication status | Paper scale and released units | What the number does not establish |
|---|---|---|
| [PromptShield](https://arxiv.org/abs/2501.15145), CODASPY 2025; extended report v2 | **Counted:** 18,909 train, 1,000 validation and 23,516 test rows. Test has 17,030 benign/6,486 injection rows and 23,359 unique exact prompt strings. | Rows mix conversational requests, application requests and constructed attacks. The number of independent original task/template families was not established. |
| [SPML](https://arxiv.org/html/2402.11755v2), preprint in the inspected evidence | **Reported:** 1,871 system prompts and approximately 20,000 user inputs. **Live release metadata:** 16,012 system/user rows. Only sample rows were inspected; distinct released policies were not counted. | The paper headline is not the size of the inspected release. Synthetic policies are not authentic production user tasks. |
| [Tensor Trust](https://proceedings.iclr.cc/paper_files/paper/2024/file/519c51529c3544b3430bd8b17d400365-Paper-Conference.pdf), ICLR 2024 | **Reported final raw v2:** 563,349 attack attempts, 294,680 distinct attacker inputs. **Counted v1 benchmarks:** 570 extraction and 776 hijacking rows; a separate 230-row output-leak detection set. | Repeated attempts and game policies are not hundreds of thousands of independent tasks. The older 126,808-attempt paper version and newer raw dump must not be mixed. |
| [PIGuard / NotInject](https://aclanthology.org/2025.acl-long.1468/), ACL 2025 | **Counted:** 339 benign NotInject examples, 113 each containing one, two or three selected trigger words. The wider PIGuard evaluation also uses other corpora. | The 339 examples measure false alarms on a constructed distribution; they are neither independent real-world tasks nor an attack/benign balanced dataset. |
| [InjecAgent](https://aclanthology.org/2024.findings-acl.624/), Findings of ACL 2024 | **Counted:** 1,054 base attack cases from **17 user fixtures × 62 attacker fixtures**. **Reported:** evaluation of 30 LLM agents. | More target models or enhanced attack wrappers increase run count, not independent user-task count. |
| [AgentDyn](https://arxiv.org/abs/2602.03117), 2026 preprint; v1 mechanics and pinned release inspected, current abstract v3 checked | **Reported:** 60 manually designed user tasks, 28 injection tasks and 560 within-suite task/injection combinations. Sample clean/attacked trajectories were inspected, not every trace. | The 560 combinations and many model traces are not 560 independent tasks. Current title/version differs from the original v1 record. |
| [Agent Security Bench](https://arxiv.org/abs/2410.02644), paper reports ICLR 2025 acceptance | **Counted pinned files:** 10 agent/scenario groups, 51 normal task strings, 400 attack-tool records, 20 normal-tool records. **Reported v1:** approximately 90,000 testing cases across configurations. | The headline covers a broad attack/defense/model grid. It is not a ready-made 90,000-example indirect-injection dataset. OpenReview access hit a browser check in this audit. |
| [R-Judge](https://aclanthology.org/2024.findings-emnlp.79/), Findings of EMNLP 2024 | **Reported paper:** 569 interaction records. **Counted pinned release:** 571 unique record IDs, 270 safe/301 unsafe, including 414 injection-origin records. | The release/paper discrepancy remains unresolved. “Safe” means the agent acted safely, not that every input was free of injection. |

## What to borrow, and what must stay separate

These papers address related questions, but several measure agent behavior rather
than injection detection. A detector can correctly recognize an attack even when the
agent would have resisted it; a safe agent can still have received malicious text.

| Work | Benign comparison, labels and checks | Useful methods to adopt; mistakes to avoid |
|---|---|---|
| PromptShield | Benign conversational and application-structured requests accompany attacks. Sources and attack methods are curated; the released schema is only `prompt`/`label`. Our exact-string check found 71 duplicate test groups and no conflicting labels or exact cross-split overlap. That does not validate semantic labels or near-duplicate independence. | Evaluate false alarms as well as detection, including low false-positive operating points and source shifts. Recover authentic instruction/input boundaries before our context ablation: the released full request is **not** an untrusted-candidate-only string. Select our thresholds on development data, then freeze them. |
| SPML | Valid user inputs and rule-violating inputs are paired with chatbot definitions. GPT-4 expands seed policies and generates inputs/attacks by negating rules. We found a subtle positive whose interpretation needs review; no independent adjudication was established by inspecting two examples. | Make authorization explicitly relative to the supplied policy. Split by whole policy/template. Audit subtle positives and negatives with policy visible; do not call all policy conflicts indirect injection or inherit construction labels as unquestionable truth. |
| Tensor Trust | Human players author attacks and defenses. Correct access-code behavior and attack robustness are different outcomes. The 230-row detection set labels leaked codes in **outputs**, not injection intent in inputs. | Use human attack diversity and authentic defenses as a separate game-policy arm. Preserve player/defense relationships where available or recover them from raw provenance. Never label failed attacks benign or reuse code-leak labels for our detector. Data permissions remain unresolved. |
| PIGuard / NotInject | All NotInject examples are designated benign. Trigger-word selection includes expert refinement; GPT-4o-mini generates sentences. This is not independent human authorship/adjudication of an authentic task corpus. | Test whether detectors overreact to ordinary words such as “ignore.” Report false-positive rate on this stress distribution separately. PIGuard's validation mixture uses some NotInject examples: trace exposure before calling a model/set comparison independent. |
| InjecAgent | Attack goals distinguish direct harm from data stealing. Original user instructions and constructed tool responses are preserved; attack success is evaluated separately. No released matched clean response is established merely by the response template. | Keep task, tool semantics and exact observed attack surface. Separate transport/invalid continuations from successful exploitation. It is useful historical replication here, but all 17 user fixtures and 62 instruction families were already exposed in project v3. |
| AgentDyn | Clean runs and helpful third-party instructions make unnecessary blocking visible. Utility and security are distinct outcomes. One inspected clean/attacked pair also differs in tool permissions; whole traces are not automatically a one-change experiment. | Include legitimate procedural instructions and measure the cost of rejecting them. For detection, extract aligned observations and required context. For prevention, preserve the environment and verifiers and report both task completion and security. Existing project task exposure must be respected. |
| ASB | Normal tasks/tools and multiple attack paths support utility/security comparisons. Observation injection, direct user attacks, memory poisoning and backdoors require different attacker powers. Exact observation assembly has not yet been verified for our adapter. | Broaden domains only after isolating the observation-injection path and reading construction code as data. Audit the actual text received by the agent. Do not cross every task and attack-tool row and present the result as a published released test set. |
| R-Judge | Whole interaction records carry human-consensus safety labels and risk descriptions; records derive partly from earlier benchmarks and expert constructions. Some safety changes replace risky agent actions. Labels concern whole behavior. | Borrow explicit annotation guidance, disagreements and task-aware risk analysis. Use only a separately scoped risk-judgment extension; slicing a tool message and inheriting the agent's safety label changes the target. Exclude post-action outcomes/gold explanations from pre-action detector inputs. |

## What this means for our experiment

1. **Build two clearly named arms.** One asks about original user-task information in
   tool/document workflows; the other asks about governing policy, including chatbot
   definitions or game defenses. Report them separately. SPML is a useful policy lead;
   it cannot by itself answer whether authentic user-task context helps with indirect
   attacks. The broader audit's AgentInjectionBench and INFUSE leads still need their
   admission checks; they are not established by this paper comparison.
2. **Give the models difficult legitimate instructions as well as attacks.** Include
   ordinary task steps, quoted instructions and benign trigger-word cases. Existing
   synthetic controls can be useful when identified honestly. Newly constructed cases
   require disclosed construction, auditable rules and independent scenario partitions.
3. **Verify what each label means before testing models.** Preserve the upstream label,
   proposed injection judgment and reviewer decision separately. Reviewers need the
   actual task/policy and candidate, but no model predictions. Record disagreement and
   unresolved cases. An agent's review is not independent human adjudication.
4. **Use the same candidate under controlled presentations.** Compare authentic context
   with candidate-only, empty formatting, a generic reminder and scrambled context,
   following the newly frozen protocol. This separates task information from merely
   adding text or warning the model. A wrong task can change authorization itself; it
   is not automatically a control that preserves the correct label.
5. **Hold out meaningful groups.** Keep entire tasks, policies, document/template
   families and shared upstream cases together. Count both candidate strings and groups.
   Preserve development/confirmation separation and check prior project/model exposure.
   Additional versions of familiar tasks are useful diagnostics, not fresh confirmation.
6. **Judge detector quality and score quality separately.** Report paired decision
   changes, missed attacks and false alarms by source/model. Use uncertainty estimates
   that respect task/family clustering. Native decision scores can support ranking and,
   where their meaning supports it, calibration/Brier/log-loss analysis. A score of
   0.99 does not establish 99% real-world correctness. Fit any calibration on development
   data, never confirmation results.

There is **no universal paper-sized sample count**. Choose the next size from the
precision needed for the primary paired comparison and the number of independent
groups available. More repeated variants can improve coverage but cannot manufacture
new task diversity. Very low false-positive claims need substantial benign support:
0.1% of PromptShield's 17,030 test negatives is only about 17 false alarms, illustrating
why uncertainty and distribution matter. Our goal is a credible estimate, not matching
another paper's largest number.

A professional five-page paper can make a narrow contribution: a transparent,
controlled comparison showing **when authentic context helps, hurts or changes nothing**.
An agent-prevention claim needs an additional sandbox experiment measuring both attacks
stopped and legitimate tasks completed. Related work should motivate the design;
writing the paper or producing a PDF should follow completed data, label, execution
and integrity checks.

## Reproducibility and evidence boundaries

The detailed local sources are [human-datasets.json](../../results/source-discovery/human-datasets.json),
[agent-datasets.json](../../results/source-discovery/agent-datasets.json),
[benign-training.json](../../results/source-discovery/benign-training.json) and
[priority-source-inspection.json](../../results/source-discovery/priority-source-inspection.json).
Their inspected URLs/revisions distinguish complete-file checks from sample/card
checks. Counts for an inspected release do not independently reproduce its paper's
evaluation or validate its gold labels. Publication status above describes the cited
evidence; a preprint label does not establish that no later venue exists. No additional
model calls, source-code execution or dataset generation was performed for this comparison.
