# Exploratory probability analysis implementation v1

Implements the existing RESEARCH-PLAN.md amendment after some evaluation outcomes
were available. It is not preregistered. No inference, prompts, labels, settings,
thresholds, datasets or preserved records change. No fitting is performed.

`forecast_analysis.py` reads saved final attempts and native probabilities only.
Valid ties at 0.5 remain forecasts. Boolean chat labels never become probabilities.
Brier contrasts use only candidates with scores in both conditions and publish all
missing denominators. Log loss clips only inside its logarithm at 1e-6; the number
of original exact-zero/one scores remains visible. Reliability uses five fixed bins.

Bootstrap draws use the complete source stratum, sorted by candidate ID, independently
of model outcomes. The same cluster weights therefore apply to every native model
and condition. Missing scores are excluded at aggregation rather than resampled as a
new population or imputed. BIPIA document and attack-family clusterings are separate
sensitivity analyses. LLMail draws are stratified by label and grouped by team or
negative fixture/topic. Intervals are omitted if any required class/stratum has fewer
than two observed clusters. Bin intervals are consequently conservative for bins
that omit an entire label stratum. They are pointwise, not simultaneous guarantees.

Run offline with:

```sh
.venv/bin/python scripts/expanded_execution/forecast_analysis.py
.venv/bin/python -m unittest discover -s tests/expanded_execution -v
```

The JSON records raw-evidence hashes and execution completeness. Interim outputs
must not be interpreted as finished comparisons. Rebuild after the runs finish.
