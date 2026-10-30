# Decision Context Benchmark: full controls v4

The full five-condition experiment is complete. Results below measure agreement with published construction/control labels; independently reviewed semantic labels remain unassigned. Detection is not evidence that an agent would resist an attack.

The main source has 408 matched clean/attack examples from 204 QA tasks and 27 articles. The supplemental source has 17 community-authored synthetic fixtures, including only three benign controls. These sources are reported separately. Neither source establishes broad real-world domain transfer or performance on near-target corruption.

Each contextual configuration received all five conditions on all 425 examples. ProtectAI received candidate-only inputs. There are seven configurations but six model IDs; the two Luna interfaces are not independent model families. Prompts, thresholds and settings were frozen before confirmation.

Central contrasts below are control error minus authentic-task error: positive favors the task. Intervals are pointwise 95% crossed bootstrap intervals, conditional on the released source and fixed broad attack family. QA uses equal article weights; AIB uses equal task weights. Zero or boundary intervals are not proof of population equivalence. Complete/planned paired denominators are shown.

## TaskTracker QA / AdvBench

| Configuration | Task vs reminder (pp), interval; pairs | Task vs empty field (pp), interval; pairs | Task vs scrambled (pp), interval; pairs |
|---|---|---|---|
| Jev 1.14 | +0.87 [0.00, 2.08]; 408/408 | +1.33 [0.00, 2.69]; 408/408 | +0.50 [0.00, 1.44]; 408/408 |
| Luna Decisions | +2.92 [-4.17, 6.88]; 406/408 | +4.48 [-4.17, 9.58]; 407/408 | +4.80 [-3.70, 9.72]; 406/408 |
| Laya | +1.73 [-1.92, 4.53]; 408/408 | -4.08 [-15.22, 0.08]; 408/408 | +1.73 [-1.92, 4.53]; 408/408 |
| Nimble | -1.27 [-5.45, 5.66]; 408/408 | +0.32 [-4.42, 3.96]; 408/408 | -1.60 [-4.76, 2.29]; 408/408 |
| Luna chat | +0.93 [-0.66, 2.84]; 407/408 | +2.81 [0.00, 5.51]; 408/408 | +1.12 [-0.18, 2.78]; 408/408 |
| Astra chat | +0.00 [0.00, 0.00]; 408/408 | +1.62 [0.00, 3.67]; 408/408 | +0.00 [0.00, 0.00]; 408/408 |

Absolute valid-response error rates are per text, not article weighted. Candidate-only and task rates are shown together so improvements are not mistaken for low error.

| Configuration | Candidate FPR / FNR (%) | Task FPR / FNR (%) | Candidate valid / planned | Task valid / planned |
|---|---|---|---|---|
| Jev 1.14 | 0.00 / 3.50 | 0.00 / 0.00 | 404/408 | 408/408 |
| Luna Decisions | 0.00 / 19.80 | 1.47 / 1.97 | 405/408 | 407/408 |
| Laya | 64.22 / 13.73 | 91.67 / 4.90 | 408/408 | 408/408 |
| Nimble | 0.00 / 14.22 | 0.00 / 16.18 | 408/408 | 408/408 |
| Luna chat | 0.00 / 10.78 | 0.00 / 2.45 | 408/408 | 408/408 |
| Astra chat | 0.00 / 3.92 | 0.00 / 0.00 | 408/408 | 408/408 |
| ProtectAI | 0.00 / 76.47 | unsupported | 408/408 | — |

Native probability Brier/log losses, all-planned missingness bounds, error-direction contrasts, equal-task/text sensitivities, token counts and observed transitions are retained in `results/controls-v4/tables/` and the full analysis JSON. No chat probabilities were invented.

## AIB supplemental static fixtures

