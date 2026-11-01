# Decision Context Benchmark

**Does knowing the legitimate user's task help a model detect prompt injection?**

This private research project compares detector decisions with and without task information. It measures both false alarms on harmless content and missed attacks. The results show model- and source-dependent effects: a better average score can hide more missed attacks.

## Start here

- [Research notebook and teacher discussion](../docs/research-notebook/README.md): history, data counts, findings, contributions and open questions.
- [Editable Google Docs notebook](https://docs.google.com/document/d/1T8pvePmYF7rYWWugGc8HkSEtiI8CK3jU_3EZer2WFmo/edit): a discussion copy of the retrospective notes.
- [The completed 761-pair study](../docs/extension-v3/COMPLETION-STATUS.md): the stage described in the owner's activity summary.
- [Larger Jev/Luna study](../results/study-v7-execution/README.md), [Sol follow-up](../results/subscription-followup-execution/README.md), and [second-source/pilot results](../results/subscription-followup-extensions-execution/README.md).

## Current status — November 1, 2026

The bounded latest experiments and computational verification are complete. Source-label ambiguity, public-data exposure, group-dependence assumptions and limited agent-pilot coverage remain research limitations. Human semantic validation and final claims/figure review remain useful next steps. No new paper is being drafted in this documentation phase; an older draft belongs to an earlier study.

The latest experiment delivery is [private draft PR15](https://github.com/tacotuesday8888/decision-context-benchmark/pull/15). This documentation branch depends on it. The PR stack is unmerged: the repository default branch may show older work. This README is the current overview for this branch, not a public GitHub Pages site.

## What was evaluated

| Stage | Data unit and size |
| --- | --- |
| Earlier completed extension | 761 task–content associations; 582 distinct texts and 138 tasks |
| Larger main study | 3,000 clean/attack groups, containing 6,000 pages |
| Sol follow-up | 500 of those groups; not new independent examples |
| Separate PromptShield benchmark | 4,000 texts; a detection check without the same task-context intervention |
| Second-source diagnostic | 66 paired groups, containing 132 released observations |
| Simulated-action pilot | 12 explicitly constructed tasks |

A task–content pair is one task associated with one piece of content. A clean/attack pair contains two examples. Repeated calls and model conditions are not additional independent data. Do not add these counts into a unique-example total. See the notebook for earlier stages and complete-cohort counts.

## Main findings and limits

- Jev's main-dataset average error improved with task context, but it missed more attacks while raising fewer false alarms.
- Luna and Sol main-dataset error increased with task context under the tested configurations.
- A second source changed the pattern; Sol's apparent benefit over simpler controls was not clear against a length control.
- The small simulated-action pilot established no security benefit. Its scoring limitation is documented, with original outcomes retained.

These are results for frozen configurations and released labels, not universal rankings, an architectural explanation, or proof of agent protection. Sources are analyzed separately. Failure, abstention and missingness records remain part of the evidence.

## Evidence and reproduction

`docs/` contains protocols, design decisions and handoffs. `scripts/` contains preparation, execution and analysis code. `results/` contains compact outcomes, tables, figures and verification receipts. The linked result READMEs provide reproduction instructions; the core and second-source compact analyses can be replayed without new model calls. Other historical analyses require retained local evidence and their documented dependencies.

Credentials, restricted raw text, full transports and weights are not uploaded. Local evidence is linked through saved hashes; access limitations are stated rather than treated as public reproducibility. Do not rerun historical inference commands simply to read this project. Failed first outcomes are not replaced, and frozen results are not rewritten to improve the story.

## Research history and participation

The original 761-pair study remains part of the project; later controls and larger evaluations strengthen or qualify its conclusions. AI assistance in engineering, execution, analysis and documentation is substantial and should be described accurately. The notebook includes owner/teacher contribution fields without inventing their work or approval.

[Historical README](../README.md) preserves the earlier setup narrative and commands. Its access, pricing and run-status statements are historical, not current operational instructions. Source notices and licensing constraints remain in their study-specific records. No public release, paper submission or merge is implied by this overview.
