# Detector and task-context evidence review

Reviewed 2026-11-01 against `docs/next-study/PROTOCOL.md` v7-plan-20261101. This is a research/readiness note, not a frozen protocol, experiment result, or authorization to change the panel. No classification, embedding, judge, or other model inference was performed. Only papers, small source files, release cards, and public metadata were retrieved; no additional benchmark corpus or model weights were downloaded.

## Actionable recommendation

**Keep the current panel and execution scope.** ProtectAI is a useful reproducible **legacy reference**, but should not be described as the strongest available dedicated detector. The literature supports investigating task information; it does not establish that adding a task always improves detection, calibration, or downstream utility.

The defensible contribution is the **within-example comparison of publisher-provided task information against empty-task, generic-reminder, and character-length controls**, using fixed models and complete Markdown on a project-held-out population. Avoid claiming the first task-aware detector or the first task-context ablation. The external PromptShield arm tests a different full-request classification question and cannot replicate the task effect.

Do not add a detector simply because its author-reported F1 exceeds ProtectAI. If another local comparator is later authorized, shortlist Horizon-Labs base for its independent agent-output evidence, subject to its known PromptShield training and exact revision. Sentinel remains an informative candidate, with weaker evidence for this particular operating setting and access/license friction. These are recommendations, not panel mutations.

## Review depth and evidence boundaries

Eight requested primary papers received targeted full-text review: methods, relevant results, limitations, and the appendices listed below. This was not a line-by-line reproduction, systematic review, or rerun of published scores. An additional close prior-work paper was spot-checked before the request to stop expanding research.

All numerical experimental results below are **paper-reported**. Public model metadata/configuration was checked separately without loading weights. Dataset counts from the existing project protocol are **not newly independently recounted here**. A card's declared size or split count is not verification of the underlying files. Unreported overlap is recorded as unknown, not absent.

## Primary-paper findings

### 1. Sentinel — Ivry and Nahum, arXiv:2506.05446

**Depth:** §§3–6, tables 1–2, implementation appendix, release card.

The paper fine-tunes 395M ModernBERT-large, with native 8,192-token context, on a source mixture including Salad-Data, benign instruction corpora, jailbreak collections, SPML, and 1,400 private synthetic examples. It reports a 90/10 internal split and average public-benchmark binary F1 of .938 versus .709 for ProtectAI v2. This is an author-run comparison, without matched-FPR results, confidence intervals, or a documented family-level split. Architecture and data improvements are changed together, so their individual contributions are not isolated. Private data obstruct exact training reconstruction; reported false positives include ambiguous/security-related phrasing.

Neither PromptShield nor BrowseSafe is named as training data. That does **not** establish zero overlap: PromptShield predates Sentinel, public corpora may share underlying prompts, and Sentinel's private mixture is unavailable. BrowseSafe++ itself postdates the 2025 paper, but later checkpoint changes and inherited attack material require separate assessment. It has no authentic-task-versus-reminder/length ablation. [Paper](https://arxiv.org/html/2506.05446)

### 2. PIGuard / NotInject — Li et al., ACL 2025

**Depth:** §§3–5, tables 1–3, limitations, appendix pointers; code/model cards.

NotInject comprises 339 GPT-4o-mini-generated, manually reviewed benign examples with one, two, or three trigger words. PIGuard uses DeBERTa-v3-base, 512 tokens; its MOF procedure identifies individually suspicious tokens, generates 1,000 benign combinations, and retrains. The source collection contains 61,089 benign and 15,666 attack examples before that step. Reported accuracies are 87.32% over-defense, 85.74% benign, and 77.39% malicious; their category average is 83.48%.

