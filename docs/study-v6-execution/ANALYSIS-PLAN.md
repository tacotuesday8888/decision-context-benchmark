# V6 frozen analysis implementation

This records implementation choices before inference; DESIGN.md remains the
scientific specification. No results or fitted parameters enter these choices.

Analyze source populations separately. Main endpoint is control-minus-task error:
average row errors within each final group and gold class, average group means
within each class, then weight the two class errors equally. Positive favors task.
Use condition-complete common rows for each contrast. Preserve explicit sourcepair
attrition; additionally show complete-sourcepair-only sensitivity requiring both
members valid under both conditions. This does not replace the declared primary
endpoint. Worst/best bounds retain every planned row and group/class denominator.

Main family is exactly Jev and Luna Decisions times task versus format/reminder/
length (six two-sided tests). Use whole-group signs with shared sign across the
two classes; exact enumeration for at most 20 nonzero contributions, otherwise
100,000 draws with +1 correction. Holm uses all six slots; absent tests remain
unavailable and conservatively occupy a p=1 slot for adjustment. Use 20,000 paired
whole-group percentile bootstrap resamples, recomputing class denominators per
resample. Seed 20261031. Show pointwise 95% and Bonferroni 99.1667% intervals;
report any degenerate resamples. These assume source-conditional exchangeability,
not population-random webpages or independently sampled rows.

Report planned/valid rows, final group/class support, FPR/FNR, raw accuracy,
both-correct sourcepair fraction, paired error transitions and source-label
agreement. The admitted semantic label is source/agent agreement, not human gold;
source-label agreement cannot independently validate labels after agreement-based
selection. No pooled headline accuracy and no low-deployment-FPR claim.

Sources with fewer than 20 groups are descriptive, including per-group effects.
Locked reviewer `task_relation` and `instruction_type` define subgroups; require
at least ten groups in each compared gold class for numerical subgroup contrasts.
No post-output subgroup discovery. Pairwise route comparisons use identical
planned/common-supported rows, intact sourcepairs and both-route valid coverage;
also report the common intersection across all four contextual comparators.
These are descriptive comparisons, not a new confirmatory significance family.

Native scores retain threshold 0.5, exact ties abstain. AUROC (with half-credit
ties), Brier and fixed ten-bin reliability plots use valid native scores, including
exact score ties for forecast diagnostics. Do not fit calibration or invent chat
confidence. Chat outputs remain Boolean. Native confidence, where supplied, is
separate from decision probability and never substituted for it. Failures,
refusals, truncation, unsupported capacity and ties retain distinct dispositions.

Every first attempt is primary. A separately justified first-valid recovery view
is sensitivity only, with linked attempts and costs preserved. No recovered wrong
answer replaces an earlier valid prediction. Selection reads only frozen grouping,
review/exposure/coverage and cost state, never outcomes or significance.

Full analysis and per-group detail remain ignored raw artifacts. Tracked tables
use strict aggregate allowlists. Empirical figure generation requires a receipt
pinning the canonical analysis hash and verified label provenance, freeze,
terminal execution, accounting and independent recomputation. No fabricated points
for unrun/null cells. The final paper follows those checks; an unresolved essential
gate instead yields a precise resumable readiness record.
