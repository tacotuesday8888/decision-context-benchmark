# Paper outline — planned study, no results yet

Working title: **Does authentic task context help prompt-injection detectors?**
Target: approximately five pages, plus reproducibility details. This document is a
writing scaffold. Empty result sections must stay empty until a bounded run is
authorized, completed and independently verified. No empirical PDF exists for v7.

1. **Question and contribution (half a page).** Test whether a publisher-provided
   task changes static attack detection beyond an empty task field, a generic
   reminder, and neutral character-length-matched filler. Explain why this is a
   detector study and does not establish browsing-agent safety. Related evidence:
   [To Jev or Not?](https://arxiv.org/html/2610.03324v1),
   [Type-Safe Is Not Error-Free](https://arxiv.org/html/2609.26758v1), and
   [Decision Hijacking](https://arxiv.org/html/2609.28613v1).
2. **Data and controls (one page).** Describe the pinned
   [BrowseSafe++ labeled training release](https://huggingface.co/datasets/perplexity-ai/browsesafe-plus-plus/tree/3e9f4b3cef9295a1928ddfb33675eafd8bb68259),
   privacy-rewritten tasks/pages, project-held-out rather than publisher-test status,
   historical exclusions, lexical components, one intact pair per group, and exact
   frozen selection. Cite the [source paper](https://arxiv.org/html/2610.17457v1).
   Describe [PromptShield](https://arxiv.org/html/2501.15145v2) as a distinct complete
   request endpoint, with no invented task. Include counts/exclusion-flow table
   regenerated from preparation receipts. Source labels are the main reference;
   the fixed 100-pair Sol audit is unblinded and diagnostic, not human ground truth.
3. **Systems and analysis (one page).** List all five configurations, fixed routes,
   reasoning/output caps, native score orientation, uncalibrated ProtectAI sliding
   windows, first attempts, repeat namespaces, coverage and failure definitions.
   Report equal-group balanced-error contrasts, the shared complete native cohort,
   two-sided paired group-mean t tests/Holm6, whole-group intervals and planned-group
   missing-outcome bounds. The general-model subset and external source remain
   descriptive. Cite [Lakens, Sample Size Justification](https://doi.org/10.1525/collabra.33267)
   for transparent prospective sensitivity; synthetic validation is not achieved power.
4. **Results (one to one-and-a-half pages, pending).** Primary effect plot with
   pointwise and simultaneous-conservative interval labels; FPR/FNR and coverage
   table; source-specific general/specialist comparison; repeat disagreement;
   audit concerns separately; actual cost and source-specific runtime. Every value
   must be regenerated from saved first attempts by a separate calculation. Do not
   pool the two sources into one headline. Do not select errors by model success.
5. **Limitations and conclusion (one page, pending).** Static classification versus
   downstream consequences; unknown pretraining overlap; privacy rewriting; source
   label ambiguity; lexical grouping cannot guarantee independent semantic families;
   balanced external sampling is not deployment prevalence; AI audit shares a panel
   model; Luna's two APIs need not expose identical physical weights; provider
   availability, context failures and outcome-blind early stopping. Non-significance
   does not establish equivalence. Frame conclusions around systems and cohorts tested.

## Reproducibility appendix

Include protocol and source revisions, hashes, selection/rank function, technical
exclusions separately from semantic concerns, audit provenance, model/API request
settings, first-attempt reconstruction, failures and unknown-charge holds, all
planned denominators, environment versions, simulation assumptions/Monte Carlo
uncertainty, private artifact locations and a source-license statement. Restricted
source text and credentials stay out of Git. Public release/submission needs a new
owner instruction.

## Software and methodological assistance

The installed experimental-design v1.5, statistical-power v1.3, and
scientific-critical-thinking v1.5 skills materially guided preparation and synthetic
checks. Record them as procedural assistance, not validation. Verified bibliographic
record on November 1, 2026 (arXiv v2, no journal reference shown): Timothy Kassis,
Vinayak Agarwal, Yuhuan He, Darshil Patel, and Aubrey M. Brueckner (2026),
[Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://doi.org/10.48550/arXiv.2609.00065).
Also disclose Codex engineering/review assistance and the future Sol pair audit.
