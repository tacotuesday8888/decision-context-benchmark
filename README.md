# Decision Context Benchmark

## Latest preparation: v6

The expanded [v6 handoff](docs/study-v6/HANDOFF.md) prepares **2,876 review examples**:
2,000 BrowseSafe++ pages, 400 NVIDIA static examples and 476 preserved source/scope
cases. **Independent review and v6 evaluation have not run.** Historical studies below
remain unchanged. Read the [design](docs/study-v6/DESIGN.md) and
[comparison of research methods](docs/study-v6/METHODS-COMPARISON.md).

Use the complete [blinded reviewer prompt](docs/study-v6/REVIEW-GOAL.md) in a fresh
chat, then the separate [Sol implementation/execution prompt](docs/study-v6/SOL-GOAL.md).
Raw restricted data, review mappings and credentials remain local and Git-ignored.

## Historical pilot

A reproducible pilot measuring how revealing the original user task and neighboring
untrusted email changes prompt-injection detection. Actual requests, responses and
per-example outcomes are saved; historical connectivity tests are kept separately.

Start with the [pilot report](results/pilot/report.md), [frozen protocol](docs/protocol.md),
[related-work and dataset review](docs/related-work.md), and [execution notes](docs/execution-notes.md).
The paper/report makes no novelty claim: closely related context ablations already exist.

## Expanded v2 preparation

The expanded collection contains **402 distinct evaluation candidates and 60 development
candidates**, with original task/source support recorded per row. The frozen preparation
record is preserved. **Expanded evaluation is complete: 5,274 saved logical cells**
across seven configurations (six model IDs), including five operational failures and
seven classification abstentions. No original pilot record was changed.
Read the [source-specific report](results/expanded-execution/report.md),
[research draft](paper/manuscript.md), [PDF draft](output/pdf/decision-context-benchmark-draft.pdf),
and [offline paper reproduction instructions](paper/README.md).
The [research/statistical plan](docs/expanded-execution/RESEARCH-PLAN.md) distinguishes
primary classification analysis from the later exploratory probability analysis.
Conservative all-in metered accounting is $0.096443 OpenAI and $0.051171 TypeSafe,
within the independent $15 / $20 caps; subscription fees and local electricity are excluded.
Local Nimble and Laya both completed all 812 planned cells without discarded weak results.

Read the [expanded protocol](docs/expanded-v2/protocol.md),
[dataset review](docs/expanded-v2/dataset-review.md),
[exact model panel](docs/expanded-v2/model-selection.md), and
[API shopping list with budget](docs/expanded-v2/api-shopping-list.md).
The original pilot below remains unchanged. See
[expanded reproduction instructions](docs/expanded-v2/README.md).

## Pilot artifacts

- `data/pilot.jsonl`: 2 development and 18 held-out, deterministically extracted examples.
  Original scenario emails are published synthetic fixtures, not real private emails.
- `data/manifest.json`: pinned upstream revisions, source hashes, selection and gold provenance.
- `results/pilot/frozen-plan.json`: protocol/data hashes, exact prompts and request hashes,
  frozen before inference. Jev 1.13.0 via an independent reseller and GPT-6 Luna via
  separately authorized ChatGPT subscription access form the primary panel.
- `results/pilot/records/`: exact requests and raw provider responses, including failures.
- `results/pilot/per-example.csv` and `summary.json`: structured records and paired statistics.
- `results/pilot/figures/`: scientific figures in PNG, SVG and PDF formats.
- `docs/gemini-substitution.md`: separately recorded bounded alternative after Gemini 3.8
  capacity failures; see the report for whether a supplementary panel actually completed.

The primary evaluation is deliberately small: nine attack teams, nine related benign
emails from one fixture, and one shared trusted task. Grouped bootstrap intervals are
conditional on that fixture. Published data contamination, selection for historical attack
success and correlated benign examples limit generalization. Native decision scores are
not calibrated probabilities. Route latency includes network and provider/reseller overhead.

## Reproduce without credentials or inference

Python 3.13 was used. All selected data and raw pilot records are included under the
upstream MIT notice in [third-party notices](docs/third-party/llmail-LICENSE.txt).
The full upstream downloads and all credentials stay ignored.

```sh
uv venv .venv --python 3.13
uv pip install --python .venv/bin/python -r requirements-pilot.lock
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/verify_pilot.py
.venv/bin/python scripts/analyze_pilot.py
```

These commands never call a model. The verifier checks frozen request/data hashes,
raw-response parsing, split/group boundaries, complete primary coverage, caps, tables,
and credential absence. Analysis rebuilds the CSV, summary, report and figures from
saved records. CI performs the same offline flow. PNG/PDF rendering metadata may vary
by platform; the analytical JSON and CSV must remain identical.

To independently re-extract the selected data from the pinned public source (~264 MB):

```sh
.venv/bin/python scripts/prepare_pilot.py
```

It refuses to replace a changed frozen manifest/selection. Network access is needed
for upstream downloads, but no model API or API key is needed. Source licenses and
provenance are documented in the related-work review and protocol.

