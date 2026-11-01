# Source and method comparison — technical notes

These notes compare experimental units and source construction. They are not a
manuscript or evidence that all benchmarks measure the same outcome. Primary
pages were inspected on November1,2026.

| Work | Actual count unit and construction | Outcome and implication here |
|---|---|---|
| [To Jev or Not?, v1](https://arxiv.org/html/2610.03324v1), University of Cyprus | Table1 has4,120 Dynamic,3,203 MHS,1,924 HateXplain and3,728 HateCheck test texts: **12,975** by addition, across four datasets. The methods compare six decision-model configurations with baselines. Text origins include annotator-authored challenge cases, social-media material and functional tests. | Static saved-text moderation, including supplied-definition changes on the same texts. An acting agent is not required for this question. Its dataset breadth is useful precedent;12,975 texts are not12,975 independent user-task groups. |
| [AgentDojo, v3](https://arxiv.org/html/2406.13352v3) | The paper describes97 user tasks and629 security cases. Its data card describes author-created tasks and LLM-generated environment data that the authors inspected and edited. | Tool-calling agents are evaluated for legitimate utility and security using environment checks. Constructed data can support a useful benchmark with transparent provenance and validation. Our old project exposure prevents presenting those task IDs as newly unseen confirmation. |
| [InjecAgent, v2](https://arxiv.org/html/2403.02691v2) |1,054 combinations arise from17 user cases and62 attacker tools/cases. Section2.2 describes GPT-4 assistance followed by manual refinement and checking. User-tool response templates and attacker instructions are assembled deliberately. | The model's next actions are evaluated for attacker goals. Attack success, parser validity and the number of underlying user cases are different quantities. The many combinations do not create1,054 independent tasks. |
| Decision Context Benchmark v7 |6,000 main pages in3,000 grouped clean/attack pairs, plus4,000 PromptShield complete requests. Every native model has four within-page context conditions; repeated requests do not create new independent cases. BrowseSafe++ supplies the main task field. | Static source-label classification. PromptShield transfer does not replicate the task-context intervention because it lacks a separate authentic task field. The causal intervention is changed supplied context on a fixed candidate, not a claim that all clean/attacked pages differ only by one injected instruction. |
| Separately prepared DTap source | Published tasks and complete clean/attacked tool observations are paired by exact instruction, trusted Agent configuration and tool-call arguments. The source is a benchmark; runtime details can differ between released episodes. Conservative history/template/document closure currently yields66 components before final review. | A second task-bearing classification source with its own frozen groups, labels, provenance and precision limits. It is not pooled with BrowseSafe++;a small attained sample cannot confirm the earlier1–2-point effects. See [source receipts and boundaries](SECOND-SOURCE.md). |
| New simulated-action pilot |12 explicitly authored fake-world task families, one clean/attacked observation pair each, crossed with no gate/Jev gate. At most48 fresh actor calls and24 native gate calls; the independent units remain the12 tasks. | A one-step action packet is executed by an isolated in-memory interpreter. Separate predicates measure requested exact-extraction completion and attacker-goal success. It is a constructed diagnostic, not a replay of released AgentDojo episodes, full-agent robustness study or evidence about real-world attack prevalence. |

Synthetic construction is compatible with useful research when its provenance,
labels, controls and validation are explicit. The current project must not borrow
the original authors' manual validation claim for newly authored cases or call
its own AI-only reviews human adjudication. Similarly, a static detector's error
rate is not an agent attack-success rate. A gate must be compared with the same
actor without that gate, on both clean and attacked conditions, while measuring
legitimate task completion as well as attacker success.

Future paper target: five pages. No manuscript drafting is part of this work.
