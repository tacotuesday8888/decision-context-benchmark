# Additional offline analysis and reporting implementation

This implements the saved research plan after evaluation began. It does not alter
requests, thresholds, model routes, labels, splits or recorded outcomes. It is not
preregistration or a new predictive configuration.

- `research_summaries.py`: source-specific paired class-error contrasts on common
  valid outputs, separate strict failures including invalids/ties, descriptive
  family/length groups, fixed threshold grid, and route-specific usage/duration.
  The grid is 0 to 1 by 0.1; exact threshold ties abstain. No operating point is chosen.
- `audit_execution.py`: full expected-cell coverage, raw parser checks via the exact
  execution verifier path, independently reported Nimble loaded digest/quantization,
  native input-context coverage, reservation linkage and separate provider caps.
  Historical unknown attempts retain their reservations.
- `verify_analysis.py`: independently recomputes classification counts/rates and
  native Brier/log-loss/bin summaries directly from saved outputs. It refuses a
  final pass while any planned cells are unrun. Bootstrap implementation has focused
  tests; bootstrap intervals remain conditional and do not include label uncertainty.
- `paper_figures.py` and `build_paper.py`: figures and manuscript tables are generated
  from saved numerical artifacts. The manifest records build input/output hashes.
  Initial/interim snapshots are not synchronized while inference is writing records;
  final regeneration and verification occur only after execution has stopped.

The PDF renderer uses ReportLab 4.4.9. The analysis environment and frozen source
preparation remain unchanged. Figure readability and every final PDF page require
visual inspection in addition to the numerical checks.

## Descriptive-grid correction v1.1

Before final reporting, replace NumPy linspace thresholds with integer-step division
by ten. This ensures a released score of exactly 0.3 ties the displayed 0.3 cutoff
rather than comparing against a binary-roundoff value just above it. No main 0.5
classification, Brier result, model request or fitted setting changes. Regenerate
the descriptive threshold table under `research-summaries-v1.1`.

## Reporting completion and qualitative review v1.2

The report now derives its partial/completed wording from actual planned-cell
coverage. This changes no statistic or inference behavior. The paper lists all
completed BIPIA model effects in source order rather than using two illustrative
arms as its only numerical prose. Deterministic qualitative selection takes the
first candidate ID in each disagreement category per model and preserves inherited
gold labels. The independent numerical gate checks these displayed predictions
and probabilities against raw records.
