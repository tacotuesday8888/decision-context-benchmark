# What this extension can add, and what it cannot claim

Context-aware prompt-injection detection and calibration of decision models are
already studied. The defensible purpose here is narrower: measure paired changes
from revealing the authentic task to fixed native decision interfaces, with
format/reminder/scrambled controls, explicit input coverage, source-specific proper
scores and preserved failed attempts. This is an empirical replication/extension
question, not an established first-of-its-kind contribution. Positive findings and
publication novelty are not completion criteria.

The table summarizes inspected artifacts. Counts refer to distinct source inputs
only where that is what the source reports; they are not automatically independent
tasks or numbers of model calls. Unverified axes are stated rather than inferred.

| Work and status | Question, models and interface | Data and counting unit | Controls, probability analysis and limits |
|---|---|---|---|
| [CAD](https://arxiv.org/html/2608.05430v1), preprint; [pinned code](https://github.com/tavia-liu/CAD/tree/26e38a67f0a9e1de4cb3a876e4b021900a5d1c27) | Trained sentence filter combines query and surrounding response with isolated sentence representations; evaluates agent security/utility. | AgentDojo and AgentDyn-style environments. This audit did not independently enumerate its distinct task/document/request counts; do not compare its headline row totals to our582 texts. MIT main repository; third-party terms separate. | Paper Appendix B and `variants.py` already ablate query/response information. Trained sentence filtering and end-to-end execution differ from our fixed whole-response judgments. Its evidence precludes claiming that context ablation itself is new. |
| [System One Security Evaluation](https://arxiv.org/html/2609.33401v1), preprint; [pinned artifact](https://github.com/yxsec/system-one-security-eval/tree/78910f045e935e73829b4629baefc8efc7ae9879) | Reliability/calibration/selective automation across Jev, Laya, Nimble and other judges. Jev is `typesafe/jev-1.13` through OpenRouter; Nimble is MLX/Metal; Laya CPU has a2,048-token override. These differ from our Jev1.14 first-party and Ollama Q4_K_M. | Reported test inputs:1,612 WAInjectBench,236 R-Judge,352 AgentHarm;2,200 total. These are input counts, not2,200 independent task environments. Repeated response cohorts must not be summed as inputs. Benchmark text/raw responses are not redistributed. | Development-only temperature fitting and separate selection/confirmation for two sources; original-task grouping for AgentHarm variants. Artifact discloses later completion/reanalysis after initial test inspection and excludes intermediate attempts. We do not reproduce its rankings or import its calibration. |
| [Passing the Test You Trained On](https://arxiv.org/html/2610.03448), preprint with revised repository; [pinned artifact](https://github.com/lzwhehe/benign-instruction-bench/tree/5d0ae7c438a7b01be2ac0a2e8bc943e45c8f851f) | Detector rank transfer, false alarms and task-aware judges. Qwen2.5-7B/Llama-3.1-8B use NF4 and normalized first-token Yes/No scores; tool text is truncated at6,000 characters. | Clean fixture replay and injected pairs from AgentDojo/tau-bench, with BIPIA comparisons. Fifteen detectors are model count, not task count. Distinct documents/tasks were not recounted here. MIT code/results; downloaded datasets retain their own terms. | `hf_judge.py` has `NO_REQUEST`; `compute_v4.py` section12 analyzes it. Task-aware/no-task ablation, task-clustered intervals and formatting controls already exist. Current README differs from arXiv v1. Low-FPR threshold selection is not the same estimand as our frozen0.5 cutoff/proper scores. |
| [nokast-secureRAG](https://arxiv.org/html/2610.28364v1), preprint; [pinned code](https://github.com/abhishek085/nokast-secureRAG/tree/287f0c747f352dd742c501dfcf78dc18c9fb1705) | Trained `Qwen/Qwen2.5-0.5B` joint query/context classifier; configuration uses a Qwen teacher and Nemotron cross-checker. | Configuration targets3,000 benign +2,000 adversarial +300 flip pairs. These are generation settings, not a verified count of released distinct authentic tasks. Seed records contain three-way labels and flip-pair fields. MIT code notice does not establish all external data terms. | Query/context ablations and judgment-flip pairs overlap. Teacher-generated context/labels do not satisfy our authentic released-task selection. Evaluation's attack-success number is labeled a detection-side proxy in source, not evidence of agent prevention. |
| This v3 extension, frozen private experiment | Six model IDs/seven routes: Jev1.14 first-party; Luna Decisions/Responses; Astra Responses; local Nimble Q4_K_M, Laya multilingual and ProtectAI v2. Exact versions/routes in request plan. |761 task/text pairs,582 distinct texts,138 tasks,9 strata;91 texts shared across tasks.11,387 planned confirmation calls,108 separate control-development calls,42 prior local diagnostics. MIT source artifacts inspected; source-specific inheritance and restrictions documented. | Fixed original question/threshold;83 preselected pairs receive three constructed controls. Native proper scores, source-specific task/text weighting, crossed resampling, missing-response bounds, full raw attempts. Small independent-group counts, shared templates, public-data exposure, inherited labels and incomplete credential-fixture filtering remain limitations. |

The reviewed CAPTURE paper (LLMSEC2025), LLMail-Inject and BIPIA further establish
context-sensitive attack construction and agent-level security evaluation. Their
endpoints and generated/constructed labels should not be silently equated to this
same-candidate task-information intervention. The original full-paper notes and
primary-source receipts remain preserved under `docs/expanded-execution` and
`results/expanded-execution`.

## What the comparison implies

A lower Brier loss can reflect better discrimination or changed confidence; it does
not alone prove calibration. A zero classification effect can coexist with changed
probability quality. A task-context improvement against source construction labels
does not prove deployment safety, and clean replay does not establish prevention.
Neither small local split separation nor exact duplicate screening rules out model
pretraining exposure to these public benchmarks.

No source supplies a directly comparable score for every version/route here. In
particular, the System One artifact's MLX Nimble, reseller Jev1.13 and calibrated
Laya are not interchangeable with our pinned local/first-party defaults. We retain
weak results and do not add alternative backends to chase a ranking.

The two newly retrieved System One protocol files match hashes in its published
manifest; URLs and receipts are saved in `related-artifact-receipts-v1.json`.
Other inspected code/revisions and licensing caveats are in RESEARCH-NOTES.md and
the existing source receipts. The review is bounded, not exhaustive; acceptance
status is not inferred from conference templates or a future venue heading.
