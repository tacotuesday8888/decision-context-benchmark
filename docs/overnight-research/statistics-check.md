# Coordinator inspection of synthetic statistical checks

2026-11-01. Inspected the worker's `scripts/study_v7/simulate.py` and `results/study-v7/statistical-simulation.json` in the Plan checkout. This is a code/output inspection, not an independent rerun or empirical model result.

The generator constructs binary page errors for two models and four conditions, sharing each model's task errors across its three contrasts. Each group contains a benign/attack pair. The loop calls the production paired-t, Holm and bootstrap functions; the reported run uses 1,000 repetitions and 20,000 bootstrap draws per interval.

Under the four tested complete-data null settings (500/3,000 groups, symmetric/skewed), familywise rejection ranged from 1.5% to 4.3%. This is reassuring for these particular synthetic settings, not proof of validity for dependent real-world groups. The familywise interval coverage varied across scenarios; one alternative setting gave 93.7%, so do not describe bootstrap coverage as guaranteed merely because Bonferroni levels are used.

The outcome-dependent missingness stress is deliberately severe: the zero-effect scenario produced 100% familywise rejection and zero simultaneous interval coverage on complete cases. Bounds retaining every planned group contained the realized full-cohort means in every simulated repetition. Those are finite-cohort partial-identification bounds, not population confidence intervals.

Execution implication: preserve all planned request IDs, known page errors and missing/error statuses. Report complete-group estimates together with all-planned bounds. Do not discard failures quietly or call them harmless. Keep prospective power separate from measured model performance, and distinguish any-contrast power from power for each individual contrast.
