# Decision Context Benchmark — extension v3 results

The frozen confirmation is fully attempted. Task context has source- and model-specific effects; neither a universal benefit nor a universal model winner follows. Crucially, some task-versus-candidate gains disappear against an empty task field or a generic reminder. Thus the candidate baseline alone does not establish a benefit from meaningful task information. The tables below report the predeclared paired effects, including negative and inconclusive findings.

What we learned: Astra misses fewer InjecAgent attacks when given the task, but the small direct-harm control subset shows no advantage over reminders or scrambled tasks. Jev has a similar distinction between candidate-baseline gains and control comparisons. Some Luna Decisions and Nimble probability comparisons remain favorable, with broad uncertainty. Laya often worsens on clean-source probability loss. These are useful differences between sources and interfaces, not a single leaderboard result. Better relative performance can still leave many attacks missed: Luna chat misses 103 of 128 valid direct-harm task examples.

The collection contains 761 task/text pairs, 582 distinct texts and 138 task groups. Confirmation contains 11,387 attempts across seven configurations/six model IDs; Luna has two interfaces. The separate 108 control-development requests and 42 local diagnostic calls are not evaluation examples.

Labels inherit published clean/default versus intended-injection construction. They are not independent semantic adjudications, real private production messages, or measured attack success. We generated no benchmark examples or gold labels and invented no missing context. Published source constructions remain explicit.

## Source coverage

| Source | Task/text pairs | Distinct texts | Tasks | Clean / injected |
|---|---:|---:|---:|---:|
| agentdojo-clean-banking | 19 | 5 | 16 | 19 / 0 |
| agentdojo-clean-slack | 23 | 6 | 14 | 23 / 0 |
| agentdojo-clean-travel | 72 | 34 | 20 | 72 / 0 |
| agentdojo-clean-workspace | 39 | 17 | 31 | 39 / 0 |
| agentdyn-dailylife | 184 | 112 | 18 | 33 / 151 |
| agentdyn-github | 13 | 13 | 3 | 5 / 8 |
| agentdyn-shopping | 139 | 124 | 19 | 26 / 113 |
| injecagent-dh | 129 | 129 | 17 | 0 / 129 |
| injecagent-ds | 143 | 143 | 17 | 0 / 143 |

Task groups and texts recur across strata; do not sum columns as independent sample sizes. AgentDojo is clean-only and InjecAgent attack-only. False-positive or false-negative rates are undefined when their denominator class is absent.

## Completed attempts

| Configuration | Planned attempts | Parsed status counts | Reported input / output tokens | Requests with usage |
|---|---:|---|---:|---:|
| jev_firstparty | 1771 | ok: 1759, tie: 12 | 1,216,419 / 38,962 | 1771/1771 |
| luna_decisions | 1771 | ok: 1770, tie: 1 | 956,110 / 0 | 1771/1771 |
| laya_local | 1771 | ok: 1771 | 799,417 / 0 | 1771/1771 |
| nimble_local | 1771 | ok: 1771 | 1,100,296 / 0 | 1771/1771 |
| luna_chat | 1771 | http_error: 3, interrupted_stream: 1, ok: 1767 | 786,149 / 28,278 | 1767/1771 |
| astra_chat | 1771 | http_error: 2, interrupted_stream: 1, ok: 1768 | 786,259 / 40,965 | 1768/1771 |
| protectai_local | 761 | ok: 761 | Not reported | 0/761 |

Token totals above are provider/runtime-reported confirmation usage, not dollar proxies. Missing failure usage is unknown, not zero; tokenizers and interfaces differ. Subscription Astra has zero incremental metered API charge despite its actual calls and token processing. ProtectAI uses overlapping detector windows rather than generated output tokens.

Failures and exact-0.5 abstentions are retained. Native 0.5 forecasts enter proper scoring; Boolean chat outputs have no invented probabilities. Continuations skip failed cells and process only unattempted jobs under the saved runtime amendments.

## Paired authentic-task effects

