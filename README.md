# Decision Context Benchmark

**Does knowing the user's task help an AI detect prompt injection?**

Prompt injection is text that tries to redirect an AI away from the user's request. This project compares decision models such as Jev with general-purpose language models, with and without task information.

## Start here

- [Experiment notes: question, data, models and findings](https://docs.google.com/document/d/1T8pvePmYF7rYWWugGc8HkSEtiI8CK3jU_3EZer2WFmo/edit)
- [Four short examples for teacher discussion](https://docs.google.com/document/d/1h5RO4VKXj-eB-dk3-C2v0YRtCl9n_DrriGXa66m7lbk/edit)
- [Results, figures and five-page outline](https://github.com/tacotuesday8888/decision-context-benchmark/tree/f88de969/docs/paper-preparation)

## What was tested

| Study | Data | Models |
|---|---|---|
| Earlier comparison | 761 task–text combinations from AgentDojo, AgentDyn and InjecAgent | Jev, GPT-6 Luna, GPT-6 Astra, Nimble, Laya; ProtectAI v2 as a content-only reference |
| Larger comparison | 3,000 normal/attacked webpage pairs from BrowseSafe++ | Jev and GPT-6 Luna (Decisions) |
| Follow-up | 500 pairs selected from the larger study | GPT-6.1 Sol |
| Supporting checks | 4,000 PromptShield texts; 66 DTap pairs; 12 authored agent tasks | Separate comparisons, not one combined test |

The earlier study contains 582 distinct texts and 138 tasks. A webpage pair contains two page versions. Counts use different units and overlap, so they should not be added together. Models were tested, not trained or enlarged.

## Main finding

**Task information changes the kinds of mistakes models make, but does not consistently improve detection.**

Compared with an empty task field, Jev's false-alarm rate fell from **12.9% to 6.6%**, while its missed-attack rate rose from **8.1% to 11.8%**. GPT-6 Luna and GPT-6.1 Sol had higher average error in their main comparisons. The small DTap comparison showed a different pattern for Sol.

The main Jev/Luna analysis uses 2,850 shared complete pairs; Sol uses 498 complete pairs. These are not a matched model ranking. Results use publisher labels, include uncertainty and preserved failures, and do not establish that working agents are safer.

## Research records

Current experiments and preparation files are on research branches under review. This front page links to saved versions rather than merging unfinished research branches.

- [Earlier 761-combination study](https://github.com/tacotuesday8888/decision-context-benchmark/blob/f88de969/results/extension-v3/report.md)
- [Main BrowseSafe++ results](https://github.com/tacotuesday8888/decision-context-benchmark/blob/f88de969/results/study-v7-execution/README.md)
- [GPT-6.1 Sol follow-up](https://github.com/tacotuesday8888/decision-context-benchmark/blob/f88de969/results/subscription-followup-execution/README.md)
- [Second source and simulated-agent test](https://github.com/tacotuesday8888/decision-context-benchmark/blob/f88de969/results/subscription-followup-extensions-execution/README.md)
- [Related work and comparisons](https://github.com/tacotuesday8888/decision-context-benchmark/blob/f88de969/docs/critical-review/METHODS-NOTE.md)

The current five-page paper has not been written. Earlier drafts and setup records are historical, not the latest findings. Documents and repository links require access.
