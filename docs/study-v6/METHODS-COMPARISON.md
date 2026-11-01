# What comparable studies actually did

Primary papers and release code checked 2026-10-30. These are method comparisons,
not endorsements of the authors' conclusions or claims of peer-review status.
Their sample sizes answer different questions. Model calls, trajectories, variants,
task families and independent source examples must not be interchanged.

| Study | Data and evaluation unit | Method worth borrowing | Limitation for our question |
|---|---|---|---|
| [To Jev or Not? / HateDecide](https://arxiv.org/html/2610.03324v1), §§3.1–3.4 | Four moderation test sets: 4,120, 3,203, 1,924 and 3,728 texts; six decision configurations and other baselines. | Paired definition-present/absent comparisons; keep normalized duplicates and perturbation relatives together. It removed cross-partition relatives instead of pretending official splits prevented leakage. | Supplying a definition changes the instruction package. Agreement with original labels does not prove adherence to the supplied definition. Moderation examples cannot supply authentic user tasks for our injection experiment. |
| [System One security decisions](https://arxiv.org/html/2609.33401v1), §§3–6 | R-Judge, WAInjectBench and AgentHarm; multiple security constructs, with separate development/selection/confirmation/test roles. | Whole-group bootstrap, paired sign randomization, Holm adjustment, full-input coverage reporting, and separate score calibration from decision accuracy. | Scores from a native decision head and self-reported LLM confidence are different measurements. Unsupported long inputs are excluded, not silently truncated. Its thresholds are not portable to our data. |
| [Decision Hijacking](https://arxiv.org/html/2609.28613v1), §3 and Appendices A, D, E, G | 510 reconstructed direct-harm decisions = 17 contexts × 30 attacker goals; 54,060 main-study calls. | Audit reconstruction; retain exact inputs, versions and outputs; account for crossed goals/contexts; validate optimized attacks with fresh calls. | A probability shift, selecting an attacker option and executing an actual harmful action are different endpoints. Hundreds of repeated calls do not create new task contexts. We do not import adaptive, outcome-selected attacks into confirmation. |
| [JevOut](https://arxiv.org/html/2609.30243v1), §4 and Appendices C–G | 700 held-out source items across seven datasets; Jev optimization qualified 508 initially correct decisions. | Explicitly count proposals, accepted target evaluations and source items separately; constrain context additions with semantic checks; report one-shot and feedback controls. | Its success denominator is initially correct items. Automatic semantic checking is not independent human validation. Its adversarial optimization asks whether context can mislead, whereas ours asks whether genuine task information helps detection. |
| [Type-Safe Is Not Error-Free](https://arxiv.org/html/2609.26758v1), §3 | 1,200 workflow decisions across four predicates, with task-specific rubrics. | Hold state/question/rubric bytes fixed while changing the option-name binding; neutral-name controls and repeated identical calls distinguish intervention effects from instability. | Schema validity does not establish semantic correctness. We keep answer orientation fixed instead of changing names across task conditions or treating name-induced flips as task effects. |
| [Nudge the Judge / JevProbe](https://arxiv.org/html/2610.18612), §§4–5 and Appendix D | Reports 2,273 program-grounded cases across 228 applications after screening popular repositories for reachable surfaces. | Validate that attacker-controlled fields reach the decision input; compare program-consumed decisions under paired contexts; retain application revisions and decision semantics. | Decision flips, potential unsafe consequences in controlled executions and real-world harm are different claims. A selected application/attack collection is not a population prevalence estimate. We inspected the paper, not independently reproduced all repository runs. |
| [REFLEX](https://arxiv.org/html/2609.26532v1) | A frozen 100-task simulation plus external evaluations and a 1,440-decision, 60-family diagnostic set. | Paired workflow comparisons and explicit family accounting; inspect both improvements and regressions. | Routing/cascade benefits do not automatically transfer to static injection classification. Small paired task sets can support a bounded result without establishing universal superiority. |
| [BrowseSafe++](https://arxiv.org/html/2610.17457), §2.2 and §4 | 38,675 constructed page pairs in the paper; 29,500 labeled training pairs in the accessible release. | Matched clean/attack pages, task fields, multiple views, provenance, and separate detection/task-execution evaluation. Upstream validation combines model checks with a roughly 10% human page-review sample. | Privacy rewriting and collection filters shape the distribution. This is not a random sample of all webpages, nor a dataset with every label human-verified. We use one text view and do not infer agent resistance from classification. |
| [INFUSE](https://arxiv.org/html/2610.20776), Appendix A.4 | 40 tasks, 56 attack scenarios, 41,824 trajectories; human validation on 219 trajectories with 624 labels. | Hide judge predictions; distinguish random validation samples from disagreement-enriched samples; retain concrete-artifact and behavioral endpoints alongside task utility. | Its human sample includes 119 proportionally sampled and 100 disagreement-enriched items. Population error estimates require sampling weights. Our agent review cannot be described as reproducing that human study, and our static reconstructions are not its trajectories. |

Additional leads include [Nudge the Judge / JevProbe](https://arxiv.org/html/2610.18612)
for program-context attacks, [Passing the Test You Trained On](https://arxiv.org/html/2610.03448)
for source-disjoint detector evaluation, and
[Context-Aware Detection](https://arxiv.org/html/2608.05430v1) for conditioning on queries.
These establish substantial prior work on context and injection. Our narrower
contribution must be the controlled test of legitimate task information through
native decision interfaces, with presentation controls and honest source boundaries.
Do not claim to be the first task-aware detector or the first evaluation of Jev.
The earlier detailed source/code investigation remains in `../study-v5/RESEARCH.md`.

## What this changes in our study

1. Expand with paired task-bearing pages, rather than more context-free attack strings.
2. Keep source-derived pages, synthetic enterprise environments, direct policy
   conflicts and authored permission contracts as separately reported populations.
3. Lock independent review before seeing source labels or predictions. Track
   ambiguity and attrition. A second fresh agent's audit is useful, but remains AI review.
4. Cluster task, document and attack-template relatives. Report actual reviewed
   groups, not a headline count inflated by controls, variants or model requests.
5. Freeze controls, cohort, routes, costs and analysis before confirmation. Preserve
   failures and coverage. An unsupported page is not a license to remove its injection.
6. Keep detection, native-score reliability and agent prevention distinct. A prevention
   extension would also require legitimate task completion and a separate run budget.

## How much data is enough?

There is no publication-quality row-count threshold. Our acquisition target is
1,000 BrowseSafe++ pairs (2,000 pages), plus 200 NVIDIA static pairs and the existing
476 source/authorization cases: at most **2,876 review rows**, before exclusions.
The relevant confirmation count is the final reviewed component count after
duplicates, exposure, semantic grouping and complete-input coverage—not 2,876.

For an illustrative paired binary comparison with discordance 0.25, a normal
approximation gives about 196 independent units for a 10-percentage-point effect
and 784 for 5 points, at 80% power and unadjusted two-sided alpha .05. Six-comparison
Bonferroni planning raises the 5-point requirement to roughly 1,210 units. These
are scenarios, not achieved power: paired balanced-error group means can have a
different variance, and labels/coverage may reduce the usable cohort.

Consequently, the earlier suggestion of roughly 800 independent families was a
planning scale, not a guarantee of detecting a 5-point effect under all controls.
The saved feasibility analysis must show multiplicity and correlation scenarios.
A precise null estimate can be valuable; adding repeated templates to manufacture
significance cannot. If the budget or reviewed groups imply wider intervals,
state the detectable scale and narrow the claim instead of claiming the study is
fully powered because it has thousands of rows.
