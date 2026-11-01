# Research notes

November 1, 2026

## Question

Does knowing the user’s task help AI spot prompt injection—text that tries to redirect it? We compare decision models such as Jev with general-purpose language models.

## Tests

- Earlier: 761 task–text combinations from AgentDojo, AgentDyn and InjecAgent (582 texts, 138 tasks).

- Larger: 3,000 BrowseSafe++ normal/attack pairs, or 6,000 page versions. Jev and GPT-6 Luna (Decisions) shared 2,850 complete pairs.

- GPT-6.1 Sol: 500 pairs from that same collection; 498 complete.

- Extra checks: 4,000 PromptShield texts, 66 DTap pairs (62 complete), and 12 invented agent tasks.

Models across studies: Jev, GPT-6 Luna, GPT-6 Astra, GPT-6.1 Sol, Nimble, Laya and ProtectAI v2. Not every model ran on every dataset.

Main comparison: same page, with no task, the real task, a warning, or filler matched by character count. No models were trained.

## Findings

Adding the task reduced Jev’s false alarms from 12.9% to 6.6%, but increased missed attacks from 8.1% to 11.8%. Luna and Sol made more errors on average in the main comparison. Sol’s smaller DTap test was mixed. The agent test showed no protection benefit.

Takeaway: task information changes mistakes; it does not always help.

## Limits

We use publisher labels, not fully human-checked answers. BrowseSafe++ uses rewritten pages from its training release. Counts overlap and use different units; don’t add them. These results do not establish a universal model winner or safer real-world agents.

## Related reading

To Jev or Not?: decision models for hate speech. CAD: a context-aware text filter. Task Shield: checks agent actions against user goals. Our study tests existing detectors, not a new defense.

## Next

Discuss the four examples and results with my teacher, then plan the paper. Outline ready; paper not written.

Code and results: private GitHub.

[Editable research notes](https://docs.google.com/document/d/1T8pvePmYF7rYWWugGc8HkSEtiI8CK3jU_3EZer2WFmo/edit) · [Four examples to discuss](https://docs.google.com/document/d/1h5RO4VKXj-eB-dk3-C2v0YRtCl9n_DrriGXa66m7lbk/edit)
