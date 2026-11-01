# Prompt for the new Astra research/design chat

```text
Take ownership of the research design for Decision Context Benchmark in this folder.
Your job is to investigate what we have, improve the research, and produce a concrete
experiment that a new GPT-6.1 Sol chat can implement and execute through /goal.
Do substantive preparation, not just suggestions or a polished paper draft. You have
room to change the proposed approach when the evidence supports something better.

Our central question is whether knowing the legitimate user task helps decision models
distinguish useful instructions from prompt injection, especially subtle attacks that
appear to help with the task. Governing-policy context is another useful dimension;
decide how to study it without quietly treating it as the same question. We want a
credible, roughly five-page research paper eventually. A positive result or a novelty
claim is not required.

Start with the actual repository, AGENTS.md and current Git state. Read:
- docs/source-discovery/README.md, catalog.json and the four detailed source audits
  under results/source-discovery;
- docs/source-discovery/METHODS-COMPARISON.md and CONTEXT-METHODS.md;
- results/source-discovery/review-preparation.json and the preparation scripts/tests;
- docs/controls-v4/COMPLETION-STATUS.md, RESULTS.md and MODEL-ROUTES.md;
- docs/source-discovery/NEXT-EXPERIMENT.md as a starting proposal, not a binding recipe.
If available, use read_thread selectively for research/API history
01a13c09-d537-73b2-98f3-c0bdd6b33fe6 and experiment history
01a17aba-1015-7ba3-91dd-7ad15322b057. Recent instructions supersede older restrictions.

Current preparation includes an audit of 27 source collections and 16,194 canonical
review records: 16,012 SPML policy/user examples and 182 AgentInjectionBench cases.
An annotation-blinded packet, blank reviewer CSV and separate mapping are also ready;
see blinded-review-preparation.json and export_blinded_review.py. Their source labels
are preserved separately, but semantic review, grouping and evaluation
eligibility remain unresolved. SPML is a direct policy-boundary setting; its user
messages are not tool-output injections. Other leads include Tensor Trust, PromptShield,
ASB, INFUSE, NVIDIA agentic IPI, NotInject, Boundary Pairs and BrowseSafe++. Access,
licensing, overlap and missing-context limitations are recorded in the audits. Check
what the files actually contain. Large row counts are not independent task counts.

Research the closest prompt-injection and context-sensitive classification papers,
including new work beyond this inventory where useful. Follow their datasets back
to actual released records. Examine how they define attacks and legitimate instructions,
construct or collect data, verify labels, partition tasks, choose models, run controls,
measure false alarms and evaluate uncertainty. Use primary sources and relevant full
methods/code, not citation summaries. Explain what we should borrow, improve or avoid.

Identify the important remaining weaknesses, then address every preparation task you
can: audit source code and samples, recover authentic task/policy boundaries, build
adapters and blinded review material, propose a defensible labeling/adjudication
process, check duplication/exposure, and design meaningful held-out groups. Existing
public or clearly disclosed constructed data are both possible. Never invent recovered
context or call AI judgments independent human review. Select challenge cases before
looking at our models' confirmation behavior.

Design the strongest feasible study rather than maximizing calls. Choose questions,
sources, attack/benign categories, controls, sample size, model panel, metrics and
analysis because they answer the research question. Existing Jev, Luna Decisions,
Luna/Astra Responses and local models are available starting points; investigate
additional comparators if they answer a real gap. Keep detector quality, native-score
quality and actual agent prevention distinct. Decide whether a prevention extension
is worthwhile and feasible instead of assuming detection proves prevention.

Make the plan executable: exact source revisions and fields, label/review status,
development/confirmation boundaries, prompts/interfaces, conditions, group counts,
sample-size rationale, budget estimate, failure/resume behavior, verification and
analysis outputs. Improve and test preparation code where useful. Do necessary small
development feasibility checks; leave the main confirmation execution to Sol. If a
dependency cannot be resolved, say precisely what is missing and what can proceed.

Preserve completed results and frozen records. Stay within the existing all-in caps:
$15 OpenAI and $20 TypeSafe/Jev, including previous spending and reservations. Reconcile
the current ledger; credits are not targets. Keep secrets/restricted data out of Git,
make no purchases or public submissions, and follow the private repository workflow.
Do not tune on evaluation outcomes or promise the study will produce a desired result.

Finish with (1) a short plain-English explanation of what is solid, what changed and
what remains unresolved; (2) a saved, evidence-backed design and preparation handoff;
and (3) one complete copyable /goal prompt for GPT-6.1 Sol in a new chat in this folder.
That prompt should let Sol implement, test, freeze, run, recover from justified
operational failures, analyze, create checked figures and finish delivery autonomously
within scope and caps. It should name actual files and readiness gates, allow sound
implementation judgment, and require honest uncertainty and retained failures. Only
have Sol produce a final paper/PDF once the evidence and checks justify it. Keep user
updates understandable: explain the meaning first, then give technical evidence.
```
