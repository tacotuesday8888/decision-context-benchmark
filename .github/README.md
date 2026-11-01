# Decision Context Benchmark

**Does knowing the user’s task help AI detect prompt injection?**

We compare decision models such as Jev with general-purpose language models, using the same content with and without task information.

[Research notes](https://docs.google.com/document/d/1T8pvePmYF7rYWWugGc8HkSEtiI8CK3jU_3EZer2WFmo/edit) · [Four examples](https://docs.google.com/document/d/1h5RO4VKXj-eB-dk3-C2v0YRtCl9n_DrriGXa66m7lbk/edit) · [Results](../results/paper-preparation/) · [Reproduce](../REPRODUCING.md) · [Data](../DATA.md)

## Main finding

Task information changes mistakes, but does not consistently improve detection. In the main comparison, Jev flagged fewer normal-labeled pages while missing more attack-labeled pages. GPT-6 Luna and GPT-6.1 Sol had higher average error; a smaller second-source test produced different patterns.

![False alarms and missed attacks](../results/paper-preparation/figure-2-error-tradeoff.png)

These are results against publisher labels, not proof of safer working agents or a universal model ranking.

## Experiments

| Stage | Data | Main models |
|---|---|---|
| Earlier study | 761 task–text combinations from three sources | Jev, GPT-6 Luna, GPT-6 Astra, Nimble, Laya; ProtectAI v2 reference |
| Larger study | 3,000 BrowseSafe++ normal/attack pairs | Jev and GPT-6 Luna (Decisions) |
| Follow-up | 500 pairs from that larger study | GPT-6.1 Sol |
| Supporting checks | PromptShield, DTap and 12 authored agent tasks | Separate comparisons |

The earlier study has 582 distinct texts and 138 tasks. The main Jev/Luna analysis uses 2,850 complete pairs; Sol uses 498. Counts overlap and must not be added. [Details and access](../DATA.md)

## Use the repository

- **Read results:** [main study](../results/study-v7-execution/README.md), [Sol follow-up](../results/subscription-followup-execution/README.md), [second source](../results/subscription-followup-extensions-execution/README.md).
- **Check the numbers:** follow [offline reproduction](../REPRODUCING.md); no model calls or API keys needed for the compact check.
- **Understand the design:** [protocol](../docs/subscription-followup/PROTOCOL-v1.md), [related work](../docs/critical-review/METHODS-NOTE.md), [review findings](../docs/paper-preparation/REVIEW-RESOLUTION.md).

`docs/` holds methods and notes; `scripts/` holds code; `results/` holds saved outputs. Restricted raw data remain local.

## Status

Completed experiments and reviewed preparation are on `main`. The current paper is not yet written. The repository remains private; there is no paper DOI or public release to cite.

Historical stage tips are kept as archive tags. The root README is a frozen earlier record; this GitHub overview is the current guide. [History](../docs/repository/HISTORY.md) · [Contribution rules](../CONTRIBUTING.md)
