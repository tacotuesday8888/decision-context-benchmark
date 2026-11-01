# Exact expanded model panel

Verified against primary documentation on October 26, 2026. This is **five evaluation
configurations over four distinct model IDs**. The second typed-decision route uses
the same Luna ID as the fast chat comparator; it is an interface control, not evidence
of a second independently specialized architecture. This adds a useful comparison
without forcing an unrelated safety classifier into the decision-model role.

| Configuration | Exact ID / provider route | Verified capability and limits | Current access |
| --- | --- | --- | --- |
| Jev decision | `jev-1.14.0`, TypeSafe first-party `api.typesafe.ai/v1/systemone` | Typed `noul`; 64K request / 32K per-question default context; text; input $0.042/M, output free | First-party key absent; prior account record had $0 credits. No current authenticated inference claim. Billing/key setup pending. |
| Luna Decisions | `gpt-6-luna`, OpenAI first-party `/v1/decisions` | Native `predicate`, `choice`, `score`; one predicate here. $0.10/M uncached input, no output charge. General model context is 1.05M; no separately verified endpoint-specific maximum is claimed. Prepared requests stay below the experiment's 32K conservative input cap. | Requires funded API-key access. The documented subscription flow supports Responses, not Decisions; do not send its OAuth token to this endpoint. |
| Fast general reference | `gpt-6-luna`, OpenAI Responses via separately authorized project ChatGPT subscription | 1.05M model context, 922K max input, 128K max output; strict structured outputs; reasoning none with output cap 256 | Catalog reauthenticated; eight v2 development calls completed. Subscription quota for the whole future run is not established. |
| Frontier reference | `gpt-6-astra`, same first-party Responses endpoint via authorized subscription | 1.05M model context, 922K max input, 128K max output; strict structured outputs; reasoning low with cap 2,048 | Current catalog and four v2 development calls verified. This is not a promise of unlimited included usage. |
| Native injection specialist | `protectai/deberta-v3-base-prompt-injection-v2`, publisher HF commit `90c9989b1a342275dd0d1a95aad283c04e075671`, local CPU | Apache 2.0; 184,423,682 FP32 parameters; native 512 positions, SAFE=0 / INJECTION=1. Candidate-only overlapping windows, max score, fixed 0.5 threshold. | Nongated weights/tokenizer downloaded; local development inference verified. No API/key/payment required. |

Primary references:
[TypeSafe versions, limits and price](https://docs.typesafe.ai/models),
[official endpoint schema](https://api.typesafe.ai/openapi.json),
[Decisions guide and endpoint-specific price](https://developers.openai.com/api/docs/guides/decisions),
[Luna model specification](https://developers.openai.com/api/docs/models/gpt-6-luna),
[Astra specification and API price](https://developers.openai.com/api/docs/models/gpt-6-astra),
[subscription endpoint support](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference),
[Protect AI publisher card](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2),
[pinned native config](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2/blob/90c9989b1a342275dd0d1a95aad283c04e075671/config.json).

Exact prompts, settings, endpoints, credentials' variable names (never values) and
API-equivalent prices are machine-readable in `data/expanded-v2/model-panel.json`.
The primary chat route is subscription access. Any later API-key alternative must
be explicitly recorded in a new run/version rather than silently mixed into it.
The only official GPT snapshot identifiers inspected are the IDs above; no extra
immutable date-stamped weight revision is invented. Require exact returned-model
matches and retain provider response metadata.

## Local hardware and specialist limitations

The current host is arm64 with 16 GiB RAM. The model actually loaded and completed
CPU development scans. FP32 parameter storage alone is about 738 MB (704 MiB), plus
tokenizer, runtime and working memory. Reserve roughly 2 GB disk for weights/runtime;
this is a planning allowance, not a measured peak RAM guarantee. No CUDA GPU or paid
hosted inference is needed. Use PyTorch CPU, two threads, no remote code, and the pinned
publisher revision. `requirements-expanded-v2.lock` records tested packages.

The publisher explicitly says the project is archived/unmaintained. We select it as
a reproducible accessible baseline, not as the current best detector. It was trained
on seven disclosed corpora; undisclosed/indirect contamination is still possible.
Its binary native interface does not understand a trusted user query as a separate
role. Adding the query to the same text would change the target and mix trust levels;
therefore it is candidate-only, with no fabricated context-effect estimate. Exact
window counts are in `local-token-counts.json`. Long-candidate maximum aggregation can
increase false positives; report length-stratified results.

## Alternatives not required

- `meta-llama/Llama-Prompt-Guard-2-86M` is a relevant alternative but its [publisher repository](https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M) is gated and governed by the Llama 4 community license. Do not bypass the gate using a reupload or buy an inference subscription to avoid the access step. The nongated selected baseline avoids another required account/gate.
- TypeSafe also documents `jev-1.13.0`, but comparing two adjacent Jev versions would not supply an independent model family. Keep it optional as a bridge to the old pilot; do not add it just to reach five names.
- The original reseller route remains `jevmodel.org`, `jev-1.13.0`; its final pilot balance was 47,935 reported input tokens. Its current balance was not reverified, its key is not a TypeSafe first-party key, and it is not a v2 substitute.
- Gemini authenticated in the pilot but failed operationally on both tried versions. It is not on the required shopping list, and adding a payment card is not evidence that capacity errors will disappear.
- A separate independently specialized decision model has not been established by the inspected sources. The selected OpenAI typed route is explicitly a route-level comparator, not a claim that such a model exists or is accessible.
