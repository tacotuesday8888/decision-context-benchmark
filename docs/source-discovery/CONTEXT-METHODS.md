# What the closest and neighboring research changes in our design

This supplements METHODS-COMPARISON.md with task-aware detection, recent evaluation
work, and context-dependent classification outside security. Counts below are paper
claims unless explicitly identified as our own audit; they are not new model results.

| Work | Relevant design and scope | What to borrow; what not to infer |
|---|---|---|
| [Task Shield, ACL 2025](https://aclanthology.org/2025.acl-long.1435/) | Checks whether extracted directives/actions contribute to the user's goals; evaluates attacks **and utility** on AgentDojo with GPT-4o/GPT-4o-mini, one trial per task. | Task contribution is a close conceptual baseline. Relevance does not establish authorization: a subtle task-related attack may appear useful. Its agent-level attack-success results are not detector accuracy. |
| [TaskTracker](https://arxiv.org/abs/2406.00799v6) | More than 500K constructed question/paragraph/task-drift instances; linear/metric probes on activation differences across six language models. | Compare original task against external text and test held-out domains. Its large cross-product is not 500K independent task environments. This project's v4 already uses a reconstructed subset; more rows from that source are not automatically fresh confirmation. |
| [Passing the Test You Trained On, October 2026 preprint](https://arxiv.org/html/2610.03448) | Replays benign tool outputs, differential injected outputs, fifteen detectors and two task-aware judges; studies transfer between BIPIA, AgentDojo and tau-bench. | Actual tool observations and hard benign instructions matter; model rank depends on data format/exposure. Our prior audit already found task/no-task and formatting controls in its repository. Do not claim context ablation is new. See the preserved v3 comparison for pinned code and replay caveats. |
| [RAG-PIBench, October 2026 preprint](https://arxiv.org/html/2610.08571) | Reports 4,876 balanced rendered contextual examples, source/template leakage checks and protected splits; compares keyword, semantic, TF-IDF and transformer detectors. | Strong simple baselines and source/template isolation are useful. A rendered host document is not necessarily an authentic user task. A usable released artifact and original task boundaries have **not** been verified in this audit; paper counts alone do not admit a new dataset. |
| [PIDS-Bench, September 2026 preprint](https://arxiv.org/html/2609.15017) | Measures over-defense, obfuscation and distribution shifts; distinguishes curated from externally sourced benign prompts and examines fixed thresholds/seed variation. | Separate hard-benign false alarms by provenance instead of relying on aggregate F1. Do not fit thresholds on confirmation or count augmented variants as independent. Released data/reuse permissions have not been verified here. |
| [Hate Speech and Counter Speech Detection: Conversational Context Does Matter, NAACL 2022](https://aclanthology.org/2022.naacl-main.433/) | Context-aware Reddit annotation for hate/counter/neutral; prior comment can change human judgments as well as neural predictions. | Audit how **people** judge the same candidate with original context before assuming the inherited context-free label is correct. This is methodological inspiration, not prompt-injection data or evidence about our decision models. |
| [Toxicity detection sensitive to conversational context](https://firstmonday.org/ojs/index.php/fm/article/download/12285/10696) | Reports 10,000 Civil Comments in Context posts, in/out-of-context annotations, and evaluation on context-sensitive subsets. Effects can disappear in aggregate when context-sensitive examples are rare. | Keep an ordinary-data arm and a separately declared context-dependent challenge arm. Enrich using pre-inference human/task criteria, not by selecting cases where our models flip. Their annotations and causal target differ from injection detection. |

The existing [v3 research comparison](../extension-v3/RESEARCH-COMPARISON.md) additionally
audits CAD's query/response ablations and a System One security evaluation of Jev,
Laya and Nimble, including route, calibration and data-distribution differences. This
new audit does not turn those earlier sources into fresh held-out data.

## A useful scale for our next study

There is no universal example count required for a five-page research paper. The
right unit is an independent task/policy/document family. A paper with tens of
thousands of attack variants can still contain only tens of independent workflows.
Our completed v4 has 425 distinct confirmation texts, 221 tasks and 44 primary
clusters, with a narrow benign-instruction supplement. The next study should improve
that coverage and label quality, rather than repeat that collection at greater cost.

Prepare two explicitly different arms: (1) a reasonably broad released-source
evaluation, and (2) an independently reviewed challenge set where understanding
authorization requires the real task/policy. Choose the final number of groups after
adapters and label review establish what is eligible, then estimate uncertainty and
run cost before freezing it. Report all exclusions and inconclusive/adverse results.
Keep separate policy, user-task, game, detector and prevention outcomes.

If the study remains a fixed-detector comparison, the present panel is adequate.
Adding a new model is justified by a missing baseline or deployment question, not
by a weak result. A lightweight lexical baseline can test shortcuts; any trained
baseline requires grouped development-only fitting and a separately frozen protocol.
