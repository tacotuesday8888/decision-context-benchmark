# Reproduce controls v4

The original pilot and all earlier experiments are immutable. These commands operate
only on controls-v4. Do not rerun old freeze or inference commands to reproduce an
analysis. Runtime and numerical dependencies reuse the existing project environments;
model weights and credentials are not needed for offline completed-route analysis.

## Source preparation

`python3 scripts/controls_v4/reproduce_preparation.py` creates an isolated ignored
directory, copies the pinned original SQuAD/AdvBench downloads, clones the local
pinned TaskTracker/AIB source repositories without network access and reruns six
adapters/checks. It requires 13 outputs, including full ignored prepared text, to match
byte-for-byte. Source component licenses and immutable download receipts are in
THIRD-PARTY-NOTICES.md and results/controls-v4/download-receipts-v1.json.

The first audit inventories and draft selection files retain their historical
"pending" status strings. Actual selection is established by the collection manifest,
independent validation/exposure receipts, protocol and split freezes. Do not interpret
an early audit's zero approved examples or zero model requests as current execution
status. No independent semantic annotations have subsequently been created.

## Completed-route numerical analysis

Use `.venv/bin/python` (numpy 2.4.4 and matplotlib 3.10.8 already installed):

```sh
.venv/bin/python scripts/controls_v4/analyze.py --config jev_firstparty
python3 scripts/controls_v4/verify_analysis.py --config jev_firstparty
.venv/bin/python scripts/controls_v4/verify_bootstrap.py --config jev_firstparty
python3 scripts/controls_v4/audit_records.py --config jev_firstparty
.venv/bin/python scripts/controls_v4/tables.py
.venv/bin/python scripts/controls_v4/figures.py
.venv/bin/python -m unittest discover -s tests/controls_v4 -v
```

Replace the configuration only with a completed route. Analysis refuses missing or
pending cells. Failed terminal cells remain in denominators and unknown usage retains
the full reservation. Completed-route ledger snapshots are not full-project balances.
The raw verifier reconstructs every request from hash-bound source/task text, reparses
responses, checks model/version metadata, local token/window accounting and costs.
The independent arithmetic checker does not import the analyzer. The bootstrap checker
uses explicit sampled group multiplicities instead of vectorized accumulation.

Tables retain source-specific absolute rates, complete/planned denominators, contrasts,
observed token counts per condition and output transitions. Route times include
concurrent local/resource and provider effects; they are not intrinsic model speeds.
Figure intervals are pointwise and conditional on the published source/family. Missing
native probabilities on Boolean chat routes are not imputed.

## Final closure and isolated numerical reproduction

Only after every planned attempt is terminal:

```sh
python3 scripts/controls_v4/closure.py --require-terminal
# Inspect/scan and stage the intended completed records, analyses and scripts first.
.venv/bin/python scripts/controls_v4/reproduce_offline.py
```

Without `--require-terminal`, closure writes an ignored live snapshot and cannot be
cited as completed execution. The final isolated check exports the Git index, verifies
5,793 historical protected file hashes, rebuilds all seven route analyses, independent
checks, figures, tables and terminal accounting, and requires identical outputs. It
exports no credentials, weights or ignored source downloads and makes no inference
calls. The saved receipt identifies the exact staged tree and artifact hashes. This
checks an installed numerical environment, not a fresh dependency installation.

Inference is separately frozen and resumable. The v4.0.1 development amendment records
an external Ollama update and one retained Decisions 503; subsequent failed confirmation
cells are never replaced. The Laya startup correction renamed only an analysis helper
that shadowed the Python standard library, before any Laya confirmation reservation.
