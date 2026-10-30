# Local backend and probability audit

The completed extension Laya arm contains 1,771 terminal records. The audit found
no reversed probability or confirmed question-syntax bug. It does not establish
that the model is accurate or calibrated. Weak results remain part of the study.

The pinned checkpoint's `rl_agent_config.json` sets temperatures to `[1, 1, 1]`
and has no option-specific temperature overrides. The installed Laya 0.4.17 SDK
constructs binary options in false/true order, divides logits by the configured
temperature, applies softmax, reverses any explicit option permutation, and returns
`noul = round(p[1], 4)`. The benchmark reads that true probability. It does not read
`confidence`, `answer_confidence` or the action probability. Optional SDK binning
changes `answer_confidence`, not `noul`; the preserved adapter supplies no fitted
calibration file, language override or option permutation. “Publisher defaults” in
run metadata therefore does not imply evidence of calibrated probabilities.

The adapter verifies all checkpoint artifact hashes and SDK version, loads CPU
with the eager backend, sets two Torch threads and calls model.eval(). It explicitly
uses an 8,192-token assembly limit and 256-token question head rather than silently
using the checkpoint's 1,024 default. All 1,771 exact requests were tokenized before
confirmation: maximum 1,702 total /113 head tokens, no dropped state or truncated
head. Every actual response checks usage against that exact assembly. This is
coverage verification, not proof of equal predictive behavior at all lengths.

The SDK's default CPU path uses fp32; CPU bf16 autocast is opt-in through
`LAYA_CPU_AMP`. The historical adapter does not persist that environment option or
per-forward dtype, so we cannot promote the source-code default into a measured
per-forward precision claim. CPU/eager and the artifact identity are enforced.
No backend or checkpoint change was made during this audit. The checkpoint's bf16
training/default CUDA configuration is not itself evidence that CPU used bf16.

The model artifact record also preserves the prior SDK compatibility normalization
of tokenizer `extra_special_tokens`; weights and vocabulary were not changed.
Nimble retains the pinned Ollama digest and Q4_K_M quantization documented in the
request plan. These local routes should not be equated with unquantized hosted
models or intrinsic device-independent latency.

The earlier 42-call development diagnostic tested statement/criterion wording.
Its mixed error/Brier changes did not justify selecting an improved prompt. The
original question was retained before confirmation. No calibration, threshold
fitting, alternate backend or outcome-based repair was selected.

Local source/configuration hashes are in `laya-backend-audit-v1.json`. This is an
implementation audit, not an independent reproduction of vendor quality claims.