NotInject is a deliberately enriched false-positive stress test, not representative traffic or a complete security benchmark: an always-benign rule gets 100% there. Its usefulness comes from evaluating attack sensitivity separately. Synthetic trigger-word construction limits deployment generalization. The paper tests training/augmentation choices, not a controlled authentic-user-task input intervention. Its shared BIPIA ancestry also matters when interpreting later benchmark scores. [Authoritative ACL paper](https://aclanthology.org/2025.acl-long.1468.pdf)

### 3. PromptShield — Jacob et al., arXiv:2501.15145v2

**Depth:** §§2–5, tables 2/4/7–9, §7, appendices A–B; official repository and dataset card.

The taxonomy distinguishes conversational requests from application-structured requests. Its evaluation uses source-separated corpora and attack-generation pipelines; the detector is trained on roughly 20,000 examples. Table 4 reports TPR at 1% FPR of 94.80% for its fine-tuned Llama-3.1-8B, 43.22% for its DeBERTa variant, and 1.97% for ProtectAI v2. These are not interchangeable model results. Thresholds are selected using evaluation ROC curves, making them diagnostic operating-point comparisons rather than separately validated deployment thresholds.

Conversational-data inclusion is a **training-composition ablation**, not an authentic-task input ablation. The released prompt combines instructions and data; treating its task text as a separately available authentic user request would change the source. Known weaknesses include concept drift, adaptive evasion, and text-only evaluation. The old detector's training-overlap assurances do not certify future models. [Paper v2](https://arxiv.org/html/2501.15145v2)

### 4. BrowseSafe++ — arXiv:2610.17457

**Depth:** construction §2, detector §3.1, §4, appendices C/E and relevant result tables; release metadata.

The paper reports 38,675 attack/control pairs, with 29,500 train and 9,175 test. Most injections were production-observed; surrounding pages were privacy-rewritten and the unchanged injections reinserted. Candidate collection uses classifier/regex screening, followed by model voting and quality checks, so this is selected, processed material rather than a random web sample. Each pair has task/outcome annotations.

Crucially, Appendix C.2 gives detectors **no user task**, caps Markdown at 40,000 characters, and excludes invalid/refused outputs from ordinary metrics. BrowseSafe-Guard is trained on these pairs using classification plus pairwise ranking, with injection-centered training crops. Its Markdown F1/FPR are 93.26/7.40%. Those are task-free, publisher-test results and cannot be compared directly with complete-page task-aware v7 results. Using released training pairs precludes calling BrowseSafe-Guard unexposed. Static recognition and resistance during task execution are distinct outcomes. [Paper and appendices](https://arxiv.org/html/2610.17457)

### 5. Passing the Test You Trained On — arXiv:2610.03448

**Depth:** §§4–6, tables 2–4, appendices A–D; public implementation inspected.

Independent detector comparisons replay ground-truth tool calls and label injections by differential replay. At 1% FPR, PIGuard detects 95.1% on BIPIA but 2.1% on AgentDojo; Horizon-Labs reaches 82.2% on AgentDojo and 100% on τ-bench. Their training audit finds PIGuard contains BIPIA training inputs, while seen InjecAgent attack strings do not improve detection in unfamiliar tool-output form.

The close task ablation is Sheltron: trusted task information raises AUROC .86→.91, but lowers TPR at 1% FPR 20.1→9.0%; this interface use is undocumented. Thus task information can alter calibration adversely. Caveats: thresholds are selected on the evaluated set; classification intervals resample rows despite shared tasks/templates; attacks are static; only some training data is auditable. Appendix A truncates Sentinel variants to 2,048 tokens, below their advertised native capacities. Results do not establish an unconditional winner for full webpages or current mutable checkpoints. [Paper](https://arxiv.org/html/2610.03448)

### 6. CAD — Liu, Ma, and Vorobeychik, arXiv:2608.05430

**Depth:** §§2–4, limitations, appendices B–C, architecture/ablation tables; checkpoint/code cards.

CAD trains a sentence classifier over frozen Jina embeddings: an isolated sentence plus its marginal embedding contribution to the query/document. Its goal is filtering sentences before downstream agent execution, not merely classifying a whole page. Synthetic training factorizes query, clean response, and attack generation; 24,665 sentence representations train the classifier. Static and adaptive evaluations use AgentDojo/AgentDyn, with explicit utility–ASR tradeoffs.

Appendix B already removes the user query while retaining the document. AgentDyn clean utility falls 36.7→28.3%, and static ASR rises 3.5→7.9%; adaptive ASR falls 8.6→7.5% while utility under attack falls 18.5→12.9%. A lower ASR alone therefore need not be better protection. This is direct task-context prior art, but it retrains representation variants and evaluates agent behavior, without the proposed warning/length controls. Sentence-level deletion, domain-dependent tuning, and finite adaptive-attack budgets limit the claims. [Paper](https://arxiv.org/html/2608.05430)

### 7. Task Shield — Jia et al., ACL 2025

**Depth:** §§3–5/8, tables 1–3, appendices B/C and prompt material.

Task Shield extracts actionable instructions, checks contribution to user goals using dialogue history, provides feedback, and can block outgoing tool calls. This is a multi-call runtime enforcement system, not a static text-only detector. On GPT-4o with Important Instructions, it reports 2.07% ASR and 69.79% utility under attack; the headline is not unconditional performance across every attack.

The Slack/GPT-4o-mini ablation already tests goal restatement. Table 3 gives full-shield utility 50.48% versus 43.80% without restatement, and ASR .95% versus 3.80%. The adjacent prose's 63.8→43.8 comparison uses Input Shield's utility as its starting point, so use the table's matched variant comparison. One trial per task, one benchmark, predominantly one model family, and added calls limit generality and cost claims. It supplies related causal motivation but does not isolate a task field against generic-warning or length controls. [Authoritative ACL paper](https://aclanthology.org/2025.acl-long.1435.pdf)

### 8. NTBench — Gong et al., arXiv:2610.32531

**Depth:** construction/validation §IV, evaluation §V, discussion, judge/generation appendices.

Near-target attacks preserve much of a legitimate answer/action while introducing a specific incorrect or harmful deviation. The evaluation fixes three attack executions per sample, shares tasks/positions across tracks, and excludes deviations already present without injection. It reports larger ASR than fixed-target baselines across seven models on ten language datasets and two agent benchmarks. The operative agent denominator is **reached injection positions**, not all attempted user tasks; matching a tool invocation does not prove its downstream effects occurred.

Human audits cover 600 retained targets and 300 language-task executions. Target validity ranges 86.7–98.0%; judge F1 ranges 83.6–89.9%, so automated labels remain imperfect. It is not a detector task-input ablation. Its relevance is a limitation on the task-alignment intuition: an attack can resemble a useful task step. The present static study cannot infer robustness to such targets or adaptive attacks. No NTBench corpus was acquired. [Paper](https://arxiv.org/html/2610.32531)

### Adjacent prior work already spot-checked: AlignSentinel

**Depth: spot-check only**, §§3–6 and relevant appendix references, not a full ninth review. It explicitly conditions detection on higher-priority task instructions, using LLM attention interactions and a three-class aligned/misaligned/non-instruction formulation. Its benchmark is synthesized across eight domains; it requires internal attention features and trains classifiers. This directly rules out a broad claim that task-aware detection is new, while leaving the proposed fixed-model warning/length-controlled estimand distinct. Do not conflate it with Qualifire Sentinel. [arXiv:2602.13597v2](https://arxiv.org/html/2602.13597v2)

## Release audit and candidate decisions

Metadata was checked anonymously on 2026-11-01. An available card/API listing means the artifact exists; it does not mean authenticated access, execution compatibility, or model behavior has been verified. No gate was accepted and no account/API inference was used.

| Artifact | Verified release facts / constraint | Recommendation |
|---|---|---|
| [ProtectAI v2](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2) | Apache-2.0; English DeBERTa; card demonstrates 512-token truncation, warns of system-prompt false positives, and says project is archived. Its training mixes public collections and community-derived attacks; a complete row manifest is unavailable. Existing protocol pins `90c9989b1a342275dd0d1a95aad283c04e075671` and full-page sliding windows. | **Keep** as the established legacy reference. Report window count, overlap/max aggregation, and length-stratified FPR; max aggregation can increase document FPR with length. Do not generalize its result to all dedicated detectors. |
| [Sentinel v1](https://huggingface.co/qualifire/prompt-injection-sentinel) | API SHA `e24131782819a4787c129ed2b9a4a67ae57a584e`; automatic gate, license `other`, ModernBERT classifier. Card lists no HF inference provider. The paper's 8,192-token capacity is not evidence that local execution has worked. | **Defer addition**. Low API spend is possible locally, but gate/license/runtime setup and unknown overlap cost time. Author F1 superiority is insufficient to replace the current baseline. |
| [Sentinel v2](https://huggingface.co/rogue-security/prompt-injection-jailbreak-sentinel-v2) | Correct full repository name; API SHA `05ff9bfd1f28c5228e53121d5ee4427bb5205212`. Gated, license `other`; card says Elastic license, Qwen3-0.6B/596M, 32K context, threefold training data, no HF inference provider. Card improvement prose and table give differing average-F1 values. | **Defer**; distinguish from paper/v1. Do not infer access from public metadata or import v1's provenance into v2. No paid API route was verified. |
| [Horizon-Labs base card](https://huggingface.co/Horizon-Labs/prompt-injection-guard-base/blob/8c321b08c01102a0a3a377f8eecda0cab80e8758/README.md) | API SHA `8c321b08c01102a0a3a377f8eecda0cab80e8758`, ungated Apache-2.0; 308M mmBERT/ModernBERT classifier, v2.2. Config and tokenizer declare 8,192 tokens; training card says max 1,024. Card includes 2,048-token windowing and normalization guidance. **Explicit training source: `hendzh/PromptShield`.** Published independent results used 2,048-token truncation and do not pin this revision. | **Add to a future shortlist**, not the ongoing panel. Best practical alternative identified here for a later local comparison. Known source-level PromptShield exposure means external independence cannot be asserted; exact split/row exposure needs audit. Card-reported synthetic successes are not independent replication. |
| [PIGuard release](https://huggingface.co/leolee99/PIGuard) | API SHA `dd78b24e330193a22d2293ac66922dd4f982f563`; ungated MIT; config confirms 512 positions and benign/injection labels. Custom code is required; card explains InjecGuard was renamed PIGuard and lists no HF provider. [Official code](https://github.com/leolee99/PIGuard) includes training/validation provenance; validation uses samples from named evaluation families. | **Defer** unless reproducible training is the priority. It is not an independent second model merely because it is also called InjecGuard. Short context and known benchmark-family exposure reduce the value of another quick headline comparison. |
| [Prompt Guard 2 86M](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M) | API SHA `a8ded8e697ce7c355e395a0df51f94adb4a2fd27`; manual gate, Llama 4 license. Card specifies 512 tokens and segmenting long inputs; its objective focuses on explicit override/jailbreak patterns. | **Defer**, a reasonable later lightweight comparator. Small size does not remove objective mismatch, window aggregation, access, or task-unaware-input limitations. |
| [CAD checkpoints](https://huggingface.co/tavialiu/CAD-models) | API SHA `550e8cf87ebf33adf6ef83e56b24629d876e0512`, ungated MIT heads; base `classifier_fullcad.pt` and AT variants are listed. They require a separate frozen encoder and sentence processing. [Jina v3 card](https://huggingface.co/jinaai/jina-embeddings-v3) declares 8,192 tokens and CC BY-NC 4.0; the head's MIT license does not cover the encoder. | **Defer integration**. Scientifically close, but whole-page aggregation, sentence segmentation, encoding cost, and changed outcome need a separately frozen comparison. No need to regenerate training data. |
| [Official PromptShield repository](https://github.com/wagner-group/PromptShield) | Public training/evaluation code and source datasets; no `.pt`, `.bin`, `.ckpt`, or `.safetensors` artifact appeared in the inspected repository tree. No author-linked ready-to-run evaluated detector checkpoint/API was located. Unaffiliated HF models bearing the name are not certified reproductions. | **Keep dataset, defer detector**. Training or validating a replica would add cost and a new method, and testing it on its own benchmark is not unexposed external validation. |

The [NotInject card/API](https://huggingface.co/datasets/leolee99/NotInject) declares MIT and three splits of 113, with `prompt`, `word_list`, and `category` fields; those are release-metadata counts, not a recount. The [PromptShield card](https://huggingface.co/datasets/hendzh/PromptShield) declares Apache-2.0 and a prompt/label schema. The existing protocol's 23,516 test records and duplicate counts come from its separate file audit. [BrowseSafe++ metadata](https://huggingface.co/api/datasets/perplexity-ai/browsesafe-plus-plus) confirms revision `3e9f4b3cef9295a1928ddfb33675eafd8bb68259` and a split-specific license: train CC BY 4.0, test evaluation-only; the umbrella card says `other`. No unpublished test labels were requested.

## Consequences for the existing study

1. **Keep the estimand narrow.** It is source-label agreement under a task-information intervention on a selected, rewritten English web population. Authenticity means publisher-provided task information, not untouched production requests. Better agreement does not establish attack prevention or increased task completion.
2. **Preserve the four fixed conditions.** Existing task-aware systems motivate the question, while the generic-reminder and length controls distinguish useful task information from extra caution or additional text. Do not infer the answer from prior utility/ASR studies. A neutral filler is character-matched, so report token differences and common-context coverage.
3. **Treat calibration as a separate question.** Balanced error at frozen rules is coherent for the primary paired comparison. Report FPR and FNR alongside it. ROC operating points chosen using confirmation labels are descriptive diagnostics, not calibrated deployment performance; do not select confirmation thresholds. Tiny development sets cannot validate 0.1% FPR precisely.
4. **Make input coverage visible.** Freeze and report native model context limits, complete-page handling, unsupported lengths, and any windowing. Window max scores and whole-page scores answer different operational questions; short-paper truncation results do not certify full-document performance. Keep complete-pair and missingness bounds from the protocol.
5. **Keep exposure claims source-specific.** No audited row overlap is not the same as no source/generator overlap. Sentinel's private data leaves uncertainty; PIGuard has known BIPIA ancestry; Horizon explicitly uses PromptShield; BrowseSafe-Guard trained on the proposed main-source split. Preserve source revisions and model revisions separately.
6. **Separate uncertainty types.** Label audit errors, model output instability, group dependence, and out-of-distribution behavior are different. Neither model consensus nor an unblinded audit by a compared model provides independent human ground truth. Continue the existing whole-component sampling and group-level analysis.
7. **Keep runtime and cost conclusions local.** Vendor APIs, local CPU/GPU classifiers, cropped inputs, and quantization are not hardware-controlled speed comparisons. Published per-inference latencies are not forecasts for all windows of complete pages. No new training, corpus, or detector is needed to execute the current study.

## Remaining limitations of this review

No published result was reproduced. Public metadata was inspected without testing gated access or importing remote custom code. Training overlap with the selected project records has not been computed. An official checkpoint not located in this bounded search may exist elsewhere. The eight-paper set is deliberately targeted; the adjacent AlignSentinel entry is only a spot-check. No claim of comprehensive literature coverage is warranted.

Appraisal procedure used the scientific-critical-thinking skill (v1.5): extract methods/results before evaluating validity and keep observed facts separate from inference. Procedural attribution: Kassis, T., Agarwal, V., He, Y., Patel, D., and Brueckner, A. M. (2026), [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065), current record checked 2026-11-01 (v2). This is workflow attribution, not empirical evidence for detector performance.
