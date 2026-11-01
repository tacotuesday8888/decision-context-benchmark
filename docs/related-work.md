# Related work and dataset selection

Reviewed October 26, 2026. The purpose is to locate this pilot accurately, not to
make novelty a precondition. Sources below are original papers, repositories, and cards.

| Source | Overlap and implication for this experiment |
| --- | --- |
| [Robust Context-Aware Detection of Malicious Instructions in Text](https://arxiv.org/html/2608.05430v1), §4 and Appendix B | CAD detects malicious sentences using isolated and contextual representations. Its ablations separately remove the user query and surrounding response. This is direct overlap with our research question; a context/no-context comparison is not new. Our pilot applies fixed prompts to a hosted typed-decision interface and general chat interfaces, with operational email-level labels. It does not reproduce CAD training or its agent-level security results. |
| [LLMail-Inject](https://arxiv.org/html/2506.09956v1), §2, §4, Appendices A/J | Adaptive attacks on an email assistant already compare defenses including LLM judges and task-drift detection. The data includes real competition submissions and synthetic scenario emails. We use its released original context and tool outcomes, not newly generated attacks. A detector's binary accuracy differs from the challenge's tool-based attack success rate. |
| [BIPIA](https://arxiv.org/html/2312.14197v4), §4–7; [repository](https://github.com/microsoft/BIPIA) | Adds published attacks into external task content and evaluates model resistance and defenses. It supports deterministic contexts, but its injection templates are not ready-made semantic segment labels for arbitrary extraction. Reusing many templates on the same documents would require grouping on both axes. |
| [Tensor Trust](https://arxiv.org/html/2311.01011v1), §3 and role ablations; [data](https://github.com/HumanCompatibleAI/tensor-trust-data) | Human game attacks, defenses and outcomes establish earlier work on prompt hierarchy and context. The access-code game has different tasks and lacks the email source-neighbor structure used here. The inspected data repository has no explicit data license; do not infer a data grant from the separate game's software license. Excluded from this pilot. |
| [InjecGuard / NotInject](https://arxiv.org/html/2410.22770v2), §3 and Appendix C; [current repository](https://github.com/leolee99/PIGuard) | NotInject contains benign prompts with attack-associated trigger words and exposes over-defense. It motivates reporting false positives. It is generated/refined using LLMs in the original study, has only benign target labels, and does not supply authentic paired user tasks/source neighbors. The code/model MIT license is not proof of every dataset's rights; a standalone NotInject data grant was not established here. Excluded rather than inventing task context. |
| [WASP](https://arxiv.org/abs/2504.18575), [implementation](https://github.com/facebookresearch/wasp) and [license](https://github.com/facebookresearch/wasp/blob/ffee6f41fde76acd14bd792db442479c506260c2/LICENSE) | End-to-end realistic web-agent attacks, with visible/hidden website content and task context. It is a different evaluation unit from text-only email classification and would require environment reconstruction. The inspected repository license includes CC BY-NC 4.0; underlying web environments/components have their own notices. No WASP content is redistributed here. |
| [ARGUS / AgentLure](https://arxiv.org/html/2605.03378v2), §3–5 | More recent task-relative attacks and auditing further limit any novelty claim. A useful larger extension would examine genuinely task-ambiguous instructions with published task/context annotations; our fixed summarization fixture cannot establish this. |

## Why LLMail-Inject

The [pinned dataset card](https://huggingface.co/datasets/microsoft/llmail-inject-challenge/blob/1063bdf01ec8762b812d5e06ee768a06faa5a6f7/README.md)
declares MIT and supplies benign fixtures, original queries and submission outcomes.
The code release's [MIT notice](third-party/llmail-LICENSE.txt) is retained. We use
stronger successful-tool-call eligibility rather than the release's model-judged
submission annotations. Failed attacks are never assigned benign labels.

Scenario 2 has 20 source emails in metadata, but the pinned BasicEmailRetriever uses
only the first nine. Its ordering gives an authentic neighbor without inventing text
or duplicating the candidate. RAG scenarios would require reconstituting the exact
retrieval result; they are omitted. Unrelated standalone benign datasets would
confound class with dataset and would need invented context, so they are not mixed in.

## Leakage and remaining scope

All sources are public and old enough to have entered model training. None of these
providers discloses a complete training corpus, so contamination cannot be ruled out.
Selection by historical success favors attacks suited to the original target defenses.
We prevent exact candidate duplication in context, metadata-to-prompt leakage, team
crossing between development/evaluation, and obvious near-duplicate attack variants.
These controls do not remove synthetic-style shortcuts, common attack motifs, one
shared trusted task, one shared benign theme, or memorization of published content.
The pilot estimates performance on the selected fixed scenario, not deployment risk.
