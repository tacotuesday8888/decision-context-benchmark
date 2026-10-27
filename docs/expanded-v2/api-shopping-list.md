# API shopping list — expanded v2.0

Only **two paid API providers/accounts** are needed for the selected native decision interfaces: TypeSafe and OpenAI. The existing ChatGPT subscription can supply the two Responses comparators subject to its actual allowance; the local specialist needs no paid API. No purchase or paid request has been made for this expansion.

| Required API | Exact selected model | Official setup | Reuse / secure credential | Minimum funding verified | Development / evaluation / bounded retries |
| --- | --- | --- | --- | --- | --- |
| TypeSafe System One | `jev-1.14.0` | [Console](https://console.typesafe.ai/) · [Keys](https://console.typesafe.ai/keys) | Reuse the existing account; first-party key not yet configured. `TYPESAFE_API_KEY`. Reseller key does not work here. | No public minimum established in inspected sources; verify in that account's billing screen. Do not assume a $5/$10 minimum. | $0.0025 / $0.0167 / $0.0008 (41 retry requests max). |
| OpenAI Decisions | `gpt-6-luna` at `/v1/decisions` | [Platform](https://platform.openai.com/) · [Billing](https://platform.openai.com/settings/organization/billing/overview) | Reuse an existing API organization/project if available; create a scoped key through the supported secure OpenAI Platform flow, saved locally as `OPENAI_API_KEY`. ChatGPT OAuth is not documented for Decisions. | Official prepaid minimum **$5**; default purchase amount is not a run budget. | $0.0060 / $0.0401 / $0.0020 (41 retries max). |

TypeSafe publishes $0.042 per million input tokens with free output; Decisions publishes $0.10 per million uncached input tokens with free output. [TypeSafe price](https://docs.typesafe.ai/models), [Decisions price](https://developers.openai.com/api/docs/guides/decisions#pricing-and-availability).

The OpenAI funding minimum and the instruction to inspect automatic recharge come from its [official prepaid-billing article](https://help.openai.com/en/articles/8264644-setting-up-and-managing-prepaid-api-billing). Automatic reload must remain off. Funding completion is not permission to start paid inference.

## Existing access and local model

| Selected comparison | Route / key | Additional account or payment | API-equivalent development / evaluation / retry estimate |
| --- | --- | --- | --- |
| Fast `gpt-6-luna` | Existing separately authorized ChatGPT subscription; local OAuth record, **no API-key variable for this route** | Current authentication and eight development calls verified. Reuse it, do not buy a duplicate subscription. Full-run remaining allowance is not verified. | If an explicitly authorized API-key alternative is needed: $0.0081 / $0.0541 / $0.0027. Same `OPENAI_API_KEY`, no new provider. |
| Frontier `gpt-6-astra` | Same authorized subscription | Four development calls verified. Quota failure must stop, not trigger a silent paid fallback. | API-key alternative: $2.2496 / $15.1545 / $0.7577. Same OpenAI account/key. |
| `protectai/deberta-v3-base-prompt-injection-v2` at pinned publisher revision | Local CPU, **no key** | Nongated Apache-2.0 weights; no paid API/subscription/GPU rental. Successfully loaded on this 16 GiB arm64 host. | $0 API; 60 development / 402 evaluation scans, with 67 / 445 token-window forwards. |

OpenAI API-equivalent rates are $0.10/$0.50 per million input/output tokens for Luna and $10/$50 for Astra. Those are fallback cost estimates, **not prices assigned to included subscription calls**. [Luna](https://developers.openai.com/api/docs/models/gpt-6-luna), [Astra](https://developers.openai.com/api/docs/models/gpt-6-astra), [authorized subscription endpoints](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference).

## Budget and purchase boundary

- If Responses remain within the existing subscription: estimated additional metered API usage for TypeSafe + Decisions is **$0.068**, plus the providers' account funding minimums. That does not establish that 812 requests/model fit the subscription allowance.
- If every selected remote configuration instead uses metered APIs: **$18.29** estimated for development + evaluation + 5% retry reserve; a long-output/byte-budget sensitivity scenario is **$129.76**. The primary protocol would need an explicit route/version update for API-key chat execution.
- These are planning estimates, not a spending cap or a provider guarantee. They use serialized characters/4, no caching discounts, 16 mean output tokens for Luna and 256 for Astra. Observed small development checks used 16 and 16–36 tokens, respectively; that sample is too small to guarantee future reasoning length. See request-plan.json for every planned request and budget.json for byte/output-cap scenarios.
- The expanded paid run remains disabled. The old pilot’s $10 authorization is not expanded. Do not fund $130 merely because a conservative scenario is shown; first choose a run cap and intended route after billing is ready. Do not enable recharge or buy another subscription.

## Optional only

No Gemini, reseller Jev, separate hosted detector or Hugging Face paid endpoint is required. Prompt Guard 2 is a gated local alternative requiring a separate license/access decision, not a paid-API requirement. First-party Jev 1.13.0 is an optional pilot-version bridge, not a required extra model.

Never paste keys or card details into chat. OpenAI key creation should use the secure Platform picker/local destination confirmation. TypeSafe account funding/key creation should use the official console and an ignored local environment file; do not expose a generated secret in terminal output or this repository.