Each original task receives equal weight within its source. Entries are task minus candidate: **negative favors task context**. Decision error is in percentage points; Brier loss is in squared-probability units. Brackets show conditional 95% crossed-bootstrap intervals (5,000 draws); pair counts are complete/planned. Intervals condition on released fixtures, fixed templates and model versions and are not multiplicity-adjusted discoveries. Zero-width intervals describe observed agreement, not proof of no population effect.

### jev_firstparty

| Source | Error difference [interval]; pairs | Brier difference [interval]; pairs |
|---|---|---|
| agentdojo-clean-banking | +0.00 [+0.00, +0.00]; 19/19 pairs | +0.0048 [+0.0008, +0.0096]; 19/19 pairs |
| agentdojo-clean-slack | +0.00 [+0.00, +0.00]; 23/23 pairs | +0.0016 [-0.0001, +0.0073]; 23/23 pairs |
| agentdojo-clean-travel | +0.00 [+0.00, +0.00]; 72/72 pairs | +0.0005 [+0.0003, +0.0007]; 72/72 pairs |
| agentdojo-clean-workspace | +0.00 [+0.00, +0.00]; 39/39 pairs | +0.0007 [+0.0003, +0.0013]; 39/39 pairs |
| agentdyn-dailylife | +0.00 [+0.00, +0.00]; 184/184 pairs | +0.0010 [-0.0013, +0.0051]; 184/184 pairs |
| agentdyn-github | +0.00 [too few groups]; 13/13 pairs | +0.0031 [too few groups]; 13/13 pairs |
| agentdyn-shopping | +5.92 [+0.00, +16.67]; 138/139 pairs | +0.0218 [+0.0038, +0.0446]; 139/139 pairs |
| injecagent-dh | -6.75 [-20.73, +5.80]; 124/129 pairs | -0.0786 [-0.1483, -0.0135]; 129/129 pairs |
| injecagent-ds | -14.19 [-30.40, +1.03]; 140/143 pairs | -0.0786 [-0.1381, -0.0271]; 143/143 pairs |

### luna_decisions

| Source | Error difference [interval]; pairs | Brier difference [interval]; pairs |
|---|---|---|
| agentdojo-clean-banking | +0.00 [+0.00, +0.00]; 19/19 pairs | +0.0000 [+0.0000, +0.0000]; 19/19 pairs |
| agentdojo-clean-slack | +0.00 [+0.00, +0.00]; 23/23 pairs | +0.0000 [+0.0000, +0.0000]; 23/23 pairs |
| agentdojo-clean-travel | +0.00 [+0.00, +0.00]; 72/72 pairs | +0.0000 [+0.0000, +0.0000]; 72/72 pairs |
| agentdojo-clean-workspace | +0.00 [+0.00, +0.00]; 39/39 pairs | +0.0000 [+0.0000, +0.0000]; 39/39 pairs |
| agentdyn-dailylife | +0.00 [+0.00, +0.00]; 184/184 pairs | -0.0000 [-0.0001, +0.0000]; 184/184 pairs |
| agentdyn-github | +0.00 [too few groups]; 13/13 pairs | +0.0002 [too few groups]; 13/13 pairs |
| agentdyn-shopping | +0.00 [+0.00, +0.00]; 139/139 pairs | +0.0004 [-0.0001, +0.0014]; 139/139 pairs |
| injecagent-dh | -9.86 [-20.98, -2.05]; 129/129 pairs | -0.1391 [-0.2465, -0.0515]; 129/129 pairs |
| injecagent-ds | -41.39 [-57.41, -26.52]; 142/143 pairs | -0.3988 [-0.5252, -0.2846]; 143/143 pairs |

### laya_local

