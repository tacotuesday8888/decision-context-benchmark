# Bibliography notes for the eventual v6 paper

Metadata and selected methods checked **2026-10-31, America/New_York**. These
notes contain no project results or changes to the frozen study. The four arXiv
citations below refer to the requested **v1** records; no venue acceptance or
peer-review status is inferred from arXiv front matter. No novelty-priority claim
is supported or proposed here.

## `chen2026browsesafepp`

- **Title:** BrowseSafe++: Benchmarking Prompt Injection Detection Across Web Contexts, Languages, and Browser Views
- **Authors, in order:** Yuetian Chen; Kaiyuan Zhang; Yuntao Du; Thomas Li; Mark Tenenholtz; Kyle Polley; Jerry Ma; Denis Yarats; Ninghui Li.
- **Year/version:** 2026; arXiv:2610.17457v1, submitted October 12, 2026.
- **Permanent metadata/version link:** [arXiv v1 record](https://arxiv.org/abs/2610.17457v1).
- **Inspected methods:** [full text](https://arxiv.org/html/2610.17457v1), §§2.1–2.2, 3.1 and C.2.
- **Restrained claims:** Its construction keeps injections while rewriting surrounding pages, with paired controls and shared task fields (§2.2). BrowseSafe-Guard is trained on the released training pairs (§3.1).
- **Use boundary:** Cite for data construction and the distinction between detection and task execution. The task field does not establish verbatim original-production-request provenance. The arXiv record marks its DOI registration pending; the versioned arXiv URL is sufficient for this citation.

## `nguyen2026infuse`

- **Title:** INFUSE: A Unified Surface Benchmark for Indirect Prompt Injection in Agentic Systems
- **Authors, in order:** Thuy Dung Nguyen; Jingyi Guo; Rana Seda Dubauskas; Sreepriya Damuluru; Taylor T. Johnson; Kevin Leach.
- **Year/version:** 2026; arXiv:2610.20776v1, submitted October 14, 2026.
- **Permanent metadata/version link:** [arXiv v1 record](https://arxiv.org/abs/2610.20776v1).
- **Inspected methods:** [full text](https://arxiv.org/html/2610.20776v1), §3.2 and Appendices A.2.2–A.4.2, B.
- **Restrained claims:** The benchmark executes agents in containers and evaluates traces and post-execution artifacts (§3.2/A.3). Its human validation combines proportional sampling with disagreement-enriched sampling (A.4.2).
- **Use boundary:** Cite its agent-evaluation methodology separately from our static file reconstruction. Source trajectories and human annotations are not project evaluation units or project human validation.

## `liu2026systemone`

- **Title:** Evaluating System One Models for Agent Security Decisions: Reliability, Calibration, and Selective Automation
- **Author:** Yixuan Liu.
- **Year/version:** 2026; arXiv:2609.33401v1, submitted September 27, 2026.
- **Permanent metadata/version link:** [arXiv v1 record](https://arxiv.org/abs/2609.33401v1).
- **Inspected methods:** [full text](https://arxiv.org/html/2609.33401v1), §§3.2–3.4, 4.1 and 5.1.
- **Restrained claims:** It separates fitting/selection/confirmation/test roles and uses whole-group paired uncertainty calculations with cluster sign randomization and Holm correction (§§3.2–3.4). Unsupported overlength inputs are distinct from silently truncated inputs (§3.3).
- **Use boundary:** Cite methodological precedent without importing thresholds, model revisions or claimed calibration. The metadata page also lists later revisions; v3 must not silently replace the inspected v1 citation. Conference-style text in HTML is not independent verification of a publication decision.

## `liu2026contextaware`

- **Title:** Robust Context-Aware Detection of Malicious Instructions in Text
- **Authors, in order:** Buzhao Liu; Xinhang Ma; Yevgeniy Vorobeychik.
- **Year/version:** 2026; arXiv:2608.05430v1, submitted August 5, 2026.
- **Permanent metadata/version link:** [arXiv v1 record](https://arxiv.org/abs/2608.05430v1).
- **Inspected methods:** [full text](https://arxiv.org/html/2608.05430v1), §4 “Approach”, Appendix B “Detector Representation and Ablations”, and Appendix C “Adversarial Training Protocol”.
- **Restrained claims:** CAD classifies sentences using the user query and surrounding response, with explicit query/context representation ablations (§4/B). Its robustness training uses embedding perturbations or generated paraphrases (§4/C).
- **Use boundary:** This is direct prior work on query-relative detection. Its trained sentence filter and agent-level utility/security evaluation are different measurements from frozen native page-level decisions; no priority claim for task-aware detection is warranted.

## `jia2025taskshield`

- **Title:** The Task Shield: Enforcing Task Alignment to Defend Against Indirect Prompt Injection in LLM Agents
- **Authors, in order:** Feiran Jia; Tong Wu; Xin Qin; Anna Squicciarini.
- **Year/venue:** 2025, *Proceedings of the 63rd Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)*, pages 29680–29697. Association for Computational Linguistics; Vienna, Austria; July.
- **Permanent metadata link:** [ACL Anthology 2025.acl-long.1435](https://aclanthology.org/2025.acl-long.1435/).
- **DOI:** [10.18653/v1/2025.acl-long.1435](https://doi.org/10.18653/v1/2025.acl-long.1435).
- **Metadata cross-check:** Anthology citation/BibTeX and the [published PDF](https://aclanthology.org/2025.acl-long.1435.pdf), title page, agree on title and author order.
- **Inspected methods:** PDF §§3.1–3.3, 4.1–4.2 and 5.1 (printed pages 29682–29685).
- **Restrained claims:** Task Shield extracts instructions, checks their contribution to user goals, and intervenes in the agent's message/tool flow (§§3–4). Its AgentDojo evaluation measures task utility and attack success (§5.1).
- **Use boundary:** This is task-conditioned agent defense, not merely an isolated static detector. Relevance/contribution should not be substituted for the separate authorization construct in v6.

## `nvidia2026agenticipi`

- **Title/version:** Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1.
- **Corporate author/owner:** NVIDIA Corporation, as identified by “Dataset Owner(s)” in the card; no individual author list is supplied there.
- **Year:** 2026. The card displays creation date `04/01/2026`; no day/month interpretation is needed for the bibliography.
- **Pinned dataset/card link:** [Hugging Face card at d738d4f361cc38bb4d7a42b9066776dade5332f5](https://huggingface.co/datasets/nvidia/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1/blob/d738d4f361cc38bb4d7a42b9066776dade5332f5/README.md).
- **Reference type:** Dataset/model-card-style `misc` citation with the full revision and access date October 31, 2026; no paper DOI is asserted.
- **Inspected sections:** “Dataset Description”, “Dataset Composition and Generation / Problem Sources”, “Curation and Filtering”, “Dataset Fields”, “Data Collection Method”, “Labeling Method”, and “License/Terms of Use”.
- **Restrained claims:** Tasks, environments and attacks are synthetic, with successful defender-targeted attacks retained after red-teaming and resampling. The verifier checks tool-call traces rather than supplying an independently human-validated static text label.
- **Use boundary:** Cite the source card for provenance. Attribute exact deletion controls to this project's adapter, not to NVIDIA observations.
