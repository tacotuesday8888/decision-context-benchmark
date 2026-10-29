# Expanded execution v2.1

This execution supersedes preparation-only restrictions under the owner's October 29,
2026 instruction. It preserves every original pilot and expanded-v2.0 freeze hash.
The collection, prompts, model settings, split boundaries and labels are unchanged.
Code, credentials and execution outputs are separately versioned.

## Authorization and credentials

The owner authorized **less than $15 total** for development checks plus execution.
The configuration reserves $0.99 for checks and $14.01 for evaluation; the ledger
rejects requests that would exceed either shared budget. No purchases, recharge,
new subscriptions or public release are authorized. There is no automatic paid chat fallback; a deliberate route switch needs a new configuration, development validation and sufficient remaining budget.
Balances were visibly $17 OpenAI and $25 TypeSafe before inference; those are not
spending caps. Both official APIs passed two actual development inference checks,
including exact returned IDs, strict parsing and token usage. `access.json` records
credentials, authentication and inference separately.

New project keys were saved only in Git-ignored `.env.local`, mode 600, preserving
other entries. OpenAI used encrypted Platform key creation after reconnecting its
connector. TypeSafe used the official console and a one-time loopback password form.
The originally created ContextBench TypeSafe key was preserved after explicit owner
confirmation to create a recoverable new key. No unrelated or historical credentials
were revoked. Legacy Gemini, OpenCode and reseller Jev entries support the separate
pilot/history and are not loaded by expanded execution. No Codex cached token is used.
Temporary key-encryption files and clipboard copies were cleaned after setup.

## Routes and accounting

`results/expanded-execution/execution-config.json` fixes these routes:

- `jev_firstparty`: official TypeSafe System One, `jev-1.14.0`, API key.
- `luna_decisions`: official OpenAI Decisions, `gpt-6-luna`, API key.
- `luna_chat`: `gpt-6-luna` Responses, existing project-authorized subscription.
- `astra_chat`: `gpt-6-astra` Responses, the same subscription.
- `protectai_local`: pinned local Protect AI model, candidate-only, CPU.

There are five configurations and four distinct model IDs. No Gemini or Perplexity
key, subscription or model is required. There has been no subscription-to-paid-chat
route switch. Such a switch requires a new configuration/version and development
validation before evaluation; do not silently substitute it after a quota failure.

The next full remote plan is 812 cells per configuration; local has 402 scans.
Preparation estimated about $0.057 for Jev+Decisions evaluation without retries,
or about $0.060 including a 5% retry allowance, with chat calls included in the
subscription. These are character-based estimates, not confirmed invoices.
Current reservations are deliberately more conservative: about $1.513 for both
metered evaluation configurations including worst-size retries. Actual raw usage
is preserved and is the basis for accounting; the owner did not authorize spending
credit balances in full.

Before each attempt, reserve UTF-8 request bytes plus a 4,096-token framing allowance
at twice documented input rates, plus the full output-token cap. This covers standard
cache-write premiums without relying on discounts. Reservations are an engineering
bound conditional on current standard prices and framing allowance, not a provider-side
billing hard limit. Stop if returned usage exceeds the reservation. Missing/ambiguous
usage retains the whole reservation. Prices: TypeSafe $0.042/M input, Decisions
$0.10/M input; output free for both. Subscriptions and local inference count as zero
new metered expense. No tools or separately billed services are enabled in payloads.

`execution-ledger*.json` together share **one $14.01 evaluation cap**, not $14.01 each.
`.budget.lock` serializes their mutations; crashed/pending attempts keep their reserves.
The original serial ledger retains completed Jev and the initially launched Astra
process; separately named ledgers allow independent configurations to continue.
Do not launch duplicate configuration processes. Each completed logical cell, including
invalid outputs, is skipped on resume; changed routes/payloads are rejected.

## Failures and reproduction

All requests, responses, returned settings, usage and per-attempt failures are saved.
Only one transient HTTP 500/502/503/504 or transport retry is allowed, at most 41 per
remote evaluation configuration. No development retries. Authentication, billing,
quota or model mismatch stops the provider and writes STOP.json. No retries of
refusals, ties, invalid formats or truncation. Partial transport bodies are retained
by the execution transport.

The first Luna evaluation process used the historical transport helper. One cell
returned HTTP 200, curl exit 0, and an empty saved body, with no terminal event or usage.
This is an observed invalid cell, not a semantic prediction and not a proven timeout.
The original failure and STOP.json remain. `stop-resolution.json` records continuation
of remaining subscription cells while skipping that invalid cell, with no repair or
retry. A queued process waits for the initial serial Astra run before resuming Luna.

Offline checks and analysis (no inference):

```sh
.venv/bin/python -m unittest discover -s tests/expanded_execution -v
.venv/bin/python -m unittest discover -s tests/expanded_v2 -v
.venv/bin/python scripts/expanded_v2/verify.py
.venv/bin/python scripts/expanded_execution/analyze.py
```

On a fresh checkout install `requirements-expanded-v2-data.txt`; local inference also
needs the frozen local-runtime lock and cached pinned weights. No dependency or model
change is needed on this host. Secrets are never in Git. A new machine must obtain its
own authorized credentials; copying this repository does not copy access.

Live commands use current authorization and configured caps; inspect running processes
and saved state before invoking them:

```sh
.venv/bin/python scripts/expanded_execution/execute.py estimate
.venv/bin/python scripts/expanded_execution/execute.py eval --config luna_decisions
.venv/bin/python scripts/expanded_execution/execute.py eval --config astra_chat
.venv/bin/python scripts/expanded_execution/execute.py eval --config luna_chat
```

## Analysis

`summary.json`, `per-example.csv`, `figures/` and `report.md` are offline derivations.
The report explicitly stays partial while intended cells remain unrun. Source strata
retain class counts, valid coverage/denominators and observed invalid/missing counts.
Strict balanced accuracy counts observed invalid outputs incorrect; it is undefined
for one-class strata. Paired inference is suppressed until the source stratum has
run both conditions. BIPIA uses separate document/family bootstrap sensitivity analyses;
LLMail positive teams and negative fixtures/topics use their own grouping units.
One-fixture negatives cannot support a population FPR interval. No pooled winner,
confirmatory p-values, generated labels or evaluation-based tuning are introduced.

Official payload/rate references: [OpenAI Decisions](https://developers.openai.com/api/docs/guides/decisions),
[TypeSafe models](https://docs.typesafe.ai/models), [TypeSafe quick start](https://docs.typesafe.ai/introduction/quickstart),
[authorized subscription Responses](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference).
