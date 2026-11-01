# Pre-inference amendment: subscription Sol

November 1, 2026. **No v7 model outputs were available when this choice was made.**
The owner changed the payment route: Jev and Luna use the API; expensive Sol uses
subscription access. Paid `sol_responses` and paid Sol authoring are disabled for
this run. This is a named change to the saved v7 proposal, not an invisible
fallback between API and subscription treatments.

The amended optional configuration is `sol_subscription`: model `gpt-6.1-sol`,
reasoning `low`, strict Boolean JSON schema for classification, stateless complete
source input, `store:false`, `stream:true`, public
`https://api.openai.com/v1/responses`, and the existing project-authorized ChatGPT
OAuth credential. No Codex authentication cache or new account is used. The
preparation/engineering agent continues at Sol Ultra; that is not a classifier
setting. The same frozen general subset, repeat subset and 100-pair audit packet
are retained. Audit responses use the separate fixed structured audit schema.

Subscription direct access does **not** support `max_output_tokens`. Therefore the
amended configuration explicitly omits it and records the provider-default output
limit as unverified. It does not claim the original API's 2,048-token cap or route
equivalence. A fixed 60-second transport deadline preserves interrupted raw bytes;
it is a runtime bound, not a token cap. Requested low reasoning, strict output,
service tier and explicit-only caching must pass authorized development as sent;
unsupported fields cannot be silently removed after a rejection. Such a change
requires another documented pre-confirmation amendment, or Sol is deferred.

The official [subscription limitations](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
and [models/inference flow](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
were checked before implementation. They describe a public Responses OAuth route,
streamed terminal events, required stateless options and the unsupported output
cap. Catalogue visibility does not establish present entitlement, credit or
accepted inference settings. Existing project OAuth tokens may be renewed in
place using their approved refresh flow; secrets are neither copied into this
checkout nor exposed in evidence. This does not modify v6 code, source selections,
raw results or spending history.

Sol has separate scheduling lanes and zero API-dollar reservations. Subscription
usage, request IDs, timestamps, raw terminal/partial responses and quota failures
remain recorded. Quota is finite and is not assumed free of operational limits.
No paid Sol fallback is permitted. If the route cannot meet the stated controls,
report it unsupported/deferred and continue Jev, Luna Decisions, cheap Luna
Responses and the pinned local ProtectAI reference. An unfinished Sol audit is
reported as unfinished; source-label admission does not depend on its verdicts.
