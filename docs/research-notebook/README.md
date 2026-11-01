# Experiment notes

Summary of saved experiments · November 1, 2026

## Question

Does giving a prompt-injection detector the user's actual task help it make fewer mistakes?

## What was tested

- **Earlier study:** 761 task–content pairs, covering 582 distinct texts and 138 tasks.
- **Larger study:** 3,000 clean/attack pairs — 6,000 pages — tested with Jev and Luna.
- **Sol follow-up:** 500 pairs from the larger study.
- **Other checks:** 4,000 PromptShield texts, 66 pairs from a second source, and 12 constructed agent tasks.

A task–content pair means one task linked to one piece of content. A clean/attack pair contains two examples. These counts overlap and use different units, so they should not be added together.

The later experiments compared the published task with an empty-task prompt, a generic warning and “Context unavailable.” filler matched by character count. These controls test several explanations, but do not isolate task meaning from every other prompt difference.

The main source uses public training-release pages rewritten for privacy and publisher-provided tasks. Results measure agreement with source labels, not independently human-validated task judgments.

## What happened

- **Jev:** fewer false alarms, but more missed attacks. On the main shared comparison, false alarms fell from 12.9% to 6.6%; missed attacks rose from 8.1% to 11.8%.
- **Sol and Luna:** task context increased errors on the main dataset. Sol's increase was about 1.1–1.3 percentage points versus the controls.
- **Second source:** Sol improved against some controls, but the advantage over unrelated text of similar length was unclear. Only 62 pairs had complete results across both models.
- **Agent pilot:** no protection benefit demonstrated. The ungated actor already resisted all 12 attacks. Blocking information also removed facts needed for the task.
- **Scoring issue:** one correct answer containing “12 units” failed a rule expecting “12”. The original score is preserved, with the issue documented.

Takeaway: task context changes decisions, but it does not consistently improve detection. Both false alarms and missed attacks matter.

## Still to check

- Complete human label review. The prepared packet includes 24 flagged pairs (23 ambiguous plus one other disagreement) and eight comparison pairs; no human judgments have been entered.
- Use the [error tradeoff figure](../../results/critical-review/error-tradeoffs.png) alongside the paired effects.
- Keep the [reviewed claim boundaries](../critical-review/INITIAL-REVIEW.md#claim-to-evidence-map) when drafting. The Astra review is complete; no numerical correction is required. See the [resolution log](../critical-review/RESOLUTION.md) for accepted and rejected findings.

## Records

[761-pair study](../extension-v3/COMPLETION-STATUS.md) · [Main results](../../results/study-v7-execution/README.md) · [Sol results](../../results/subscription-followup-execution/README.md) · [Second source and pilot](../../results/subscription-followup-extensions-execution/README.md)

[Editable notes](https://docs.google.com/document/d/1T8pvePmYF7rYWWugGc8HkSEtiI8CK3jU_3EZer2WFmo/edit)
