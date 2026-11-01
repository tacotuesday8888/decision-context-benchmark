# V7 statistical preparation

This document describes code and synthetic checks. It contains no model results.
The frozen v6 analysis is unchanged. The implementation is
`scripts/study_v7/analysis.py`; fixtures are in
`tests/study_v7/test_analysis.py`; simulation inputs, seeds, software versions and
Monte Carlo uncertainty are saved in `results/study-v7/statistical-simulation.json`.

Each group has one clean/attacked pair. For each native model and control, the
group difference is `(control_clean_error + control_attack_error - task_clean_error
- task_attack_error) / 2`. Positive values favor authentic task information. The
primary estimate gives every group the same weight and includes only groups with
valid first outputs in both native models under all four conditions, on both
pages. Six two-sided one-sample t tests compare group differences with zero;
Holm correction keeps all six tests in the family even when a test is unavailable.
Contrast-specific complete groups are a separate sensitivity analysis.

The two reported percentile intervals use 20,000 whole-group bootstrap draws:
95% pointwise and 99.166667% for each of six comparisons. The latter uses
Bonferroni's marginal confidence level; its family coverage still depends on
the quality of the individual approximate bootstrap intervals. It is not an
exact simultaneous procedure. Each draw resamples complete group differences.
Multinomial counts over identical observed values compress that empirical
resampling distribution without approximation. Seeds, draws and omitted draws
are retained. Empty cohorts omit all draws; constant cohorts have degenerate
intervals. A constant zero difference gets p=1; a constant nonzero difference
uses the limiting t-test p=0 and is explicitly flagged. Fewer than two groups
cannot supply a t-test p value.

Missing outputs, exact native probability ties, unsupported inputs and failures
are not correct answers. The full planned-cohort bounds retain each known
individual error and let each missing error range independently from zero to
one before averaging the signed group contrasts. These bound the finite planned
cohort's effect, not an unobserved population parameter. Shared complete cases
can still be selected by outcome-related failures; the bounds and coverage
breakdown are mandatory.

The evidence adapter reads only v7 main confirmation first attempts, checks their
frozen request and payload identities, verifies retained raw hashes, and preserves
interrupted attempts. Repeats, development, audits and external outputs are
filtered before any evidence file is opened. A repeat cannot replace a primary
failure. Native ties remain available for AUROC, Brier and fixed-bin reliability;
Boolean outputs do not receive invented confidence scores.
Source-specific FPR, FNR, balanced error and Brier also receive 95% whole-group
percentile intervals. Their class/score denominators are recomputed in every
draw, and draws without a necessary class or score are counted as omitted.
AUROC and reliability bins remain point diagnostics without intervals; they
must not receive an inferential interpretation.

The hand fixture `D=[1,1,0,0]` has mean 1/2, sample SD `sqrt(1/3)`, t=`sqrt(3)`,
three degrees of freedom, and two-sided p=`1/2 - 1/pi` (about 0.1816901).
The Holm fixture `.001,.01,.02,.04,.2,missing` gives adjusted values
`.006,.05,.08,.12,.4,missing`; only the first two reject at 0.05. Exhaustive
binary filling verifies known-error bounds, and exhaustive small-group index
resampling verifies the multinomial bootstrap identity.

The synthetic harness generates coherent binary page errors: controls share
each model's task errors, and clean/attack members remain together. Symmetric
differences lie in `{-1,0,1}` with SD close to 0.5, 0.7071 or 1.0. Skewed
differences lie in `{-0.5,0,1}`. Assumed alternatives are three or five percentage
points. It checks n=500 and n=3,000 nulls, the n=3,000 effect/variance sensitivities,
independent cell missingness and deliberately informative missingness. It invokes
the production t/Holm and bootstrap functions, rather than a normal power
approximation. Familywise rejection, contrast power, interval coverage and
finite-cohort bound coverage have separate denominators and Wilson 95% Monte
Carlo intervals. These checks do not prove validity for every data distribution
or establish independence of the acquired source groups.

The saved run used 1,000 test repetitions **and 1,000 interval repetitions per
scenario**, each interval with all 20,000 draws. Its calculation took 203.31
seconds. The separate procedure fixtures passed 11 tests. Run the synthetic
check with `python scripts/study_v7/simulate.py`; it needs NumPy and SciPy, makes
no network requests and does not load model weights.

| Synthetic scenario | Holm familywise null rejection | Simultaneous coverage of the six nominal 99.166667% intervals |
|---|---:|---:|
| Symmetric null, 500 groups | 4.3% | 96.2% |
| Skewed null, 500 groups | 2.7% | 97.6% |
| Symmetric null, 3,000 groups | 4.2% | 95.8% |
| Skewed null, 3,000 groups | 1.5% | 98.2% |
| Skewed null, independent cell missingness | 1.2% | 98.7% |
| Skewed null, deliberately informative missingness | 100% | 0% |

For 3,000 groups without missing outputs, the three-point alternative's adjusted
per-contrast power ranged from 84.9–87.4% at SD near 0.5, 45.5–48.6% near
0.7071, and 15.5–16.8% near 1.0. At five points those ranges were 99.9–100%,
95.6–96.7%, and 60.4–61.2%. These are the assumed correlated synthetic
families' rejection rates, not guarantees or achieved power. The exact Holm
procedure can differ materially from a per-contrast Bonferroni planning formula.

Across the complete/independently-missing scenarios, pointwise 95% coverage
ranged from 94.2% to 96.7%; the six-interval family coverage ranged from 93.7%
to 98.8%. The lowest family result was 937/1,000, Wilson Monte Carlo 95% interval
92.02–95.05%, so finite simulation does not certify a hard 95% coverage guarantee.
Do not call these bootstrap intervals exact. The intentionally informative
missingness shifted complete-case estimates by about nine percentage points
and destroyed nominal coverage. Known-error full-cohort bounds contained the
realized planned-cohort mean in every synthetic repetition under every mechanism.
That deterministic finite-cohort protection is separate from population-level
sampling uncertainty.


## Descriptive comparators and repeated calls

`analyze_run.py` preserves every planned confirmation first cell. Contextual model
pairs are compared within each condition on the locked500main groups. External
pairs use the locked1,000request subset. Each comparison reports its own complete
cohort hash, planned/observed class counts and95% whole-group interval. The external
matched metric is a request-mean error difference; it is not called balanced error
when missing outputs change the class balance. No extra pvalues are introduced.

`repeat_analysis.py` separately matches native100groups and general50groups to
fresh repeat-1 calls with identical payload hashes, distinct keys/namespaces,
verified raw/started records and the same configuration revision. It reports
valid-first/valid-repeat/both-valid class denominators, ties, other missingness,
flip directions and available provider IDs/timestamps. Duplicate recorded IDs
are diagnostic; missing IDs/timestamps are not invented. Repeats never replace
first outputs. No classification accuracy is used to select or retry a repeat.

The paired-page disagreement rate uses whole planned-group resampling and
recomputes the observed paired-page denominator in each of20,000draws. This avoids
silently replacing the page rate by an unweighted average of incomplete-group
rates. A separate complete-two-page-group mean is a sensitivity description.
Native absolute score changes include valid tie scores and use their own explicit
score-pair denominator; Boolean models have no score-change calculation. Intervals
are descriptive and conditional on observed paired outputs, with omitted
zero-denominator draws reported. There are no additional pvalues.
