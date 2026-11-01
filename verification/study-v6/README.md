# Independent v6 arithmetic verification

Prepared before any confirmation predictions, scores, outcomes, or label joins
were accessed by this agent. Everything in this directory is ignored. The core
imports NumPy and the Python standard library, with no project analytical code.
No provider calls or package installation are involved.

`TOOLS-FINAL-FROZEN.json` binds the core, synthetic fixture programs/results,
initial freeze, and this guide. Preserve all of these files unchanged. The
initial `TOOLS-FROZEN.json` is also enforced by the empirical CLI.

The fixtures cover hand-calculable group/class weights, class-missing and all-zero
effects, planned missingness bounds, exact sign probabilities, six-position Holm,
source-pair attrition/transitions, route intersection, subgroup support gates,
Brier/rank AUROC/reliability ties, a complete two-route synthetic analysis, and
nonconstant Monte Carlo/bootstrap oracles. The RNG oracles preserve the exact
frozen draw recipe while checking statistics by a separate count/scalar method.

Only after the root executor has verified terminal execution and authorized
empirical access, supply a new ignored authorization JSON object:

```json
{
  "root_authorized_terminal_analysis": true,
  "terminal_execution_verified": true,
  "planned_sha256": "SHA256 of every planned confirmation cell including unsupported/unrun",
  "records_sha256": "SHA256 of terminal normalized primary records plus literal baselines",
  "analysis_sha256": "SHA256 of the frozen analyze output file"
}
```

Record the final tool-manifest SHA in the root provenance receipt as well. Then,
from the repository root, run with the existing environment:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B \
  data/raw/study-v6/execution-v1/independent-analysis-tools/independent_math.py compare \
  --planned PATH_TO_PLANNED_JSONL \
  --records PATH_TO_RECORDS_JSONL \
  --analysis PATH_TO_ANALYSIS_JSON \
  --authorization PATH_TO_AUTHORIZATION_JSON \
  --output PATH_TO_NEW_IGNORED_COMPARISON_RECEIPT_JSON
```

The CLI refuses changed code/initial fixture hashes, missing authorization, input
hash changes, or overwriting conflicting evidence. It independently reconstructs
the numerical/categorical analysis projection and reports every mismatch. The
comparison uses absolute/relative tolerance `1e-10`, with nulls, dispositions,
identifiers and booleans exact. It also records both file hashes and the canonical
JSON-object analysis digest required by the reporting adapters.

The projection covers all conditions/contrasts, primary and explicit-source-pair
sensitivity inference, native forecast diagnostics, six fixed primary Holm slots,
reviewer subgroup gates, pairwise route comparisons and all-route intersections.
Explanatory prose fields are not compared. Root must separately verify that these
normalized inputs retain all frozen cells, source/group/pair/label invariants and
raw first-attempt provenance. This arithmetic checker does not validate human
gold, sampling assumptions, scientific code integrity, or invoice charges.

Do not interpret an arithmetic pass as full study readiness. Root must supply the
separate terminal-execution, accounting, label-provenance and freeze gates before
empirical figure or paper authoring.