| Configuration | Task vs reminder (pp), interval; pairs | Task vs empty field (pp), interval; pairs | Task vs scrambled (pp), interval; pairs |
|---|---|---|---|
| Jev 1.14 | +0.00 [-25.00, 25.00]; 17/17 | +5.88 [0.00, 28.57]; 17/17 | +5.88 [0.00, 27.27]; 17/17 |
| Luna Decisions | +0.00 [0.00, 0.00]; 16/17 | +0.00 [0.00, 0.00]; 17/17 | +5.88 [0.00, 27.27]; 17/17 |
| Laya | +0.00 [0.00, 0.00]; 17/17 | +0.00 [0.00, 0.00]; 17/17 | +0.00 [0.00, 0.00]; 17/17 |
| Nimble | +17.65 [0.00, 50.00]; 17/17 | +17.65 [0.00, 50.00]; 17/17 | +17.65 [0.00, 50.00]; 17/17 |
| Luna chat | +0.00 [0.00, 0.00]; 17/17 | +0.00 [0.00, 0.00]; 17/17 | +0.00 [0.00, 0.00]; 17/17 |
| Astra chat | +0.00 [0.00, 0.00]; 17/17 | +0.00 [0.00, 0.00]; 17/17 | +0.00 [0.00, 0.00]; 17/17 |

Absolute valid-response error rates are per text, not article weighted. Candidate-only and task rates are shown together so improvements are not mistaken for low error.

| Configuration | Candidate FPR / FNR (%) | Task FPR / FNR (%) | Candidate valid / planned | Task valid / planned |
|---|---|---|---|---|
| Jev 1.14 | 0.00 / 21.43 | 0.00 / 7.14 | 17/17 | 17/17 |
| Luna Decisions | 0.00 / 7.14 | 0.00 / 0.00 | 17/17 | 17/17 |
| Laya | 100.00 / 0.00 | 100.00 / 0.00 | 17/17 | 17/17 |
| Nimble | 0.00 / 71.43 | 0.00 / 50.00 | 17/17 | 17/17 |
| Luna chat | 0.00 / 7.14 | 0.00 / 7.14 | 17/17 | 17/17 |
| Astra chat | 0.00 / 0.00 | 0.00 / 0.00 | 17/17 | 17/17 |
| ProtectAI | 66.67 / 28.57 | unsupported | 17/17 | — |

Native probability Brier/log losses, all-planned missingness bounds, error-direction contrasts, equal-task/text sensitivities, token counts and observed transitions are retained in `results/controls-v4/tables/` and the full analysis JSON. No chat probabilities were invented.

## Execution and interpretation limits

All 13,547 frozen development and confirmation cells are terminal. Unknown-usage reservations retained: 4. Cumulative conservative accounting, including earlier studies: OpenAI $0.483840 / $15; TypeSafe $0.258775 / $20. These are usage/reservation records, not refreshed account balances or invoices.

Provider errors, truncations, refusals, ties and semantic disagreements remain distinct. Failed confirmation cells were not replaced. Development retained one Decisions 503 and an explicit Ollama runtime update to 0.40.13 with unchanged Nimble weights. The analysis-helper import collision was fixed before any Laya confirmation call. Details and hashes are retained in the amendment/startup receipts.

Scrambling retains lexical clues and can retain meaning; token counts can change. The task-versus-scrambled contrast alone cannot isolate semantics. All prompts contain the same detector definition, so the reminder contrast tests additional reminder wording rather than a completely instruction-free detector.

The main source is dominated by explicit distant-target diversions and ordinary encyclopedia paragraphs. The tiny supplemental source probes legitimate imperatives and authority claims but cannot supply a precise false-alarm estimate. Gold remains source construction status, not independent human semantic adjudication. Examples requiring missing trusted context or unresolved source alignment were quarantined; no post-outcome exclusions were made.

See ERROR-REVIEW.md for exploratory output transitions, counterexamples and source limitations. Those observations do not infer internal reasoning. The next justified data work is an independently reviewed set of authentic task-relative benign instructions and near-target attacks with reliable provenance and held-out document/family groups. Calibration, fine-tuning and end-to-end prevention would be separate experiments.

Independent arithmetic, explicit-multiplicity bootstrap and raw-request/parser/accounting checks passed for every configuration. Final isolated reproduction and repository CI are documented by their own receipts; this report does not replace those delivery checks.
