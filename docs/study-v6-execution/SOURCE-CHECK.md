# Primary-source check for the v6 paper

Checked **2026-10-31, America/New_York**. This is a reading/provenance check,
not reproduction of an upstream experiment or verification of our results. Only
papers, public documentation, pinned release cards and licences were retrieved.
No restricted test pages/labels, new corpus examples, upstream execution or model
calls were used. Final project counts must come from the locked v3 admission and
execution receipts, not the upstream sizes below.

## BrowseSafe++: construction and task provenance

Inspected [paper v1](https://arxiv.org/html/2610.17457v1), §§2.1–2.2, 3.1,
4 and C.2, plus E.3. The paper describes 38,675 page pairs. Production-origin
injections are preserved while surrounding pages undergo identifier masking,
fictional substitution and prose rewriting. Pair construction and rendered-view
checks are additional selection stages. Approximately 10% of pages receive human
inspection during rewriting; this does not mean every released label was human
validated. Section 3.1 explicitly trains BrowseSafe-Guard on these training pairs.
Section C.2 separates its page-only detection evaluation from task execution.

Paper wording: **privacy-rewritten benchmark pages with source-provided tasks**.
Calling them untouched production captures would be inaccurate. The inspected
construction account does not establish that `benign_task` is the original
production request verbatim. That is an unresolved provenance question, not proof
that every task was invented. Detection differences here cannot establish agent
resistance or transfer to production prevalence.

## BrowseSafe++: released partitions and rights

Inspected the [dataset card](https://huggingface.co/datasets/perplexity-ai/browsesafe-plus-plus/blob/3e9f4b3cef9295a1928ddfb33675eafd8bb68259/README.md),
"What's included" and "Field guide"; the [licence](https://huggingface.co/datasets/perplexity-ai/browsesafe-plus-plus/blob/3e9f4b3cef9295a1928ddfb33675eafd8bb68259/LICENSE.md),
opening split assignments and Test Split Evaluation License §§1–2; and the pinned
[SDK README](https://github.com/perplexityai/browsesafe-plus-plus/blob/95f99494b4bdafec41a8a50ddcefbb795fbae68f/README.md),
“Dataset”, “Test split and leaderboard”, “License”, and
[data documentation](https://github.com/perplexityai/browsesafe-plus-plus/blob/95f99494b4bdafec41a8a50ddcefbb795fbae68f/docs/data.md),
"Layout", "Pairs and splits", and "Fields / Task and outcome".

The labelled release contains 29,500 training pairs / 59,000 pages. Public test
inputs contain **9,175 label-free pages**, one member of each test pair; 18,350
describes the underlying paired test population, not released labelled pages.
`benign_task` is defined as the legitimate request associated with a page; that
definition supplies no stronger original-request provenance. Expected outcomes
and injection references are separate fields, not detector evidence.

Training data are CC BY 4.0; SDK code is separately MIT. Test inputs have a separate
evaluation-only licence, including prohibitions on tuning, redistribution and
label/pair recovery. V6's held-out cohort comes from the **training release** and
must not be called the official test or a leaderboard evaluation. These facts
also preclude presenting BrowseSafe-Guard as unexposed to this cohort.

## NVIDIA: synthetic, success-selected source and local controls

Inspected the [pinned NVIDIA card](https://huggingface.co/datasets/nvidia/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1/blob/d738d4f361cc38bb4d7a42b9066776dade5332f5/README.md),
“Dataset Description”, “License/Terms of Use”, “Dataset Composition and Generation”
(“Problem Sources”, “Curation and Filtering”, “Dataset Fields”), “Data Collection
Method”, “Labeling Method” and “Dataset Quantification”.

The card states 1,272 records across nine simulated enterprise domains, CC BY 4.0.
Tasks, environments, attacker goals and injections are generated, with no seed
data. An attacker iterates against a Nemotron Nano 3 defender; susceptibility
resampling and retention of successful attacks shape the population. Thus this is
a **fully synthetic, success-selected transfer diagnostic**, not a sample of
observed enterprise incidents. Trace verification concerns specific tool calls
and arguments, not a universal semantic injection label.

Project derivation, separately checked in `scripts/study_v6/prepare.py::nvidia_pair`:
the candidate is one environment string containing a unique exact injection;
the control deletes that occurrence once, without whitespace repair. These are
**local deletion counterfactuals**, not upstream benign rollouts or complete tool
observations. Static predictions do not reproduce the upstream defender's success.

## INFUSE: trajectories and our static reconstruction are different units

Inspected [paper v1](https://arxiv.org/html/2610.20776v1), §3,
Appendices A.2.2–A.4.2 and B. It describes 40 tasks, 56 attack scenarios and 41,824
adversarial trajectories. The evaluation initializes containers, inserts compatible
payloads, runs an agent, records actions/observations, and evaluates traces and
post-execution artifacts. Static file content is only one supported surface;
targeting categories, runtime observations and placement strategies are distinct.

Appendix A.4.2 reports 219 human-reviewed trajectories and 624 labels: 119 sampled
proportionally and 100 enriched for judge disagreement, with judge outputs hidden.
Population error estimates require the recorded sampling weights. Neither that
human study nor its trajectory count describes our agent review.

Our preserved project adapter copies eligible repository files and applies the
pinned default prefix/template/position to construct static pairs. It does not
run setup, containers or agents. Paper wording: **static file reconstructions from
INFUSE**, with actual retained pair/template/group counts reported separately.
Do not describe their classifications as INFUSE attack-success rates or count
repeated trajectories as independent tasks.

## Statistical precedent and remaining uncertainty

Inspected [System One security evaluation v1](https://arxiv.org/html/2609.33401v1),
§§3.2–3.4, 4.1 and 5.1–5.3. It separates fitting/selection/confirmation/test roles,
keeps duplicate/related units together, preserves full inputs with unsupported
overlength cases, and distinguishes decisions from probability analyses. Section
3.4 uses whole-group paired bootstrap resampling (2,000 resamples), cluster sign
randomization with an exchangeability assumption, and Holm adjustment. Section
4.1 restricts comparisons to shared supported populations and leaves empty
denominators undefined.

This supports grouped, paired uncertainty calculations rather than treating rows,
variants or requests as independent replication. Our six-test family, 20,000
bootstrap resamples and missingness bounds are v6's own frozen choices. Neither
this precedent nor lexical closure proves our groups independent, our labels human
gold, or achieved power. Closed-model exposure and unknown genealogy remain
limitations; no novelty-priority claim was established by this check.
