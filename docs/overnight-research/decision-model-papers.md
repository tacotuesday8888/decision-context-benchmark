# Decision-model papers: focused evidence review

November 1, 2026. Research note for Decision Context Benchmark; no experimental
inference, local model forward pass, or spending was performed for this review.
This file changes no protocol or historical result. The coordinator requested a
focused close-out before further broad research.

The important corrections are version changes, selection denominators, and release
scope. All eight records below are arXiv preprints; independent peer-review or
conference acceptance was not established here. JevOut's author-maintained README
reports an Agenthon @ NeurIPS 2026 poster acceptance; this is an author report,
not evidence of main-conference acceptance.

## Evidence matrix

“Reported” means extracted from the paper, not reproduced. Reading depth lists
the methods, results, validity discussions, and selected appendices actually
inspected; it does not claim every reference, appendix table, or experiment was
independently checked. Latest-version metadata was checked against arXiv records.

| Paper and reading depth | Units, design, and analysis checked | Interpretation for this study |
| --- | --- | --- |
| **[Broad Jev benchmark, v2](https://arxiv.org/html/2609.37647v2)**, revised October 29. Read v1 §§3–5; v2 §§5–6 and version metadata. | 37 datasets; **346,009 unique evaluation requests**, not independent environments. One template piloted on 20 development examples/dataset; duplicates reuse responses. One overlength rejection; requests run once. Qwen/Gemma baselines use exact option-token probabilities with thinking disabled. Example bootstrap: 500 resamples. Thresholds for selected tasks fit on 1,000 development examples. Choice and binary/multilabel Noul calibration differ. Main Jev evaluation: $9.15; $9.40 including pilot/additional static analyses. V2 adds five sequential environments, with episode bootstrap. | A large cheap run is feasible on its short-input workload; its throughput/cost does not forecast our longer pages. MMLU option rotation/question withholding do not exclude memorized question–answer pairs. Sequential failures reinforce the distinction between static decisions and agent outcomes. Training exposure remains unknown. |
| **[To Jev or Not?, v1](https://arxiv.org/html/2610.03324v1)**, October 2. Read §§3–5 and Appendices C–I, emphasizing C/D/G/H/I. | **12,975 test texts** across four sets; group count not supplied in the inspected analysis. Normalized copies, Dynamic perturbation relatives, and HateCheck template families are grouped; test takes priority over training/validation. Same texts receive absent versus dataset-specific definition packages and direct versus decomposed questions. All compared outputs valid. Group bootstrap: 10,000 draws; Bonferroni families. Definitions produce eight significant gains and eight losses among 28 contrasts. Appendix G compares decomposition with a direct threshold fitted on 200 validation texts. Timing uses concurrency one; Jev direct HateCheck cost $0.033/1,000 texts. | The intervention changes definitions **and label descriptions**, so it does not identify a pure definition effect. Agreement with original labels differs from policy adherence. Changed/corrected/broken predictions reveal cancellation hidden by aggregate scores. Exploratory routing fractions were not development-selected. Public-benchmark training overlap remains unresolved. |
| **[System One security evaluation, v3](https://arxiv.org/html/2609.33401v3)**, October 3. Read §3; selected §4/5 tables; §§6.1–6.3/6.6,7–8; corresponding v1 passages. | **2,200 test inputs**: WAInjectBench 1,612; R-Judge 236; AgentHarm 352 from 44 original test-task groups. Separate development/selection/confirmation/test for the first two sources; AgentHarm excluded from threshold-policy experiments. WAInjectBench inference groups use only **12 source clusters**. Paired cluster bootstrap: 2,000 draws; sign randomization assumes model exchangeability; Holm correction. V3 reports full-input valid labels for every applicable model. Calibration checks include multiple ECE bins, Brier/constant reference, signed bias, and development temperature scaling. | V1's 108-input common R-Judge subset is **historical**, not the current v3 denominator. Temperature fitting can worsen held-out scores. Fixed empirical error-budget checks are not formal deployment guarantees. The security task and unsafe-label meaning differ across sources. Total attempt count and cost were not established by this paper inspection; use the release caveats below. |
| **[JevOut, v2](https://arxiv.org/html/2609.30243v2)**, October 8. Read v1 methods/results; v2 Appendices B–D,I/J; selected H sensitivity and §4 results. | Seven sources supply 350 development and **700 held-out items**; Jev optimization selects **508 initially correct** items. Wrong target fixed before search; up to 64 accepted target evaluations/item, separate from rejected proposals. Across four targets: 1,449 eligible model–item cases, 68,912 proposals and 60,685 primary target evaluations. Wilson intervals and source-item bootstrap answer different questions. V2 adds a same-ceiling independent-generation control, blinded human assessment of **250 successes plus 100 unsuccessful controls**, and fresh identical-input retests. | The current paper is **not automatic-validation-only**. Human success validity is reported as 91.6%; it does not certify every context. Optimization is conditional vulnerability discovery, not ordinary-context prevalence or our task-information effect. Legal cases overlap development/evaluation items; a learned-generator sensitivity removes associated items. Probability cutoffs are not evidence of common calibration across systems. |
| **[Type-Safe Is Not Error-Free, v3](https://arxiv.org/html/2609.26758v3)**, October 8. Read §§3–4,7 and selected appendices; v1 compared. | **1,200 binary questions**, 300 per workflow predicate; another 600 generic-definition questions excluded from the main population. Swap name–definition bindings while preserving question/state/strings. Neutral names and random strings control structural reassignment. Bootstrap: 2,000 state resamples. Jev repeat floor uses 300 questions. Open-Jev's larger population differs. The headline **70.4-point excess flip rate is Laya**, not Jev; Jev's yes/no excess versus 0/1 is 30.4 points. | Freeze branch meanings and evaluate semantic outputs, not merely returned names. A schema-valid decision can be wrong. The study reports stability/discrimination rather than a calibration or deployment-security guarantee. Uncontrolled architecture/competence differences limit mechanism attribution. Total calls/cost and an experimental-record release were not established here. |
| **[Decision Hijacking, v1](https://arxiv.org/html/2609.28613v1)**, September 23. Read §§3–5, limitations; Appendices A/G/H. | **510 reconstructed cases = 17 contexts × 30 goals**. Three-choice snapshot main space; eight-choice sensitivity. Controls isolate override markers and generic/relatedness text. Main study **54,060 calls**, 64,860 including preliminary work; all 510 clean-qualify. Conditions interleaved; two-way pigeonhole bootstrap over contexts/goals, 10,000 draws. Adaptive search has 24 proposals plus initial call and five fresh validation calls/checkpoint. Registered relatedness effect threshold: 0.02. Reported probability grid: 0.01. | Small aggregate score shifts can be measurable without many target selections. Attacker selection, majority-repeat success, returned-confidence gates, and harmful execution are distinct endpoints. Success concentration in few goals limits generalization. Fresh validation supports repeat design; adaptive outcome selection does not belong in our primary cohort. No generative-model security ranking is established. Total monetary cost/reusable raw release not verified here. |
| **[Nudge the Judge, v1](https://arxiv.org/html/2610.18612v1)**, October 13. Read §§4–5, limitations/ethics; Appendices C/D. | Candidate collection: 1,711 repositories; top-star 356 inspected; 228 reachable applications retained. Benign markers validate data flow. Paired runs hold application state and decision contracts fixed; impact uses program rules plus model assistance. Main headline: **2,273 cases**, 1,853 flips; 1,827 unsafe labels conditional on flips. Comparison/defense subset: 183 cases in ten applications; Jev-targeted replay limits cross-model interpretation. | Application reachability and program-consumed thresholds are valuable methods. The release adds a decisive **flips-first curation** qualification below. These rates do not estimate attack prevalence across all attempts or applications. Unsafe labels describe controlled potential consequences. Total calls, invalid-attempt denominator, cost, and uncertainty were not resolved by inspected sections. |
| **[Typed-decision evidence audit, v1](https://arxiv.org/html/2609.32160v1)**, September 26. Read corpus construction/extraction, Findings 1–6, §§6–8 and Appendices A/B. | **28 papers**, not model test examples; arXiv search snapshot through September 25, with version ledger. LLM-assisted extraction followed by a second pass without first-pass access and author review. Applicability, compliance, unclear, and unscored disclosures remain distinct. Nine checklist items scored; no pooled effect meta-analysis. It reports missing label-probability controls, uncertainty, and cache measurements across its corpus. | Useful methodological map, not independent replication of those experiments or current consensus. Its older JevOut/Type-Safe versions cannot override later primary papers. A comparator's route/readout must be reported; cross-model results cannot isolate the benefit of a typed interface. No experiment call count or cost follows from “28 papers.” |

## Release checks beyond the papers

Only small documentation, manifests, repository metadata, and file trees were
retrieved. No response database, model weights, or full benchmark payload was
downloaded; no reproduction scripts were run. Repository existence and reported
record counts are distinguished below.

| Artifact inspected on November 1 | What is verified, and remaining limits |
| --- | --- |
| [Broad benchmark README at a86e675](https://github.com/AppliedMachineLearning-Lab/jev-benchmarking/blob/a86e6757e51acf3aa7d745572532f48ebf3dbb7c/README.md), [response license](https://github.com/AppliedMachineLearning-Lab/jev-benchmarking/blob/a86e6757e51acf3aa7d745572532f48ebf3dbb7c/responses/LICENSE_RESPONSES.md) | Code/results files exist; README links the [Zenodo response archive](https://doi.org/10.5281/zenodo.23039006), which was not downloaded or recomputed. Code is MIT; Jev responses have separate research/evaluation terms with imitation/competition restrictions; upstream datasets retain their terms. Do not equate open code with unrestricted response training rights. Cached-request reconstruction depends on upstream source identity. |
| [Security-eval README at 78910f0](https://github.com/yxsec/system-one-security-eval/blob/78910f045e935e73829b4629baefc8efc7ae9879/README.md) | Final predictions, partitions, protocol and analysis files exist. Release explicitly omits intermediate attempts, retries/failure diagnostics, raw responses, and benchmark text. README discloses that completion/reanalysis followed initial test inspection and is not new prospective validation. Later retained-valid responses and changed formats have separate cohort meaning. GitHub metadata reports no repository-wide license; benchmark-specific notices do not establish blanket reuse permission. |
| [JevOut protocol at c8ab231](https://github.com/xzx34/JevOut/blob/c8ab231728abb54bd61cf3c8812cb48811aae36b/docs/paper_protocol.md), [README](https://github.com/xzx34/JevOut/blob/c8ab231728abb54bd61cf3c8812cb48811aae36b/README.md) | Apache-2.0 code, prompts, synthetic examples and aggregate summaries exist. Experimental source items, raw trajectories, individual human ratings, proposer training code and weights are **not bundled**. Thus current paper reports stronger human/repeat evidence, but the public package does not independently expose all supporting observations. The independent-generation baseline shares the accepted-call ceiling, not identical realized calls, addition composition, or rejected-slot replenishment. |
| [JevProbeBench README at 9cec1be](https://github.com/xiaoxiaohg8d/JevProbe-/blob/9cec1be6ee57cc9872626222ba99739c8fcca610/benchmarks/JevProbeBench/README.md), [manifest](https://github.com/xiaoxiaohg8d/JevProbe-/blob/9cec1be6ee57cc9872626222ba99739c8fcca610/benchmarks/JevProbeBench/manifest.json) | Tree contains a 7.75-MB records file; manifest declares 2,273 records/228 projects. **Per-project cap ten, flips-first stable selection** defines the curated sample. Consequently the released 81.5% flip rate is not an unbiased all-attempt rate. Full attempt ledgers/raw execution logs are absent; historical nulls remain. One input is redacted without rerunning it; historic outcomes do not measure edited bytes. Repository MIT license verified; records were not independently counted. |

Public benchmark use and project-held-out sampling do not establish model-training
non-overlap. No private training corpus was inspected. Preserve that uncertainty
for every proposed model, including the specialist baseline.

## Prioritized implications, without changing the preparation protocol

1. **Correct the related-work version ledger before reusing its claims.** Use broad
   Jev v2, security v3, JevOut v2, Type-Safe v3; retain earlier versions as historical
   evidence. Avoid transferring a headline from Laya to Jev or an old common-support
   cohort into current results.
2. **Keep the narrow contribution.** In this inspected set, the exact contrast of
   authentic publisher task information against empty/reminder/character-matched
   filler for source-label agreement on unchanged paired webpages was not found.
   This is a contribution hypothesis, not a literature-complete “first” claim.
   Context sensitivity, instruction-package effects, calibration failures and
   program consequences already have direct prior evidence.
3. **Preserve original planned denominators.** Do not import initially-correct,
   successful-attack, or flips-first selection into confirmation. Report groups,
   pages, condition cells, logical evaluations, actual transports, retries and
   windows separately. Existing complete-pair estimates plus full-target bounds
   are preferable to a single silently reduced cohort.
4. **Add explanatory summaries only within the frozen analysis scope.** Counts of
   corrected and newly broken predictions, FPR/FNR, probability diagnostics and
   missingness can explain a net task effect. They must not replace the primary
   estimand or become threshold/prompt selection criteria on confirmation.
5. **Treat repeat measurements as new observations.** Identical bytes, fresh
   transport namespace, request identity and interleaving matter. A cache replay
   is not a stability measurement; selected successful examples do not estimate
   whole-cohort stability. The planned outcome-blind repeat subset avoids that
   particular selection restriction.
6. **Keep the endpoints separate.** PromptShield supplies a different complete-
   request classification endpoint; neither it nor static page classification
   proves task completion, attack prevention, causal architecture superiority,
   deployment calibration, or real-world prevalence. A larger model/call count
   cannot repair a mismatched construct.

The current preparation already addresses most of these methods. No extra model,
data source, factorial, threshold tuning, or agent-environment run is justified
merely to match the literature. No paper text was drafted here.

Skill provenance: scientific-critical-thinking v1.5 guided unit/selection/claim
checks. Reference metadata verified November 1: Kassis, T., Agarwal, V., He, Y.,
Patel, D., and Brueckner, A. M. (2026), [Scientific Agent Skills: A Library of
Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065),
current arXiv record v2. The skill is procedural guidance, not independent review
or certification of this note.