## Live inference (separate from offline reproduction)

Owner authorization now covers the bounded pilot and analysis, superseding the old
preparation-only scope. The owner set a US$10 total spending cap. The implemented
protocol uses existing free grants, free quotas and subscription access with no paid
fallback, purchases or recharge. Do not assume this authorizes an unbounded new study.
Never print, commit or upload `.env.local`, `.secrets/` or credentials.

`provider_access.py` authenticates the two chat catalogs without inference and refreshes
only the project's separately authorized subscription credentials. It never reads Codex
cached tokens. Setup instructions and historical evidence remain below.

```sh
.venv/bin/python scripts/provider_access.py
.venv/bin/python scripts/run_pilot.py --freeze-only
.venv/bin/python scripts/run_pilot.py --provider jevmodel --split dev
.venv/bin/python scripts/run_pilot.py --provider openai --split dev
.venv/bin/python scripts/run_pilot.py --provider gemini --split dev
# Inspect development records before evaluating a provider.
.venv/bin/python scripts/run_pilot.py --provider jevmodel --split eval
.venv/bin/python scripts/run_pilot.py --provider openai --split eval
```

Completed records are skipped. The original Gemini route did not pass development;
do not run its evaluation merely to fill a table. The independently documented
substitution is invoked with `scripts/run_gemini_comparison.py` and stops on failed
availability/development checks. A fresh experiment needs a separate output directory,
a pre-inference protocol and fresh quota checks; deleting existing records to rerun is
not a reproduction procedure. Existing result directories are the historical record.

