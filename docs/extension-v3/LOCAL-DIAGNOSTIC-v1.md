# Local development diagnostic v1

This is an operational and semantic audit, not confirmation or model selection.
The completed study remains unchanged. No held-out outcomes are used to select
examples or adjust thresholds. The sample is exactly the seven candidates / 14
conditions in the previous Nimble development check, including its longest input.
Reuse the saved original-question responses for both models; do not repeat them.

Before calls, freeze exact requests, source code, this document and the completed
study integrity check. Run 14 Nimble statement cells and 28 Laya cells (statement,
statement with explicit false/true criteria). All inference is local, free and
uses the existing pinned weights/backends. Do not change quantization, head budget,
tokenizer, probability direction, threshold, or input content. Do not fit calibration.
Nimble criteria are omitted because their support has not been established here.

The SDK inspection establishes that Laya's returned noul is P(true): output index
1, semantic option order false then true. The published model card includes a
question-form example, so question syntax is not a confirmed implementation bug.
The short declarative variant tests sensitivity; it is not a proposed fix. Exact
wording and criteria are in the frozen request manifest. All score directions stay
unchanged, including poor predictions and exact-0.5 abstentions.

Retain every attempt's full payload, raw response, usage, local model identity,
elapsed time and token audit. Stop on the first runtime/coverage/schema failure;
never automatically retry a failed or interrupted reservation. Model identities
and input coverage use the preserved adapters' strict checks.

Report paired probability changes, Brier scores and classification transitions
with denominators by source/condition. This tiny, operationally selected sample
cannot establish an accuracy improvement or generalization. Any eventual choice
requires a separately documented development selection rule and fresh confirmation.

Commands from repository root:

```sh
python3 scripts/extension_v3/local_diagnostic.py freeze
.venv/bin/python scripts/extension_v3/local_diagnostic.py nimble
.venv-laya/bin/python scripts/extension_v3/local_diagnostic.py laya
```
