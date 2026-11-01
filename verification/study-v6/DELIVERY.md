# Independent arithmetic verification bundle

The nine sealed files beside this note are byte-identical copies of a checker
prepared with synthetic fixtures while confirmation execution was in progress,
before its author accessed confirmation predictions or prediction/label joins.
The primary analytical methods were already frozen. The original ignored location
is recorded in the sealed README.
This tracked copy makes the independent arithmetic implementation reviewable;
it changes no frozen evaluator, requests, schedules or statistical methods.

Final bundle manifest SHA-256:
`6d1f91bc94f5d6f15a5e83c0769303143da7d99c786b449a93edd12bd1465c62`.
Primary mathematical implementation SHA-256:
`519a7f31c3a89a4a217b032469b38eda90c6f792a4c42eb2288832d490e1c3d8`.

Preserve the sealed sibling files unchanged. The additional DELIVERY.md is a
relocation note outside that seal. From the repository root, synthetic checks are:

```sh
.venv/bin/python -B verification/study-v6/independent_math.py freeze-fixtures
.venv/bin/python -B verification/study-v6/extended_fixtures.py
.venv/bin/python -B verification/study-v6/rng_fixtures.py
```

Empirical comparison requires terminal raw verification, the root's explicit
terminal-analysis authorization and exact input-file hashes described in the
sealed README. Invoke the copied tool as follows; every input and comparison
receipt remains in the ignored execution directory:

```sh
.venv/bin/python -B verification/study-v6/independent_math.py compare \
  --planned data/raw/study-v6/execution-v1/analysis-v1/planned.jsonl \
  --records data/raw/study-v6/execution-v1/analysis-v1/records.jsonl \
  --analysis data/raw/study-v6/execution-v1/analysis-v1/analysis.json \
  --authorization data/raw/study-v6/execution-v1/analysis-v1/terminal-authorization.json \
  --output data/raw/study-v6/execution-v1/analysis-v1/independent-comparison.json
```

An arithmetic pass separately supports numerical reproducibility. Raw-request,
source/label, grouping, freeze, accounting, scientific interpretation and visual
checks remain required. This checker calls no provider or local model and imports
no project analytical functions. It establishes neither human-gold labels nor
provider invoice charges.
