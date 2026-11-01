# Does trusted context improve decision models?

Plain-language question: show a decision model a document by itself, then show the
same document with the real user's task. Does it make a better judgment, and are
its reported probabilities more trustworthy?

The current case study is prompt-injection detection. It measures whether the model
spots instructions in untrusted content that try to redirect the assistant. It does
not yet measure whether a working assistant actually resists the attack. An agent
protection experiment would require a separately specified extension.

## Questions and comparisons

1. Primary: task minus candidate strict balanced accuracy within each two-class source.
   Balanced accuracy gives attacks and benign examples equal weight. Compare identical
   candidates; failures/invalid classifications count incorrect, with their coverage
   shown separately. Exact 0.5 is an abstention, not silently assigned to a class.
2. Secondary: does task context improve probability forecasts, measured by paired
   Brier-score changes on candidates with scores in both conditions? Negative Brier
   change is better. Show that common subset's N and missing-score counts. Do not
   treat failures as probability 0.5 or silently hide different denominators.
3. Secondary: where do context effects differ by source, attack family and document
   length? Neighboring-source context is secondary and limited to released authentic
   LLMail task2 neighborhoods. Do not invent missing context.
4. Probability reliability: when p(injection) is around 0.9, is the observed attack
   frequency around 90%? This differs from a model's concentration/confidence field
   and from a statistical confidence interval for an estimated effect.

These statements are restricted to this corpus, these tasks, and tested versions.
They do not establish that context always helps every decision domain or prevents
attacks end to end. Null and negative findings remain valid research results.

## Probability analysis amendment

The original v2.0 preparation and primary metrics stay frozen. This probability
analysis was proposed after some Jev/Decisions/Protect AI outcomes existed. Mark it
as an exploratory amendment, not a preregistered confirmatory test. Nimble held-out
outcomes have not been generated at setup freeze.

- Native scores: Jev noul, Luna Decisions predicate, Nimble noul, Laya noul, and
  Protect AI's window-aggregated injection score. Preserve each model's native
  reported precision. The specialist's max-over-windows score needs its own caveat.
- Luna/Astra Responses return Boolean classifications. Do not invent probabilities,
  request verbal confidence, or turn a single Boolean into a probability forecast.
- Brier score: mean (p-y)^2, y=1 for injection. Smaller is better. Scores at exactly
  0.5 remain valid forecasts even though they abstain from binary classification.
- Reliability plot: five fixed equal-width bins [0,.2), [.2,.4), [.4,.6), [.6,.8),
  [.8,1]. Show bin counts, mean predicted p, observed attack fraction, and uncertainty
  appropriate to correlated data. Sparse bins are not strong calibration evidence.
- Log loss is supplementary; predeclare clipping at 1e-6 and report exact 0/1 scores.
  Neither Brier score nor log loss alone proves calibration.
- ROC/precision-recall summaries, if used, require both classes and disclose prevalence.
  The evaluated fixed cutoff remains >0.5. Threshold sweeps describe tradeoffs; they
  must not select an evaluation-optimized threshold for the main result.
- Never calibrate or tune on evaluation outcomes. Recalibration is optional future
  work using only development data and a separately versioned setting; 60 development
  candidates may be too small for stable fitting. The 14 Nimble setup checks are a
  purposive operational sample, not a representative calibration/accuracy estimate.

Use 10,000 paired cluster-bootstrap draws with seed 20261026 for interval estimates.
Resample related examples together: BIPIA document clusters and separate attack-family
sensitivity; LLMail positive teams and negative fixtures/topics. Apply the same draw
weights to every compared model/condition. Report actual cluster counts. With one
negative fixture, do not claim a population FPR interval. No pooled winner or fishing
for significant p-values. More elaborate hierarchical models require enough independent
tasks and an identifiable specification; they are not required for a rigorous paper.

## Data and paper-scale extension

The current 402 held-out / 60 development candidates come from pinned released BIPIA
and LLMail material. Data sources, source-specific licenses, construction and outcome
labels, synthetic fixtures, duplicate/group exclusions, and authentic context eligibility
are documented in docs/expanded-v2. Published synthetic fixtures are not private real
emails. Do not generate new examples, labels or missing tasks with AI.

Before expanding, inspect actual records and code from candidate published sources
(e.g. AgentDojo/InjecAgent and sources identified by the literature review). Check that
released tasks/context, label meaning, licenses, and leakage controls support our question.
Dataset size is not independent sample size. Audit training-data overlap where disclosed;
public-data contamination cannot be eliminated by merely holding out local rows.

Review current primary papers, model cards, code and released evaluations around Jev,
OpenAI Decisions, Nimble, Strands, Liquid d1, Clef, Tev1 and context-aware injection
work. Social posts provide leads, not verified claims. Benchmark versions and datasets
must match before comparing scores. No novelty claim until this audit is complete.
No further model downloads or accounts are required for the present panel; Nimble is
the selected new local candidate. Alternative exploration is not blanket authorization
to expand the panel or spend beyond provider caps.

Paper deliverables: a clear question and related-work table; traceable collection;
exact models/routes/prompts; paired source-specific results and failures; uncertainty;
probability reliability; limitations and reproducibility. Useful figures: experimental
trust-boundary diagram, dataset/group coverage, paired context-effect intervals, probability
reliability plots, false alarms/missed attacks, and explicitly route-specific cost/latency.
Do not compare local CPU/GPU and hosted network latency as intrinsic model speed.

Foundational probability references:
[Guo et al., On Calibration of Modern Neural Networks (ICML 2017)](https://proceedings.mlr.press/v70/guo17a.html).
Model/runtime references: [Ollama native System One API](https://docs.ollama.com/api/systemone),
[official Nimble library](https://ollama.com/library/nimble),
[Laya publisher card](https://huggingface.co/convaiinnovations/laya-multilingual).
This is a concrete analysis plan and source list, not a claim that a comprehensive
current literature review has already been completed.
