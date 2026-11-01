# V7 collection and analysis handoff

The authorized eligible run is closed and independently verified. On the shared
2,850-group native cohort, authentic task information lowers Jev’s source-label
balanced error by 1.07–2.37 percentage points and raises Luna Decisions’ error by
1.16–1.77 points across the three controls. All six Holm-adjusted p-values are below
.001; the all-planned missing-error bounds retain those directions. Jev’s lower
balanced error includes fewer false positives and more false negatives: on the
same cohort, empty task → task changes FPR from 12.88% to 6.63% and FNR from 8.11%
to 11.79%.

Start with the [technical handoff](results/study-v7-execution/README.md),
[reviewed primary figure](results/study-v7-execution/reviewed-figures/primary-contrasts.png)
and [exact primary table](results/study-v7-execution/tables/primary-contrasts.csv).
Delivery remains [private draft PR #14](https://github.com/tacotuesday8888/decision-context-benchmark/pull/14).
No manuscript, PDF, public release, submission or merge was produced.

## Completed and deferred coverage

- Native main: all 3,000 groups and 48,000 first attempts are terminal:
  47,840 OK, 157 ties and three HTTP failures.
- ProtectAI main: all 1,000 candidate-only pages on the fixed 500-group subset.
- External PromptShield: all 4,000 Jev and 4,000 ProtectAI records; ten Jev ties retained.
- Jev repeats: all 800 fresh repeat-1 calls, with 797 OK and three ties.
  First outcomes were never replaced.
- Luna Responses main: 109 valid, two missing_usage credit failures and 3,889
  unattempted cells out of 4,000 planned.
- Remaining paid OpenAI external/repeat cells were deferred after explicit
  credit_balance_exhausted provider errors. No credit probe, recharge or reset occurred.
- Sol confirmation/repeats were separately deferred after repeated service failures.
  Its 569 valid development/audit classifications are not confirmation results.

Original labels, plan, subsets, payloads, settings and analysis methods remain.
Planned denominators, cancellations, ties and failures are explicit. Authorized
remaining eligible routes are complete; the full five-configuration experiment
is not complete.

## Cost and verification

New usage accounting: OpenAI 29.69410125 known + 1.9952816 unknown holds =
31.68938285 USD; TypeSafe 5.951424192 USD known. Incremental caps remain 350/20 USD.
No active reservation remains. Historical-inclusive totals are 38.71694205 and
7.77900912600000006 USD, with inherited literals preserved. These are conservative
usage estimates and holds, not verified invoices or provider balances. No paid
Sol, purchase or new subscription was used.

The [final accounting audit](results/study-v7/execution-accounting-v7.0.8.json)
verifies 135,053 journal events, 60,186 unique actual attempts (including four
legacy Sol parameter failures) and 350,716 evidence files. All 5,200 local records
match 16,048 full overlapping windows. Independent numerical audits agree on
primary/sensitivity results, source metrics, all 34 matched comparisons and
separate repeat stability. All 98 offline tests passed; see the private PR for
current delivery CI.

## Frozen records and closure

- [Active pointer](results/study-v7/active-run.json)
- [Final execution manifest](results/study-v7/run-manifest-confirmation-v7.0.8.json),
  SHA d8f76649b18fbfbaa5a548ebc4248839fdceb609ef62b24de705a696213d19b2
- [Credit deferral](results/study-v7/openai-credit-deferral-v7.0.8.json)
- [Collection closure](results/study-v7/collection-closeout.json)
- [Chronological checkpoints](docs/study-v7/EXECUTION-STATUS.md)

The closure stop is unacknowledged by existing owner receipts; the execution
guard has been verified to block further inference. Original stops, attempts and
journal records remain immutable. Further paid inference needs new bounded owner
scope; no balance restoration or provider substitution is authorized. The canonical
v6 checkout, data and results and the older SLM Benchmark workspace were preserved.

Reproduction commands are in the technical handoff. Use the current ignored
request-plan-v7.0.2.json, SHA
70d8606f6a3090514ac08c2c67d27f84d3cf95db18847e08a0f48cc3f4d644da.
Do not rerun prepare.py over historical preparation. Original frozen numerical
artifacts and renders remain; reviewed figures have separate presentation-only
code and an [input/output hash manifest](results/study-v7-execution/reviewed-render-manifest.json).
