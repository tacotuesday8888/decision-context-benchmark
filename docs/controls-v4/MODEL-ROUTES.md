# Reused model routes in controls v4

All seven configurations passed the bounded development access/format checks, except
one preserved transient Decisions HTTP503. That is current experiment access evidence,
not proof of an account balance, future quota or independent physical model instances.

| Configuration | Exact model / checkpoint | Actual route | Incremental API accounting |
|---|---|---|---|
| Jev | `jev-1.14.0` | TypeSafe first-party `/v1/systemone` | $0.042/M input, free output |
| Luna Decisions | `gpt-6-luna` | OpenAI first-party `/v1/decisions` | $0.10/M uncached input, free output; conservative cache reservation |
| Luna chat | `gpt-6-luna` | Separately authorized ChatGPT subscription, standalone Responses requests | Zero incremental metered API charge on this route |
| Astra chat | `gpt-6-astra` | Same authorized subscription route, standalone Responses requests | Zero incremental metered API charge on this route |
| Nimble | `nimble:9b-q4_K_M`, digest `d99f22c363cea449151cc473887de081b98ca98e8a29b1a8710e09da916f2c79` | Local native decisions, Ollama 0.40.13 | No paid API |
| Laya | `convaiinnovations/laya-multilingual`, revision `1720e3e3357cfe1e281542e223f8273b0890ca34` | Local CPU/eager, laya 0.4.17 | No paid API |
| ProtectAI | `protectai/deberta-v3-base-prompt-injection-v2`, revision `90c9989b1a342275dd0d1a95aad283c04e075671` | Local CPU candidate-only sliding-window detector | No paid API |

Official paid prices were rechecked on 2026-10-30:
[TypeSafe models](https://docs.typesafe.ai/models),
[OpenAI Decisions pricing](https://developers.openai.com/api/docs/guides/decisions#pricing-and-availability).
No API chat fallback, reseller, new account, subscription, payment method or purchase
was introduced. Existing environment/key setup is reused; credentials are never in
records or Git. Subscription fees and electricity are not assigned per-request costs.

This is six model IDs and seven configurations. Luna Decisions is an interface
comparison, not evidence of independently specialized weights. Context limits,
output budgets, thresholds, exact prompts and returned metadata are recorded in the
request plan and raw records. Laya input coverage was tokenized before inference;
other routes are checked against returned usage and terminal status. ProtectAI's
window maximum is a detector score, not an asserted calibrated document probability.

The inherited `paid_enabled: false` field in the old preparation panel describes
that old preparation adapter's disabled execution function. The new authorized,
capped controls runner uses its own ledger. Actual `paid_request` and `access_route`
fields in each new record are authoritative for this experiment; the historical
preparation flag does not mean these first-party calls were free.

The original Jev 1.13 reseller pilot, authorized subscription pilot route and failed
Gemini operation remain preserved in their original records. New first-party access
and later versions do not retroactively change those historical facts. Ollama's
external update from 0.40.11 to 0.40.13 is explicit in the development amendment;
Nimble weights, request shape and threshold remain unchanged.