Project research history: [Plan small-model coding benchmarks](codex://threads/01a13c09-d537-73b2-98f3-c0bdd6b33fe6).
Read recent decisions before older brainstorming. Preserve the separate older SLM
Benchmark workspace. Project name: Decision Context Benchmark.

## Historical setup evidence

The following records describe October 24 preparation, not the current experimental
results. Earlier statements that no benchmark was run or that only setup was authorized
apply to that historical period. Current results are in the pilot report above.

## Access preparation — October 24, 2026

| Provider | Verified status | Remaining step |
| --- | --- | --- |
| Google Gemini | Gemini 3.8 Flash passed the tiny inference check: expected and received YES; free API tier | Initial request returned 503, bounded retry succeeded. Console shows 5 requests/minute, 250K input tokens/minute, and 20 requests/day |
| TypeSafe Jev direct | Signed in; key creation rejected because the organization has $0 credits | Optional paid route; no funding authorized |
| Jev through OpenCode | Restricted key saved; `jev-1.13-free` enabled at $0; documented decision endpoint is reachable using standard curl | Two rejected requests returned HTTP 429; captured error is `FreeUsageLimitError`. No successful Jev inference. Workspace has no budget policies to remove |
| Jev through independent public playground | One free browser check at jevplayground.com returned Yes with displayed probability 0.99; site reports model ID `typesafe-ai/jev` | Browser access only. Exact model version and upstream identity not independently verified; reusable API not established |
| Jev through jevmodel.org API | Authenticated HTTP test passed; request and response both identify `jev-1.13.0`; answer YES, P(yes)=0.99 | Free signup trial: 99,721 input tokens remain. Jev 1.14 is paid-only according to the live API; no plan purchased |
| Perplexity | Project created; no key at $0 credits | Deferred at owner's request |
| OpenAI / ChatGPT subscription | GPT-6 Luna passed the tiny inference check: expected and received YES, with response.completed | First completed call exposed a streaming-capture bug; parser fixed and second call verified. Project token refresh is now implemented in provider_access.py; browser reauthorization remains a separate setup operation |

Google AI Pro's $10/month GenAI and Cloud credit benefit is visible in the owner's
Developer Program account, but is unclaimed because there is no Cloud billing account.
Do not create billing or assume these credits are active. Google documents a positive
prepaid balance requirement before eligible promotional credits apply to prepaid Gemini API billing.

Sources: [TypeSafe models](https://docs.typesafe.ai/models),
[OpenCode models and free Jev](https://opencode.ai/v2/docs/console/models/),
[Google Developer Program benefits](https://developers.google.com/profile/help/benefits),
[Gemini API billing](https://ai.google.dev/gemini-api/docs/billing).

No payment method, automatic recharge, credit purchase, paid-model fallback, or full benchmark was performed.
The old SLM Benchmark folder has not been moved or renamed.

The OpenCode key has model-request permission only. Billing, membership, provider,
workspace-settings, service-account, and other administrative permissions are disabled.
The console shows expiry January 23, 2027. Do not silently substitute paid `jev-1.13`
for the free model. Free access is promotional and must be rechecked before a run.
OpenCode's model-list endpoint initially returned Cloudflare 1010. The documented
decision endpoint was then tested using standard curl, without browser impersonation,
protection changes, or network changes. Its actual blocker is the provider's free-usage
gate. No further rate-limit retries were made after capturing the error.
Related upstream reports: [free-usage failure on unused accounts](https://github.com/anomalyco/opencode/issues/58205)
and [Jev free budget errors](https://github.com/anomalyco/opencode/issues/57859).

## Tiny access check — October 24, 2026

Task: given "The submitted number is 7.", answer whether it is odd. Expected answer: YES.
Jev receives one typed `noul` question; chat models receive a short YES/NO prompt.
This verifies basic access and response handling only; it measures no benchmark accuracy.

| Model | Outcome |
| --- | --- |
| Jev 1.13 Free (OpenCode) | Blocked: HTTP 429, FreeUsageLimitError |
| Site-reported TypeSafe Jev (jevplayground.com) | Browser check passed: Yes, displayed P(true)=0.99; version unpinned |
| Jev 1.13.0 through jevmodel.org HTTP API | Passed: HTTP 200, YES, P(yes)=0.99; response model matched pinned version |
| Gemini 3.8 Flash (free API tier) | Passed: YES |
| GPT-6 Luna (ChatGPT subscription) | Passed: YES, terminal completion verified |

All nine attempts, including failures and the separate browser-only check, are indexed in `results/smoke-summary.csv`.
Requests and provider responses are saved locally under ignored `results/raw/smoke/`.
The first OpenAI call completed but its answer was not captured by the original parser;
that record is not counted as a verified answer. The fixed parser has regression tests.

### Free alternate Jev route

Working API: [jevmodel.org](https://jevmodel.org/docs/) at
`POST https://jevmodel.org/v1/systemone`, with Bearer authentication.
The owner approved Google signup, the service terms, and a project key stored only
as `JEVMODEL_API_KEY` in ignored `.env.local`. The authenticated dashboard showed
the one-time 100,000-input-token free grant; no card, payment, or subscription was configured.

The first API request pinned `jev-1.14.0` and was rejected with HTTP 402 `payment_required`.
The live API said 1.14 requires a paid plan, contradicting the pricing page's claim
that the signup tier includes 1.14. No tokens were deducted for the rejection.
The next request pinned the documented stable version `jev-1.13.0` and succeeded:

```json
{
  "model": "jev-1.13.0",
  "answers": {"is_odd": {"type": "noul", "noul": 0.99}},
  "usage": {"input_tokens": 279, "output_tokens": 22}
}
```

HTTP status was 200 and `X-Tokens-Remaining` was `99721`. The request's state was
"The submitted number is 7." and its sole question was "Is the submitted number odd?".
This is a real API response, not copied playground output. Model version confirmation
means the reseller's response matched the pinned model; there is no independent
attestation of the upstream model weights. Usage and probabilities are preserved as
reported by this reseller, without assuming they match TypeSafe's direct accounting.

`smoke_access.py jevmodel` requires a verified free balance, no configured payment,
and a matching pinned model. A moving alias or missing model ID does not pass.
The completed tiny test is recorded and the local guard now refuses another request;
any further inference requires a new owner instruction. Regression tests cover this
guard, unverified balances, and unresolved model aliases. The benchmark has not run.

The owner authorized one further free tiny test. At [Jev Playground](https://jevplayground.com/),
the same state and Boolean question returned Yes, with normalized probability 0.99.
The UI reports model ID `typesafe-ai/jev`, 279 input tokens, 20 output tokens,
and 639 ms (site-reported server + network time). Its details explicitly round probabilities
to two decimals; do not treat 0.99 as an unrounded native probability.
No account, credential, billing setup, or payment was required.

This is an independent site's reported result, not provider-authenticated model identity.
The exact Jev version is unknown. The site's [API guide](https://jevplayground.com/jev-api)
states that its internal evaluate endpoint is not a public third-party API. Do not
reverse-engineer or reuse that endpoint for the benchmark. This check proves the browser
tool responds to our input; it does not establish a reproducible, version-pinned Jev API.
The complete visible result and captured accessibility text are preserved in `results/raw/smoke/`.
Other access routes assessed are indexed in `results/jev-free-access-options.csv`.

The smoke utility accepts one provider per invocation and never retries automatically:

```sh
.venv/bin/python scripts/smoke_access.py jev
.venv/bin/python scripts/smoke_access.py gemini
.venv/bin/python scripts/smoke_access.py openai
```

These commands perform live requests. Re-run only when another access test is authorized.

## Subscription sign-in setup

This follows OpenAI's documented [ChatGPT plan authorization flow](https://developers.openai.com/siwc/token-sharing-open-source/sign-in).
It creates a separate project registration and never reads cached Codex credentials.

```sh
uv venv .venv --python python3
uv pip install --python .venv/bin/python -r requirements-setup.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/chatgpt_signin.py
```

Open the printed local setup URL in Chrome. After explicit browser authorization,
the utility validates the identity token, saves credentials with owner-only permissions
in the ignored `.secrets/chatgpt.json`, and requests model metadata. It does not perform inference.
The server expires after 20 minutes. If it expires, restart the utility and use the new URL.
The browser utility handles first-time registration. `provider_access.py` refreshes the
existing project session atomically and serializes refresh-token rotation. If refresh
fails and browser reauthorization becomes necessary, stop and resolve sign-in before
continuing that provider; never read cached Codex credentials.