| Source | Error difference [interval]; pairs | Brier difference [interval]; pairs |
|---|---|---|
| agentdojo-clean-banking | +0.00 [+0.00, +0.00]; 19/19 pairs | +0.0308 [-0.0265, +0.3379]; 19/19 pairs |
| agentdojo-clean-slack | -7.14 [-25.00, +0.00]; 23/23 pairs | +0.0774 [-0.1367, +0.2663]; 23/23 pairs |
| agentdojo-clean-travel | -0.67 [-13.33, +10.79]; 72/72 pairs | +0.0967 [+0.0067, +0.1893]; 72/72 pairs |
| agentdojo-clean-workspace | +17.74 [-12.50, +47.37]; 39/39 pairs | +0.1935 [-0.0088, +0.3517]; 39/39 pairs |
| agentdyn-dailylife | +3.21 [-1.67, +11.89]; 184/184 pairs | +0.0216 [-0.0162, +0.0812]; 184/184 pairs |
| agentdyn-github | -16.67 [too few groups]; 13/13 pairs | -0.1098 [too few groups]; 13/13 pairs |
| agentdyn-shopping | +0.00 [+0.00, +0.00]; 139/139 pairs | +0.0003 [-0.0034, +0.0046]; 139/139 pairs |
| injecagent-dh | +4.58 [+0.00, +13.73]; 129/129 pairs | +0.0281 [+0.0011, +0.0864]; 129/129 pairs |
| injecagent-ds | +2.14 [-6.02, +10.50]; 143/143 pairs | +0.0229 [-0.0205, +0.0782]; 143/143 pairs |

### nimble_local

| Source | Error difference [interval]; pairs | Brier difference [interval]; pairs |
|---|---|---|
| agentdojo-clean-banking | +0.00 [+0.00, +0.00]; 19/19 pairs | +0.0009 [+0.0001, +0.0023]; 19/19 pairs |
| agentdojo-clean-slack | +0.00 [+0.00, +0.00]; 23/23 pairs | +0.0026 [-0.0040, +0.0178]; 23/23 pairs |
| agentdojo-clean-travel | +0.00 [+0.00, +0.00]; 72/72 pairs | +0.0002 [-0.0001, +0.0007]; 72/72 pairs |
| agentdojo-clean-workspace | +0.00 [+0.00, +0.00]; 39/39 pairs | +0.0001 [+0.0000, +0.0003]; 39/39 pairs |
| agentdyn-dailylife | -0.46 [-2.78, +0.00]; 184/184 pairs | -0.0539 [-0.1231, -0.0010]; 184/184 pairs |
| agentdyn-github | +0.00 [too few groups]; 13/13 pairs | +0.0037 [too few groups]; 13/13 pairs |
| agentdyn-shopping | +3.12 [-3.95, +11.20]; 139/139 pairs | +0.0063 [-0.0170, +0.0300]; 139/139 pairs |
| injecagent-dh | -19.07 [-35.79, -4.24]; 129/129 pairs | -0.1757 [-0.2823, -0.0819]; 129/129 pairs |
| injecagent-ds | -34.44 [-51.51, -18.00]; 143/143 pairs | -0.2197 [-0.3119, -0.1351]; 143/143 pairs |

### luna_chat

| Source | Error difference [interval]; pairs | Brier difference [interval]; pairs |
|---|---|---|
| agentdojo-clean-banking | +0.00 [+0.00, +0.00]; 19/19 pairs | Not applicable |
| agentdojo-clean-slack | +0.00 [+0.00, +0.00]; 22/23 pairs | Not applicable |
| agentdojo-clean-travel | +0.00 [+0.00, +0.00]; 71/72 pairs | Not applicable |
| agentdojo-clean-workspace | +0.00 [+0.00, +0.00]; 39/39 pairs | Not applicable |
| agentdyn-dailylife | +0.00 [+0.00, +0.00]; 184/184 pairs | Not applicable |
| agentdyn-github | +0.00 [too few groups]; 13/13 pairs | Not applicable |
| agentdyn-shopping | +1.18 [+0.00, +4.89]; 139/139 pairs | Not applicable |
| injecagent-dh | -13.76 [-26.93, -3.35]; 128/129 pairs | Not applicable |
| injecagent-ds | -35.12 [-53.53, -17.26]; 143/143 pairs | Not applicable |

### astra_chat

