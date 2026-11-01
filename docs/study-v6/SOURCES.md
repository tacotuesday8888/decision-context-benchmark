# V6 source acquisition and boundaries

## BrowseSafe++

- [Dataset](https://huggingface.co/datasets/perplexity-ai/browsesafe-plus-plus), pinned
  revision `3e9f4b3cef9295a1928ddfb33675eafd8bb68259`.
- [Construction/evaluation repository](https://github.com/perplexityai/browsesafe-plus-plus),
  inspected at `95f99494b4bdafec41a8a50ddcefbb795fbae68f`. The local inert code cache
  has Git-blob and SHA-256 receipts. No upstream code was executed.
- Training release: **29,500 pairs / 59,000 pages**, CC BY 4.0. Test release:
  **9,175 unlabeled pages**, one arm per test pair; not 18,350 released labeled pages.
  Test terms prohibit training/tuning, redistribution and label/pair recovery.
  Our downloader accepts only `data/members-train-NNNN.parquet`, never test paths.
- The owner confirmed gated access. Connector access and local authenticated
  training-Parquet reads were separately verified. Credentials stay in the local
  Hugging Face cache, outside Git. No inference, purchase or subscription was involved.
- The embedded screenshot dataset is about 39 GB. `fetch_browse.py` reads metadata
  and selected Markdown columns by Parquet ranges, with four bounded download workers.
  It never requests screenshot, HTML or accessibility-tree columns. Restricted raw
  material, IDs, text and review mappings remain Git-ignored.
- License bytes are retained at `data/raw/study-v6/browsesafe-license.md`, SHA-256
  `4c0a61dfdb9039ab8cd5d65e5881f56216b60064aa523807de3a0d5878b37d68`.

Detector input is exactly `benign_task` plus complete `content_markdown` (and the
fixed question/role markers). There is no released governing system policy to
invent. Neither `expected_outcome`, `malicious_goal`, injection fragments, source
labels, IDs nor attack annotations enter the detector. Task text must match
between both arms. Empty/identical Markdown pairs are quarantined without replacement.
Injection-reference binding is reported separately; absence of an exact reference
match is not an automatic semantic decision, because a renderer can change strings.

The task is **source-provided benchmark context**. The inspected evidence does not
establish that it is the original production user's exact request. Surrounding
pages were rewritten and identifiers masked; do not call our exported page an
untouched real-world capture. Upstream labels and quality checks are evidence,
not independent review performed by this project.

The pool selection first joins exact normalized tasks and repeated injection
reference strings of at least five words over all labeled training pairs. One
hash-ranked pair per component is eligible for a fixed 1,000-component sample.
This favors distinct cases over repeated variants; it is not prevalence sampling.
Subsequent full-text grouping and external semantic review can merge those
components further. The final confirmation is our held-out use of a public
**training** release, not the official BrowseSafe++ test or leaderboard result.
Closed-model pretraining exposure remains unknown. BrowseSafe-Guard, trained on
these training pairs, must not be scored here as a clean held-out baseline.

## NVIDIA agentic indirect injection

[Release](https://huggingface.co/datasets/nvidia/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1),
CC BY 4.0, revision `d738d4f361cc38bb4d7a42b9066776dade5332f5`.
The 1,272-row JSONL is pinned by SHA-256 in `scripts/study_v6/common.py`.

The release is fully synthetic and success-selected against its defender. We take
the exact source system message as policy, exact user message as task, and the
single environment string containing the complete injection as candidate. A
counterfactual control deletes that unique exact injection occurrence only; it is
**our constructed deletion control**, not an upstream observed benign rollout.
No whitespace repair, paraphrase or invented task is applied. Tool catalogs are
not inserted into the task; reviewers must flag cases whose meaning requires them.

Audit: 1,253 adaptable pairs; four ambiguous/missing injection locations and 15
empty deletion controls quarantined. Task/injection lexical closure gives 205
provisional components. Select at most one pair per component, hash-ranked with a
domain round-robin, yielding **200 pairs / 400 rows** across nine source domains.
These are field-level static classifications, not full tool observations, traces,
or measurements of whether the upstream verifier's attack actually succeeded here.

## Other useful sources and non-expansions

| Source | Decision |
|---|---|
| AIB | Preserve the 158 reviewed-candidate preparation rows; a separate replication source with supplied task/policy. No independent reviews completed yet. |
| SPML | Preserve 200 selected direct user/policy cases from 16,012 released records. More SPML rows do not add authentic tool-output task contexts. |
| INFUSE | Preserve 35 static clean/attack pairs; do not count 41,824 trajectories as distinct tasks or claim our static reconstruction ran their containers. |
| Authored scope pairs | Preserve 24 pairs / 48 rows as an explicit synthetic authorization diagnostic. |
| AgentDyn | Repository revision remained `5353cf7615b135cace8d07c8f12dac53a16b6db3`; all 60 tasks were already used in earlier project work. More attack runs are replication, not fresh tasks. The cached recursive tree is truncated and is not a complete inventory. |
| Original BrowseSafe, BoundaryPairs | No suitable independent authentic user-task field for this intervention. Do not infer a task from page topic or categorical context. |
| Prompt-2-Prompt v2 | Inspected structure has prompt/prompt_injection/mark; provenance, license and task boundaries do not support adding it to the main task study. |
| TensorTrust / ASB | Policy-game and attack-template evidence remains useful related work. Unresolved rights or lack of a faithful static observed tool boundary prevent a casual bulk import. |
| BIPIA / TaskTracker / AgentDojo / InjecAgent | Preserve prior exposure records; adding old prepared cases would not create fresh confirmation. |

The broader 27-source inventory and earlier license/provenance audits remain in
`docs/source-discovery/` and `docs/study-v5/RESEARCH.md`. A larger public string
collection is not automatically a better dataset for the task-information question.
