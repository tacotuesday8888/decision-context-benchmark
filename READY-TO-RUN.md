# V7 preparation is complete; confirmation is still gated

November 1, 2026. The owner has resumed bounded testing. Development and the
fixed audit are authorized; confirmation requires their operational validation
and a separate final freeze. **No v7 experimental results existed when this
preparation report was written.** No paper is being written during this run.

## Locked data

- BrowseSafe++: **200 development +3,000 fresh confirmation groups**, one complete
  clean/attack pair each: **6,400 pages**. Acquired all 15,579 eligible English
  reserve pairs and screened complete historical/task-held components covering
  7,654 source pairs, including unselected/rejected relatives (2,986 additional
  pairs downloaded). Tasks and pages retain the source's privacy-rewritten provenance.
- PromptShield: **4,000 balanced test requests**, the fixed balanced **1,000-request
  general subset**, and **100 validation requests**. Test hash/schema verified.
  Requests and original labels are unchanged; no user task was invented.
- Main general subset: the same **500 groups**; native repeats **100 groups**;
  general repeats **50 groups**. The **100-group source-label audit packet** is
  locked and cannot remove semantic disagreements from the primary population.

Exact/near task/document components, historical exclusions, split closure,
source/pair/partition hashes and all subsets passed local verification. A separate
read-only reviewer independently reconstructed the main grouping and hash-rank
selection. Lexical closure does not certify semantic independence, private
training-data separation, or paths through unacquired non-English pages.

## Fixed configurations

| Configuration | Settings and route |
|---|---|
| Jev | `jev-1.14.0`, first-party `/v1/systemone`, native noul, default limits/no long-context header |
| Luna Decisions | `gpt-6-luna`, OpenAI `/v1/decisions`, native predicate |
| Luna Responses | `gpt-6-luna`, paid `/v1/responses`, reasoning `none`, output cap256, strict Boolean JSON |
| Sol subscription v7.0.2 | `gpt-6.1-sol`, existing project OAuth/public Responses, reasoning `low`, strict structured output; output cap and cache control unsupported/provider default |
| ProtectAI | `90c9989b1a342275dd0d1a95aad283c04e075671`, complete candidate-only 510-token windows/64 overlap, maximum score |

Responses are stateless, `store:false`, `stream:true`, default service tier.
Paid Luna uses explicit-only caching with no breakpoints; subscription Sol's cache
control is provider default/uncontrolled. Sol's separately named route must pass
development as requested or be reported unsupported. **Paid Sol and paid authoring
are disabled.** Engineering uses Sol Ultra; the experimental Sol setting is low.
See [route amendment](docs/study-v7/ROUTE-AMENDMENT.md).

Full planned work is **64,500 paid API calls +6,000 Sol subscription calls +5,200
local records**. These are requests, not independent examples. The corrected
local count is **16,048 windows**; `forecast-v1.json` is superseded because its
saved tokenizer clipped at512. The full-window runtime regression reaches a
terminal marker beyond512 and checks maximum aggregation over every window.

## Cost and limits

The [current measured forecast](results/study-v7/forecast-v3.json) gives
**$21.41 ordinary /$41.32 with all native Luna inputs priced as12h cache writes**;
the doubled-input/maximum-paid-output scenario is **$83.31**. Sol uses subscription
allowance, not API dollars. Optional API authoring allocation is zero.

Counts under local `o200k_base` are measured exactly for serialized requests, but
that tokenizer is **not certified for Jev or GPT-6** and omits hidden server framing.
These are proxy forecasts, not exact billed token counts. Task-minus-length token
differences are reported per configuration. Actual ProtectAI full-document token
and window counts use its pinned tokenizer with truncation/padding disabled.

Conservative full-accepted-context reservations total **$16,661.71** across all
planned paid calls. That is a deliberately loose maximum, not an expected bill;
it does **not** fit the authorized caps. The executor admits whole groups only
when their worst-case reservations fit remaining allocations, settles actual
known usage, retains unknown charges, and stops at the frozen time/cost boundary.
It cannot guarantee the entire target before actual development usage/throughput.

Authorized new limits are **$350 OpenAI experiments and $20 TypeSafe**. Historical
accounted spending/holds are $7.0275592/$1.82758493400000006; operational cumulative
ceilings are therefore $357.0275592/$21.82758493400000006. No purchase/recharge is
authorized. See [authorization](docs/study-v7/RUN-AUTHORIZATION.md).

## Checks and remaining operational questions

Offline fixtures cover exact native prompts, global mixed-label component sampling,
historical rejected relatives, atomic reservations, unknown holds, repeat identity,
no replay/fallback, subscription failures, default inference denial, long-document
window coverage, hand-computable statistics and synthetic null/alternative cases.
The exact paired group-mean t/Holm6 and20,000-draw whole-group intervals were tested
on15synthetic scenarios. Outcome-dependent missingness can invalidate complete-case
inference; planned-group bounds and coverage reporting remain mandatory.