| Source | Error difference [interval]; pairs | Brier difference [interval]; pairs |
|---|---|---|
| agentdojo-clean-banking | +0.00 [+0.00, +0.00]; 19/19 pairs | Not applicable |
| agentdojo-clean-slack | +0.00 [+0.00, +0.00]; 23/23 pairs | Not applicable |
| agentdojo-clean-travel | +0.00 [+0.00, +0.00]; 72/72 pairs | Not applicable |
| agentdojo-clean-workspace | +0.00 [+0.00, +0.00]; 39/39 pairs | Not applicable |
| agentdyn-dailylife | +0.00 [+0.00, +0.00]; 184/184 pairs | Not applicable |
| agentdyn-github | +0.00 [too few groups]; 12/13 pairs | Not applicable |
| agentdyn-shopping | +0.00 [+0.00, +0.00]; 138/139 pairs | Not applicable |
| injecagent-dh | -21.44 [-37.50, -8.03]; 129/129 pairs | Not applicable |
| injecagent-ds | -6.13 [-17.65, +0.00]; 143/143 pairs | Not applicable |

ProtectAI has candidate-only window-max scores and no task-context contrast. Absolute false-alarm/miss rates, accuracy bounds, native Brier/log losses and reliability-bin denominators remain in [source metrics](analysis/source-metrics.csv) and the per-model JSON files. An improvement can coexist with a high absolute miss rate. The [primary table](analysis/primary-effects.csv) also includes task/text sensitivity, group counts, leave-one-task-out ranges and all-planned missing-response bounds.

## Controls, reliability and interpretation

The 83 pairs for format/reminder/scrambled controls were selected before outcomes. Compare task and each comparator on that same subset. Scrambling preserves words and may preserve partial meaning; these are constructed information interventions on the original scenario, not authentic alternate tasks with newly established labels. See [all control contrasts](analysis/control-effects.csv) and [source-specific interpretation](../../docs/extension-v3/CONTROL-RESULTS.md).

The [paired-effect figure](figures/completed-arm-effects.png) and source-specific reliability grids are generated from saved evidence. Brier improvement does not alone establish calibration; bin averages have no uncertainty bands. Specialist window maxima are scores, not calibrated probabilities. Single-class sources and public-fixture prevalence limit reliability interpretation. No thresholds or calibration parameters were fitted on confirmation outcomes.

## Accounting and limitations

Conservative all-in metered accounting is $0.2896254 OpenAI and $0.154397208 TypeSafe, including prior checks and studies. This is recorded usage/reservation accounting, not a newly verified balance or invoice. Subscription fees and local electricity are excluded. No purchases, recharge or paid-route fallback were used.

The original pilot, completed study and PDF remain historical. Source labels, repeated documents, shared attack templates, few independent tasks in some strata, public-data exposure and possible pretraining contamination limit generalization. The narrow frozen credential-fixture filter misses some published simulated prose/serialized mentions; no post-outcome exclusion or relabeling was applied. No prevention or legitimate-task-completion result is claimed.

Broader research needs remain unmet: this is not a collection of thousands of independent tasks, independently adjudicated benign semantic labels, diverse unseen attack templates, or real production interactions. The GitHub stratum has only three task groups; clean-only and attack-only strata cannot supply both error rates. The preserved sources did not justify filling a larger numerical quota with repetitions or invented context. These limits motivate a separately scoped future collection with additional independent tasks and human-reviewed label semantics, not more calls on these same fixtures.

See the [protocol](../../docs/extension-v3/PROTOCOL-v3.0.md), [related-artifact comparison](../../docs/extension-v3/RESEARCH-COMPARISON.md), [backend audit](../../docs/extension-v3/BACKEND-AUDIT.md), [representative errors and label limits](../../docs/extension-v3/ERROR-REVIEW.md), [reproduction instructions](../../docs/extension-v3/REPRODUCE.md), and [completion audit](../../docs/extension-v3/COMPLETION-STATUS.md), and [prioritized next-run handoff](../../docs/extension-v3/NEXT-RUN.md).
