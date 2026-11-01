# Decision Context Benchmark

**Testing whether task context improves prompt-injection detection.**

A series of controlled experiments comparing detector decisions with and without the legitimate user's task. Evaluation tracks both **false alarms** on harmless content and **missed attacks**.

[Experiment notes](../docs/research-notebook/README.md) · [Main results](../results/study-v7-execution/README.md) · [Sol follow-up](../results/subscription-followup-execution/README.md) · [Methods](../docs/subscription-followup/PROTOCOL-v1.md)

---

## Research question

Does useful task information improve detection—or do apparent gains come from other prompt changes?

The larger experiments compare four conditions: the published task, empty-task formatting, a generic warning, and repeated “Context unavailable.” filler matched by character count. The candidate content stays fixed across these conditions. The filler is not token-matched or semantically empty.

## Findings at a glance

| Observation | Interpretation |
| :--- | :--- |
| Jev raised fewer false alarms but missed more attacks on the main dataset. | A better average score can conceal a security tradeoff. |
| Sol and Luna made more errors with task context on the main dataset. | Context did not consistently improve detection. |
| The second source produced a different pattern. | Results depend on the source and comparison prompt. |
| The small agent pilot demonstrated no protection benefit. | Detector accuracy alone does not establish agent safety. |

Findings apply to the tested configurations and source labels. Sources are analyzed separately; no universal model ranking is claimed. Detailed results retain uncertainty estimates, failures and abstentions.

The main source is a project-held-out subset of BrowseSafe++'s public training release, with privacy-rewritten pages and publisher-provided tasks. These are not untouched production requests or independently human-validated labels. [Error tradeoff figure](../results/critical-review/error-tradeoffs.png) · [Critical review and claim boundaries](../docs/critical-review/README.md)

## Experiment map

| Study | Evaluation scope | Record |
| :--- | :--- | :--- |
| Earlier context study | **761 task–content pairs**; 582 distinct texts, 138 tasks | [Completion audit](../docs/extension-v3/COMPLETION-STATUS.md) |
| Larger Jev/Luna study | **3,000 clean/attack pairs**; 6,000 pages | [Results and coverage](../results/study-v7-execution/README.md) |
| Sol follow-up | **500 pairs** from the larger study | [Results and repeat checks](../results/subscription-followup-execution/README.md) |
| PromptShield benchmark | **4,000 texts**; separate detection evaluation | [External-source results](../results/study-v7-execution/README.md#coverage-and-operational-limits) |
| Second-source diagnostic | **66 pairs**; 132 released observations | [Results and limitations](../results/subscription-followup-extensions-execution/README.md#released-simulated-service-source) |
| Simulated-action pilot | **12 constructed tasks** | [Pilot outcomes](../results/subscription-followup-extensions-execution/README.md#constructed-one-step-pilot) |

**Counting note:** a task–content pair links one task to one content example; a clean/attack pair contains two examples. The Sol subset reuses main-study data. These counts are not an additive total of independent examples.

## Status

As of **November 1, 2026**, the latest bounded experiments and critical review are complete. Independent offline checks reproduce the main findings; no numerical correction is required. Human label review remains open; a blinded packet is prepared. The new five-page paper has not been drafted.

[Working notes](../docs/research-notebook/README.md) summarize the history and next steps. The [editable Google Doc](https://docs.google.com/document/d/1T8pvePmYF7rYWWugGc8HkSEtiI8CK3jU_3EZer2WFmo/edit) supports discussion with the teacher.

## Repository guide

| Location | Contents |
| :--- | :--- |
| [`docs/`](../docs/) | Protocols, design decisions and experiment notes |
| [`scripts/`](../scripts/) | Data preparation, execution and analysis code |
| [`results/`](../results/) | Compact outcomes, tables, figures and verification records |

Start with each study's result README for reproduction instructions and access requirements. The core Sol and second-source records include offline reanalysis examples. Restricted raw evidence remains local and is linked through saved hashes. Original outcomes and failures are preserved.

## Project history

The 761-pair study is an earlier completed stage. Later controls and larger evaluations extend and qualify its findings. The [historical root README](../README.md) remains unchanged as part of that record.

This repository is private. [Experiment PR15](https://github.com/tacotuesday8888/decision-context-benchmark/pull/15) and [documentation PR16](https://github.com/tacotuesday8888/decision-context-benchmark/pull/16) are draft deliveries. This overview is on the documentation branch; the default branch may still display older work.