Fresh API and project-subscription catalogues returned200 and listed the requested
models. This verifies authentication/catalogue visibility, **not inference access,
credit, quota or rate limits**. Those checks, returned settings/model IDs, actual
native tokens, throughput and audit span fidelity remain authorized-development
work. No provider or unsupported example may be silently replaced.

## Commands and artifacts

Default inspection stays offline:

```sh
cd '/Users/langqi/Developer/Projects/Decision Context Benchmark Plan'
'/Users/langqi/Developer/Projects/Decision Context Benchmark/.venv/bin/python' -m scripts.study_v7.run --manifest results/study-v7/run-manifest-confirmation-v7.0.6.json
```

The complete bounded core confirmation instruction is:

```sh
cd '/Users/langqi/Developer/Projects/Decision Context Benchmark Plan'
'/Users/langqi/Developer/Projects/Decision Context Benchmark/.venv/bin/python' -m scripts.study_v7.run --manifest results/study-v7/run-manifest-confirmation-v7.0.6.json --authorization results/study-v7/confirmation-authorization-v7.0.7.json --phase confirmation --execute
```

It is inert until its owner receipt matches the exact frozen plan/manifest/code,
provider budgets, phase and cutoff. The default authorization template stays false.
Confirmation cannot run through this development-only receipt. New admissions
stop14:00UTC; verified private handoff is due by16:06UTC. See the
[schedule and recorded preparation time](docs/study-v7/SCHEDULE.md).

Tracked artifacts: [main selection](results/study-v7/main-selection.json),
[external selection](results/study-v7/external-selection-v3.json),
[request counts](results/study-v7/request-summary.json),
[run manifest](results/study-v7/run-manifest.json),
[synthetic validation](results/study-v7/statistical-simulation.json), and
[statistics methods](docs/study-v7/STATISTICS.md). Restricted source text, complete
request plan, token audit and raw attempts stay only under ignored
`data/raw/study-v7/`. Delivery is in [private draft PR14](https://github.com/tacotuesday8888/decision-context-benchmark/pull/14),
dependent on [planning PR12](https://github.com/tacotuesday8888/decision-context-benchmark/pull/12).
Preparation commit: `975106875047d08756a10e61c5cb8a3e93e0e58c`.

All22applicable preparation CI checks passed. The first13development responses
exposed an overly strict metadata parser; [v7.0.1](docs/study-v7/AMENDMENT-v7.0.1.md)
documents the correction and an exact-hash continuation without resending those
requests. The original preparation manifest/authorization and stop remain
preserved; [active-run.json](results/study-v7/active-run.json) identifies the current
amendment. [V7.0.2](docs/study-v7/AMENDMENT-v7.0.2.md) separately records subscription
Sol's unsupported cache-control parameter, preserves its four rejected requests,
and changes only Sol payloads. All69,700non-Sol requests remain identical. Revised
Sol development has finished:499valid classifications and one preserved temporary503.
[V7.0.3](docs/study-v7/AMENDMENT-v7.0.3.md) records a single continuation of the
eight never-sent requests, all successful. The failed first attempt was not retried.
The final [operational receipt](results/study-v7/development-validation-v7.0.3-final.json)
validates all five configurations. The locked100-pair audit stopped at70valid reviews, oneHTTP504 and29unattempted.
The one bounded continuation is exhausted: Sol is operationally deferred, with
all planned cells retained. [Final readiness](results/study-v7/route-validation-confirmation-v7.0.4.json)
validates the four core configurations. [Confirmation freeze](docs/study-v7/CONFIRMATION-FREEZE.md)
binds unchanged payloads/settings and the tested v7 accounting cache.86offline
tests and the full locked-source/raw-artifact verification pass. No confirmation
accuracy was inspected before freezing.

The Scientific Agent Skills procedural assistance is cited in the
[software provenance outline](docs/study-v7/PAPER-OUTLINE.md); it does not certify
the study. No manuscript or empirical PDF has been created.


The [first core continuation](docs/study-v7/CORE-CONTINUATION-v7.0.5.md) preserves
one LunaDecisions HTTP504 and its0.525unknown-charge hold after27native groups.
Only new first requests resume after cooldown under the SAME frozen manifest;
the failed key is never retried. The active pointer identifies the current receipt.


The [TPM pacing amendment](docs/study-v7/TPM-PACING-v7.0.6.md) shares one
conservative rolling allowance across both paid Luna routes after a provider429.
94offline tests pass; payloads/cohorts/statistics/caps/deadline remain unchanged.
Both native failures retain0.525unknown-charge holds. Seven never-sent requests
in the admitted group resume first; completed/failed first outcomes are not retried.


The [v7.0.7 service continuation](docs/study-v7/CORE-CONTINUATION-v7.0.7.md)
preserves a later native504 and all1.575unknown-charge holds. The paced execution
manifest/code remain unchanged; only untouched first requests resume after cooldown.
