# Decision Context Benchmark

Does knowing the user's task help a model detect prompt injection?

This project compares detection with and without task information, tracking false alarms on harmless content and missed attacks.

## Start here

- [Experiment notes](../docs/research-notebook/README.md): what was tested, what happened and what still needs checking.
- [Google Doc](https://docs.google.com/document/d/1T8pvePmYF7rYWWugGc8HkSEtiI8CK3jU_3EZer2WFmo/edit): editable notes for discussion.
- [Earlier 761-pair study](../docs/extension-v3/COMPLETION-STATUS.md).
- [Larger Jev/Luna study](../results/study-v7-execution/README.md), [Sol follow-up](../results/subscription-followup-execution/README.md), and [second-source/pilot results](../results/subscription-followup-extensions-execution/README.md).

## Current findings

Jev raised fewer false alarms with task context but missed more attacks. Sol and Luna made more errors on the main dataset. A second source gave different results, and the small agent pilot did not demonstrate better protection.

These findings concern the tested configurations and source labels. They do not establish a universal model ranking or reliable agent protection.

## Data and status

The earlier study used **761 task–content pairs**. Later work included **3,000 clean/attack pairs**, a **500-pair Sol subset**, **4,000 separate benchmark texts**, **66 second-source pairs**, and **12 constructed pilot tasks**. These are different units with overlap, not one additive total.

Latest runs and computational checks are complete. Ambiguous labels and final claims still need review. The new five-page paper has not been drafted.

## Repository guide

- `docs/`: methods, protocols and experiment notes.
- `scripts/`: preparation, execution and analysis code.
- `results/`: compact outcomes, figures and verification records.

Result READMEs explain reproduction and access limits. Restricted raw records remain local; saved hashes link them to analyses. Original outcomes and failures are preserved.

Work is private and delivered through draft pull requests, including [experiments in PR15](https://github.com/tacotuesday8888/decision-context-benchmark/pull/15) and [these notes in PR16](https://github.com/tacotuesday8888/decision-context-benchmark/pull/16). The default branch may still show older work. The [root README](../README.md) is preserved as historical documentation.
